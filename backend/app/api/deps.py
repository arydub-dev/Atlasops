"""Shared FastAPI dependencies: session/API-token auth and tenant context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import hash_token
from app.core.database import get_db
from app.identity.orgs import build_tenant_context
from app.identity.sessions import resolve_session
from app.models import ApiToken, Membership, Organization, User
from app.models.enums import MembershipStatus, OrgStatus
from app.rbac.enforce import has_permission, require_permission
from app.tenancy.context import TenantContext, set_tenant
from app.tenancy.rls import set_session_org

__all__ = [
    "RequestContext",
    "ensure_request_context",
    "get_current_user",
    "get_current_user_optional_org",
    "get_db_with_tenant",
    "get_request_context",
    "has_permission",
    "require_permission",
    "require_platform_admin",
]

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)


@dataclass(slots=True)
class RequestContext:
    user: User
    org: Organization
    membership: Membership
    tenant: TenantContext
    session_id: UUID | None = None
    auth_via: str = "session"  # session | api_token


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _request_id(request: Request) -> str:
    return (
        request.headers.get("X-Request-Id")
        or request.headers.get("X-Request-ID")
        or getattr(request.state, "request_id", "")
        or ""
    )


def _parse_org_id(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(str(raw).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Organization-Id",
        ) from exc


def _load_active_org(db: Session, org_id: UUID, *, billing_recovery: bool = False) -> Organization:
    org = db.get(Organization, org_id)
    if (
        org is None
        or org.deleted_at is not None
        or org.status == OrgStatus.DELETED
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    if org.status == OrgStatus.SUSPENDED and not billing_recovery:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization suspended")
    return org


def _load_active_membership(db: Session, org_id: UUID, user_id: UUID) -> Membership:
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    return membership


def _persist_auth_activity(db: Session) -> None:
    """Commit sliding-session / idle-revoke / token last_used mutations.

    Auth runs inside the request-scoped session. Most GET handlers never
    ``commit()``, so without this helper ``last_seen_at`` and idle revokes
    are rolled back when the session closes.
    """
    try:
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        raise


def _auth_via_session(request: Request, db: Session) -> tuple[User, UUID | None, UUID | None]:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    row = resolve_session(db, raw)
    if row is None:
        # Persist idle-timeout revoke if resolve_session marked the row.
        if db.dirty or db.new or db.deleted:
            _persist_auth_activity(db)
        raise _CREDENTIALS_ERROR
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user, row.organization_id, row.id


def _auth_via_api_token(request: Request, db: Session, bearer: str) -> tuple[User, UUID, None]:
    token_hash = hash_token(bearer)
    token = db.scalar(select(ApiToken).where(ApiToken.token_hash == token_hash))
    if token is None:
        bind = db.get_bind()
        dialect = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect == "postgresql":
            try:
                row = db.execute(
                    text(
                        "SELECT id, organization_id, created_by_user_id, scopes, expires_at, revoked_at "
                        "FROM app_lookup_api_token_by_hash(:h)"
                    ),
                    {"h": token_hash},
                ).mappings().first()
                if row:
                    set_session_org(db, row["organization_id"])
                    token = db.scalar(select(ApiToken).where(ApiToken.token_hash == token_hash))
            except Exception:
                token = None

    if token is None or token.revoked_at is not None:
        raise _CREDENTIALS_ERROR
    if token.expires_at is not None and (token.expires_at.replace(tzinfo=timezone.utc) if token.expires_at.tzinfo is None else token.expires_at) <= _utcnow():
        raise _CREDENTIALS_ERROR

    set_session_org(db, token.organization_id)
    user = db.get(User, token.created_by_user_id) if token.created_by_user_id else None
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    token.last_used_at = _utcnow()
    return user, token.organization_id, None


def ensure_request_context(
    request: Request,
    db: Session,
    x_organization_id: str | None = None,
) -> RequestContext:
    """Authenticate and bind tenant context (idempotent per request via request.state)."""
    cached = getattr(request.state, "supply_ctx", None)
    if cached is not None:
        return cached

    auth_header = request.headers.get("Authorization") or ""
    bearer = ""
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()

    session_id: UUID | None = None
    auth_via = "session"
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if cookie:
        user, session_org_id, session_id = _auth_via_session(request, db)
        token_org_id = None
    elif bearer:
        user, token_org_id, session_id = _auth_via_api_token(request, db, bearer)
        session_org_id = token_org_id
        auth_via = "api_token"
    else:
        raise _CREDENTIALS_ERROR

    header_org = _parse_org_id(x_organization_id or request.headers.get("X-Organization-Id"))
    org_id = header_org or session_org_id
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization selected. Pass X-Organization-Id or switch org.",
        )

    # API tokens are organization-scoped credentials. Reject cross-org header overrides
    # even when the creating user is a member of multiple organizations.
    if auth_via == "api_token" and token_org_id is not None and org_id != token_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API token is bound to a different organization",
        )

    billing_recovery = request.url.path.startswith(("/api/v1/billing/", "/v1/billing/"))
    org = _load_active_org(db, org_id, billing_recovery=billing_recovery)
    membership = _load_active_membership(db, org.id, user.id)
    tenant = build_tenant_context(
        org=org,
        user=user,
        membership=membership,
        request_id=_request_id(request),
    )

    # API tokens never inherit platform-admin bypass. Scopes further restrict.
    if auth_via == "api_token" and bearer:
        token = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(bearer)))
        if token is not None:
            if token.scopes:
                scoped = frozenset(str(s) for s in token.scopes) & tenant.permissions
            else:
                # Empty scopes = creator role perms only (already on tenant), never platform admin.
                scoped = tenant.permissions
            tenant = TenantContext(
                organization_id=tenant.organization_id,
                user_id=tenant.user_id,
                membership_id=tenant.membership_id,
                permissions=scoped,
                role_slug=tenant.role_slug,
                request_id=tenant.request_id,
                is_platform_admin=False,
            )

    set_tenant(tenant)
    try:
        set_session_org(db, org.id)
    except Exception as exc:
        # SQLite / non-Postgres: RLS GUC unavailable; app-level filters still apply.
        # On PostgreSQL, failing to set the GUC is a Critical isolation risk — refuse.
        bind = db.get_bind()
        dialect = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect == "postgresql":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to establish tenant database context",
            ) from exc

    ctx = RequestContext(
        user=user,
        org=org,
        membership=membership,
        tenant=tenant,
        session_id=session_id,
        auth_via=auth_via,
    )
    request.state.supply_ctx = ctx
    # Persist sliding expiry / last_seen / API token last_used immediately.
    _persist_auth_activity(db)
    return ctx


async def get_request_context(
    request: Request,
    db: Session = Depends(get_db),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> RequestContext:
    """Authenticate and bind tenant ContextVar on the event-loop context.

    Sync FastAPI dependencies run in a worker thread; ContextVars set there are
    discarded when the thread returns. Re-binding here ensures ``get_tenant()``
    is visible to sync endpoints (anyio copies the async context into the
    endpoint worker thread).
    """
    from starlette.concurrency import run_in_threadpool

    ctx = await run_in_threadpool(ensure_request_context, request, db, x_organization_id)
    set_tenant(ctx.tenant)
    return ctx


def get_current_user(ctx: RequestContext = Depends(get_request_context)) -> User:
    return ctx.user


async def get_db_with_tenant(
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
) -> Session:
    """DB session with tenant context + RLS GUC already applied.

    Re-binds the Postgres tenant GUC on the *current* transaction. Auth may
    have committed (clearing SET LOCAL); ``after_begin`` also restores from
    ``session.info``, and this explicit call covers the active transaction
    before the endpoint runs.
    """
    set_tenant(ctx.tenant)
    try:
        set_session_org(db, ctx.org.id)
    except Exception as exc:
        bind = db.get_bind()
        dialect = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect == "postgresql":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to establish tenant database context",
            ) from exc
    return db


def get_current_user_optional_org(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via session or API token without requiring an organization.

    Used for flows like accepting invitations before the user has an org context.
    """
    auth_header = request.headers.get("Authorization") or ""
    bearer = ""
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if cookie:
        user, _session_org_id, _session_id = _auth_via_session(request, db)
        _persist_auth_activity(db)
        return user
    if bearer:
        user, _token_org_id, _ = _auth_via_api_token(request, db, bearer)
        _persist_auth_activity(db)
        return user
    raise _CREDENTIALS_ERROR


def require_platform_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Session-only ATLASOPS operator gate.

    API tokens never inherit ``is_platform_admin`` (even if the creating user
    is an operator). Tenant GUC is intentionally **not** set here so FORCE RLS
    hides customer tables until a handler binds a specific organization.
    """
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user, _session_org_id, _session_id = _auth_via_session(request, db)
    _persist_auth_activity(db)
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required",
        )
    return user
