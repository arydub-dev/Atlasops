"""Aggregate metric computations for dashboard and analytics endpoints.

All functions require ``organization_id`` for defense-in-depth tenant isolation
(in addition to PostgreSQL RLS when enabled).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from app.models import (
    Alert,
    Inventory,
    RiskAssessment,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import (
    AlertStatus,
    RiskLevel,
    ShipmentStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_kpis(db: Session, organization_id: UUID) -> dict:
    """Compute KPI dict with a small number of aggregate queries."""
    active_statuses = (
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.AT_WAREHOUSE,
        ShipmentStatus.CUSTOMS_HOLD,
    )
    shipment_row = db.execute(
        select(
            func.count(Shipment.id),
            func.sum(
                case((Shipment.status.in_(active_statuses), 1), else_=0)
            ),
            func.sum(case((Shipment.status == ShipmentStatus.DELAYED, 1), else_=0)),
            func.sum(case((Shipment.status == ShipmentStatus.DELIVERED, 1), else_=0)),
            func.sum(
                case(
                    (
                        (Shipment.status == ShipmentStatus.DELIVERED)
                        & (Shipment.delay_days <= 0),
                        1,
                    ),
                    else_=0,
                )
            ),
        ).where(Shipment.organization_id == organization_id)
    ).one()
    total, active, delayed, delivered, on_time = (
        int(shipment_row[0] or 0),
        int(shipment_row[1] or 0),
        int(shipment_row[2] or 0),
        int(shipment_row[3] or 0),
        int(shipment_row[4] or 0),
    )
    on_time_rate = round((on_time / delivered) * 100, 1) if delivered else 0.0

    inv_row = db.execute(
        select(
            func.count(Inventory.id),
            func.sum(
                case((Inventory.quantity <= Inventory.reorder_point, 1), else_=0)
            ),
        ).where(
            Inventory.organization_id == organization_id,
            Inventory.is_current.is_(True),
        )
    ).one()
    inv_total = int(inv_row[0] or 0)
    at_risk = int(inv_row[1] or 0)
    inventory_health = round((1 - (at_risk / inv_total)) * 100, 1) if inv_total else 100.0

    supplier_reliability = (
        db.scalar(
            select(func.avg(Supplier.supplier_score)).where(
                Supplier.organization_id == organization_id
            )
        )
        or 0.0
    )
    open_alerts = (
        db.scalar(
            select(func.count(Alert.id)).where(
                Alert.organization_id == organization_id,
                Alert.status != AlertStatus.RESOLVED,
            )
        )
        or 0
    )
    critical_risks = (
        db.scalar(
            select(func.count(RiskAssessment.id)).where(
                RiskAssessment.organization_id == organization_id,
                RiskAssessment.level == RiskLevel.CRITICAL,
            )
        )
        or 0
    )

    return {
        "total_shipments": total,
        "active_shipments": active,
        "delayed_shipments": delayed,
        "on_time_delivery_rate": on_time_rate,
        "inventory_health_score": inventory_health,
        "supplier_reliability_score": round(float(supplier_reliability), 1),
        "open_alerts": int(open_alerts),
        "critical_risks": int(critical_risks),
    }


def shipment_trend(db: Session, organization_id: UUID, weeks: int = 12) -> list[dict]:
    """Weekly shipped vs delivered counts via SQL grouping."""
    since = _utcnow() - timedelta(weeks=weeks)
    # Portable week key: ISO year-week as string via strftime-compatible approach.
    # SQLite: strftime('%Y-%W'); Postgres: to_char. Use Python bucketing on
    # date_trunc-equivalent by selecting shipped_at only for portability... 
    # Prefer dialect-aware expression.
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        week_expr = func.to_char(Shipment.shipped_at, "IYYY-\"W\"IW")
    else:
        # SQLite approximate ISO week
        week_expr = func.strftime("%Y-W%W", Shipment.shipped_at)

    rows = db.execute(
        select(
            week_expr.label("label"),
            func.count(Shipment.id).label("shipped"),
            func.sum(
                case((Shipment.status == ShipmentStatus.DELIVERED, 1), else_=0)
            ).label("delivered"),
            func.sum(
                case(
                    (
                        (Shipment.status == ShipmentStatus.DELAYED)
                        | (Shipment.delay_days > 0),
                        1,
                    ),
                    else_=0,
                )
            ).label("delayed"),
        )
        .where(
            Shipment.organization_id == organization_id,
            Shipment.shipped_at >= since,
        )
        .group_by(week_expr)
        .order_by(week_expr)
    ).all()
    return [
        {
            "label": r.label,
            "shipped": int(r.shipped or 0),
            "delivered": int(r.delivered or 0),
            "delayed": int(r.delayed or 0),
        }
        for r in rows
    ]


def delay_trend(db: Session, organization_id: UUID, weeks: int = 12) -> list[dict]:
    since = _utcnow() - timedelta(weeks=weeks)
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        week_expr = func.to_char(Shipment.shipped_at, "IYYY-\"W\"IW")
    else:
        week_expr = func.strftime("%Y-W%W", Shipment.shipped_at)

    rows = db.execute(
        select(
            week_expr.label("label"),
            func.avg(Shipment.delay_days).label("avg_delay"),
            func.count(Shipment.id).label("n"),
            func.sum(case((Shipment.delay_days > 0, 1), else_=0)).label("delayed_n"),
        )
        .where(
            Shipment.organization_id == organization_id,
            Shipment.shipped_at >= since,
        )
        .group_by(week_expr)
        .order_by(week_expr)
    ).all()
    out = []
    for r in rows:
        n = int(r.n or 0)
        delayed_n = int(r.delayed_n or 0)
        out.append(
            {
                "label": r.label,
                "avg_delay_days": round(float(r.avg_delay or 0), 2),
                "delayed_pct": round(delayed_n / n * 100, 1) if n else 0.0,
            }
        )
    return out


def inventory_trend(db: Session, organization_id: UUID, weeks: int = 12) -> list[dict]:
    """Current utilization snapshot repeated as a short series (no synthetic wobble).

    Historical utilization requires warehouse snapshots (roadmap). Until then we
    return a flat series of the live utilization so charts still render without
    fabricating seasonal noise.
    """
    warehouses = db.scalars(
        select(Warehouse).where(Warehouse.organization_id == organization_id)
    ).all()
    if not warehouses:
        return []
    base_util = sum(w.utilization for w in warehouses) / len(warehouses)
    label = _week_key(_utcnow())
    return [{"label": label, "utilization": round(base_util, 1)}]


def supplier_performance_trend(
    db: Session, organization_id: UUID, months: int = 6
) -> list[dict]:
    """Live supplier averages only — no fabricated historical wobble."""
    avg_score = (
        db.scalar(
            select(func.avg(Supplier.supplier_score)).where(
                Supplier.organization_id == organization_id
            )
        )
    )
    avg_reliability = (
        db.scalar(
            select(func.avg(Supplier.delivery_reliability)).where(
                Supplier.organization_id == organization_id
            )
        )
    )
    if avg_score is None or avg_reliability is None:
        return []
    label = _utcnow().strftime("%b %Y")
    return [
        {
            "label": label,
            "supplier_score": round(float(avg_score), 1),
            "delivery_reliability": round(float(avg_reliability), 1),
        }
    ]


def inventory_health_breakdown(db: Session, organization_id: UUID) -> dict:
    """Classify current inventory lines with a single SQL aggregate."""
    row = db.execute(
        select(
            func.sum(case((Inventory.quantity <= 0, 1), else_=0)).label("stockout"),
            func.sum(
                case(
                    (
                        (Inventory.quantity > 0)
                        & (Inventory.quantity <= Inventory.reorder_point),
                        1,
                    ),
                    else_=0,
                )
            ).label("low_stock"),
            func.sum(
                case(
                    (
                        (Inventory.max_stock > 0)
                        & (Inventory.quantity >= Inventory.max_stock),
                        1,
                    ),
                    else_=0,
                )
            ).label("overstock"),
            func.count(Inventory.id).label("total"),
        ).where(
            Inventory.organization_id == organization_id,
            Inventory.is_current.is_(True),
        )
    ).one()
    stockout = int(row.stockout or 0)
    low_stock = int(row.low_stock or 0)
    overstock = int(row.overstock or 0)
    total = int(row.total or 0)
    ok = max(total - stockout - low_stock - overstock, 0)
    return {
        "ok": ok,
        "low_stock": low_stock,
        "overstock": overstock,
        "stockout": stockout,
    }


def _week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
