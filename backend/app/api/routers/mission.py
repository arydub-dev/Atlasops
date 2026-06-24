"""Mission Control — the executive command surface.

Aggregates health, situation report, ranked actions, critical feed and trends
into a single payload so the landing page renders in one round-trip.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.services import insights, metrics, risk_engine

router = APIRouter(prefix="/mission-control", tags=["Mission Control"])


@router.get("")
def mission_control(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    kpis = metrics.compute_kpis(db)
    risk = risk_engine.summarize(db)
    overall_risk = risk["overall_score"]

    # inventory risk count = low_stock + stockout lines
    health_breakdown = metrics.inventory_health_breakdown(db)
    inventory_risk_count = health_breakdown.get("low_stock", 0) + health_breakdown.get("stockout", 0)

    return {
        "health": insights.health_score(kpis, overall_risk),
        "kpis": {
            **kpis,
            "overall_risk_score": overall_risk,
            "inventory_risk_count": inventory_risk_count,
        },
        "situation_report": insights.situation_report(db),
        "recommended_actions": insights.recommended_actions(db, limit=5),
        "critical_alerts": insights.critical_feed(db, limit=5),
        "shipment_trend": metrics.shipment_trend(db),
        "delay_trend": metrics.delay_trend(db),
        "inventory_trend": metrics.inventory_trend(db),
        "supplier_performance_trend": metrics.supplier_performance_trend(db),
    }
