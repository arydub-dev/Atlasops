"""Shared append-only audit log helper with optional integrity chaining."""
from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def _chain_hash(prev: str | None, payload: str) -> str:
    base = f"{prev or ''}|{payload}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def write_audit(
    db: Session,
    *,
    organization_id: UUID,
    user_id: UUID | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    """Insert an immutable audit row (application never updates audit_logs)."""
    prev = db.scalar(
        select(AuditLog.integrity_hash)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    ip = None
    ua = None
    request_id = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        request_id = request.headers.get("X-Request-Id") or getattr(
            request.state, "request_id", None
        )

    payload = "|".join(
        [
            str(organization_id),
            str(user_id or ""),
            action,
            resource,
            resource_id or "",
            detail or "",
        ]
    )
    row = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip,
        user_agent=ua,
        request_id=request_id,
        integrity_hash=_chain_hash(prev, payload),
    )
    db.add(row)
    db.flush()
    return row
