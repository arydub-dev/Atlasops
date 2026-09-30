"""Mission Control — the executive command surface."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import Connection, Incident, PurchaseOrder, SalesOrder
from app.models.enums import ConnectorStatus, IncidentStatus, OrderStatus
from app.services import data_quality, graph, insights, metrics, predictions, risk_engine, timeline
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/mission-control", tags=["Mission Control"])


@router.get("")
def mission_control(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    org_id = ctx.organization_id
    kpis = metrics.compute_kpis(db, org_id)
    risk = risk_engine.summarize(db)
    overall_risk = risk["overall_score"]

    health_breakdown = metrics.inventory_health_breakdown(db, org_id)
    inventory_risk_count = health_breakdown.get("low_stock", 0) + health_breakdown.get("stockout", 0)

    open_pos = (
        db.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .where(
                PurchaseOrder.organization_id == org_id,
                PurchaseOrder.status.in_(
                    [OrderStatus.OPEN, OrderStatus.CONFIRMED, OrderStatus.IN_FULFILLMENT]
                ),
            )
        )
        or 0
    )
    open_sos = (
        db.scalar(
            select(func.count())
            .select_from(SalesOrder)
            .where(
                SalesOrder.organization_id == org_id,
                SalesOrder.status.in_(
                    [
                        OrderStatus.OPEN,
                        OrderStatus.CONFIRMED,
                        OrderStatus.IN_FULFILLMENT,
                        OrderStatus.PARTIALLY_SHIPPED,
                    ]
                ),
            )
        )
        or 0
    )
    recent_pos = db.scalars(
        select(PurchaseOrder)
        .where(PurchaseOrder.organization_id == org_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(5)
    ).all()
    recent_sos = db.scalars(
        select(SalesOrder)
        .where(SalesOrder.organization_id == org_id)
        .order_by(SalesOrder.created_at.desc())
        .limit(5)
    ).all()

    connectors = db.scalars(select(Connection).where(Connection.organization_id == org_id)).all()
    by_status: dict[str, int] = {}
    for c in connectors:
        key = c.status.value if hasattr(c.status, "value") else str(c.status)
        by_status[key] = by_status.get(key, 0) + 1

    open_incidents = db.scalars(
        select(Incident)
        .where(
            Incident.organization_id == org_id,
            Incident.status.in_(
                [
                    IncidentStatus.OPEN,
                    IncidentStatus.INVESTIGATING,
                    IncidentStatus.MITIGATING,
                ]
            ),
        )
        .order_by(Incident.created_at.desc())
        .limit(5)
    ).all()

    dq = data_quality.latest(db, org_id)
    if dq is None:
        dq = data_quality.assess(db, org_id, persist=True)
    preds = predictions.list_active(db, org_id, limit=5)

    return {
        "health": insights.health_score(kpis, overall_risk),
        "data_health": {
            "score": dq.get("overall_score"),
            "grade": dq.get("grade"),
            "confidence": dq.get("confidence"),
            "remediations": (dq.get("remediations") or [])[:3],
        },
        "kpis": {
            **kpis,
            "overall_risk_score": overall_risk,
            "inventory_risk_count": inventory_risk_count,
            "open_purchase_orders": open_pos,
            "open_sales_orders": open_sos,
        },
        "situation_report": insights.situation_report(db),
        "ai_situation_report": insights.situation_report(db),
        "recommended_actions": insights.recommended_actions(db, limit=5),
        "critical_alerts": insights.critical_feed(db, limit=5),
        "shipment_trend": metrics.shipment_trend(db, org_id),
        "delay_trend": metrics.delay_trend(db, org_id),
        "inventory_trend": metrics.inventory_trend(db, org_id),
        "supplier_performance_trend": metrics.supplier_performance_trend(db, org_id),
        "inventory_health": health_breakdown,
        "risk_heatmap": risk.get("by_category") or {},
        "purchase_orders": {
            "open_count": open_pos,
            "recent": [
                {
                    "id": str(p.id),
                    "reference": p.reference,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "total_amount": p.total_amount,
                }
                for p in recent_pos
            ],
        },
        "sales_orders": {
            "open_count": open_sos,
            "recent": [
                {
                    "id": str(s.id),
                    "reference": s.reference,
                    "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                    "customer_name": s.customer_name,
                    "total_amount": s.total_amount,
                }
                for s in recent_sos
            ],
        },
        "top_incidents": [
            {
                "id": str(i.id),
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
            }
            for i in open_incidents
        ],
        "operational_timeline": timeline.global_timeline(db, org_id, limit=12),
        "connector_status": {
            "total": len(connectors),
            "by_status": by_status,
            "healthy": by_status.get(ConnectorStatus.CONNECTED.value, 0),
            "error": by_status.get(ConnectorStatus.ERROR.value, 0),
            "items": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "type": c.connector_type.value,
                    "status": c.status.value,
                    "health": c.health.value,
                    "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                }
                for c in connectors[:8]
            ],
        },
        "graph": graph.graph_stats(db, org_id),
        "upcoming_risks": [
            {
                "title": r.title,
                "score": r.score,
                "level": r.level.value if hasattr(r.level, "value") else str(r.level),
            }
            for r in risk["top_risks"][:5]
        ],
        "predictions": preds,
    }
