"""Authentication endpoints — email-first WorkOS + opaque session cookies."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_request_context
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit_auth
from app.identity import workos as workos_client
from app.identity.device import device_label_from_ua
from app.identity.discovery import discover_organization
from app.identity.oauth_state import consume_login_state, create_login_state, safe_return_path
from app.identity.orgs import accept_invitation, create_organization, get_membership
from app.identity.sessions import (
    cookie_max_age_seconds,
    create_session,
    list_user_sessions,
    resolve_session,
    revoke_all_user_sessions,
    revoke_session,
)
from app.identity.workos import WorkOSNotConfigured
from app.models import AuditLog, Membership, Organization, Session as SessionModel, User
from app.models.enums import MembershipStatus, OrgStatus
from app.schemas.auth import (
    ContinueLoginRequest,
    ContinueLoginResponse,
    DevLoginRequest,
    LoginRedirectResponse,
    MeResponse,
    MembershipOut,
    OrganizationOut,
    SessionOut,
    SwitchOrgRequest,
    UserOut,
)
from app.tenancy.rls import set_session_org

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str | None:
    if settings.TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For") or ""
        if forwarded:
            return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


def _set_session_cookie(
    response: Response,
    raw_token: str,
    *,
    remember_device: bool = False,
) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE or settings.is_production,
        samesite="lax",
        max_age=cookie_max_age_seconds(remember_device=remember_device),
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE or settings.is_production,
        httponly=True,
    )


def _membership_out(m: Membership, org: Organization | None = None) -> MembershipOut:
    return MembershipOut(
        id=m.id,
        organization_id=m.organization_id,
        user_id=m.user_id,
        role_slug=m.role_slug,
        status=m.status.value if hasattr(m.status, "value") else str(m.status),
        organization_name=org.name if org else None,
        organization_slug=org.slug if org else None,
    )


def _audit_auth(
    db: Session,
    *,
    organization_id: UUID | None,
    user_id: UUID | None,
    action: str,
    detail: str | None,
    request: Request,
    resource_id: str | None = None,
) -> None:
    if organization_id is None:
        return
    # FORCE RLS on audit_logs requires the tenant GUC on this transaction.
    set_session_org(db, organization_id)
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            resource="auth",
            resource_id=resource_id,
            detail=detail,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )


def _upsert_workos_user(db: Session, profile: dict) -> User:
    email = (profile.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Identity provider profile missing email")

    workos_user_id = profile.get("workos_user_id")
    user = None
    if workos_user_id:
        user = db.scalar(select(User).where(User.workos_user_id == workos_user_id))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))

    full_name = (
        f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        or email.split("@")[0]
    )
    now = _utcnow()
    if user is None:
        user = User(
            workos_user_id=workos_user_id,
            email=email,
            full_name=full_name,
            avatar_url=profile.get("profile_picture_url"),
            email_verified_at=now if profile.get("email_verified") else None,
            last_login_at=now,
        )
        db.add(user)
    else:
        user.workos_user_id = workos_user_id or user.workos_user_id
        user.full_name = full_name or user.full_name
        if profile.get("profile_picture_url"):
            user.avatar_url = profile["profile_picture_url"]
        if profile.get("email_verified") and user.email_verified_at is None:
            user.email_verified_at = now
        user.last_login_at = now
        user.is_active = True
    db.flush()
    return user


def _bind_workos_org(
    db: Session,
    *,
    workos_org_id: str | None,
    domain: str | None,
) -> Organization | None:
    if not workos_org_id:
        return None
    org = db.scalar(
        select(Organization).where(Organization.workos_organization_id == workos_org_id)
    )
    if org is None and domain:
        from app.identity.discovery import find_local_org_for_domain

        org = find_local_org_for_domain(db, domain)
        if org and not org.workos_organization_id:
            org.workos_organization_id = workos_org_id
            settings_dict = dict(org.settings or {})
            settings_dict["primary_email_domain"] = domain
            org.settings = settings_dict
            db.flush()
    return org


@router.post("/continue", response_model=ContinueLoginResponse)
def continue_login(
    payload: ContinueLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_auth),
) -> ContinueLoginResponse:
    """Email-first entry: discover org/IdP via WorkOS and return redirect URL."""
    if not settings.workos_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enterprise sign-in is not configured. Use local development sign-in.",
        )

    try:
        discovery = discover_organization(
            db,
            email=str(payload.email),
            invite_token=payload.invite_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return_path = safe_return_path(payload.return_path)
    _row, state, challenge = create_login_state(
        db,
        email=discovery.email,
        domain=discovery.domain,
        workos_organization_id=discovery.workos_organization_id,
        invite_token=discovery.invite_token,
        remember_device=payload.remember_device,
        return_path=return_path,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    try:
        url = workos_client.get_authorization_url(
            organization_id=discovery.workos_organization_id,
            login_hint=discovery.email,
            domain_hint=discovery.domain,
            state=state,
            code_challenge=challenge,
        )
    except WorkOSNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.commit()
    if discovery.mode == "sso":
        message = "Redirecting to your organization's identity provider…"
    else:
        message = "Checking your organization…"
    return ContinueLoginResponse(
        authorization_url=url,
        mode=discovery.mode,
        domain=discovery.domain,
        message=message,
    )


@router.get("/login", response_model=LoginRedirectResponse)
def login(
    request: Request,
    provider: str = Query("authkit"),
    organization_id: str | None = Query(None),
    login_hint: str | None = None,
    remember_device: bool = False,
    invite_token: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_auth),
) -> LoginRedirectResponse:
    """Legacy redirect helper. Prefer POST /auth/continue (email-first)."""
    email = (login_hint or "").strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""
    workos_org = organization_id
    if email and not workos_org:
        try:
            discovery = discover_organization(db, email=email, invite_token=invite_token)
            workos_org = discovery.workos_organization_id
            domain = discovery.domain
            invite_token = discovery.invite_token
        except ValueError:
            pass

    _row, state, challenge = create_login_state(
        db,
        email=email or "unknown@unknown",
        domain=domain or "unknown",
        workos_organization_id=workos_org,
        invite_token=invite_token,
        remember_device=remember_device,
        return_path="/auth/callback",
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    try:
        url = workos_client.get_authorization_url(
            provider=provider if not workos_org else "authkit",
            organization_id=workos_org,
            login_hint=login_hint,
            domain_hint=domain or None,
            state=state,
            code_challenge=challenge,
        )
    except WorkOSNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.commit()
    mode = "sso" if workos_org else "authkit"
    return LoginRedirectResponse(
        authorization_url=url,
        provider="authkit" if workos_org else provider,
        mode=mode,
        message="Redirecting to your identity provider…",
    )


@router.get("/callback")
def callback(
    request: Request,
    code: str = Query(...),
    state: str | None = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_auth),
):
    login_state = consume_login_state(db, state)
    if login_state is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired sign-in state. Please try again.",
        )

    try:
        profile = workos_client.authenticate_with_code(
            code,
            code_verifier=login_state.code_verifier,
        )
    except WorkOSNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Authentication failed") from exc

    user = _upsert_workos_user(db, profile)

    # Prefer WorkOS-linked org, then invite, then oldest membership.
    workos_org_id = profile.get("organization_id") or login_state.workos_organization_id
    bound = _bind_workos_org(db, workos_org_id=workos_org_id, domain=login_state.domain)
    org_id: UUID | None = bound.id if bound else None

    if login_state.invite_token:
        try:
            membership = accept_invitation(db, token=login_state.invite_token, user=user)
            org_id = membership.organization_id
            _audit_auth(
                db,
                organization_id=org_id,
                user_id=user.id,
                action="accept_invitation",
                detail=user.email,
                request=request,
                resource_id=str(membership.id),
            )
        except ValueError:
            # Invite may already be accepted or mismatched — continue login.
            pass

    if org_id is None:
        membership = db.scalar(
            select(Membership)
            .where(
                Membership.user_id == user.id,
                Membership.status == MembershipStatus.ACTIVE,
            )
            .order_by(Membership.created_at.asc())
        )
        org_id = membership.organization_id if membership else None

    ua = request.headers.get("user-agent")
    session, raw = create_session(
        db,
        user=user,
        organization_id=org_id,
        ip_address=_client_ip(request),
        user_agent=ua,
        device_trusted=login_state.remember_device,
        device_label=device_label_from_ua(ua),
    )
    _audit_auth(
        db,
        organization_id=org_id,
        user_id=user.id,
        action="login",
        detail=user.email,
        request=request,
        resource_id=str(session.id),
    )
    # Also record login when user has no org yet — use a synthetic audit skip;
    # platform-level events without org are omitted by design (tenant audit).
    db.commit()

    qs = urlencode(
        {
            "status": "ok",
            **({"invite": "1"} if login_state.invite_token else {}),
        }
    )
    path = safe_return_path(login_state.return_path)
    if path == "/auth/callback":
        redirect_url = f"{settings.FRONTEND_URL}{path}?{qs}"
    else:
        redirect_url = f"{settings.FRONTEND_URL}{path}"

    redirect = RedirectResponse(url=redirect_url, status_code=302)
    _set_session_cookie(redirect, raw, remember_device=login_state.remember_device)
    return redirect


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row:
        _audit_auth(
            db,
            organization_id=row.organization_id,
            user_id=row.user_id,
            action="logout",
            detail=None,
            request=request,
            resource_id=str(row.id),
        )
        revoke_session(db, row)
        db.commit()
    _clear_session_cookie(response)
    return {"ok": True}


@router.post("/logout-all")
def logout_all(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    count = revoke_all_user_sessions(db, row.user_id)
    _audit_auth(
        db,
        organization_id=row.organization_id,
        user_id=row.user_id,
        action="logout_all",
        detail=f"revoked={count}",
        request=request,
    )
    db.commit()
    _clear_session_cookie(response)
    return {"ok": True, "revoked": count}


@router.get("/sessions", response_model=list[SessionOut])
def my_sessions(
    request: Request,
    db: Session = Depends(get_db),
) -> list[SessionOut]:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    current = resolve_session(db, raw)
    if current is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    rows = list_user_sessions(db, current.user_id)
    return [
        SessionOut(
            id=r.id,
            device_label=r.device_label,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            device_trusted=r.device_trusted,
            is_current=r.id == current.id,
            created_at=r.created_at,
            last_seen_at=r.last_seen_at,
            expires_at=r.expires_at,
            organization_id=r.organization_id,
            user_id=r.user_id,
        )
        for r in rows
    ]


@router.delete("/sessions/{session_id}")
def revoke_my_session(
    session_id: UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    current = resolve_session(db, raw)
    if current is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    target = db.get(SessionModel, session_id)
    if target is None or target.user_id != current.user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if target.revoked_at is None:
        revoke_session(db, target)
        _audit_auth(
            db,
            organization_id=current.organization_id,
            user_id=current.user_id,
            action="revoke_session",
            detail=str(session_id),
            request=request,
            resource_id=str(session_id),
        )
        db.commit()
    if target.id == current.id:
        _clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(
    request: Request,
    db: Session = Depends(get_db),
) -> MeResponse:
    """Return the signed-in user, memberships, and current org (if resolved)."""
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row is None:
        auth = request.headers.get("Authorization") or ""
        if not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        ctx = ensure_request_context(request, db)
        user = ctx.user
        session_org_id = ctx.org.id
    else:
        user = db.get(User, row.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Not authenticated")
        session_org_id = row.organization_id
        # Persist sliding / last_seen updates
        db.commit()

    memberships = db.scalars(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.INVITED]),
        )
    ).all()
    org_ids = [m.organization_id for m in memberships]
    orgs = {
        o.id: o
        for o in db.scalars(
            select(Organization).where(
                Organization.id.in_(org_ids),
                Organization.deleted_at.is_(None),
            )
        ).all()
    } if org_ids else {}

    membership_outs = [_membership_out(m, orgs.get(m.organization_id)) for m in memberships]

    current_org = None
    current_membership = None
    header_org = request.headers.get("X-Organization-Id")
    chosen: UUID | None = None
    if header_org:
        try:
            chosen = UUID(header_org)
        except ValueError:
            chosen = None
    chosen = chosen or session_org_id
    if chosen and chosen in orgs:
        current_org = OrganizationOut.model_validate(orgs[chosen])
        m = next((x for x in memberships if x.organization_id == chosen), None)
        if m:
            current_membership = _membership_out(m, orgs[chosen])

    return MeResponse(
        user=UserOut.model_validate(user),
        memberships=membership_outs,
        current_organization=current_org,
        current_membership=current_membership,
    )


@router.post("/switch-org", response_model=MeResponse)
def switch_org(
    payload: SwitchOrgRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MeResponse:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")

    membership = get_membership(db, payload.organization_id, user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    org = db.get(Organization, payload.organization_id)
    if org is None or org.deleted_at is not None or org.status == OrgStatus.DELETED:
        raise HTTPException(status_code=404, detail="Organization not found")

    row.organization_id = org.id
    _audit_auth(
        db,
        organization_id=org.id,
        user_id=user.id,
        action="switch_org",
        detail=str(org.id),
        request=request,
    )
    db.commit()
    return me(request, db)


@router.post("/dev-login", response_model=MeResponse)
def dev_login(
    payload: DevLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_auth),
) -> MeResponse:
    """Local-only auth bypass. Never available outside ENVIRONMENT=development."""
    if settings.ENVIRONMENT.lower() != "development":
        raise HTTPException(status_code=404, detail="Not found")
    if settings.workos_configured:
        raise HTTPException(status_code=404, detail="Not found")

    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=payload.full_name or email.split("@")[0])
        db.add(user)
        db.flush()
        org, _membership = create_organization(db, name=f"{user.full_name}'s Org", owner=user)
        org_id = org.id
    else:
        user.full_name = payload.full_name or user.full_name
        user.last_login_at = _utcnow()
        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        if membership is None:
            org, membership = create_organization(db, name=f"{user.full_name}'s Org", owner=user)
            org_id = org.id
        else:
            org_id = membership.organization_id

    ua = request.headers.get("user-agent")
    _session, raw_token = create_session(
        db,
        user=user,
        organization_id=org_id,
        ip_address=_client_ip(request),
        user_agent=ua,
        device_label=device_label_from_ua(ua),
    )
    _audit_auth(
        db,
        organization_id=org_id,
        user_id=user.id,
        action="dev_login",
        detail=user.email,
        request=request,
    )
    db.commit()
    _set_session_cookie(response, raw_token, remember_device=False)
    request._cookies = {  # type: ignore[attr-defined]
        **(getattr(request, "_cookies", {}) or {}),
        settings.SESSION_COOKIE_NAME: raw_token,
    }
    user = db.get(User, user.id)
    memberships = db.scalars(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    orgs = {
        o.id: o
        for o in db.scalars(
            select(Organization).where(Organization.id.in_([m.organization_id for m in memberships]))
        ).all()
    }
    org = orgs.get(org_id)
    m = next((x for x in memberships if x.organization_id == org_id), None)
    return MeResponse(
        user=UserOut.model_validate(user),
        memberships=[_membership_out(x, orgs.get(x.organization_id)) for x in memberships],
        current_organization=OrganizationOut.model_validate(org) if org else None,
        current_membership=_membership_out(m, org) if m and org else None,
    )

