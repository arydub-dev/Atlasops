"""Supplier intelligence: ranking, scorecards, comparison, trends."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import Shipment, Supplier
from app.models.enums import ShipmentStatus
from app.schemas.entities import SupplierOut, SupplierScorecard
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("suppliers.read")),
    q: str | None = Query(None),
    sort_by: str = Query("supplier_score"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> list[Supplier]:
    stmt = select(Supplier).where(Supplier.organization_id == ctx.organization_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Supplier.name.ilike(like) | Supplier.country.ilike(like))
    column = getattr(Supplier, sort_by, Supplier.supplier_score)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc())
    return list(db.scalars(stmt).all())


@router.get("/ranking", response_model=list[SupplierScorecard])
def supplier_ranking(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("suppliers.read")),
    limit: int = Query(50, ge=1, le=100),
) -> list[SupplierScorecard]:
    org_id = ctx.organization_id
    suppliers = list(
        db.scalars(
            select(Supplier)
            .where(Supplier.organization_id == org_id)
            .order_by(Supplier.supplier_score.desc())
            .limit(limit)
        ).all()
    )
    if not suppliers:
        return []

    supplier_ids = [s.id for s in suppliers]
    agg_rows = db.execute(
        select(
            Shipment.supplier_id,
            func.count(Shipment.id),
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
        )
        .where(
            Shipment.organization_id == org_id,
            Shipment.supplier_id.in_(supplier_ids),
        )
        .group_by(Shipment.supplier_id)
    ).all()
    aggregates = {
        sid: {
            "total": int(total or 0),
            "delayed": int(delayed or 0),
            "delivered": int(delivered or 0),
            "on_time": int(on_time or 0),
        }
        for sid, total, delayed, delivered, on_time in agg_rows
    }

    now_label = datetime.now(timezone.utc).strftime("%b %Y")
    cards: list[SupplierScorecard] = []
    for i, supplier in enumerate(suppliers):
        stats = aggregates.get(
            supplier.id, {"total": 0, "delayed": 0, "delivered": 0, "on_time": 0}
        )
        delivered = stats["delivered"]
        on_time_rate = (
            round(stats["on_time"] / delivered * 100, 1) if delivered else 0.0
        )
        cards.append(
            SupplierScorecard(
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
                rank=i + 1,
                total_shipments=stats["total"],
                delayed_shipments=stats["delayed"],
                on_time_rate=on_time_rate,
                monthly_trend=[
                    {
                        "label": now_label,
                        "score": round(supplier.supplier_score, 1),
                        "reliability": round(supplier.delivery_reliability, 1),
                    }
                ],
            )
        )
    return cards


@router.get("/compare", response_model=list[SupplierScorecard])
def compare_suppliers(
    ids: str = Query(..., description="Comma-separated supplier UUIDs"),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("suppliers.read")),
) -> list[SupplierScorecard]:
    try:
        id_list = [UUID(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="ids must be comma-separated UUIDs") from exc
    suppliers = db.scalars(
        select(Supplier).where(
            Supplier.organization_id == ctx.organization_id,
            Supplier.id.in_(id_list),
        )
    ).all()
    cards = []
    for s in suppliers:
        higher = db.scalar(
            select(func.count(Supplier.id)).where(
                Supplier.organization_id == ctx.organization_id,
                Supplier.supplier_score > s.supplier_score,
            )
        ) or 0
        cards.append(_scorecard(db, s, rank=higher + 1, org_id=ctx.organization_id))
    return cards


@router.get("/{supplier_id}/scorecard", response_model=SupplierScorecard)
def supplier_scorecard(
    supplier_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("suppliers.read")),
) -> SupplierScorecard:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == ctx.organization_id,
        )
    )
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    higher = db.scalar(
        select(func.count(Supplier.id)).where(
            Supplier.organization_id == ctx.organization_id,
            Supplier.supplier_score > supplier.supplier_score,
        )
    ) or 0
    return _scorecard(db, supplier, rank=higher + 1, org_id=ctx.organization_id)


def _scorecard(db: Session, supplier: Supplier, rank: int, org_id: UUID) -> SupplierScorecard:
    row = db.execute(
        select(
            func.count(Shipment.id),
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
        ).where(
            Shipment.organization_id == org_id,
            Shipment.supplier_id == supplier.id,
        )
    ).one()
    total = int(row[0] or 0)
    delayed = int(row[1] or 0)
    delivered = int(row[2] or 0)
    on_time = int(row[3] or 0)
    on_time_rate = round(on_time / delivered * 100, 1) if delivered else 0.0

    # Current-only point — no fabricated historical wobble (matches metrics.py)
    now_label = datetime.now(timezone.utc).strftime("%b %Y")
    trend = [
        {
            "label": now_label,
            "score": round(supplier.supplier_score, 1),
            "reliability": round(supplier.delivery_reliability, 1),
        }
    ]

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
