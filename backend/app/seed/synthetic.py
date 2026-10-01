"""Optional demo sandbox seed for FEATURE_DEMO_SANDBOX only.

Never runs on production startup. Creates one org with sample operational data
for sales demos — not used as default product data.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.identity.orgs import create_organization
from app.models import (
    Alert,
    Inventory,
    Product,
    PurchaseOrder,
    RiskAssessment,
    SalesOrder,
    Shipment,
    ShipmentEvent,
    Supplier,
    User,
    Warehouse,
)
from app.models.enums import (
    AlertPriority,
    AlertStatus,
    AlertType,
    OrderStatus,
    RiskCategory,
    RiskLevel,
    ShipmentStatus,
    WarehouseRiskLevel,
)

logger = logging.getLogger("supply.seed")
fake = Faker()
Faker.seed(42)
random.seed(42)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_seeded(db: Session, organization_id: UUID | None = None) -> bool:
    q = select(func.count()).select_from(Supplier)
    if organization_id:
        q = q.where(Supplier.organization_id == organization_id)
    return (db.scalar(q) or 0) > 0


def seed_sandbox(
    db: Session,
    *,
    owner_email: str = "demo@example.com",
    org_name: str = "Demo Manufacturing Co",
    n_suppliers: int = 12,
    n_warehouses: int = 6,
    n_products: int = 40,
    n_shipments: int = 80,
) -> dict:
    """Create a sandbox org + sample data. Idempotent per owner email org name."""
    user = db.scalar(select(User).where(User.email == owner_email.lower()))
    if user is None:
        user = User(email=owner_email.lower(), full_name="Demo Owner", is_active=True)
        db.add(user)
        db.flush()

    org, _membership = create_organization(db, name=org_name, owner=user)
    if is_seeded(db, org.id):
        return {"organization_id": str(org.id), "skipped": True}

    org_id = org.id
    suppliers: list[Supplier] = []
    for _ in range(n_suppliers):
        s = Supplier(
            organization_id=org_id,
            name=fake.company(),
            country=fake.country(),
            region=fake.state(),
            category=random.choice(["raw_materials", "components", "packaging", "finished"]),
            supplier_score=round(random.uniform(55, 98), 1),
            delivery_reliability=round(random.uniform(70, 99), 1),
            average_delay_days=round(random.uniform(0, 8), 1),
            order_fulfillment_rate=round(random.uniform(80, 99), 1),
            defect_rate=round(random.uniform(0.1, 5), 2),
        )
        db.add(s)
        suppliers.append(s)
    db.flush()

    warehouses: list[Warehouse] = []
    for i in range(n_warehouses):
        w = Warehouse(
            organization_id=org_id,
            name=f"DC-{i+1:02d} {fake.city()}",
            location=f"{fake.city()}, {fake.country_code()}",
            region=fake.state(),
            latitude=float(fake.latitude()),
            longitude=float(fake.longitude()),
            capacity=random.randint(50_000, 250_000),
            current_inventory=0,
            risk_level=random.choice(list(WarehouseRiskLevel)),
        )
        db.add(w)
        warehouses.append(w)
    db.flush()

    products: list[Product] = []
    for i in range(n_products):
        p = Product(
            organization_id=org_id,
            sku=f"SKU-{i+1:05d}",
            name=fake.catch_phrase()[:80],
            category=random.choice(["electronics", "apparel", "industrial", "consumables"]),
            unit_cost=round(random.uniform(2, 400), 2),
            unit_price=round(random.uniform(5, 800), 2),
            lead_time_days=random.randint(3, 45),
            supplier_id=random.choice(suppliers).id,
        )
        db.add(p)
        products.append(p)
    db.flush()

    for w in warehouses:
        total = 0
        for p in random.sample(products, k=min(20, len(products))):
            qty = random.randint(50, 5000)
            total += qty
            db.add(
                Inventory(
                    organization_id=org_id,
                    warehouse_id=w.id,
                    product_id=p.id,
                    quantity=qty,
                    reorder_point=max(20, qty // 10),
                    safety_stock=max(10, qty // 20),
                    max_stock=qty * 2,
                    avg_daily_demand=round(random.uniform(1, 80), 2),
                    is_current=True,
                )
            )
        w.current_inventory = total

    statuses = list(ShipmentStatus)
    for i in range(n_shipments):
        status = random.choice(statuses)
        shipped = _utcnow() - timedelta(days=random.randint(1, 40))
        eta = shipped + timedelta(days=random.randint(3, 21))
        sh = Shipment(
            organization_id=org_id,
            reference=f"SHP-{org.slug[:8].upper()}-{i+1:05d}",
            origin=fake.city(),
            destination=fake.city(),
            carrier=random.choice(["UPS", "FedEx", "DHL", "Maersk"]),
            current_location=fake.city(),
            status=status,
            delay_risk_score=round(random.uniform(0, 100), 1),
            units=random.randint(10, 2000),
            value_usd=round(random.uniform(1000, 250000), 2),
            shipped_at=shipped,
            eta=eta,
            delivered_at=eta if status == ShipmentStatus.DELIVERED else None,
            delay_days=round(random.uniform(0, 10), 1) if status == ShipmentStatus.DELAYED else 0,
            supplier_id=random.choice(suppliers).id,
            warehouse_id=random.choice(warehouses).id,
            product_id=random.choice(products).id,
            tracking_number=f"1Z{fake.bothify('??????????').upper()}",
        )
        db.add(sh)
        db.flush()
        db.add(
            ShipmentEvent(
                organization_id=org_id,
                shipment_id=sh.id,
                status=status,
                location=sh.current_location,
                note="Sandbox seed event",
                occurred_at=shipped,
            )
        )

    for _ in range(15):
        db.add(
            Alert(
                organization_id=org_id,
                alert_type=random.choice(list(AlertType)),
                priority=random.choice(list(AlertPriority)),
                status=AlertStatus.OPEN,
                title=fake.sentence(nb_words=6)[:80],
                message=fake.paragraph(nb_sentences=2),
            )
        )

    # Deterministic disruption spine: worst supplier → POs → delayed shipments → SO exposure
    disruption = apply_disruption_scenario(
        db,
        organization_id=org_id,
        suppliers=suppliers,
        warehouses=warehouses,
    )

    db.commit()
    counts = {
        "organization_id": str(org_id),
        "suppliers": n_suppliers,
        "warehouses": n_warehouses,
        "products": n_products,
        "shipments": n_shipments,
        "owner_email": owner_email,
        "disruption_supplier": disruption.get("supplier_name"),
    }
    logger.info("Sandbox seeded: %s", counts)
    return counts


def apply_disruption_scenario(
    db: Session,
    *,
    organization_id: UUID,
    suppliers: list[Supplier] | None = None,
    warehouses: list[Warehouse] | None = None,
) -> dict:
    """Overlay a realistic supplier-delay disruption on an existing org.

    Safe to call repeatedly: creates additional PO/SO/alert/risk rows keyed by
    a stable disruption marker in meta/title rather than wiping tenant data.
    """
    if suppliers is None:
        suppliers = list(
            db.scalars(select(Supplier).where(Supplier.organization_id == organization_id)).all()
        )
    if warehouses is None:
        warehouses = list(
            db.scalars(select(Warehouse).where(Warehouse.organization_id == organization_id)).all()
        )
    if not suppliers or not warehouses:
        return {"skipped": True, "reason": "missing_suppliers_or_warehouses"}

    worst = min(suppliers, key=lambda s: s.supplier_score)
    worst.delivery_reliability = 62.0
    worst.average_delay_days = 5.0
    worst.supplier_score = 55.0

    delayed = list(
        db.scalars(
            select(Shipment).where(
                Shipment.organization_id == organization_id,
                Shipment.supplier_id == worst.id,
            )
        ).all()
    )[:5]
    for sh in delayed:
        sh.status = ShipmentStatus.DELAYED
        sh.delay_days = 5.0
        sh.delay_risk_score = 88.0

    existing_po = db.scalar(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(
            PurchaseOrder.organization_id == organization_id,
            PurchaseOrder.reference.like("PO-DX-%"),
        )
    )

    if not existing_po:
        for i in range(6):
            db.add(
                PurchaseOrder(
                    organization_id=organization_id,
                    reference=f"PO-DX-{organization_id.hex[:6].upper()}-{i+1:04d}",
                    status=OrderStatus.OPEN if i < 4 else OrderStatus.CONFIRMED,
                    supplier_id=worst.id if i < 3 else random.choice(suppliers).id,
                    warehouse_id=random.choice(warehouses).id,
                    currency="USD",
                    total_amount=round(random.uniform(8000, 120000), 2),
                    ordered_at=_utcnow() - timedelta(days=random.randint(2, 20)),
                    expected_at=_utcnow() + timedelta(days=random.randint(3, 25)),
                    line_items=[],
                    meta={"seed": True, "disruption": True},
                )
            )
        for i in range(5):
            db.add(
                SalesOrder(
                    organization_id=organization_id,
                    reference=f"SO-DX-{organization_id.hex[:6].upper()}-{i+1:04d}",
                    status=OrderStatus.OPEN if i < 3 else OrderStatus.IN_FULFILLMENT,
                    customer_name=fake.company(),
                    warehouse_id=random.choice(warehouses).id,
                    shipment_id=delayed[i].id if i < len(delayed) else None,
                    currency="USD",
                    total_amount=round(random.uniform(5000, 90000), 2),
                    ordered_at=_utcnow() - timedelta(days=random.randint(1, 14)),
                    promised_at=_utcnow() + timedelta(days=random.randint(2, 18)),
                    line_items=[],
                    meta={"seed": True, "disruption": True},
                )
            )

    alert_title = f"{worst.name} delayed by 5 days"
    existing_alert = db.scalar(
        select(Alert).where(
            Alert.organization_id == organization_id,
            Alert.title == alert_title,
        )
    )
    existing_risk = db.scalar(
        select(RiskAssessment).where(
            RiskAssessment.organization_id == organization_id,
            RiskAssessment.title == f"Supplier delay: {worst.name}",
        )
    )
    if existing_alert is None:
        db.add(
            Alert(
                organization_id=organization_id,
                alert_type=AlertType.SUPPLIER_FAILURE_RISK,
                priority=AlertPriority.CRITICAL,
                status=AlertStatus.OPEN,
                title=alert_title,
                message=(
                    f"Supplier {worst.name} is reporting a 5-day slip. "
                    f"Downstream shipments, POs, and customer orders are exposed."
                ),
                entity_type="supplier",
                entity_id=worst.id,
            )
        )

    if existing_risk is None:
        db.add(
            RiskAssessment(
                organization_id=organization_id,
                category=RiskCategory.SUPPLIER,
                level=RiskLevel.CRITICAL,
                title=f"Supplier delay: {worst.name}",
                description=(
                    f"{worst.name} reliability {worst.delivery_reliability}% with "
                    f"{worst.average_delay_days} day average delay."
                ),
                score=88.0,
                recommendation=(
                    "Expedite high-value shipments, activate backup supplier capacity, "
                    "and simulate a 10-day delay before committing mitigation spend."
                ),
                entity_type="supplier",
                entity_id=worst.id,
                factors={
                    "delivery_reliability": worst.delivery_reliability,
                    "average_delay_days": worst.average_delay_days,
                    "concentration": "high",
                },
            )
        )

    return {
        "supplier_id": str(worst.id),
        "supplier_name": worst.name,
        "delayed_shipments": len(delayed),
    }


# Back-compat aliases used by older admin paths
seed_all = seed_sandbox
