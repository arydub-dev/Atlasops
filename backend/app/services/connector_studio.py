"""Connector Studio — catalogue, mapping, diagnostics, health scoring."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors import registry
from app.models import Connection, ConnectorDeadLetter, ConnectorSyncLog, ImportJob
from app.models.enums import ConnectorHealth, ConnectorStatus, ImportStatus
from app.services.platform_console import sanitize_error


def catalogue() -> list[dict[str, Any]]:
    """Self-describing connector catalogue for Studio install flow."""
    items: list[dict[str, Any]] = []
    for entry in registry.list_connectors():
        ctype = entry["type"]
        try:
            cls = registry.get_connector(ctype)
        except KeyError:
            continue
        auth = getattr(cls, "auth_methods", None)
        if not isinstance(auth, (list, tuple)):
            auth = ["api_key", "oauth2"]
        version = getattr(cls, "version", "1.0.0")
        if not isinstance(version, str):
            version = "1.0.0"
        items.append(
            {
                "type": ctype,
                "display_name": entry.get("display_name") or ctype,
                "class_name": entry.get("class") or getattr(cls, "__name__", ctype),
                "auth_methods": list(auth),
                "supports_incremental": True,
                "supports_webhooks": True,
                "supports_field_mapping": True,
                "version": version,
                "capabilities": [
                    "authenticate",
                    "discover",
                    "validate",
                    "fieldMappings",
                    "sync",
                    "incrementalSync",
                    "health",
                    "retry",
                    "disconnect",
                ],
            }
        )
    # Upload connectors that may not be in live registry
    for t, name in (
        ("csv_upload", "CSV Upload"),
        ("excel_upload", "Excel Upload"),
        ("json_upload", "JSON Upload"),
    ):
        if not any(i["type"] == t for i in items):
            items.append(
                {
                    "type": t,
                    "display_name": name,
                    "class": name.replace(" ", ""),
                    "auth_methods": ["none"],
                    "supports_incremental": False,
                    "supports_webhooks": False,
                    "supports_field_mapping": True,
                    "version": "1.0.0",
                    "capabilities": ["validate", "fieldMappings", "sync"],
                }
            )
    return items


def connection_studio_detail(db: Session, org_id: UUID, connection_id: UUID) -> dict[str, Any] | None:
    conn = db.get(Connection, connection_id)
    if conn is None or conn.organization_id != org_id:
        return None
    cfg = dict(conn.config or {})
    logs = db.scalars(
        select(ConnectorSyncLog)
        .where(
            ConnectorSyncLog.organization_id == org_id,
            ConnectorSyncLog.connection_id == connection_id,
        )
        .order_by(ConnectorSyncLog.created_at.desc())
        .limit(25)
    ).all()
    dlq = (
        db.scalar(
            select(func.count())
            .select_from(ConnectorDeadLetter)
            .where(
                ConnectorDeadLetter.organization_id == org_id,
                ConnectorDeadLetter.connection_id == connection_id,
                ConnectorDeadLetter.resolved_at.is_(None),
            )
        )
        or 0
    )
    return {
        "id": str(conn.id),
        "name": conn.name,
        "connector_type": conn.connector_type.value,
        "status": conn.status.value,
        "health": conn.health.value,
        "health_score": health_score(conn),
        "version": conn.connector_version,
        "sync_frequency": conn.sync_frequency,
        "webhook_url": conn.webhook_url,
        "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        "next_sync_at": conn.next_sync_at.isoformat() if conn.next_sync_at else None,
        "record_count": conn.record_count,
        "last_error": sanitize_error(conn.last_error),
        "field_mappings": cfg.get("field_mappings") or [],
        "transforms": cfg.get("transforms") or [],
        "validation_rules": cfg.get("validation_rules") or [],
        "conflict_resolution": cfg.get("conflict_resolution") or "source_wins",
        "retry_policy": cfg.get("retry_policy")
        or {"max_attempts": 3, "backoff_seconds": 60},
        "schedule": cfg.get("schedule") or {"frequency": conn.sync_frequency},
        "unknown_fields": cfg.get("unknown_fields") or [],
        "manual_overrides": cfg.get("manual_overrides") or {},
        "dead_letter_count": dlq,
        "logs": [
            {
                "id": str(l.id),
                "mode": l.mode,
                "status": l.status,
                "records_processed": l.records_processed,
                "records_imported": l.records_imported,
                "records_rejected": l.records_rejected,
                "latency_ms": l.latency_ms,
                "message": sanitize_error(l.message),
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "usage": {
            "records_synced": conn.record_count,
            "failed_imports": _failed_imports(db, org_id),
        },
    }


def health_score(conn: Connection) -> int:
    base = {
        ConnectorHealth.HEALTHY: 92,
        ConnectorHealth.DEGRADED: 55,
        ConnectorHealth.DOWN: 15,
        ConnectorHealth.UNKNOWN: 40,
    }.get(conn.health, 40)
    if conn.status == ConnectorStatus.ERROR:
        base = min(base, 25)
    if conn.last_error:
        base = max(10, base - 15)
    return int(base)


def update_studio_config(
    db: Session,
    org_id: UUID,
    connection_id: UUID,
    *,
    field_mappings: list[dict] | None = None,
    transforms: list[dict] | None = None,
    validation_rules: list[dict] | None = None,
    conflict_resolution: str | None = None,
    retry_policy: dict | None = None,
    schedule: dict | None = None,
    manual_overrides: dict | None = None,
    webhook_url: str | None = None,
    sync_frequency: str | None = None,
) -> Connection | None:
    conn = db.get(Connection, connection_id)
    if conn is None or conn.organization_id != org_id:
        return None
    cfg = dict(conn.config or {})
    if field_mappings is not None:
        cfg["field_mappings"] = field_mappings
    if transforms is not None:
        cfg["transforms"] = transforms
    if validation_rules is not None:
        cfg["validation_rules"] = validation_rules
    if conflict_resolution is not None:
        cfg["conflict_resolution"] = conflict_resolution
    if retry_policy is not None:
        cfg["retry_policy"] = retry_policy
    if schedule is not None:
        cfg["schedule"] = schedule
        if schedule.get("frequency"):
            conn.sync_frequency = str(schedule["frequency"])
    if manual_overrides is not None:
        cfg["manual_overrides"] = manual_overrides
    conn.config = cfg
    if webhook_url is not None:
        conn.webhook_url = webhook_url or None
    if sync_frequency is not None:
        conn.sync_frequency = sync_frequency or None
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def sync_preview(db: Session, org_id: UUID, connection_id: UUID) -> dict[str, Any] | None:
    detail = connection_studio_detail(db, org_id, connection_id)
    if detail is None:
        return None
    mappings = detail["field_mappings"]
    return {
        "connection_id": str(connection_id),
        "mode": "preview",
        "estimated_entities": max(1, len(mappings) or 3),
        "field_mappings": mappings,
        "validation_rules": detail["validation_rules"],
        "conflict_resolution": detail["conflict_resolution"],
        "warnings": []
        if mappings
        else ["No field mappings configured — defaults will be used on sync."],
    }


def record_sync_log(
    db: Session,
    *,
    org_id: UUID,
    connection_id: UUID,
    mode: str,
    status: str,
    records_processed: int = 0,
    records_imported: int = 0,
    records_rejected: int = 0,
    latency_ms: int = 0,
    message: str | None = None,
    details: dict | None = None,
) -> ConnectorSyncLog:
    row = ConnectorSyncLog(
        organization_id=org_id,
        connection_id=connection_id,
        mode=mode,
        status=status,
        records_processed=records_processed,
        records_imported=records_imported,
        records_rejected=records_rejected,
        latency_ms=latency_ms,
        message=message,
        details=details or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _failed_imports(db: Session, org_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ImportJob)
            .where(
                ImportJob.organization_id == org_id,
                ImportJob.status == ImportStatus.FAILED,
            )
        )
        or 0
    )


def diagnostics_summary(db: Session, org_id: UUID) -> dict[str, Any]:
    connections = db.scalars(select(Connection).where(Connection.organization_id == org_id)).all()
    return {
        "total": len(connections),
        "by_health": _count_attr(connections, "health"),
        "by_status": _count_attr(connections, "status"),
        "avg_health_score": round(
            sum(health_score(c) for c in connections) / len(connections), 1
        )
        if connections
        else 0.0,
        "items": [
            {
                "id": str(c.id),
                "name": c.name,
                "type": c.connector_type.value,
                "health_score": health_score(c),
                "status": c.status.value,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            }
            for c in connections
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _count_attr(rows: list, attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        val = getattr(r, attr)
        key = val.value if hasattr(val, "value") else str(val)
        out[key] = out.get(key, 0) + 1
    return out
