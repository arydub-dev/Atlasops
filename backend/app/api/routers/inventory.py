"""Inventory intelligence: warehouses, inventory monitoring, reorder recommendations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Inventory, Product, User, Warehouse
from app.schemas.entities import (
    InventoryEnriched,
    Page,
    WarehouseOut,
)
from app.services.inventory_logic import (
    days_of_supply,
    inventory_status,
    reorder_recommendation,
)
from app.services.metrics import inventory_health_breakdown

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Warehouse]:
    return list(db.scalars(select(Warehouse).order_by(Warehouse.name)).all())


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Warehouse:
    wh = db.get(Warehouse, warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh


@router.get("/health", response_model=dict)
def inventory_health(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return inventory_health_breakdown(db)


@router.get("/items", response_model=Page[InventoryEnriched])
def list_inventory(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str | None = Query(None, description="Search product name or SKU"),
    warehouse_id: int | None = None,
    status_filter: str | None = Query(None, alias="status", description="ok|low_stock|overstock|stockout"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[InventoryEnriched]:
    stmt = (
        select(Inventory, Warehouse, Product)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.is_current.is_(True))
    )
    if warehouse_id:
        stmt = stmt.where(Inventory.warehouse_id == warehouse_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

    # status filtering at SQL level for the common buckets
    if status_filter == "low_stock":
        stmt = stmt.where(Inventory.quantity <= Inventory.reorder_point, Inventory.quantity > 0)
    elif status_filter == "stockout":
        stmt = stmt.where(Inventory.quantity <= 0)
    elif status_filter == "overstock":
        stmt = stmt.where(Inventory.quantity >= Inventory.max_stock, Inventory.max_stock > 0)
    elif status_filter == "ok":
        stmt = stmt.where(
            Inventory.quantity > Inventory.reorder_point,
            or_(Inventory.max_stock == 0, Inventory.quantity < Inventory.max_stock),
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Inventory.quantity.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).all()

    items = [
        InventoryEnriched(
            id=inv.id,
            warehouse_id=inv.warehouse_id,
            warehouse_name=wh.name,
            product_id=inv.product_id,
            product_sku=prod.sku,
            product_name=prod.name,
            quantity=inv.quantity,
            reorder_point=inv.reorder_point,
            safety_stock=inv.safety_stock,
            max_stock=inv.max_stock,
            avg_daily_demand=inv.avg_daily_demand,
            days_of_supply=days_of_supply(inv.quantity, inv.avg_daily_demand),
            status=inventory_status(inv),
            reorder_recommendation=reorder_recommendation(inv),
        )
        for inv, wh, prod in rows
    ]
    return Page[InventoryEnriched](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/reorders", response_model=list[InventoryEnriched])
def reorder_recommendations(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
) -> list[InventoryEnriched]:
    rows = db.execute(
        select(Inventory, Warehouse, Product)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.is_current.is_(True), Inventory.quantity <= Inventory.reorder_point)
        .order_by((Inventory.reorder_point - Inventory.quantity).desc())
        .limit(limit)
    ).all()
    return [
        InventoryEnriched(
            id=inv.id,
            warehouse_id=inv.warehouse_id,
            warehouse_name=wh.name,
            product_id=inv.product_id,
            product_sku=prod.sku,
            product_name=prod.name,
            quantity=inv.quantity,
            reorder_point=inv.reorder_point,
            safety_stock=inv.safety_stock,
            max_stock=inv.max_stock,
            avg_daily_demand=inv.avg_daily_demand,
            days_of_supply=days_of_supply(inv.quantity, inv.avg_daily_demand),
            status=inventory_status(inv),
            reorder_recommendation=reorder_recommendation(inv),
        )
        for inv, wh, prod in rows
    ]
