"""Authorization enforcement helpers."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.tenancy.context import TenantContext, get_tenant_or_none, set_tenant


def has_permission(ctx: TenantContext, permission: str) -> bool:
    if ctx.is_platform_admin:
        return True
    return permission in ctx.permissions


async def get_tenant_dep(
    request: Request,
    db: Session = Depends(get_db),
) -> TenantContext:
    """Ensure request auth ran, then return the tenant contextvar.

    Tenant ContextVar is bound on the event loop (not only inside a worker
    thread) so sync route handlers can call ``get_tenant()`` safely.
    """
    existing = get_tenant_or_none()
    if existing is not None:
        return existing
    # Lazy import avoids circular import with app.api.deps at module load.
    from starlette.concurrency import run_in_threadpool

    from app.api.deps import ensure_request_context

    ctx = await run_in_threadpool(ensure_request_context, request, db)
    set_tenant(ctx.tenant)
    return ctx.tenant


def require_permission(permission: str):
    """FastAPI dependency factory."""

    async def _dep(ctx: TenantContext = Depends(get_tenant_dep), db: Session = Depends(get_db)) -> TenantContext:
        if not has_permission(ctx, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        if not permission.startswith("org."):
            from app.billing.enforce import enforce_subscription_access
            enforce_subscription_access(db, ctx.organization_id)
        plan_feature = {
            "org.tokens.manage": "api_tokens",
            "org.webhooks.manage": "webhooks",
            "org.audit.read": "audit_log",
            "ai.chat": "ai_chat",
            "ai.reports": "ai_reports",
        }.get(permission)
        if plan_feature:
            from app.billing.enforce import enforce_feature
            enforce_feature(db, ctx.organization_id, plan_feature)
        # Re-bind in case another dependency path cleared or skipped set_tenant.
        set_tenant(ctx)
        return ctx

    return _dep
