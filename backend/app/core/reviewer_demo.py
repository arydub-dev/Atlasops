"""Fail-closed boundary for a synchronous, isolated reviewer deployment."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

# Only locally verified synchronous surfaces. No connector writes, external
# transactions, subscriptions, invitations, scheduling, or administrative access.
READ_SURFACES = {"mission-control", "dashboard", "inventory", "shipments", "suppliers", "orders", "graph", "network", "analytics", "risks", "priorities", "data"}
WRITE_SURFACES = {"recovery", "incidents"}
AUTH_PATHS = {"auth/me", "auth/logout", "auth/logout-all", "auth/sessions"}


def restrict_reviewer_demo(request: Request, db: Session = Depends(get_db)):
    if not settings.REVIEWER_DEMO_ONLY:
        return
    from app.api.deps import ensure_request_context
    from app.identity.demo_access import allowed
    path = request.url.path
    for prefix in ("/api/v1/", "/v1/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if path == "auth/demo-login" and request.method == "POST":
        return  # Existing credential verification and Redis rate limit still apply.
    ctx = ensure_request_context(request, db)
    if not allowed(db, ctx.user.id, ctx.tenant.organization_id):
        raise HTTPException(403, "This deployment is restricted to the synthetic reviewer workspace")
    surface = path.split("/", 1)[0]
    permitted = (path in AUTH_PATHS or path.startswith("auth/sessions/")
                 or surface in WRITE_SURFACES
                 or (request.method in {"GET", "HEAD"} and surface in READ_SURFACES)
                 or path.startswith("data/import/"))
    if not permitted:
        raise HTTPException(403, "This operation is unavailable in the reviewer demonstration")
