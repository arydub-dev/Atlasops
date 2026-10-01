"""Scheduled connector sync — enqueue due connections."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.connectors.jobs import recover_stale_syncing_connections
from app.connectors.queue import enqueue_sync_connection
from app.core.database import SessionLocal
from app.integrations import flags
from app.models import Connection, Organization
from app.models.enums import ConnectorStatus, OrgStatus
from app.tenancy.rls import set_session_org

logger = logging.getLogger("supply.connectors.schedule")

_FREQ_RE = re.compile(r"^(\d+)(m|h|d)$", re.I)


def parse_sync_frequency(freq: str | None) -> timedelta | None:
    if not freq:
        return None
    raw = freq.strip().lower()
    if raw in {"hourly", "hour"}:
        return timedelta(hours=1)
    if raw in {"daily", "day"}:
        return timedelta(days=1)
    if raw in {"15m", "every_15m"}:
        return timedelta(minutes=15)
    match = _FREQ_RE.match(raw)
    if not match:
        return None
    n = int(match.group(1))
    unit = match.group(2).lower()
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    return timedelta(days=n)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def schedule_next(connection: Connection) -> datetime | None:
    delta = parse_sync_frequency(connection.sync_frequency)
    if delta is None:
        return None
    return _utcnow() + delta


def _due_connections(db: Session, organization_id, now: datetime) -> list[Connection]:
    """Return due connections for one org (app filter + RLS when on Postgres)."""
    return list(
        db.scalars(
            select(Connection).where(
                Connection.organization_id == organization_id,
                Connection.is_active.is_(True),
                Connection.status != ConnectorStatus.SYNCING,
                Connection.sync_frequency.is_not(None),
                or_(Connection.next_sync_at.is_(None), Connection.next_sync_at <= now),
            )
        ).all()
    )


async def enqueue_due_connector_syncs(ctx: dict | None = None) -> dict:
    """ARQ cron: find due connections and enqueue sync jobs.

    Under PostgreSQL FORCE RLS, ``connections`` is invisible until
    ``app.current_org_id`` is set. Organizations are not RLS-scoped, so we
    iterate active orgs (same pattern as workflow cron), bind the session per
    org, then enqueue due connections for that tenant.
    """
    if not flags.is_enabled("connector_scheduled_sync", default=True):
        return {"enqueued": 0, "skipped": "flag_off"}

    db: Session = SessionLocal()
    enqueued = 0
    orgs_scanned = 0
    try:
        now = _utcnow()
        orgs = db.scalars(
            select(Organization).where(
                Organization.status.in_([OrgStatus.ACTIVE, OrgStatus.TRIALING])
            )
        ).all()
        for org in orgs:
            orgs_scanned += 1
            try:
                set_session_org(db, org.id)
                recover_stale_syncing_connections(db, org.id, now=now)
                for conn in _due_connections(db, org.id, now):
                    try:
                        await enqueue_sync_connection(
                            connection_id=conn.id,
                            organization_id=conn.organization_id,
                            mode="incremental",
                        )
                        conn.next_sync_at = schedule_next(conn)
                        enqueued += 1
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "schedule_enqueue_failed connection=%s org=%s",
                            conn.id,
                            org.id,
                        )
                # Flush while this tenant's RLS context is still active.
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
                logger.exception("schedule_org_scan_failed org=%s", org.id)
    finally:
        db.close()
    return {"enqueued": enqueued, "orgs_scanned": orgs_scanned}
