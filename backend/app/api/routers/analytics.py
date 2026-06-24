"""Analytics Hub: delivery, supplier, inventory and forecast analytics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Inventory, Product, Shipment, Supplier, User, Warehouse
from app.models.enums import ShipmentStatus
from app.services import metrics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/delivery", response_model=dict)
def delivery_performance(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    status_counts = dict(
        db.execute(select(Shipment.status, func.count(Shipment.id)).group_by(Shipment.status)).all()
    )
    carrier_rows = db.execute(
        select(
            Shipment.carrier,
            func.count(Shipment.id),
            func.avg(Shipment.delay_days),
        ).group_by(Shipment.carrier)
    ).all()
    carriers = [
        {
            "carrier": c,
            "shipments": n,
            "avg_delay_days": round(float(avg or 0), 2),
        }
        for c, n, avg in sorted(carrier_rows, key=lambda x: x[1], reverse=True)
    ]
    return {
        "status_breakdown": {k.value: v for k, v in status_counts.items()},
        "shipment_trend": metrics.shipment_trend(db),
        "delay_trend": metrics.delay_trend(db),
        "carrier_performance": carriers,
    }


@router.get("/suppliers", response_model=dict)
def supplier_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    region_rows = db.execute(
        select(
            Supplier.region,
            func.avg(Supplier.supplier_score),
            func.avg(Supplier.delivery_reliability),
            func.count(Supplier.id),
        ).group_by(Supplier.region)
    ).all()
    regions = [
        {
            "region": r,
            "avg_score": round(float(score or 0), 1),
            "avg_reliability": round(float(rel or 0), 1),
            "suppliers": n,
        }
        for r, score, rel, n in region_rows
    ]
    top = db.scalars(select(Supplier).order_by(Supplier.supplier_score.desc()).limit(10)).all()
    bottom = db.scalars(select(Supplier).order_by(Supplier.supplier_score.asc()).limit(10)).all()
    return {
        "performance_trend": metrics.supplier_performance_trend(db),
        "by_region": regions,
        "top_performers": [{"name": s.name, "score": round(s.supplier_score, 1)} for s in top],
        "bottom_performers": [{"name": s.name, "score": round(s.supplier_score, 1)} for s in bottom],
    }


@router.get("/inventory", response_model=dict)
def inventory_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    # Heat map: utilization per warehouse region
    wh_rows = db.execute(
        select(
            Warehouse.region,
            func.avg(Warehouse.current_inventory * 100.0 / Warehouse.capacity),
            func.count(Warehouse.id),
        ).group_by(Warehouse.region)
    ).all()
    heatmap = [
        {"region": r, "avg_utilization": round(float(util or 0), 1), "warehouses": n}
        for r, util, n in wh_rows
    ]
    category_rows = db.execute(
        select(Product.category, func.sum(Inventory.quantity))
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.category)
    ).all()
    by_category = [
        {"category": c, "units": int(qty or 0)}
        for c, qty in sorted(category_rows, key=lambda x: x[1] or 0, reverse=True)
    ]
    return {
        "health_breakdown": metrics.inventory_health_breakdown(db),
        "utilization_trend": metrics.inventory_trend(db),
        "utilization_heatmap": heatmap,
        "inventory_by_category": by_category,
    }


@router.get("/forecast", response_model=dict)
def forecast_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    horizon_weeks: int = Query(8, ge=2, le=26),
) -> dict:
    """Simple demand forecast extrapolated from recent shipment volume."""
    history = metrics.shipment_trend(db, weeks=12)
    recent = [h["shipped"] for h in history[-6:]] or [0]
    avg = sum(recent) / len(recent) if recent else 0
    # linear trend slope from recent points
    slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1) if len(recent) > 1 else 0

    forecast = []
    last_label_dt = datetime.now(timezone.utc)
    for i in range(1, horizon_weeks + 1):
        dt = last_label_dt + timedelta(weeks=i)
        iso = dt.isocalendar()
        projected = max(0, avg + slope * i)
        # widen confidence band with horizon
        band = projected * (0.08 + 0.02 * i)
        forecast.append(
            {
                "label": f"{iso.year}-W{iso.week:02d}",
                "projected_demand": round(projected, 1),
                "lower": round(max(0, projected - band), 1),
                "upper": round(projected + band, 1),
            }
        )
    return {
        "history": history,
        "forecast": forecast,
        "method": "trend-extrapolation",
        "avg_weekly_volume": round(avg, 1),
    }
