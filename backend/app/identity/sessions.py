"""Server-side session management (httpOnly cookie)."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.crypto import hash_token
from app.identity.device import device_label_from_ua
from app.models import Session, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def create_session(
    db: DBSession,
    *,
    user: User,
    organization_id: UUID | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_trusted: bool = False,
    device_label: str | None = None,
) -> tuple[Session, str]:
    """Create a session row and return (session, raw_token for cookie)."""
    active = db.scalars(
        select(Session).where(
            Session.user_id == user.id,
            Session.revoked_at.is_(None),
            Session.expires_at > _utcnow(),
        )
    ).all()
    if len(active) >= settings.MAX_CONCURRENT_SESSIONS:
        oldest = sorted(active, key=lambda s: s.last_seen_at)[0]
        oldest.revoked_at = _utcnow()

    ttl_hours = (
        settings.SESSION_REMEMBER_TTL_HOURS if device_trusted else settings.SESSION_TTL_HOURS
    )
    raw = secrets.token_urlsafe(48)
    row = Session(
        user_id=user.id,
        organization_id=organization_id,
        token_hash=hash_token(raw),
        ip_address=ip_address,
        user_agent=user_agent,
        device_label=device_label or device_label_from_ua(user_agent),
        device_trusted=device_trusted,
        expires_at=_utcnow() + timedelta(hours=ttl_hours),
    )
    db.add(row)
    db.flush()
    return row, raw


def resolve_session(db: DBSession, raw_token: str | None) -> Session | None:
    if not raw_token:
        return None
    row = db.scalar(select(Session).where(Session.token_hash == hash_token(raw_token)))
    if row is None or row.revoked_at is not None:
        return None

    now = _utcnow()
    expires = _aware(row.expires_at)
    if expires <= now:
        return None

    last_seen = _aware(row.last_seen_at)
    idle_minutes = settings.SESSION_IDLE_MINUTES
    # Remembered devices get a longer idle window (2x) but still expire.
    if row.device_trusted:
        idle_minutes = max(idle_minutes, settings.SESSION_IDLE_MINUTES * 2)
    if idle_minutes > 0 and last_seen + timedelta(minutes=idle_minutes) <= now:
        row.revoked_at = now
        return None

    row.last_seen_at = now
    # Sliding expiration: extend absolute expiry while actively used.
    if settings.SESSION_SLIDING_ENABLED:
        ttl_hours = (
            settings.SESSION_REMEMBER_TTL_HOURS
            if row.device_trusted
            else settings.SESSION_TTL_HOURS
        )
        row.expires_at = now + timedelta(hours=ttl_hours)
    return row


def revoke_session(db: DBSession, session: Session) -> None:
    session.revoked_at = _utcnow()


def revoke_all_user_sessions(
    db: DBSession,
    user_id: UUID,
    *,
    except_session_id: UUID | None = None,
) -> int:
    rows = db.scalars(
        select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    ).all()
    now = _utcnow()
    count = 0
    for row in rows:
        if except_session_id and row.id == except_session_id:
            continue
        row.revoked_at = now
        count += 1
    return count


def list_user_sessions(db: DBSession, user_id: UUID) -> list[Session]:
    return list(
        db.scalars(
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
                Session.expires_at > _utcnow(),
            )
            .order_by(Session.last_seen_at.desc())
        ).all()
    )


def list_org_sessions(db: DBSession, organization_id: UUID) -> list[Session]:
    return list(
        db.scalars(
            select(Session)
            .where(
                Session.organization_id == organization_id,
                Session.revoked_at.is_(None),
                Session.expires_at > _utcnow(),
            )
            .order_by(Session.last_seen_at.desc())
        ).all()
    )


def cookie_max_age_seconds(*, remember_device: bool) -> int:
    hours = (
        settings.SESSION_REMEMBER_TTL_HOURS if remember_device else settings.SESSION_TTL_HOURS
    )
    return hours * 3600
