"""Shipment management endpoints: list/search/filter/sort, detail, status updates."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db_with_tenant, require_permission
from app.models import AuditLog, Shipment, ShipmentEvent, Supplier, Warehouse
from app.models.enums import ShipmentStatus
from app.schemas.entities import (
    Page,
    ShipmentDetail,
    ShipmentEventOut,
    ShipmentOut,
    ShipmentStatusUpdate,
)
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/shipments", tags=["Shipments"])

_SORTABLE = {
    "eta": Shipment.eta,
    "shipped_at": Shipment.shipped_at,
    "delay_risk_score": Shipment.delay_risk_score,
    "value_usd": Shipment.value_usd,
    "delay_days": Shipment.delay_days,
    "reference": Shipment.reference,
}


@router.get("", response_model=Page[ShipmentOut])
def list_shipments(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("shipments.read")),
    q: str | None = Query(None, description="Search reference, origin, destination, carrier, location"),
    status_filter: ShipmentStatus | None = Query(None, alias="status"),
    supplier_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    sort_by: str = Query("eta"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[ShipmentOut]:
    stmt = select(Shipment).where(Shipment.organization_id == ctx.organization_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Shipment.reference.ilike(like),
                Shipment.origin.ilike(like),
                Shipment.destination.ilike(like),
                Shipment.carrier.ilike(like),
                Shipment.current_location.ilike(like),
            )
        )
    if status_filter:
        stmt = stmt.where(Shipment.status == status_filter)
    if supplier_id:
        stmt = stmt.where(Shipment.supplier_id == supplier_id)
    if warehouse_id:
        stmt = stmt.where(Shipment.warehouse_id == warehouse_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    column = _SORTABLE.get(sort_by, Shipment.eta)
    order = asc(column) if sort_dir == "asc" else desc(column)
    stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())

    return Page[ShipmentOut](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{shipment_id}", response_model=ShipmentDetail)
def get_shipment(
    shipment_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("shipments.read")),
) -> ShipmentDetail:
    shipment = db.scalar(
        select(Shipment)
        .options(selectinload(Shipment.events))
        .where(
            Shipment.id == shipment_id,
            Shipment.organization_id == ctx.organization_id,
        )
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    supplier = (
        db.scalar(
            select(Supplier).where(
                Supplier.id == shipment.supplier_id,
                Supplier.organization_id == ctx.organization_id,
            )
        )
        if shipment.supplier_id
        else None
    )
    warehouse = (
        db.scalar(
            select(Warehouse).where(
                Warehouse.id == shipment.warehouse_id,
                Warehouse.organization_id == ctx.organization_id,
            )
        )
        if shipment.warehouse_id
        else None
    )
    events = sorted(shipment.events, key=lambda e: e.occurred_at, reverse=True)
    detail = ShipmentDetail.model_validate(shipment)
    detail.supplier_name = supplier.name if supplier else None
    detail.warehouse_name = warehouse.name if warehouse else None
    detail.events = [ShipmentEventOut.model_validate(e) for e in events]
    return detail


@router.patch("/{shipment_id}/status", response_model=ShipmentDetail)
def update_status(
    shipment_id: UUID,
    payload: ShipmentStatusUpdate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("shipments.update")),
) -> ShipmentDetail:
    shipment = db.scalar(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.organization_id == ctx.organization_id,
        )
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    shipment.status = payload.status
    if payload.current_location:
        shipment.current_location = payload.current_location
    if payload.status == ShipmentStatus.DELIVERED and shipment.delivered_at is None:
        shipment.delivered_at = datetime.now(timezone.utc)

    db.add(
        ShipmentEvent(
            organization_id=ctx.organization_id,
            shipment_id=shipment.id,
            status=payload.status,
            location=payload.current_location or shipment.current_location,
            note=payload.note,
        )
    )
    db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="update_status",
            resource="shipment",
            resource_id=str(shipment.id),
            detail=f"{shipment.reference} -> {payload.status.value}",
        )
    )
    db.commit()
    db.refresh(shipment)
    return get_shipment(shipment.id, db, ctx)
