"""Operational insight synthesis.

Turns raw metrics into executive narrative: a supply-chain health score, a
situation report ("what / why"), ranked recommended actions ("what next"), and
a full executive brief. All deterministic so output is explainable.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Inventory,
    Product,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import AlertStatus, ShipmentStatus
from app.services import metrics, risk_engine


# --------------------------------------------------------------------------- #
# Health score
# --------------------------------------------------------------------------- #
def health_score(kpis: dict, overall_risk: float) -> dict:
    on_time = kpis["on_time_delivery_rate"]
    inv = kpis["inventory_health_score"]
    rel = kpis["supplier_reliability_score"]
    risk_inv = max(0.0, 100.0 - overall_risk)
    score = round(0.30 * on_time + 0.25 * inv + 0.25 * rel + 0.20 * risk_inv, 1)
    if score >= 85:
        grade, label = "A", "Excellent"
    elif score >= 75:
        grade, label = "B", "Healthy"
    elif score >= 65:
        grade, label = "C", "Watch"
    elif score >= 50:
        grade, label = "D", "At Risk"
    else:
        grade, label = "E", "Critical"
    return {"score": score, "grade": grade, "label": label}


# --------------------------------------------------------------------------- #
# Situation report  (what is happening + why)
# --------------------------------------------------------------------------- #
def situation_report(db: Session) -> dict:
    insights: list[dict] = []

    # 1) Delay momentum from the weekly delay trend
    delay_trend = metrics.delay_trend(db, weeks=8)
    delta_pct = 0.0
    if len(delay_trend) >= 2:
        prev = delay_trend[-2]["delayed_pct"]
        curr = delay_trend[-1]["delayed_pct"]
        delta_pct = round(curr - prev, 1)
    direction = "increased" if delta_pct > 0 else "decreased" if delta_pct < 0 else "held steady"
    insights.append(
        {
            "icon": "trend",
            "severity": "high" if delta_pct > 2 else "medium" if delta_pct != 0 else "low",
            "text": (
                f"Shipment delays {direction} {abs(delta_pct):.1f} points week-over-week"
                if delta_pct
                else "Shipment delay rate is stable week-over-week"
            ),
        }
    )

    # 2) Concentration: which supplier drives the most delays
    delayed_total = db.scalar(
        select(func.count(Shipment.id)).where(Shipment.status == ShipmentStatus.DELAYED)
    ) or 0
    top_supplier_text = None
    if delayed_total:
        row = db.execute(
            select(Supplier.name, func.count(Shipment.id).label("c"))
            .join(Shipment, Shipment.supplier_id == Supplier.id)
            .where(Shipment.status == ShipmentStatus.DELAYED)
            .group_by(Supplier.name)
            .order_by(func.count(Shipment.id).desc())
            .limit(1)
        ).first()
        if row:
            name, count = row
            share = round(count / delayed_total * 100)
            top_supplier_text = (
                f"{name} accounts for {share}% of currently delayed shipments"
            )
            insights.append(
                {
                    "icon": "supplier",
                    "severity": "high" if share >= 30 else "medium",
                    "text": top_supplier_text,
                }
            )

    # 3) Warehouse closest to a stockout / capacity ceiling
    wh_row = db.execute(
        select(
            Warehouse.name,
            Warehouse.id,
            (Warehouse.current_inventory * 100.0 / Warehouse.capacity).label("util"),
        ).order_by((Warehouse.current_inventory * 1.0 / Warehouse.capacity).desc())
    ).first()
    if wh_row:
        name, wid, util = wh_row
        # estimate days to critical from lowest days-of-supply lines in that warehouse
        low = db.execute(
            select(Inventory.quantity, Inventory.avg_daily_demand)
            .where(
                Inventory.is_current.is_(True),
                Inventory.warehouse_id == wid,
                Inventory.avg_daily_demand > 0,
            )
            .order_by((Inventory.quantity * 1.0 / Inventory.avg_daily_demand).asc())
            .limit(1)
        ).first()
        days = None
        if low and low[1]:
            days = max(1, int(low[0] / low[1]))
        if util >= 88:
            insights.append(
                {
                    "icon": "warehouse",
                    "severity": "high",
                    "text": f"{name} is at {util:.0f}% capacity and constrained for inbound flow",
                }
            )
        elif days is not None and days <= 7:
            insights.append(
                {
                    "icon": "warehouse",
                    "severity": "high" if days <= 3 else "medium",
                    "text": f"{name} is projected to reach critical inventory on at least one SKU within {days} days",
                }
            )

    # 4) Open critical alert pressure
    open_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.status != AlertStatus.RESOLVED)
    ) or 0
    if open_alerts:
        insights.append(
            {
                "icon": "alert",
                "severity": "medium",
                "text": f"{open_alerts} operational alerts are open and awaiting triage",
            }
        )

    headline = insights[0]["text"] if insights else "Operations are running within normal parameters."
    return {"headline": headline, "insights": insights[:5]}


# --------------------------------------------------------------------------- #
# Ranked recommended actions  (what to do next)
# --------------------------------------------------------------------------- #
def recommended_actions(db: Session, limit: int = 5) -> list[dict]:
    actions: list[dict] = []
    risk = risk_engine.summarize(db)

    for r in risk["top_risks"][: limit + 3]:
        impact, cost = _impact_cost(db, r)
        actions.append(
            {
                "priority": r.level.value,
                "title": r.title,
                "detail": r.recommendation,
                "expected_impact": impact,
                "estimated_cost": cost,
                "category": r.category.value,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "score": r.score,
            }
        )

    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda a: (priority_rank.get(a["priority"], 9), -a["score"]))
    return actions[:limit]


def _impact_cost(db, r) -> tuple[str, str]:
    cat = r.category.value
    if cat == "supplier":
        reduction = min(45, int(r.score * 0.5))
        return (f"~{reduction}% delay-risk reduction", "$$ medium")
    if cat == "inventory":
        reduction = min(40, int(r.score * 0.45))
        return (f"~{reduction}% stockout-risk reduction", "$ low")
    if cat == "shipment":
        return ("Protect in-transit value & ETA", "$$ medium")
    if cat == "geographic":
        return ("Reduce regional concentration", "$$$ high")
    return ("Improve operational resilience", "$$ medium")


# --------------------------------------------------------------------------- #
# Critical alert feed (enriched)
# --------------------------------------------------------------------------- #
_RESPONSES = {
    "delayed_shipment": "Expedite via priority carrier and notify the consignee of revised ETA.",
    "inventory_stockout_risk": "Trigger emergency replenishment or inter-warehouse transfer.",
    "supplier_failure_risk": "Activate backup supplier and place vendor on a recovery plan.",
    "forecasted_demand_spike": "Pre-build inventory for high-velocity SKUs ahead of demand.",
}


def critical_feed(db: Session, limit: int = 6) -> list[dict]:
    from app.models.enums import AlertPriority

    alerts = db.scalars(
        select(Alert)
        .where(
            Alert.status != AlertStatus.RESOLVED,
            Alert.priority.in_([AlertPriority.CRITICAL, AlertPriority.HIGH]),
        )
        .order_by(Alert.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "priority": a.priority.value,
            "alert_type": a.alert_type.value,
            "created_at": a.created_at.isoformat(),
            "recommended_response": _RESPONSES.get(a.alert_type.value, "Investigate and assign an owner."),
        }
        for a in alerts
    ]


# --------------------------------------------------------------------------- #
# Executive brief  (management-consulting style)
# --------------------------------------------------------------------------- #
def executive_brief(db: Session) -> dict:
    kpis = metrics.compute_kpis(db)
    risk = risk_engine.summarize(db)
    overall_risk = risk["overall_score"]
    health = health_score(kpis, overall_risk)
    situation = situation_report(db)
    actions = recommended_actions(db, limit=5)

    exec_summary = (
        f"Supply chain health is **{health['score']}/100 ({health['label']})**. "
        f"The network is managing {kpis['active_shipments']:,} active shipments with an on-time "
        f"delivery rate of {kpis['on_time_delivery_rate']}% and {kpis['delayed_shipments']:,} "
        f"shipments currently delayed. Inventory health stands at {kpis['inventory_health_score']}% "
        f"and average supplier reliability at {kpis['supplier_reliability_score']}/100. "
        f"Overall operational risk is {overall_risk}/100 ({risk['overall_level'].value if hasattr(risk['overall_level'], 'value') else risk['overall_level']})."
    )

    current_risks = [
        f"{r.title} — {r.level.value.upper()} (score {r.score:.0f}). {r.description}"
        for r in risk["top_risks"][:5]
    ]

    by_cat = risk["by_category"]
    performance = [
        f"On-time delivery: {kpis['on_time_delivery_rate']}%",
        f"Active / delayed shipments: {kpis['active_shipments']:,} / {kpis['delayed_shipments']:,}",
        f"Inventory health: {kpis['inventory_health_score']}% of lines healthy",
        f"Supplier reliability: {kpis['supplier_reliability_score']}/100",
        f"Open alerts: {kpis['open_alerts']:,} ({kpis['critical_risks']} critical risks)",
    ]
    perf_by_cat = [f"{k.title()} risk: {v:.0f}/100" for k, v in by_cat.items()]

    key_recs = [f"[{a['priority'].upper()}] {a['title']}: {a['detail']} ({a['expected_impact']})" for a in actions]

    strategic = _strategic_concerns(db, by_cat, kpis)

    return {
        "generated_at": _now_iso(),
        "health": health,
        "executive_summary": exec_summary,
        "current_risks": current_risks,
        "operational_performance": performance + perf_by_cat,
        "key_recommendations": key_recs,
        "strategic_concerns": strategic,
        "situation_headline": situation["headline"],
    }


def _strategic_concerns(db, by_cat: dict, kpis: dict) -> list[str]:
    concerns: list[str] = []
    if by_cat.get("geographic", 0) >= 50:
        concerns.append(
            "Geographic concentration risk is elevated — sourcing is over-indexed to a few regions, "
            "exposing the network to localized disruptions. Diversify the supplier base."
        )
    if by_cat.get("supplier", 0) >= 55:
        concerns.append(
            "A long tail of underperforming suppliers is dragging reliability. Consolidate spend toward "
            "top performers and qualify backups for single-sourced critical SKUs."
        )
    if kpis["inventory_health_score"] < 85:
        concerns.append(
            "Inventory positioning is suboptimal relative to demand — rebalance safety stock toward "
            "high-velocity regions to reduce stockout exposure without inflating carrying cost."
        )
    if kpis["on_time_delivery_rate"] < 85:
        concerns.append(
            "On-time performance is below an enterprise SLA benchmark of 95%. Carrier diversification "
            "and proactive exception management should be prioritized."
        )
    if not concerns:
        concerns.append(
            "No structural concerns detected. Maintain current operating posture and continue "
            "monitoring leading indicators."
        )
    return concerns


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
