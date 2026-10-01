"""Internal operator console — cross-tenant operational metadata.

Privileged access model (do not weaken):

* Caller must already be a session-authenticated ``User.is_platform_admin``.
* Identity tables (``organizations``, ``memberships``, ``users``) have no RLS
  and are queried directly — same pattern as connector cron scheduling.
* Tenant-owned tables remain under FORCE RLS. Handlers call
  ``set_session_org`` for **one organization at a time** and always filter
  ``organization_id`` in application SQL. The app role is never granted
  BYPASSRLS and RLS is never disabled.
* Responses omit credentials, encrypted blobs, connector config, and tokens.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AuditLog,
    Connection,
    ConnectorDeadLetter,
    ConnectorSyncLog,
    ImportJob,
    Membership,
    Organization,
    User,
)
from app.models.enums import (
    ConnectorHealth,
    ConnectorStatus,
    ImportStatus,
    MembershipStatus,
    OrgStatus,
)
from app.services.audit import write_audit
from app.tenancy.rls import set_session_org

logger = logging.getLogger("supply.platform_console")

MAX_ORGS = 200
STALE_SYNC_HOURS = 2
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|bearer|sk_live_|sk_test_|whsec_|private_key)\S{0,40}"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def sanitize_error(text: str | None, *, limit: int = 280) -> str | None:
    """Return an operator-safe error snippet with credential-like tokens stripped."""
    if not text:
        return None
    cleaned = _SECRET_RE.sub("[redacted]", str(text))
    cleaned = cleaned.replace("\x00", "")
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1] + "…"
    return cleaned


def classify_failure(text: str | None) -> str:
    blob = (text or "").lower()
    if any(k in blob for k in ("429", "rate limit", "too many requests", "throttl")):
        return "rate_limiting"
    if any(
        k in blob
        for k in (
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "invalid_grant",
            "authentication",
            "expired token",
            "invalid client",
        )
    ):
        return "authentication_failure"
    if any(
        k in blob
        for k in ("timeout", "timed out", "connection refused", "dns", "ssl", "502", "503", "504", "network")
    ):
        return "api_network_failure"
    if any(k in blob for k in ("redis", "arq", "enqueue", "signature", "worker")):
        return "worker_failure"
    if any(
        k in blob
        for k in ("validation", "schema", "mapping", "rejected", "parse", "invalid filename")
    ):
        return "data_validation_failure"
    if blob:
        return "unknown_failure"
    return "none"


def connector_display_status(conn: Connection, *, now: datetime | None = None) -> str:
    now = now or _utcnow()
    if not conn.is_active:
        return "disabled"
    if conn.status == ConnectorStatus.SYNCING:
        return "syncing"
    if conn.status == ConnectorStatus.NOT_CONFIGURED:
        return "not_configured"
    if conn.status == ConnectorStatus.ERROR or conn.health == ConnectorHealth.DOWN:
        return "failed"
    stale = False
    if conn.last_sync_at:
        last = conn.last_sync_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        stale = (now - last) > timedelta(hours=STALE_SYNC_HOURS)
    if conn.health == ConnectorHealth.DEGRADED or conn.last_error or stale:
        return "warning"
    if conn.health == ConnectorHealth.HEALTHY and conn.last_sync_at:
        return "healthy"
    if conn.status == ConnectorStatus.CONNECTED:
        return "connected"
    return "unknown"


def tenant_health_status(
    *,
    org: Organization,
    failed_jobs: int,
    connector_states: list[str],
) -> str:
    if org.deleted_at is not None or org.status in {OrgStatus.DELETED, OrgStatus.SUSPENDED}:
        return "critical"
    if any(s == "failed" for s in connector_states):
        return "critical"
    if failed_jobs > 0 or any(s in {"warning", "syncing"} for s in connector_states):
        return "warning"
    if not connector_states:
        return "unknown"
    return "healthy"


def _bind_org(db: Session, org_id: UUID) -> None:
    set_session_org(db, org_id)


def iter_active_orgs(db: Session) -> Iterator[Organization]:
    orgs = db.scalars(
        select(Organization)
        .where(Organization.deleted_at.is_(None), Organization.status != OrgStatus.DELETED)
        .order_by(Organization.created_at.desc())
        .limit(MAX_ORGS)
    ).all()
    yield from orgs


def _membership_counts(db: Session) -> dict[UUID, int]:
    rows = db.execute(
        select(Membership.organization_id, func.count(Membership.id)).where(
            Membership.status == MembershipStatus.ACTIVE
        ).group_by(Membership.organization_id)
    ).all()
    return {org_id: int(n) for org_id, n in rows}


def _check_postgres(db: Session) -> dict[str, Any]:
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        return {"name": "postgres", "state": "healthy", "detail": "SELECT 1 succeeded"}
    except Exception:  # noqa: BLE001
        logger.exception("platform_console_postgres_check_failed")
        return {"name": "postgres", "state": "critical", "detail": "Database query failed"}


def _check_redis() -> dict[str, Any]:
    if settings.CONNECTOR_SYNC_INLINE:
        return {
            "name": "redis",
            "state": "warning",
            "detail": "CONNECTOR_SYNC_INLINE=true; Redis not required for local sync",
        }
    if not settings.REDIS_URL:
        return {"name": "redis", "state": "critical", "detail": "REDIS_URL is not configured"}
    try:
        from app.core.startup_checks import ping_redis

        ping_redis(settings.REDIS_URL)
        return {"name": "redis", "state": "healthy", "detail": "PING succeeded"}
    except Exception:  # noqa: BLE001
        logger.info("platform_console_redis_check_failed", exc_info=True)
        return {"name": "redis", "state": "critical", "detail": "Redis PING failed"}


def _arq_worker_stats() -> dict[str, Any]:
    """Inspect ARQ Redis keys. Missing heartbeat is Critical, never pretended Healthy."""
    empty = {
        "state": "unknown",
        "detail": "Worker heartbeat not observed",
        "active_workers": 0,
        "queued_jobs": 0,
        "running_jobs": 0,
        "failed_jobs_heartbeat": None,
        "completed_jobs_heartbeat": None,
        "heartbeat_at": None,
        "heartbeat_raw": None,
        "queue_known": False,
    }
    if settings.CONNECTOR_SYNC_INLINE:
        return {
            **empty,
            "state": "warning",
            "detail": "Jobs run inline in the API process; dedicated ARQ workers are not used",
        }
    if not settings.REDIS_URL:
        return {**empty, "state": "critical", "detail": "REDIS_URL is not configured"}
    try:
        from redis import Redis
        from arq.constants import default_queue_name, health_check_key_suffix, in_progress_key_prefix

        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.8,
            socket_timeout=0.8,
            decode_responses=True,
        )
        try:
            queued = int(client.zcard(default_queue_name) or 0)
            running = 0
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=f"{in_progress_key_prefix}*", count=100)
                running += len(keys)
                if cursor == 0:
                    break
                if running > 10_000:
                    break
            health_key = default_queue_name + health_check_key_suffix
            raw = client.get(health_key)
            ttl = client.pttl(health_key)
        finally:
            client.close()
    except Exception:  # noqa: BLE001
        logger.info("platform_console_arq_inspect_failed", exc_info=True)
        return {**empty, "state": "unknown", "detail": "Unable to inspect Redis/ARQ"}

    parsed: dict[str, Any] = {}
    if raw:
        # Example: "Aug-16 12:00:00 j_complete=12 j_failed=1 j_retried=0 j_ongoing=2 queued=4"
        for token in str(raw).split():
            if "=" in token:
                k, _, v = token.partition("=")
                parsed[k] = v

    if not raw:
        state = "critical"
        detail = "Worker heartbeat not observed"
    else:
        state = "healthy"
        detail = "ARQ health-check key present"
        if ttl is not None and 0 <= ttl < 5_000:
            state = "warning"
            detail = "ARQ health-check key is near expiry"

    return {
        "state": state,
        "detail": detail,
        "active_workers": 1 if raw else 0,
        "queued_jobs": queued,
        "running_jobs": running,
        "failed_jobs_heartbeat": _maybe_int(parsed.get("j_failed")),
        "completed_jobs_heartbeat": _maybe_int(parsed.get("j_complete")),
        "retried_jobs_heartbeat": _maybe_int(parsed.get("j_retried")),
        "heartbeat_at": _parse_arq_heartbeat_at(raw) if raw else None,
        "heartbeat_raw": str(raw)[:240] if raw else None,
        "health_key_ttl_ms": ttl if isinstance(ttl, int) and ttl >= 0 else None,
        "queue_known": True,
    }


def _parse_arq_heartbeat_at(raw: str) -> str | None:
    """Parse the leading ``Mon-DD HH:MM:SS`` token from an ARQ health-check value."""
    token = str(raw).split()[0:2]
    if len(token) < 2:
        return None
    stamp = f"{token[0]} {token[1]}"
    now = _utcnow()
    for year in (now.year, now.year - 1):
        try:
            parsed = datetime.strptime(f"{year} {stamp}", "%Y %b-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            return _iso(parsed)
        except ValueError:
            continue
    return None


def _maybe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _config_state(configured: bool, *, name: str, missing: str) -> dict[str, Any]:
    if configured:
        return {"name": name, "state": "healthy", "detail": "Configured"}
    return {"name": name, "state": "warning", "detail": missing}


def collect_system_health(db: Session) -> dict[str, Any]:
    postgres = _check_postgres(db)
    redis = _check_redis()
    workers = _arq_worker_stats()
    workos = _config_state(
        settings.workos_configured,
        name="workos",
        missing="WORKOS_API_KEY / WORKOS_CLIENT_ID not set",
    )
    stripe = _config_state(
        settings.stripe_configured,
        name="stripe",
        missing="STRIPE_SECRET_KEY not set",
    )
    sentry = _config_state(
        bool(settings.SENTRY_DSN),
        name="sentry",
        missing="SENTRY_DSN not set",
    )
    api = {"name": "api", "state": "healthy", "detail": f"process up ({settings.ENVIRONMENT})"}

    components = [api, postgres, redis, {**workers, "name": "workers"}, workos, stripe, sentry]
    ranks = {"critical": 3, "warning": 2, "unknown": 1, "healthy": 0}
    overall = max((c.get("state") or "unknown" for c in components), key=lambda s: ranks.get(s, 1))
    return {
        "overall": overall,
        "checked_at": _iso(_utcnow()),
        "environment": settings.ENVIRONMENT,
        "inline_sync": settings.CONNECTOR_SYNC_INLINE,
        "components": components,
        "workers": workers,
    }


def _org_operational_snapshot(db: Session, org: Organization, *, now: datetime) -> dict[str, Any]:
    _bind_org(db, org.id)
    connections = list(
        db.scalars(select(Connection).where(Connection.organization_id == org.id)).all()
    )
    states = [connector_display_status(c, now=now) for c in connections]
    last_sync = max((c.last_sync_at for c in connections if c.last_sync_at), default=None)
    failed_jobs = int(
        db.scalar(
            select(func.count(ImportJob.id)).where(
                ImportJob.organization_id == org.id,
                ImportJob.status == ImportStatus.FAILED,
            )
        )
        or 0
    )
    failed_syncs = int(
        db.scalar(
            select(func.count(ConnectorSyncLog.id)).where(
                ConnectorSyncLog.organization_id == org.id,
                ConnectorSyncLog.status.in_(("failed", "error")),
            )
        )
        or 0
    )
    last_activity = db.scalar(
        select(func.max(AuditLog.created_at)).where(AuditLog.organization_id == org.id)
    )
    open_dlq = int(
        db.scalar(
            select(func.count(ConnectorDeadLetter.id)).where(
                ConnectorDeadLetter.organization_id == org.id,
                ConnectorDeadLetter.resolved_at.is_(None),
            )
        )
        or 0
    )
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "status": org.status.value if hasattr(org.status, "value") else str(org.status),
        "health": tenant_health_status(
            org=org,
            failed_jobs=failed_jobs + failed_syncs,
            connector_states=states,
        ),
        "user_count": 0,  # filled by caller
        "connector_count": len(connections),
        "last_successful_sync_at": _iso(last_sync),
        "failed_jobs": failed_jobs + failed_syncs,
        "open_dead_letters": open_dlq,
        "last_activity_at": _iso(last_activity or org.updated_at),
        "created_at": _iso(org.created_at),
        "plan": org.plan.value if hasattr(org.plan, "value") else str(org.plan),
    }


def list_tenants(db: Session) -> dict[str, Any]:
    now = _utcnow()
    counts = _membership_counts(db)
    items = []
    for org in iter_active_orgs(db):
        row = _org_operational_snapshot(db, org, now=now)
        row["user_count"] = counts.get(org.id, 0)
        items.append(row)
    warning = sum(1 for i in items if i["health"] == "warning")
    critical = sum(1 for i in items if i["health"] == "critical")
    return {
        "checked_at": _iso(now),
        "counts": {
            "tenants": len(items),
            "warning": warning,
            "critical": critical,
        },
        "items": items,
    }


def _connection_out(conn: Connection, *, retry_count: int, last_attempt: datetime | None) -> dict[str, Any]:
    return {
        "id": str(conn.id),
        "organization_id": str(conn.organization_id),
        "name": conn.name,
        "connector_type": conn.connector_type.value
        if hasattr(conn.connector_type, "value")
        else str(conn.connector_type),
        "status": connector_display_status(conn),
        "lifecycle_status": conn.status.value if hasattr(conn.status, "value") else str(conn.status),
        "health": conn.health.value if hasattr(conn.health, "value") else str(conn.health),
        "last_successful_sync_at": _iso(conn.last_sync_at),
        "last_attempted_sync_at": _iso(last_attempt or conn.last_sync_at),
        "next_sync_at": _iso(conn.next_sync_at),
        "last_error": sanitize_error(conn.last_error),
        "failure_class": classify_failure(conn.last_error),
        "retry_count": retry_count,
        "is_active": conn.is_active,
        "current_job_status": conn.status.value if hasattr(conn.status, "value") else str(conn.status),
    }


def _retry_count_for(db: Session, org_id: UUID, connection_id: UUID) -> tuple[int, datetime | None]:
    logs = list(
        db.scalars(
            select(ConnectorSyncLog)
            .where(
                ConnectorSyncLog.organization_id == org_id,
                ConnectorSyncLog.connection_id == connection_id,
            )
            .order_by(ConnectorSyncLog.created_at.desc())
            .limit(25)
        ).all()
    )
    last_attempt = logs[0].created_at if logs else None
    retries = sum(1 for log in logs if log.status in {"failed", "error"})
    return retries, last_attempt


def get_tenant(db: Session, tenant_id: UUID, *, admin_user: User, request=None) -> dict[str, Any]:
    org = db.get(Organization, tenant_id)
    if org is None or org.deleted_at is not None:
        return None  # type: ignore[return-value]
    now = _utcnow()
    counts = _membership_counts(db)
    overview = _org_operational_snapshot(db, org, now=now)
    overview["user_count"] = counts.get(org.id, 0)
    _bind_org(db, org.id)

    connections = list(
        db.scalars(select(Connection).where(Connection.organization_id == org.id)).all()
    )
    connector_rows = []
    for conn in connections:
        retries, last_attempt = _retry_count_for(db, org.id, conn.id)
        connector_rows.append(_connection_out(conn, retry_count=retries, last_attempt=last_attempt))

    jobs = _jobs_for_org(db, org.id, limit=40)
    audits = [
        {
            "id": str(row.id),
            "action": row.action,
            "resource": row.resource,
            "resource_id": row.resource_id,
            "detail": sanitize_error(row.detail, limit=160),
            "created_at": _iso(row.created_at),
            "user_id": str(row.user_id) if row.user_id else None,
        }
        for row in db.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == org.id)
            .order_by(AuditLog.created_at.desc())
            .limit(40)
        ).all()
    ]
    write_audit(
        db,
        organization_id=org.id,
        user_id=admin_user.id,
        action="admin.view_tenant",
        resource="platform_console",
        resource_id=str(org.id),
        detail="viewed tenant operational details",
        request=request,
    )
    db.commit()
    return {
        "overview": overview,
        "connectors": connector_rows,
        "jobs": jobs,
        "audit_events": audits,
        "checked_at": _iso(now),
    }


def _jobs_for_org(db: Session, org_id: UUID, *, limit: int = 50) -> list[dict[str, Any]]:
    _bind_org(db, org_id)
    org = db.get(Organization, org_id)
    org_name = org.name if org else None
    items: list[dict[str, Any]] = []
    logs = db.scalars(
        select(ConnectorSyncLog)
        .where(ConnectorSyncLog.organization_id == org_id)
        .order_by(ConnectorSyncLog.created_at.desc())
        .limit(limit)
    ).all()
    for log in logs:
        items.append(
            {
                "id": str(log.id),
                "kind": "connector_sync",
                "organization_id": str(org_id),
                "organization_name": org_name,
                "job_type": f"sync:{log.mode}",
                "status": log.status,
                "started_at": _iso(log.created_at),
                "completed_at": _iso(log.created_at),
                "duration_ms": log.latency_ms,
                "retry_count": 0,
                "error_summary": sanitize_error(log.message),
                "failure_class": classify_failure(log.message),
                "connection_id": str(log.connection_id),
                "can_retry": log.status in {"failed", "error"},
            }
        )
    imports = db.scalars(
        select(ImportJob)
        .where(ImportJob.organization_id == org_id)
        .order_by(ImportJob.created_at.desc())
        .limit(limit)
    ).all()
    for job in imports:
        err = None
        mapping = dict(job.mapping or {})
        if isinstance(job.error_summary, dict):
            err = str(job.error_summary.get("message") or job.error_summary)[:280]
        elif isinstance(job.error_summary, list) and job.error_summary:
            err = str(job.error_summary[0])[:280]
        items.append(
            {
                "id": str(job.id),
                "kind": "import",
                "organization_id": str(org_id),
                "organization_name": org_name,
                "job_type": f"import:{job.source_type}:{job.entity_type}",
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "started_at": mapping.get("started_at") or _iso(job.created_at),
                "completed_at": mapping.get("finished_at") or _iso(job.created_at),
                "duration_ms": job.duration_ms,
                "retry_count": int(mapping.get("retry_count") or 0),
                "error_summary": sanitize_error(err),
                "failure_class": mapping.get("failure_class") or classify_failure(err),
                "connection_id": mapping.get("connection_id"),
                "can_retry": False,
            }
        )
    items.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return items[:limit]


def list_connectors(db: Session) -> dict[str, Any]:
    now = _utcnow()
    names = {o.id: o.name for o in iter_active_orgs(db)}
    items: list[dict[str, Any]] = []
    for org_id, org_name in names.items():
        _bind_org(db, org_id)
        for conn in db.scalars(select(Connection).where(Connection.organization_id == org_id)).all():
            retries, last_attempt = _retry_count_for(db, org_id, conn.id)
            row = _connection_out(conn, retry_count=retries, last_attempt=last_attempt)
            row["organization_name"] = org_name
            items.append(row)
    items.sort(key=lambda r: (0 if r["status"] in {"failed", "warning"} else 1, r["name"]))
    return {"checked_at": _iso(now), "items": items}


def list_jobs(db: Session, *, status: str | None = None) -> dict[str, Any]:
    now = _utcnow()
    items: list[dict[str, Any]] = []
    for org in iter_active_orgs(db):
        items.extend(_jobs_for_org(db, org.id, limit=30))
    if status:
        wanted = status.lower()
        items = [j for j in items if str(j.get("status", "")).lower() == wanted]
    items.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    last_ok = next((j for j in items if j["status"] in {"success", "healthy", "partial"}), None)
    last_fail = next((j for j in items if j["status"] in {"failed", "error"}), None)
    since = now - timedelta(hours=24)
    completed_24h = sum(
        1
        for j in items
        if j["status"] in {"success", "partial"} and (j.get("started_at") or "") >= (since.isoformat())
    )
    return {
        "checked_at": _iso(now),
        "queued": sum(1 for j in items if j["status"] in {"running", "queued", "retrying"}),
        "running": sum(1 for j in items if j["status"] in {"running", "retrying"}),
        "failed": sum(1 for j in items if j["status"] in {"failed", "error"}),
        "successful": sum(1 for j in items if j["status"] in {"success", "partial"}),
        "completed_24h": completed_24h,
        "last_successful": last_ok,
        "last_failed": last_fail,
        "items": items[:100],
    }


def get_job(db: Session, organization_id: UUID, job_id: UUID) -> dict[str, Any] | None:
    _bind_org(db, organization_id)
    log = db.scalar(
        select(ConnectorSyncLog).where(
            ConnectorSyncLog.id == job_id,
            ConnectorSyncLog.organization_id == organization_id,
        )
    )
    if log:
        jobs = _jobs_for_org(db, organization_id, limit=80)
        return next((j for j in jobs if j["id"] == str(job_id) and j["kind"] == "connector_sync"), None)
    job = db.scalar(
        select(ImportJob).where(ImportJob.id == job_id, ImportJob.organization_id == organization_id)
    )
    if job:
        jobs = _jobs_for_org(db, organization_id, limit=80)
        return next((j for j in jobs if j["id"] == str(job_id) and j["kind"] == "import"), None)
    return None


def list_errors(db: Session) -> dict[str, Any]:
    now = _utcnow()
    groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "subsystem": "",
            "severity": "warning",
            "error_type": "",
            "message": "",
            "tenant_ids": set(),
            "tenant_names": set(),
            "last_seen_at": None,
            "sample_id": None,
        }
    )
    for org in iter_active_orgs(db):
        _bind_org(db, org.id)
        conns = db.scalars(
            select(Connection).where(
                Connection.organization_id == org.id,
                Connection.last_error.isnot(None),
            )
        ).all()
        for conn in conns:
            msg = sanitize_error(conn.last_error) or "error"
            etype = classify_failure(conn.last_error)
            key = ("connector", etype, msg[:80])
            g = groups[key]
            g["count"] += 1
            g["subsystem"] = "connector"
            g["severity"] = "critical" if etype == "authentication_failure" else "warning"
            g["error_type"] = etype
            g["message"] = msg
            g["tenant_ids"].add(str(org.id))
            g["tenant_names"].add(org.name)
            g["last_seen_at"] = _iso(conn.updated_at)
            g["sample_id"] = str(conn.id)
        failed_imports = db.scalars(
            select(ImportJob)
            .where(ImportJob.organization_id == org.id, ImportJob.status == ImportStatus.FAILED)
            .order_by(ImportJob.created_at.desc())
            .limit(20)
        ).all()
        for job in failed_imports:
            raw = None
            if isinstance(job.error_summary, dict):
                raw = str(job.error_summary.get("message") or job.error_summary)
            elif isinstance(job.error_summary, list) and job.error_summary:
                raw = str(job.error_summary[0])
            msg = sanitize_error(raw) or "import failed"
            etype = classify_failure(raw)
            key = ("import", etype, msg[:80])
            g = groups[key]
            g["count"] += 1
            g["subsystem"] = "import"
            g["severity"] = "warning"
            g["error_type"] = etype
            g["message"] = msg
            g["tenant_ids"].add(str(org.id))
            g["tenant_names"].add(org.name)
            g["last_seen_at"] = _iso(job.created_at)
            g["sample_id"] = str(job.id)

    items = []
    for g in groups.values():
        items.append(
            {
                "count": g["count"],
                "subsystem": g["subsystem"],
                "severity": g["severity"],
                "error_type": g["error_type"],
                "message": g["message"],
                "tenant_count": len(g["tenant_ids"]),
                "tenants": sorted(g["tenant_names"])[:8],
                "last_seen_at": g["last_seen_at"],
                "sample_id": g["sample_id"],
            }
        )
    items.sort(key=lambda r: (-r["count"], r.get("last_seen_at") or ""), reverse=False)
    items.sort(key=lambda r: -r["count"])
    return {"checked_at": _iso(now), "items": items[:50]}


async def retry_connector_sync(
    db: Session,
    *,
    organization_id: UUID,
    connection_id: UUID,
    admin_user: User,
    request=None,
) -> dict[str, Any]:
    """Enqueue an incremental sync. Duplicate ARQ ids are treated as already queued."""
    org = db.get(Organization, organization_id)
    if org is None or org.deleted_at is not None:
        raise ValueError("tenant_not_found")
    _bind_org(db, organization_id)
    conn = db.scalar(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.organization_id == organization_id,
        )
    )
    if conn is None:
        raise ValueError("connection_not_found")
    if not conn.is_active:
        raise ValueError("connection_disabled")
    if not conn.credentials_encrypted:
        raise ValueError("credentials_missing")

    from app.connectors.jobs import create_queued_import_job
    from app.connectors.queue import enqueue_sync_connection

    import_job = create_queued_import_job(db, conn, mode="incremental")
    existing_arq = (import_job.mapping or {}).get("arq_job_id")
    if existing_arq:
        write_audit(
            db,
            organization_id=organization_id,
            user_id=admin_user.id,
            action="admin.retry_sync",
            resource="connection",
            resource_id=str(conn.id),
            detail=f"already queued job_id={existing_arq}",
            request=request,
        )
        db.commit()
        return {
            "queued": True,
            "job_id": existing_arq,
            "connection_id": str(conn.id),
            "organization_id": str(organization_id),
            "mode": "incremental",
        }

    job_id = await enqueue_sync_connection(
        connection_id=conn.id,
        organization_id=organization_id,
        mode="incremental",
    )
    mapping = dict(import_job.mapping or {})
    mapping["arq_job_id"] = job_id
    import_job.mapping = mapping
    write_audit(
        db,
        organization_id=organization_id,
        user_id=admin_user.id,
        action="admin.retry_sync",
        resource="connection",
        resource_id=str(conn.id),
        detail=f"enqueued incremental sync job_id={job_id}",
        request=request,
    )
    db.commit()
    return {
        "queued": True,
        "job_id": job_id,
        "connection_id": str(conn.id),
        "organization_id": str(organization_id),
        "mode": "incremental",
    }
