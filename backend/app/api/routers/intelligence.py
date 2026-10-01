"""Search, executive reports, and platform observability."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import Alert, Connection, ConnectorDeadLetter, ImportJob, Incident, Simulation
from app.models.enums import AlertStatus, ConnectorStatus, ImportStatus
from app.services import executive_reports, graph, search as search_service
from app.services.platform_console import sanitize_error
from app.tenancy.context import TenantContext

router = APIRouter(tags=["Intelligence"])


@router.get("/search")
def enterprise_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(40, ge=1, le=100),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    items = search_service.search(db, ctx.organization_id, q, limit=limit)
    return {"query": q, "items": items, "count": len(items)}


@router.get("/reports/kinds")
def report_kinds(
    ctx: TenantContext = Depends(require_permission("ai.reports")),
) -> dict:
    return {"kinds": executive_reports.REPORT_KINDS}


@router.post("/reports/generate")
def generate_report(
    kind: str = Query("executive"),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("ai.reports")),
) -> dict:
    return executive_reports.generate_report(db, ctx.organization_id, kind)


@router.get("/observability/platform")
def platform_observability(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    org_id = ctx.organization_id
    connections = db.scalars(
        select(Connection).where(Connection.organization_id == org_id)
    ).all()
    by_status: dict[str, int] = {}
    for c in connections:
        key = c.status.value if hasattr(c.status, "value") else str(c.status)
        by_status[key] = by_status.get(key, 0) + 1

    failed_jobs = (
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
    open_alerts = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.organization_id == org_id, Alert.status != AlertStatus.RESOLVED)
        )
        or 0
    )
    open_incidents = (
        db.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.organization_id == org_id)
        )
        or 0
    )
    sims = (
        db.scalar(
            select(func.count()).select_from(Simulation).where(Simulation.organization_id == org_id)
        )
        or 0
    )

    return {
        "connectors": {
            "total": len(connections),
            "by_status": by_status,
            "syncing": by_status.get(ConnectorStatus.SYNCING.value, 0),
            "error": by_status.get(ConnectorStatus.ERROR.value, 0),
            "items": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "type": c.connector_type.value,
                    "status": c.status.value,
                    "health": c.health.value,
                    "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                    "next_sync_at": c.next_sync_at.isoformat() if c.next_sync_at else None,
                    "record_count": c.record_count,
                    "last_error": sanitize_error(c.last_error),
                }
                for c in connections
            ],
        },
        "workers": {
            "failed_import_jobs": failed_jobs,
            "dead_letter_count": dlq,
            "note": "Queue depth requires Redis metrics scrape; see Prometheus /metrics",
        },
        "operations": {
            "open_alerts": open_alerts,
            "incidents": open_incidents,
            "simulations_run": sims,
        },
        "graph": graph.graph_stats(db, org_id),
    }
