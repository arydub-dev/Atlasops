"""Security Center aggregations and emergency controls."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ApiToken, AuditLog, Membership, Session as UserSession
from app.models.enums import MembershipStatus
from app.services import audit


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def security_overview(db: Session, org_id: UUID) -> dict[str, Any]:
    since = _utcnow() - timedelta(days=14)
    sessions = db.scalars(
        select(UserSession)
        .where(
            UserSession.organization_id == org_id,
            UserSession.revoked_at.is_(None),
        )
        .order_by(UserSession.last_seen_at.desc())
        .limit(25)
    ).all()
    # Login history is often stored as audit events
    login_events = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == org_id,
            AuditLog.action.in_(["auth.login", "auth.login_failed", "auth.logout", "session.create"]),
            AuditLog.created_at >= since,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(40)
    ).all()
    failed = [e for e in login_events if "fail" in e.action]
    tokens = db.scalars(select(ApiToken).where(ApiToken.organization_id == org_id)).all()
    active_tokens = [t for t in tokens if t.revoked_at is None]
    perm_changes = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == org_id,
            AuditLog.action.in_(
                [
                    "member.role_updated",
                    "member.removed",
                    "token.created",
                    "token.revoked",
                    "security.settings_updated",
                ]
            ),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(20)
    ).all()
    connector_activity = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == org_id,
            AuditLog.resource.in_(["connection", "connector", "data_source"]),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(15)
    ).all()

    recommendations: list[str] = []
    if failed:
        recommendations.append("Review failed login attempts and force password reset if patterned")
    if len(active_tokens) > 10:
        recommendations.append("Rotate unused API tokens and tighten scopes")
    stale = [
        s
        for s in sessions
        if s.last_seen_at and s.last_seen_at.replace(tzinfo=timezone.utc) < _utcnow() - timedelta(days=30)
    ]
    if stale:
        recommendations.append(f"Revoke {len(stale)} stale sessions older than 30 days")
    if not recommendations:
        recommendations.append("Security posture looks healthy — keep MFA enforced for admins")

    return {
        "sessions": [
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
                "user_agent": s.user_agent,
                "ip_address": s.ip_address,
                "device_label": s.device_label,
            }
            for s in sessions
        ],
        "recent_logins": [_audit_out(e) for e in login_events if "fail" not in e.action][:15],
        "failed_logins": [_audit_out(e) for e in failed][:15],
        "api_tokens": {
            "total": len(tokens),
            "active": len(active_tokens),
            "items": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                    "revoked": t.revoked_at is not None,
                }
                for t in tokens[:20]
            ],
        },
        "permission_changes": [_audit_out(e) for e in perm_changes],
        "connector_activity": [_audit_out(e) for e in connector_activity],
        "recommendations": recommendations,
        "member_count": db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == org_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        or 0,
    }


def revoke_all_sessions(
    db: Session, org_id: UUID, *, actor_user_id: UUID, except_session_id: UUID | None = None
) -> int:
    rows = db.scalars(
        select(UserSession).where(
            UserSession.organization_id == org_id,
            UserSession.revoked_at.is_(None),
        )
    ).all()
    count = 0
    now = _utcnow()
    for s in rows:
        if except_session_id and s.id == except_session_id:
            continue
        s.revoked_at = now
        db.add(s)
        count += 1
    audit.write_audit(
        db,
        organization_id=org_id,
        user_id=actor_user_id,
        action="security.emergency_session_revoke",
        resource="session",
        detail=f"revoked={count}",
    )
    db.commit()
    return count


def rotate_api_token(
    db: Session, org_id: UUID, token_id: UUID, *, actor_user_id: UUID
) -> ApiToken | None:
    token = db.get(ApiToken, token_id)
    if token is None or token.organization_id != org_id:
        return None
    token.revoked_at = _utcnow()
    db.add(token)
    audit.write_audit(
        db,
        organization_id=org_id,
        user_id=actor_user_id,
        action="token.revoked",
        resource="api_token",
        resource_id=str(token_id),
        detail="rotation",
    )
    db.commit()
    return token


def emergency_lockout(db: Session, org_id: UUID, *, actor_user_id: UUID) -> dict[str, Any]:
    """Revoke all sessions and API tokens for the organization."""
    revoked_sessions = revoke_all_sessions(db, org_id, actor_user_id=actor_user_id)
    tokens = db.scalars(
        select(ApiToken).where(ApiToken.organization_id == org_id, ApiToken.revoked_at.is_(None))
    ).all()
    now = _utcnow()
    for t in tokens:
        t.revoked_at = now
        db.add(t)
    audit.write_audit(
        db,
        organization_id=org_id,
        user_id=actor_user_id,
        action="security.emergency_lockout",
        resource="organization",
        detail=f"sessions={revoked_sessions};tokens={len(tokens)}",
    )
    db.commit()
    return {"sessions_revoked": revoked_sessions, "tokens_revoked": len(tokens)}


def _audit_out(e: AuditLog) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "action": e.action,
        "resource": e.resource,
        "user_id": str(e.user_id) if e.user_id else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "detail": e.detail,
    }
