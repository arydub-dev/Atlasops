"""Operational risk scoring engine.

Produces a 0-100 risk score per category and entity, classifies the level,
and emits actionable recommendations. Results are persisted as RiskAssessment
rows (and optionally as Alerts) so they can be ranked and trended.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Inventory,
    RiskAssessment,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import RiskCategory, RiskLevel, ShipmentStatus


def level_for_score(score: float) -> RiskLevel:
    if score >= 80:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


# --------------------------------------------------------------------------- #
# Per-entity scoring
# --------------------------------------------------------------------------- #
def score_supplier(s: Supplier) -> tuple[float, dict]:
    factors = {
        "low_reliability": _clamp(100 - s.delivery_reliability) * 0.35,
        "delay": _clamp(s.average_delay_days * 12) * 0.25,
        "defects": _clamp(s.defect_rate * 8) * 0.20,
        "fulfillment_gap": _clamp(100 - s.order_fulfillment_rate) * 0.20,
    }
    return _clamp(sum(factors.values())), factors


def score_shipment(s: Shipment) -> tuple[float, dict]:
    status_weight = {
        ShipmentStatus.CUSTOMS_HOLD: 70,
        ShipmentStatus.DELAYED: 80,
        ShipmentStatus.IN_TRANSIT: 30,
        ShipmentStatus.AT_WAREHOUSE: 10,
        ShipmentStatus.DELIVERED: 0,
    }
    factors = {
        "model_risk": s.delay_risk_score * 0.5,
        "status": status_weight.get(s.status, 30) * 0.3,
        "delay_days": _clamp(s.delay_days * 10) * 0.2,
    }
    return _clamp(sum(factors.values())), factors


def score_warehouse(w: Warehouse, low_stock_lines: int, total_lines: int) -> tuple[float, dict]:
    util = w.utilization
    util_risk = 0.0
    if util >= 95:
        util_risk = 80
    elif util >= 88:
        util_risk = 55
    elif util <= 15:
        util_risk = 45  # underutilized / potential stockout of variety
    low_stock_ratio = (low_stock_lines / total_lines * 100) if total_lines else 0
    factors = {
        "utilization": util_risk * 0.5,
        "low_stock_pressure": _clamp(low_stock_ratio * 1.5) * 0.5,
    }
    return _clamp(sum(factors.values())), factors


# --------------------------------------------------------------------------- #
# Full recomputation
# --------------------------------------------------------------------------- #
def recompute_all(db: Session, limit_per_category: int = 25) -> int:
    """Recompute risk assessments. Returns number of assessments written."""
    db.execute(delete(RiskAssessment))

    created: list[RiskAssessment] = []

    # ---- Supplier risk ----
    suppliers = db.scalars(select(Supplier).where(Supplier.is_active.is_(True))).all()
    scored_suppliers = []
    for s in suppliers:
        score, factors = score_supplier(s)
        scored_suppliers.append((s, score, factors))
    scored_suppliers.sort(key=lambda x: x[1], reverse=True)
    for s, score, factors in scored_suppliers[:limit_per_category]:
        if score < 25:
            continue
        created.append(
            RiskAssessment(
                category=RiskCategory.SUPPLIER,
                level=level_for_score(score),
                score=score,
                title=f"Supplier risk: {s.name}",
                description=(
                    f"{s.name} ({s.country}) shows reliability {s.delivery_reliability:.0f}%, "
                    f"avg delay {s.average_delay_days:.1f}d, defect rate {s.defect_rate:.1f}%."
                ),
                recommendation=_supplier_recommendation(score),
                entity_type="supplier",
                entity_id=s.id,
                factors=factors,
            )
        )

    # ---- Shipment risk (focus on non-delivered, high-risk) ----
    shipments = db.scalars(
        select(Shipment)
        .where(Shipment.status != ShipmentStatus.DELIVERED)
        .order_by(Shipment.delay_risk_score.desc())
        .limit(limit_per_category * 4)
    ).all()
    scored_shipments = []
    for sh in shipments:
        score, factors = score_shipment(sh)
        scored_shipments.append((sh, score, factors))
    scored_shipments.sort(key=lambda x: x[1], reverse=True)
    for sh, score, factors in scored_shipments[:limit_per_category]:
        if score < 40:
            continue
        created.append(
            RiskAssessment(
                category=RiskCategory.SHIPMENT,
                level=level_for_score(score),
                score=score,
                title=f"Shipment risk: {sh.reference}",
                description=(
                    f"{sh.reference} {sh.origin} -> {sh.destination} via {sh.carrier} "
                    f"is {sh.status.value} near {sh.current_location}."
                ),
                recommendation=_shipment_recommendation(sh),
                entity_type="shipment",
                entity_id=sh.id,
                factors=factors,
            )
        )

    # ---- Inventory / warehouse risk ----
    warehouses = db.scalars(select(Warehouse)).all()
    low_counts = dict(
        db.execute(
            select(Inventory.warehouse_id, func.count(Inventory.id))
            .where(Inventory.is_current.is_(True), Inventory.quantity <= Inventory.reorder_point)
            .group_by(Inventory.warehouse_id)
        ).all()
    )
    total_counts = dict(
        db.execute(
            select(Inventory.warehouse_id, func.count(Inventory.id))
            .where(Inventory.is_current.is_(True))
            .group_by(Inventory.warehouse_id)
        ).all()
    )
    scored_wh = []
    for w in warehouses:
        score, factors = score_warehouse(
            w, low_counts.get(w.id, 0), total_counts.get(w.id, 0)
        )
        scored_wh.append((w, score, factors))
    scored_wh.sort(key=lambda x: x[1], reverse=True)
    for w, score, factors in scored_wh[:limit_per_category]:
        if score < 30:
            continue
        created.append(
            RiskAssessment(
                category=RiskCategory.INVENTORY,
                level=level_for_score(score),
                score=score,
                title=f"Inventory risk: {w.name}",
                description=(
                    f"{w.name} at {w.utilization:.0f}% utilization with "
                    f"{low_counts.get(w.id, 0)} SKUs below reorder point."
                ),
                recommendation=_inventory_recommendation(w),
                entity_type="warehouse",
                entity_id=w.id,
                factors=factors,
            )
        )

    # ---- Geographic risk (aggregate by region) ----
    created.extend(_geographic_risk(db))

    db.add_all(created)
    db.commit()
    return len(created)


def _geographic_risk(db: Session) -> list[RiskAssessment]:
    rows = db.execute(
        select(
            Supplier.region,
            func.avg(Supplier.supplier_score),
            func.count(Supplier.id),
        ).group_by(Supplier.region)
    ).all()
    out = []
    for region, avg_score, count in rows:
        score = _clamp((100 - float(avg_score or 80)) * 1.1)
        if score < 30:
            continue
        out.append(
            RiskAssessment(
                category=RiskCategory.GEOGRAPHIC,
                level=level_for_score(score),
                score=score,
                title=f"Geographic risk: {region}",
                description=(
                    f"{region} concentrates {count} suppliers averaging "
                    f"{float(avg_score or 0):.0f} supplier score."
                ),
                recommendation=(
                    f"Diversify sourcing away from {region}; qualify alternate suppliers "
                    "in lower-risk regions to reduce concentration exposure."
                ),
                entity_type="region",
                entity_id=None,
                factors={"avg_supplier_score": round(float(avg_score or 0), 1), "supplier_count": count},
            )
        )
    return out


def summarize(db: Session) -> dict:
    assessments = db.scalars(select(RiskAssessment)).all()
    by_category: dict[str, list[float]] = {}
    counts = {lvl.value: 0 for lvl in RiskLevel}
    for a in assessments:
        by_category.setdefault(a.category.value, []).append(a.score)
        counts[a.level.value] += 1
    cat_avg = {k: round(sum(v) / len(v), 1) for k, v in by_category.items()}
    overall = round(sum(cat_avg.values()) / len(cat_avg), 1) if cat_avg else 0.0
    top = sorted(assessments, key=lambda a: a.score, reverse=True)[:8]
    return {
        "overall_score": overall,
        "overall_level": level_for_score(overall),
        "by_category": cat_avg,
        "counts": counts,
        "top_risks": top,
    }


# --------------------------------------------------------------------------- #
# Recommendation text
# --------------------------------------------------------------------------- #
def _supplier_recommendation(score: float) -> str:
    if score >= 80:
        return "Escalate to dual-sourcing immediately and place this supplier on a recovery plan with weekly reviews."
    if score >= 60:
        return "Qualify a backup supplier and reduce single-supplier dependency on critical SKUs."
    return "Monitor performance and tighten delivery SLAs in the next contract cycle."


def _shipment_recommendation(s: Shipment) -> str:
    if s.status == ShipmentStatus.CUSTOMS_HOLD:
        return "Engage customs broker to expedite clearance and notify destination warehouse of revised ETA."
    if s.status == ShipmentStatus.DELAYED:
        return "Expedite via priority lane or alternate carrier; pre-position safety stock at destination."
    return "Add proactive tracking checkpoints and alert the consignee of potential slippage."


def _inventory_recommendation(w: Warehouse) -> str:
    util = w.utilization
    if util >= 95:
        return "Capacity critical: rebalance inbound flow to alternate sites and accelerate outbound picking."
    if util <= 15:
        return "Underutilized: consolidate slow-moving stock and reallocate capacity to high-demand regions."
    return "Trigger reorders for SKUs below reorder point and review safety-stock levels."
