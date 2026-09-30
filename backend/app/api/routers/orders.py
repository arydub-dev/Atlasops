"""Canonical orders + operational events (procurement / demand spine)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import OperationalEvent, PurchaseOrder, SalesOrder
from app.models.enums import OperationalEventType, OrderStatus
from app.tenancy.context import TenantContext

router = APIRouter(tags=["Orders & Events"])


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    status: str
    supplier_id: UUID | None = None
    warehouse_id: UUID | None = None
    currency: str
    total_amount: float
    ordered_at: datetime | None = None
    expected_at: datetime | None = None
    external_id: str | None = None
    line_items: list = Field(default_factory=list)
    created_at: datetime


class SalesOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    status: str
    customer_name: str | None = None
    warehouse_id: UUID | None = None
    shipment_id: UUID | None = None
    currency: str
    total_amount: float
    ordered_at: datetime | None = None
    promised_at: datetime | None = None
    external_id: str | None = None
    line_items: list = Field(default_factory=list)
    created_at: datetime


class OperationalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    title: str
    message: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    severity: str
    occurred_at: datetime
    payload: dict = Field(default_factory=dict)


class PurchaseOrderCreate(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    supplier_id: UUID | None = None
    warehouse_id: UUID | None = None
    total_amount: float = 0
    currency: str = "USD"
    line_items: list = Field(default_factory=list)
    status: OrderStatus = OrderStatus.OPEN


class SalesOrderCreate(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    customer_name: str | None = None
    warehouse_id: UUID | None = None
    total_amount: float = 0
    currency: str = "USD"
    line_items: list = Field(default_factory=list)
    status: OrderStatus = OrderStatus.OPEN


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("suppliers.read")),
    limit: int = Query(50, ge=1, le=200),
) -> list[PurchaseOrder]:
    return list(
        db.scalars(
            select(PurchaseOrder)
            .where(PurchaseOrder.organization_id == ctx.organization_id)
            .order_by(PurchaseOrder.created_at.desc())
            .limit(limit)
        ).all()
    )


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("suppliers.create")),
) -> PurchaseOrder:
    row = PurchaseOrder(
        organization_id=ctx.organization_id,
        reference=payload.reference,
        status=payload.status,
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        total_amount=payload.total_amount,
        currency=payload.currency,
        line_items=payload.line_items,
    )
    db.add(row)
    db.flush()
    db.add(
        OperationalEvent(
            organization_id=ctx.organization_id,
            event_type=OperationalEventType.INGEST,
            title=f"Purchase order {payload.reference} created",
            entity_type="purchase_order",
            entity_id=row.id,
            severity="info",
            payload={"reference": payload.reference},
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/sales-orders", response_model=list[SalesOrderOut])
def list_sales_orders(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("shipments.read")),
    limit: int = Query(50, ge=1, le=200),
) -> list[SalesOrder]:
    return list(
        db.scalars(
            select(SalesOrder)
            .where(SalesOrder.organization_id == ctx.organization_id)
            .order_by(SalesOrder.created_at.desc())
            .limit(limit)
        ).all()
    )


@router.post("/sales-orders", response_model=SalesOrderOut, status_code=201)
def create_sales_order(
    payload: SalesOrderCreate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("shipments.create")),
) -> SalesOrder:
    row = SalesOrder(
        organization_id=ctx.organization_id,
        reference=payload.reference,
        status=payload.status,
        customer_name=payload.customer_name,
        warehouse_id=payload.warehouse_id,
        total_amount=payload.total_amount,
        currency=payload.currency,
        line_items=payload.line_items,
    )
    db.add(row)
    db.flush()
    db.add(
        OperationalEvent(
            organization_id=ctx.organization_id,
            event_type=OperationalEventType.INGEST,
            title=f"Sales order {payload.reference} created",
            entity_type="sales_order",
            entity_id=row.id,
            severity="info",
            payload={"reference": payload.reference},
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/events", response_model=list[OperationalEventOut])
def list_operational_events(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
    limit: int = Query(100, ge=1, le=500),
) -> list[OperationalEvent]:
    return list(
        db.scalars(
            select(OperationalEvent)
            .where(OperationalEvent.organization_id == ctx.organization_id)
            .order_by(OperationalEvent.occurred_at.desc())
            .limit(limit)
        ).all()
    )
