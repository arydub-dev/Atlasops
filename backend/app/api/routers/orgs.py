"""Organization administration API."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    RequestContext,
    get_current_user_optional_org,
    get_db_with_tenant,
    get_request_context,
    require_permission,
)
from app.core.config import settings
from app.core.crypto import encrypt_str, generate_token
from app.core.database import get_db
from app.identity.orgs import (
    create_organization,
    invite_member,
    soft_delete_organization,
    transfer_ownership,
    usage_snapshot,
)
from app.identity.sessions import list_org_sessions, resolve_session, revoke_session
from app.models import (
    ApiToken,
    AuditLog,
    Membership,
    Organization,
    Session as SessionModel,
    User,
    WebhookEndpoint,
)
from app.models.enums import MembershipStatus
from app.tenancy.rls import set_session_org
from pydantic import BaseModel
from app.schemas.auth import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenOut,
    AuthSettingsOut,
    AuthSettingsUpdate,
    InvitationCreate,
    InvitationCreated,
    InvitationOut,
    InvitationPreview,
    LoginHistoryItem,
    MemberOut,
    MemberUpdate,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    SessionOut,
    TransferOwnershipRequest,
    WebhookCreate,
    WebhookOut,
    WebhookUpdate,
)
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/orgs", tags=["Organizations"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    # FORCE RLS on audit_logs requires the tenant GUC for this org.
    set_session_org(db, org_id)
    db.add(
        AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_id=getattr(getattr(request, "state", None), "request_id", None) if request else None,
        )
    )


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_org(
    payload: OrganizationCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> Organization:
    """Create an organization for the signed-in user (session cookie required)."""
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")

    org, _membership = create_organization(db, name=payload.name, owner=user)
    row.organization_id = org.id
    _audit(
        db,
        org_id=org.id,
        user_id=user.id,
        action="create",
        resource="organization",
        resource_id=str(org.id),
        detail=org.name,
        request=request,
    )
    db.commit()
    db.refresh(org)
    return org


@router.get("", response_model=list[OrganizationOut])
def list_my_orgs(
    request: Request,
    db: Session = Depends(get_db),
) -> list[Organization]:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    memberships = db.scalars(
        select(Membership).where(
            Membership.user_id == row.user_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    if not memberships:
        return []
    org_ids = [m.organization_id for m in memberships]
    return list(
        db.scalars(
            select(Organization)
            .where(Organization.id.in_(org_ids), Organization.deleted_at.is_(None))
            .order_by(Organization.name)
        ).all()
    )


@router.get("/current", response_model=OrganizationOut)
def get_current_org(ctx: RequestContext = Depends(get_request_context)) -> Organization:
    return ctx.org


@router.patch("/current", response_model=OrganizationOut)
def update_current_org(
    payload: OrganizationUpdate,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.update")),
    req_ctx: RequestContext = Depends(get_request_context),
) -> Organization:
    org = req_ctx.org
    if payload.name is not None:
        org.name = payload.name
    if payload.settings is not None:
        # Domain / IdP binding keys must go through /security/settings (validated).
        # Outbound URLs must pass SSRF checks before persistence.
        from app.core.outbound_url import assert_safe_outbound_url
        from app.connectors.ssrf import SSRFError

        privileged = {
            "allowed_email_domains",
            "allowed_domains",
            "primary_email_domain",
            "workos_organization_id",
        }
        merged = dict(org.settings or {})
        incoming = dict(payload.settings)
        for key in privileged:
            incoming.pop(key, None)
        for url_key in ("slack_webhook_url", "teams_webhook_url"):
            if url_key in incoming and incoming[url_key]:
                try:
                    incoming[url_key] = assert_safe_outbound_url(
                        str(incoming[url_key]),
                        field=url_key,
                        require_known_chat_host=True,
                    )
                except SSRFError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
        merged.update(incoming)
        org.settings = merged
    if payload.branding is not None:
        branding = dict(payload.branding)
        branding.pop("email_domain", None)
        org.branding = branding
    _audit(
        db,
        org_id=org.id,
        user_id=ctx.user_id,
        action="update",
        resource="organization",
        resource_id=str(org.id),
        request=request,
    )
    db.commit()
    db.refresh(org)
    return org


@router.post("/current/invitations", response_model=InvitationCreated, status_code=201)
def create_invitation(
    payload: InvitationCreate,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.invite")),
) -> InvitationCreated:
    from app.billing.enforce import enforce_seat_limit

    try:
        enforce_seat_limit(db, ctx.organization_id, additional=1)
        inv = invite_member(
            db,
            organization_id=ctx.organization_id,
            email=payload.email,
            role_slug=payload.role_slug,
            invited_by=ctx.user_id,
            inviter_role_slug=ctx.role_slug,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="invite",
        resource="invitation",
        resource_id=str(inv.id),
        detail=payload.email,
        request=request,
    )
    db.commit()
    db.refresh(inv)
    invite_url = f"{settings.FRONTEND_URL.rstrip('/')}/invite/{inv.token}"
    return InvitationCreated(
        id=inv.id,
        email=inv.email,
        role_slug=inv.role_slug,
        status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
        expires_at=inv.expires_at,
        created_at=inv.created_at,
        token=inv.token,
        invite_url=invite_url,
    )


class AcceptInvitationBody(BaseModel):
    token: str


@router.get("/invitations/preview", response_model=InvitationPreview)
def preview_invitation(
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> InvitationPreview:
    """Public preview for invitation deep links (no auth required)."""
    from app.models import Invitation

    inv = db.scalar(select(Invitation).where(Invitation.token == token))
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    org = db.get(Organization, inv.organization_id)
    return InvitationPreview(
        email=inv.email,
        organization_name=org.name if org else "Organization",
        role_slug=inv.role_slug,
        expires_at=inv.expires_at,
        status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
    )


@router.post("/invitations/accept", response_model=MemberOut)
def accept_invitation_http(
    payload: AcceptInvitationBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional_org),
) -> MemberOut:
    """Accept an invitation for the signed-in user (email must match)."""
    from app.billing.enforce import enforce_seat_limit
    from app.identity.orgs import accept_invitation
    from app.models import Invitation
    from app.models.enums import InvitationStatus

    try:
        inv = db.scalar(select(Invitation).where(Invitation.token == payload.token))
        if inv and inv.status == InvitationStatus.PENDING:
            enforce_seat_limit(db, inv.organization_id, additional=1)
        membership = accept_invitation(db, token=payload.token, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _audit(
        db,
        org_id=membership.organization_id,
        user_id=user.id,
        action="accept_invitation",
        resource="invitation",
        resource_id=str(membership.id),
        request=request,
    )
    db.commit()
    return MemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=user.email,
        full_name=user.full_name,
        role_slug=membership.role_slug,
        status=membership.status.value,
        created_at=membership.created_at,
    )


@router.get("/current/members", response_model=list[MemberOut])
def list_members(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.read")),
) -> list[MemberOut]:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == ctx.organization_id,
            Membership.status != MembershipStatus.REMOVED,
        )
        .order_by(Membership.created_at.asc())
    ).all()
    return [
        MemberOut(
            id=m.id,
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role_slug=m.role_slug,
            status=m.status.value,
            created_at=m.created_at,
        )
        for m, u in rows
    ]


@router.patch("/current/members/{member_id}", response_model=MemberOut)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.manage")),
) -> MemberOut:
    membership = db.get(Membership, member_id)
    if membership is None or membership.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if membership.role_slug == "owner" and payload.role_slug and payload.role_slug != "owner":
        raise HTTPException(status_code=400, detail="Use transfer-ownership to change owner role")

    if payload.role_slug is not None:
        if payload.role_slug == "owner":
            raise HTTPException(
                status_code=400,
                detail="Use transfer-ownership to grant the owner role",
            )
        membership.role_slug = payload.role_slug
    if payload.status is not None:
        status_val = payload.status.lower()
        if status_val == "suspended":
            membership.status = MembershipStatus.SUSPENDED
            membership.suspended_at = _utcnow()
            membership.suspended_reason = payload.suspended_reason
        elif status_val == "active":
            membership.status = MembershipStatus.ACTIVE
            membership.suspended_at = None
            membership.suspended_reason = None
        else:
            raise HTTPException(status_code=400, detail="status must be active or suspended")

    user = db.get(User, membership.user_id)
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="update_member",
        resource="membership",
        resource_id=str(membership.id),
        request=request,
    )
    db.commit()
    return MemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=user.email if user else "",
        full_name=user.full_name if user else "",
        role_slug=membership.role_slug,
        status=membership.status.value,
        created_at=membership.created_at,
    )


@router.delete("/current/members/{member_id}", status_code=204, response_class=Response)
def remove_member(
    member_id: UUID,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.manage")),
) -> Response:
    membership = db.get(Membership, member_id)
    if membership is None or membership.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if membership.role_slug == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    membership.status = MembershipStatus.REMOVED
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="remove_member",
        resource="membership",
        resource_id=str(membership.id),
        request=request,
    )
    db.commit()
    return Response(status_code=204)


@router.post("/current/transfer-ownership", response_model=OrganizationOut)
def transfer_org_ownership(
    payload: TransferOwnershipRequest,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.transfer_ownership")),
    req_ctx: RequestContext = Depends(get_request_context),
) -> Organization:
    new_owner = db.get(User, payload.new_owner_user_id)
    if new_owner is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        transfer_ownership(db, req_ctx.org, new_owner)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="transfer_ownership",
        resource="organization",
        resource_id=str(req_ctx.org.id),
        detail=str(new_owner.id),
        request=request,
    )
    db.commit()
    db.refresh(req_ctx.org)
    return req_ctx.org


@router.delete("/current", response_model=dict)
def delete_current_org(
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.delete")),
    req_ctx: RequestContext = Depends(get_request_context),
) -> dict:
    soft_delete_organization(db, req_ctx.org)
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="soft_delete",
        resource="organization",
        resource_id=str(req_ctx.org.id),
        request=request,
    )
    db.commit()
    return {"ok": True, "deleted_at": req_ctx.org.deleted_at.isoformat() if req_ctx.org.deleted_at else None}


@router.get("/current/audit-logs", response_model=list[dict])
def list_audit_logs(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.audit.read")),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == ctx.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "action": r.action,
            "resource": r.resource,
            "resource_id": r.resource_id,
            "detail": r.detail,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/current/security/settings", response_model=AuthSettingsOut)
def get_auth_settings(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.read")),
) -> AuthSettingsOut:
    org = db.get(Organization, ctx.organization_id)
    assert org is not None
    settings_dict = org.settings or {}
    allowed = settings_dict.get("allowed_email_domains") or settings_dict.get("allowed_domains") or []
    if isinstance(allowed, str):
        allowed = [allowed]
    return AuthSettingsOut(
        allowed_email_domains=[str(d).lower().strip() for d in allowed if d],
        workos_organization_id=org.workos_organization_id,
        sso_configured=bool(org.workos_organization_id),
        mfa_required=bool(settings_dict.get("mfa_required", False)),
    )


@router.patch("/current/security/settings", response_model=AuthSettingsOut)
def update_auth_settings(
    payload: AuthSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.update")),
) -> AuthSettingsOut:
    org = db.get(Organization, ctx.organization_id)
    assert org is not None
    settings_dict = dict(org.settings or {})
    if payload.allowed_email_domains is not None:
        cleaned = sorted(
            {
                d.lower().strip().lstrip("@")
                for d in payload.allowed_email_domains
                if d and "." in d.lower().strip()
            }
        )
        settings_dict["allowed_email_domains"] = cleaned
        if cleaned:
            settings_dict["primary_email_domain"] = cleaned[0]
        org.settings = settings_dict
        _audit(
            db,
            org_id=org.id,
            user_id=ctx.user_id,
            action="update_auth_settings",
            resource="auth",
            detail=",".join(cleaned),
            request=request,
        )
        db.commit()
        db.refresh(org)
    return get_auth_settings(db, ctx)


@router.get("/current/security/sessions", response_model=list[SessionOut])
def list_org_active_sessions(
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.manage")),
) -> list[SessionOut]:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    current = resolve_session(db, raw)
    rows = list_org_sessions(db, ctx.organization_id)
    user_ids = {r.user_id for r in rows}
    users = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    } if user_ids else {}
    return [
        SessionOut(
            id=r.id,
            device_label=r.device_label,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            device_trusted=r.device_trusted,
            is_current=bool(current and r.id == current.id),
            created_at=r.created_at,
            last_seen_at=r.last_seen_at,
            expires_at=r.expires_at,
            organization_id=r.organization_id,
            user_id=r.user_id,
            user_email=users[r.user_id].email if r.user_id in users else None,
        )
        for r in rows
    ]


@router.delete("/current/security/sessions/{session_id}")
def admin_revoke_session(
    session_id: UUID,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.manage")),
) -> dict:
    target = db.get(SessionModel, session_id)
    if target is None or target.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if target.revoked_at is None:
        revoke_session(db, target)
        _audit(
            db,
            org_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="admin_revoke_session",
            resource="auth",
            resource_id=str(session_id),
            request=request,
        )
        db.commit()
    return {"ok": True}


@router.get("/current/security/login-history", response_model=list[LoginHistoryItem])
def login_history(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.audit.read")),
    limit: int = Query(100, ge=1, le=500),
) -> list[LoginHistoryItem]:
    rows = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == ctx.organization_id,
            AuditLog.resource == "auth",
            AuditLog.action.in_(
                [
                    "login",
                    "logout",
                    "logout_all",
                    "dev_login",
                    "revoke_session",
                    "admin_revoke_session",
                    "accept_invitation",
                    "switch_org",
                ]
            ),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    user_ids = {r.user_id for r in rows if r.user_id}
    users = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    } if user_ids else {}
    return [
        LoginHistoryItem(
            id=r.id,
            user_id=r.user_id,
            user_email=users[r.user_id].email if r.user_id and r.user_id in users else None,
            action=r.action,
            detail=r.detail,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/current/usage", response_model=dict)
def get_usage(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.usage.read")),
) -> dict:
    return usage_snapshot(db, ctx.organization_id)


# --------------------------------------------------------------------------- #
# API tokens
# --------------------------------------------------------------------------- #
@router.get("/current/tokens", response_model=list[ApiTokenOut])
def list_tokens(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.tokens.manage")),
) -> list[ApiToken]:
    return list(
        db.scalars(
            select(ApiToken)
            .where(ApiToken.organization_id == ctx.organization_id)
            .order_by(ApiToken.created_at.desc())
        ).all()
    )


@router.post("/current/tokens", response_model=ApiTokenCreated, status_code=201)
def create_token(
    payload: ApiTokenCreate,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.tokens.manage")),
) -> ApiTokenCreated:
    full, prefix, token_hash = generate_token()
    row = ApiToken(
        organization_id=ctx.organization_id,
        name=payload.name,
        token_prefix=prefix,
        token_hash=token_hash,
        scopes=payload.scopes or [],
        created_by_user_id=ctx.user_id,
        expires_at=payload.expires_at,
    )
    db.add(row)
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="create_token",
        resource="api_token",
        detail=payload.name,
        request=request,
    )
    db.commit()
    db.refresh(row)
    return ApiTokenCreated(
        id=row.id,
        name=row.name,
        token_prefix=row.token_prefix,
        scopes=row.scopes,
        last_used_at=row.last_used_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        token=full,
    )


@router.delete("/current/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def revoke_token(
    token_id: UUID,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.tokens.manage")),
) -> Response:
    row = db.get(ApiToken, token_id)
    if row is None or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Token not found")
    row.revoked_at = _utcnow()
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="revoke_token",
        resource="api_token",
        resource_id=str(row.id),
        request=request,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# Webhooks
# --------------------------------------------------------------------------- #
@router.get("/current/webhooks", response_model=list[WebhookOut])
def list_webhooks(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.webhooks.manage")),
) -> list[WebhookEndpoint]:
    return list(
        db.scalars(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.organization_id == ctx.organization_id)
            .order_by(WebhookEndpoint.created_at.desc())
        ).all()
    )


@router.post("/current/webhooks", response_model=WebhookOut, status_code=201)
def create_webhook(
    payload: WebhookCreate,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.webhooks.manage")),
) -> WebhookEndpoint:
    import secrets

    from app.connectors.ssrf import SSRFError
    from app.core.outbound_url import assert_safe_outbound_url

    try:
        safe_url = assert_safe_outbound_url(payload.url, field="url")
    except SSRFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    secret = payload.secret or secrets.token_urlsafe(24)
    row = WebhookEndpoint(
        organization_id=ctx.organization_id,
        url=safe_url,
        secret_encrypted=encrypt_str(secret),
        events=payload.events or [],
        is_active=True,
    )
    db.add(row)
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="create_webhook",
        resource="webhook",
        detail=payload.url,
        request=request,
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/current/webhooks/{webhook_id}", response_model=WebhookOut)
def update_webhook(
    webhook_id: UUID,
    payload: WebhookUpdate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.webhooks.manage")),
) -> WebhookEndpoint:
    row = db.get(WebhookEndpoint, webhook_id)
    if row is None or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if payload.url is not None:
        from app.connectors.ssrf import SSRFError
        from app.core.outbound_url import assert_safe_outbound_url

        try:
            row.url = assert_safe_outbound_url(payload.url, field="url")
        except SSRFError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.events is not None:
        row.events = payload.events
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.secret is not None:
        row.secret_encrypted = encrypt_str(payload.secret)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/current/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_webhook(
    webhook_id: UUID,
    request: Request,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.webhooks.manage")),
) -> Response:
    row = db.get(WebhookEndpoint, webhook_id)
    if row is None or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(row)
    _audit(
        db,
        org_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="delete_webhook",
        resource="webhook",
        resource_id=str(webhook_id),
        request=request,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
