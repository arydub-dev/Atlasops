"""Platform operations dashboard — workers, queues, AI, automations."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AIReport,
    Alert,
    AlertDelivery,
    Connection,
    ConnectorDeadLetter,
    ConnectorSyncLog,
    ImportJob,
    Simulation,
    WorkflowRun,
)
from app.models.enums import AlertStatus, DeliveryStatus, ImportStatus
from app.core.config import settings
from app.services import connector_studio, data_quality, graph


def platform_ops(db: Session, org_id: UUID) -> dict[str, Any]:
    connections = db.scalars(select(Connection).where(Connection.organization_id == org_id)).all()
    recent_syncs = db.scalars(
        select(ConnectorSyncLog)
        .where(ConnectorSyncLog.organization_id == org_id)
        .order_by(ConnectorSyncLog.created_at.desc())
        .limit(20)
    ).all()
    avg_latency = (
        round(sum(l.latency_ms for l in recent_syncs) / len(recent_syncs), 1) if recent_syncs else 0.0
    )
    dlq = (
        db.scalar(
            select(func.count())
            .select_from(ConnectorDeadLetter)
            .where(
                ConnectorDeadLetter.organization_id == org_id,
                ConnectorDeadLetter.resolved_at.is_(None),
            )
        )
        or 0
    )
    failed_imports = (
        db.scalar(
            select(func.count())
            .select_from(ImportJob)
            .where(ImportJob.organization_id == org_id, ImportJob.status == ImportStatus.FAILED)
        )
        or 0
    )
    ai_reports = (
        db.scalar(select(func.count()).select_from(AIReport).where(AIReport.organization_id == org_id))
        or 0
    )
    workflow_runs = (
        db.scalar(
            select(func.count()).select_from(WorkflowRun).where(WorkflowRun.organization_id == org_id)
        )
        or 0
    )
    sims = (
        db.scalar(select(func.count()).select_from(Simulation).where(Simulation.organization_id == org_id))
        or 0
    )
    alert_deliveries = (
        db.scalar(
            select(func.count())
            .select_from(AlertDelivery)
            .where(AlertDelivery.organization_id == org_id)
        )
        or 0
    )
    alert_failed = (
        db.scalar(
            select(func.count())
            .select_from(AlertDelivery)
            .where(
                AlertDelivery.organization_id == org_id,
                AlertDelivery.status == DeliveryStatus.FAILED,
            )
        )
        or 0
    )
    open_alerts = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.organization_id == org_id, Alert.status != AlertStatus.RESOLVED)
        )
        or 0
    )
    gstats = graph.graph_stats(db, org_id)
    dq = data_quality.latest(db, org_id)

    return {
        "workers": {
            "failed_import_jobs": failed_imports,
            "dead_letter_count": dlq,
            "note": "Queue depth via Redis/Prometheus /metrics; ARQ cron every 15m for connectors",
        },
        "connectors": {
            **connector_studio.diagnostics_summary(db, org_id),
            "avg_sync_latency_ms": avg_latency,
            "recent_syncs": [
                {
                    "id": str(l.id),
                    "connection_id": str(l.connection_id),
                    "status": l.status,
                    "latency_ms": l.latency_ms,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in recent_syncs[:10]
            ],
        },
        "ai_usage": {"reports_generated": ai_reports},
        "automations": {"workflow_runs": workflow_runs},
        "simulations": {"jobs": sims},
        "alerts": {
            "open": open_alerts,
            "deliveries": alert_deliveries,
            "delivery_failures": alert_failed,
        },
        "graph": gstats,
        "data_quality": dq,
        "search": {"note": "PostgreSQL ILIKE enterprise search; Meilisearch reserved for Phase C+"},
        "timeline": {"note": "Operational events via /timeline"},
        "integrations": {
            "sentry": bool(settings.SENTRY_DSN),
            "posthog": bool(settings.POSTHOG_API_KEY),
            "prometheus": bool(settings.METRICS_TOKEN) or settings.ENVIRONMENT != "development",
        },
        "connection_count": len(connections),
    }
