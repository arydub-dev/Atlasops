"""Automatic alert generation from current operational state."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Inventory, Product, Shipment, Supplier, Warehouse
from app.models.enums import (
    AlertPriority,
    AlertStatus,
    AlertType,
    ShipmentStatus,
)
from app.tenancy.context import get_tenant


def _exists(
    db: Session,
    org_id: UUID,
    alert_type: AlertType,
    entity_type: str,
    entity_id: UUID,
) -> bool:
    return (
        db.scalar(
            select(func.count(Alert.id)).where(
                Alert.organization_id == org_id,
                Alert.alert_type == alert_type,
                Alert.entity_type == entity_type,
                Alert.entity_id == entity_id,
                Alert.status != AlertStatus.RESOLVED,
            )
        )
        > 0
    )


def generate_alerts(db: Session, *, deliver_notifications: bool = True) -> int:
    """Scan state and create alerts for open conditions. Returns count created."""
    org_id = get_tenant().organization_id
    new_alerts: list[Alert] = []

    delayed = db.scalars(
        select(Shipment)
        .where(
            Shipment.organization_id == org_id,
            Shipment.status == ShipmentStatus.DELAYED,
        )
        .order_by(Shipment.value_usd.desc())
        .limit(60)
    ).all()
    for sh in delayed:
        if _exists(db, org_id, AlertType.DELAYED_SHIPMENT, "shipment", sh.id):
            continue
        priority = (
            AlertPriority.CRITICAL
            if sh.value_usd > 250_000
            else AlertPriority.HIGH
            if sh.value_usd > 75_000
            else AlertPriority.MEDIUM
        )
        new_alerts.append(
            Alert(
                organization_id=org_id,
                alert_type=AlertType.DELAYED_SHIPMENT,
                priority=priority,
                status=AlertStatus.OPEN,
                title=f"Delayed shipment {sh.reference}",
                message=(
                    f"{sh.reference} ({sh.origin} -> {sh.destination}) is delayed by "
                    f"{sh.delay_days:.1f} days near {sh.current_location}. Value ${sh.value_usd:,.0f}."
                ),
                entity_type="shipment",
                entity_id=sh.id,
            )
        )

    low_stock = db.execute(
        select(Inventory, Warehouse.name, Product.name)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.organization_id == org_id,
            Inventory.is_current.is_(True),
            Inventory.quantity <= Inventory.reorder_point,
        )
        .order_by((Inventory.reorder_point - Inventory.quantity).desc())
        .limit(80)
    ).all()
    for inv, wh_name, prod_name in low_stock:
        if _exists(db, org_id, AlertType.INVENTORY_STOCKOUT_RISK, "inventory", inv.id):
            continue
        priority = AlertPriority.CRITICAL if inv.quantity <= 0 else AlertPriority.HIGH
        new_alerts.append(
            Alert(
                organization_id=org_id,
                alert_type=AlertType.INVENTORY_STOCKOUT_RISK,
                priority=priority,
                status=AlertStatus.OPEN,
                title=f"Stockout risk: {prod_name} @ {wh_name}",
                message=(
                    f"{prod_name} at {wh_name} is at {inv.quantity} units "
                    f"(reorder point {inv.reorder_point}). Recommend immediate replenishment."
                ),
                entity_type="inventory",
                entity_id=inv.id,
            )
        )

    weak_suppliers = db.scalars(
        select(Supplier)
        .where(
            Supplier.organization_id == org_id,
            Supplier.supplier_score < 55,
            Supplier.is_active.is_(True),
        )
        .order_by(Supplier.supplier_score.asc())
        .limit(25)
    ).all()
    for s in weak_suppliers:
        if _exists(db, org_id, AlertType.SUPPLIER_FAILURE_RISK, "supplier", s.id):
            continue
        priority = AlertPriority.CRITICAL if s.supplier_score < 40 else AlertPriority.HIGH
        new_alerts.append(
            Alert(
                organization_id=org_id,
                alert_type=AlertType.SUPPLIER_FAILURE_RISK,
                priority=priority,
                status=AlertStatus.OPEN,
                title=f"Supplier failure risk: {s.name}",
                message=(
                    f"{s.name} score {s.supplier_score:.0f}, reliability {s.delivery_reliability:.0f}%, "
                    f"defect rate {s.defect_rate:.1f}%. Activate contingency sourcing."
                ),
                entity_type="supplier",
                entity_id=s.id,
            )
        )

    spike_candidates = db.execute(
        select(Inventory, Product.name, Warehouse.name)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(
            Inventory.organization_id == org_id,
            Inventory.is_current.is_(True),
            Inventory.avg_daily_demand > 0,
            Inventory.quantity < Inventory.avg_daily_demand * 21,
        )
        .order_by(Inventory.avg_daily_demand.desc())
        .limit(25)
    ).all()
    for inv, prod_name, wh_name in spike_candidates:
        if _exists(db, org_id, AlertType.FORECASTED_DEMAND_SPIKE, "inventory", inv.id):
            continue
        new_alerts.append(
            Alert(
                organization_id=org_id,
                alert_type=AlertType.FORECASTED_DEMAND_SPIKE,
                priority=AlertPriority.MEDIUM,
                status=AlertStatus.OPEN,
                title=f"Inventory coverage risk: {prod_name} @ {wh_name}",
                message=(
                    f"{prod_name} at {wh_name} has only "
                    f"{inv.quantity / inv.avg_daily_demand:.0f} days of cover against recorded average demand "
                    f"({inv.avg_daily_demand:.0f}/day). Pre-build inventory."
                ),
                entity_type="inventory",
                entity_id=inv.id,
            )
        )

    db.add_all(new_alerts)
    db.flush()
    if new_alerts and deliver_notifications:
        from app.services.alert_channels import dispatch_new_alerts

        dispatch_new_alerts(db, new_alerts)
    db.commit()
    return len(new_alerts)
