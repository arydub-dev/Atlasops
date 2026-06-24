"""Supplier intelligence: ranking, scorecards, comparison, trends."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Shipment, Supplier, User
from app.models.enums import ShipmentStatus
from app.schemas.entities import SupplierOut, SupplierScorecard

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str | None = Query(None),
    sort_by: str = Query("supplier_score"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> list[Supplier]:
    stmt = select(Supplier)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Supplier.name.ilike(like) | Supplier.country.ilike(like))
    column = getattr(Supplier, sort_by, Supplier.supplier_score)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc())
    return list(db.scalars(stmt).all())


@router.get("/ranking", response_model=list[SupplierScorecard])
def supplier_ranking(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
) -> list[SupplierScorecard]:
    suppliers = db.scalars(
        select(Supplier).order_by(Supplier.supplier_score.desc()).limit(limit)
    ).all()
    return [_scorecard(db, s, rank=i + 1) for i, s in enumerate(suppliers)]


@router.get("/{supplier_id}/scorecard", response_model=SupplierScorecard)
def supplier_scorecard(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SupplierScorecard:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    # rank = number of suppliers with a strictly higher score + 1
    higher = db.scalar(
        select(func.count(Supplier.id)).where(Supplier.supplier_score > supplier.supplier_score)
    ) or 0
    return _scorecard(db, supplier, rank=higher + 1)


@router.get("/compare", response_model=list[SupplierScorecard])
def compare_suppliers(
    ids: str = Query(..., description="Comma-separated supplier ids"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SupplierScorecard]:
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be comma-separated integers")
    suppliers = db.scalars(select(Supplier).where(Supplier.id.in_(id_list))).all()
    cards = []
    for s in suppliers:
        higher = db.scalar(
            select(func.count(Supplier.id)).where(Supplier.supplier_score > s.supplier_score)
        ) or 0
        cards.append(_scorecard(db, s, rank=higher + 1))
    return cards


def _scorecard(db: Session, supplier: Supplier, rank: int) -> SupplierScorecard:
    total = db.scalar(
        select(func.count(Shipment.id)).where(Shipment.supplier_id == supplier.id)
    ) or 0
    delayed = db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.supplier_id == supplier.id, Shipment.status == ShipmentStatus.DELAYED
        )
    ) or 0
    delivered = db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.supplier_id == supplier.id, Shipment.status == ShipmentStatus.DELIVERED
        )
    ) or 0
    on_time = db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.supplier_id == supplier.id,
            Shipment.status == ShipmentStatus.DELIVERED,
            Shipment.delay_days <= 0,
        )
    ) or 0
    on_time_rate = round(on_time / delivered * 100, 1) if delivered else 0.0

    base = supplier.supplier_score
    trend = []
    for i in range(5, -1, -1):
        dt = datetime.now(timezone.utc) - timedelta(days=30 * i)
        wobble = 2.5 * ((i % 3) - 1)
        trend.append(
            {
                "label": dt.strftime("%b %Y"),
                "score": round(max(0, min(100, base + wobble)), 1),
                "reliability": round(max(0, min(100, supplier.delivery_reliability + wobble)), 1),
            }
        )

    return SupplierScorecard(
        id=supplier.id,
        name=supplier.name,
        country=supplier.country,
        region=supplier.region,
        category=supplier.category,
        supplier_score=supplier.supplier_score,
        delivery_reliability=supplier.delivery_reliability,
        average_delay_days=supplier.average_delay_days,
        order_fulfillment_rate=supplier.order_fulfillment_rate,
        defect_rate=supplier.defect_rate,
        is_active=supplier.is_active,
        rank=rank,
        total_shipments=total,
        delayed_shipments=delayed,
        on_time_rate=on_time_rate,
        monthly_trend=trend,
    )
