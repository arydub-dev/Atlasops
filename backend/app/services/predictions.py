"""Predictive intelligence from historical operational data."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Inventory, Prediction, Shipment, Supplier, Warehouse
from app.models.enums import PredictionKind, ShipmentStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate(db: Session, org_id: UUID, *, replace_active: bool = True) -> list[dict[str, Any]]:
    if replace_active:
        for old in db.scalars(
            select(Prediction).where(
                Prediction.organization_id == org_id, Prediction.is_active.is_(True)
            )
        ).all():
            old.is_active = False
            db.add(old)

    created: list[Prediction] = []
    created.extend(_shipment_delay_predictions(db, org_id))
    created.extend(_supplier_deterioration(db, org_id))
    created.extend(_inventory_shortages(db, org_id))
    created.extend(_warehouse_congestion(db, org_id))
    created.extend(_demand_and_anomalies(db, org_id))
    db.commit()
    return [_out(p) for p in created]


def list_active(db: Session, org_id: UUID, *, limit: int = 40) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Prediction)
        .where(Prediction.organization_id == org_id, Prediction.is_active.is_(True))
        .order_by(Prediction.score.desc())
        .limit(limit)
    ).all()
    return [_out(p) for p in rows]


def _shipment_delay_predictions(db: Session, org_id: UUID) -> list[Prediction]:
    outs: list[Prediction] = []
    ships = db.scalars(
        select(Shipment)
        .where(
            Shipment.organization_id == org_id,
            Shipment.status.in_([ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELAYED]),
        )
        .order_by(Shipment.delay_risk_score.desc())
        .limit(8)
    ).all()
    for sh in ships:
        if sh.delay_risk_score < 45 and sh.status != ShipmentStatus.DELAYED:
            continue
        conf = min(0.95, 0.55 + (sh.delay_risk_score / 200.0))
        p = Prediction(
            organization_id=org_id,
            kind=PredictionKind.SHIPMENT_DELAY,
            title=f"Delay risk on {sh.reference}",
            confidence=round(conf, 2),
            reasoning=(
                f"Shipment {sh.reference} shows delay_risk_score={sh.delay_risk_score:.0f} "
                f"with status={sh.status.value} and delay_days={sh.delay_days}."
            ),
            contributing_factors=[
                f"delay_risk_score={sh.delay_risk_score}",
                f"status={sh.status.value}",
                f"route={sh.origin}→{sh.destination}",
            ],
            recommended_actions=[
                "Notify customer of revised ETA",
                "Evaluate alternate carrier for remaining leg",
                "Open incident if score exceeds 80",
            ],
            linked_entities=[{"type": "shipment", "id": str(sh.id), "label": sh.reference}],
            horizon_hours=72,
            score=float(sh.delay_risk_score),
        )
        db.add(p)
        outs.append(p)
    return outs


def _supplier_deterioration(db: Session, org_id: UUID) -> list[Prediction]:
    outs: list[Prediction] = []
    suppliers = db.scalars(
        select(Supplier)
        .where(Supplier.organization_id == org_id, Supplier.is_active.is_(True))
        .order_by(Supplier.supplier_score.asc())
        .limit(5)
    ).all()
    for s in suppliers:
        if s.supplier_score >= 70 and s.average_delay_days < 3:
            continue
        conf = min(0.9, 0.5 + ((100 - s.supplier_score) / 150.0))
        p = Prediction(
            organization_id=org_id,
            kind=PredictionKind.SUPPLIER_DETERIORATION,
            title=f"Supplier deterioration: {s.name}",
            confidence=round(conf, 2),
            reasoning=(
                f"{s.name} score={s.supplier_score:.0f}, reliability={s.delivery_reliability:.0f}%, "
                f"avg delay={s.average_delay_days:.1f}d."
            ),
            contributing_factors=[
                f"supplier_score={s.supplier_score}",
                f"delivery_reliability={s.delivery_reliability}",
                f"average_delay_days={s.average_delay_days}",
            ],
            recommended_actions=[
                "Increase inbound QC sampling",
                "Qualify alternate supplier",
                "Reduce PO volume until score recovers",
            ],
            linked_entities=[{"type": "supplier", "id": str(s.id), "label": s.name}],
            horizon_hours=168,
            score=100 - float(s.supplier_score),
        )
        db.add(p)
        outs.append(p)
    return outs


def _inventory_shortages(db: Session, org_id: UUID) -> list[Prediction]:
    outs: list[Prediction] = []
    rows = db.scalars(
        select(Inventory).where(Inventory.organization_id == org_id, Inventory.is_current.is_(True))
    ).all()
    at_risk = [r for r in rows if r.quantity <= r.reorder_point]
    for inv in at_risk[:8]:
        conf = 0.78 if inv.quantity <= inv.safety_stock else 0.65
        p = Prediction(
            organization_id=org_id,
            kind=PredictionKind.INVENTORY_SHORTAGE,
            title="Inventory shortage risk",
            confidence=conf,
            reasoning=(
                f"On-hand {inv.quantity} at or below reorder point {inv.reorder_point} "
                f"(safety stock {inv.safety_stock})."
            ),
            contributing_factors=[
                f"quantity={inv.quantity}",
                f"reorder_point={inv.reorder_point}",
                f"avg_daily_demand={inv.avg_daily_demand}",
            ],
            recommended_actions=[
                "Raise expedite PO",
                "Reallocate stock from sister warehouse",
                "Adjust safety stock policy",
            ],
            linked_entities=[
                {"type": "inventory", "id": str(inv.id)},
                {"type": "warehouse", "id": str(inv.warehouse_id)},
                {"type": "product", "id": str(inv.product_id)},
            ],
            horizon_hours=48,
            score=float(max(0, inv.reorder_point - inv.quantity) + 40),
        )
        db.add(p)
        outs.append(p)
    return outs


def _warehouse_congestion(db: Session, org_id: UUID) -> list[Prediction]:
    outs: list[Prediction] = []
    for w in db.scalars(select(Warehouse).where(Warehouse.organization_id == org_id)).all():
        util = w.utilization
        if util < 85:
            continue
        p = Prediction(
            organization_id=org_id,
            kind=PredictionKind.WAREHOUSE_CONGESTION,
            title=f"Warehouse congestion: {w.name}",
            confidence=0.72 if util < 95 else 0.88,
            reasoning=f"{w.name} utilization is {util:.0f}% of capacity {w.capacity}.",
            contributing_factors=[f"utilization={util}", f"capacity={w.capacity}"],
            recommended_actions=[
                "Defer non-critical inbound",
                "Open overflow lane",
                "Prioritize outbound waves",
            ],
            linked_entities=[{"type": "warehouse", "id": str(w.id), "label": w.name}],
            horizon_hours=36,
            score=float(util),
        )
        db.add(p)
        outs.append(p)
    return outs


def _demand_and_anomalies(db: Session, org_id: UUID) -> list[Prediction]:
    outs: list[Prediction] = []
    inv = db.scalars(
        select(Inventory)
        .where(Inventory.organization_id == org_id, Inventory.is_current.is_(True))
        .order_by(Inventory.avg_daily_demand.desc())
        .limit(3)
    ).all()
    for row in inv:
        if row.avg_daily_demand <= 0:
            continue
        days_cover = row.quantity / row.avg_daily_demand if row.avg_daily_demand else 999
        if days_cover > 10:
            continue
        p = Prediction(
            organization_id=org_id,
            kind=PredictionKind.DEMAND_SPIKE
            if row.avg_daily_demand >= 50
            else PredictionKind.LEAD_TIME_CHANGE,
            title="Demand pressure on inventory cover",
            confidence=0.7,
            reasoning=f"Days of cover ≈ {days_cover:.1f} at demand {row.avg_daily_demand:.1f}/day.",
            contributing_factors=[
                f"avg_daily_demand={row.avg_daily_demand}",
                f"quantity={row.quantity}",
            ],
            recommended_actions=["Pull-in PO", "Validate forecast assumptions"],
            linked_entities=[{"type": "inventory", "id": str(row.id)}],
            horizon_hours=96,
            score=float(100 - min(days_cover * 8, 90)),
        )
        db.add(p)
        outs.append(p)

    delayed = (
        db.scalar(
            select(Shipment)
            .where(
                Shipment.organization_id == org_id,
                Shipment.status == ShipmentStatus.DELAYED,
            )
            .limit(1)
        )
    )
    if delayed and delayed.delay_days >= 5:
        p = Prediction(
            organization_id=org_id,
            kind=PredictionKind.ANOMALY,
            title="Anomalous multi-day shipment delay",
            confidence=0.8,
            reasoning=f"{delayed.reference} delayed {delayed.delay_days} days — outside normal band.",
            contributing_factors=[f"delay_days={delayed.delay_days}"],
            recommended_actions=["Root-cause via timeline", "Escalate carrier"],
            linked_entities=[{"type": "shipment", "id": str(delayed.id), "label": delayed.reference}],
            horizon_hours=24,
            score=float(delayed.delay_days * 10),
        )
        db.add(p)
        outs.append(p)
    return outs


def _out(p: Prediction) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "kind": p.kind.value,
        "title": p.title,
        "confidence": None,
        "method": "rule_based",
        "calibration_status": "not_calibrated",
        "reasoning": p.reasoning,
        "contributing_factors": p.contributing_factors,
        "recommended_actions": p.recommended_actions,
        "linked_entities": p.linked_entities,
        "horizon_hours": p.horizon_hours,
        "score": p.score,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
