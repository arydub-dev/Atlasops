"""Executive dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import Alert
from app.models.enums import AlertPriority, AlertStatus
from app.schemas.entities import DashboardResponse, KPISet
from app.services import metrics, risk_engine
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("analytics.read")),
) -> DashboardResponse:
    org_id = ctx.organization_id
    kpis = metrics.compute_kpis(db, org_id)

    critical_alerts = list(
        db.scalars(
            select(Alert)
            .where(
                Alert.organization_id == org_id,
                Alert.status != AlertStatus.RESOLVED,
                Alert.priority.in_([AlertPriority.CRITICAL, AlertPriority.HIGH]),
            )
            .order_by(Alert.created_at.desc())
            .limit(6)
        ).all()
    )

    risk = risk_engine.summarize(db)
    top_risks = risk["top_risks"][:6]

    recommended_actions = [
        {
            "title": r.title,
            "action": r.recommendation,
            "priority": r.level.value,
            "score": r.score,
        }
        for r in top_risks[:5]
    ]

    return DashboardResponse(
        kpis=KPISet(**kpis),
        shipment_trend=metrics.shipment_trend(db, org_id),
        inventory_trend=metrics.inventory_trend(db, org_id),
        delay_trend=metrics.delay_trend(db, org_id),
        supplier_performance_trend=metrics.supplier_performance_trend(db, org_id),
        critical_alerts=critical_alerts,
        top_risks=top_risks,
        recommended_actions=recommended_actions,
    )
