"""Synthetic data engine.

Generates a realistic enterprise supply-chain dataset:
  - default users (one per role)
  - 50 suppliers
  - 100 products
  - 25 warehouses
  - 5,000 shipments (+ shipment events)
  - current inventory (warehouse x product) + historical snapshots (~100,000 rows)

Deterministic via a fixed random seed so demos are reproducible. Uses bulk
inserts for the high-volume tables to keep seeding fast.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Inventory,
    Product,
    Shipment,
    ShipmentEvent,
    Supplier,
    User,
    Warehouse,
)
from app.models.enums import (
    ShipmentStatus,
    UserRole,
    WarehouseRiskLevel,
)
from app.services import alert_engine, risk_engine

SEED = 42
fake = Faker()

CARRIERS = [
    "Maersk Line", "DHL Global", "FedEx Freight", "UPS Supply Chain", "Kuehne+Nagel",
    "DB Schenker", "Expeditors", "CMA CGM", "Hapag-Lloyd", "Nippon Express",
]
CATEGORIES = [
    "Electronics", "Industrial", "Automotive", "Consumer Goods", "Pharmaceuticals",
    "Raw Materials", "Apparel", "Food & Beverage", "Aerospace", "Chemicals",
]
REGIONS = ["North America", "Europe", "APAC", "LATAM", "Middle East", "Africa"]
COUNTRIES = {
    "North America": ["United States", "Canada", "Mexico"],
    "Europe": ["Germany", "Netherlands", "France", "Poland", "United Kingdom"],
    "APAC": ["China", "Vietnam", "India", "Japan", "South Korea", "Taiwan"],
    "LATAM": ["Brazil", "Chile", "Colombia"],
    "Middle East": ["UAE", "Saudi Arabia", "Turkey"],
    "Africa": ["South Africa", "Egypt", "Morocco"],
}
CITIES = [
    ("Los Angeles", 34.05, -118.24), ("Newark", 40.73, -74.17), ("Chicago", 41.88, -87.63),
    ("Rotterdam", 51.92, 4.48), ("Hamburg", 53.55, 9.99), ("Shanghai", 31.23, 121.47),
    ("Shenzhen", 22.54, 114.06), ("Singapore", 1.35, 103.82), ("Mumbai", 19.08, 72.88),
    ("Dubai", 25.20, 55.27), ("Sao Paulo", -23.55, -46.63), ("Tokyo", 35.68, 139.69),
    ("Busan", 35.18, 129.08), ("Antwerp", 51.22, 4.40), ("Houston", 29.76, -95.37),
    ("Atlanta", 33.75, -84.39), ("Memphis", 35.15, -90.05), ("Dallas", 32.78, -96.80),
    ("Felixstowe", 51.96, 1.35), ("Gdansk", 54.35, 18.65), ("Veracruz", 19.17, -96.13),
    ("Santos", -23.96, -46.33), ("Jebel Ali", 25.01, 55.06), ("Kaohsiung", 22.62, 120.27),
    ("Ho Chi Minh City", 10.82, 106.63),
]

DEFAULT_USERS = [
    ("admin@scc.io", "Avery Admin", UserRole.ADMIN, "admin1234"),
    ("ops@scc.io", "Morgan Ops", UserRole.OPERATIONS_MANAGER, "ops12345"),
    ("analyst@scc.io", "Riley Analyst", UserRole.ANALYST, "analyst123"),
    ("exec@scc.io", "Jordan Exec", UserRole.EXECUTIVE, "exec12345"),
]


def is_seeded(db: Session) -> bool:
    return (db.scalar(select(func.count(Supplier.id))) or 0) > 0


def seed_all(
    db: Session,
    *,
    n_suppliers: int = 50,
    n_products: int = 100,
    n_warehouses: int = 25,
    n_shipments: int = 5000,
    inventory_history_snapshots: int = 39,
    verbose: bool = True,
) -> dict:
    rng = random.Random(SEED)
    Faker.seed(SEED)

    def log(msg: str) -> None:
        if verbose:
            print(f"[seed] {msg}", flush=True)

    counts: dict[str, int] = {}

    # ---- Users ----
    counts["users"] = _seed_users(db)
    log(f"users: {counts['users']}")

    # ---- Suppliers ----
    suppliers = _seed_suppliers(db, rng, n_suppliers)
    counts["suppliers"] = len(suppliers)
    log(f"suppliers: {len(suppliers)}")

    # ---- Warehouses ----
    warehouses = _seed_warehouses(db, rng, n_warehouses)
    counts["warehouses"] = len(warehouses)
    log(f"warehouses: {len(warehouses)}")

    # ---- Products ----
    products = _seed_products(db, rng, n_products, suppliers)
    counts["products"] = len(products)
    log(f"products: {len(products)}")

    # ---- Inventory (current + historical) ----
    counts["inventory"] = _seed_inventory(
        db, rng, warehouses, products, inventory_history_snapshots, log
    )
    log(f"inventory: {counts['inventory']}")

    # ---- Shipments + events ----
    counts["shipments"] = _seed_shipments(db, rng, n_shipments, suppliers, warehouses, products, log)
    log(f"shipments: {counts['shipments']}")

    # ---- Risk + alerts ----
    counts["risk_assessments"] = risk_engine.recompute_all(db)
    counts["alerts"] = alert_engine.generate_alerts(db)
    log(f"risk_assessments: {counts['risk_assessments']}, alerts: {counts['alerts']}")

    return counts


def _seed_users(db: Session) -> int:
    created = 0
    for email, name, role, password in DEFAULT_USERS:
        if db.scalar(select(User).where(User.email == email)):
            continue
        db.add(
            User(
                email=email,
                full_name=name,
                role=role,
                hashed_password=hash_password(password),
                is_active=True,
            )
        )
        created += 1
    db.commit()
    return created


def _seed_suppliers(db: Session, rng: random.Random, n: int) -> list[Supplier]:
    suppliers = []
    for _ in range(n):
        region = rng.choice(REGIONS)
        country = rng.choice(COUNTRIES[region])
        # Bias most suppliers to be decent, with a tail of poor performers.
        base = rng.gauss(82, 12)
        score = max(20.0, min(99.0, base))
        reliability = max(40.0, min(99.5, score + rng.gauss(3, 5)))
        s = Supplier(
            name=f"{fake.company()} {rng.choice(['Industries', 'Group', 'Logistics', 'Manufacturing', 'Trading'])}",
            country=country,
            region=region,
            category=rng.choice(CATEGORIES),
            supplier_score=round(score, 1),
            delivery_reliability=round(reliability, 1),
            average_delay_days=round(max(0.0, (100 - score) / 18 + rng.uniform(0, 1.5)), 1),
            order_fulfillment_rate=round(max(60.0, min(99.9, score + rng.gauss(2, 4))), 1),
            defect_rate=round(max(0.1, (100 - score) / 22 + rng.uniform(0, 1.0)), 2),
            is_active=rng.random() > 0.04,
        )
        suppliers.append(s)
    db.add_all(suppliers)
    db.commit()
    for s in suppliers:
        db.refresh(s)
    return suppliers


def _seed_warehouses(db: Session, rng: random.Random, n: int) -> list[Warehouse]:
    warehouses = []
    cities = CITIES.copy()
    rng.shuffle(cities)
    for i in range(n):
        city, lat, lon = cities[i % len(cities)]
        region = rng.choice(REGIONS)
        capacity = rng.choice([50_000, 75_000, 100_000, 150_000, 200_000, 250_000])
        util = rng.gauss(0.72, 0.16)
        util = max(0.08, min(0.99, util))
        current = int(capacity * util)
        if util >= 0.9:
            risk = WarehouseRiskLevel.HIGH
        elif util >= 0.8 or util <= 0.15:
            risk = WarehouseRiskLevel.MEDIUM
        else:
            risk = WarehouseRiskLevel.LOW
        warehouses.append(
            Warehouse(
                name=f"{city} DC-{i + 1:02d}",
                location=f"{city}",
                region=region,
                latitude=lat + rng.uniform(-0.05, 0.05),
                longitude=lon + rng.uniform(-0.05, 0.05),
                capacity=capacity,
                current_inventory=current,
                risk_level=risk,
            )
        )
    db.add_all(warehouses)
    db.commit()
    for w in warehouses:
        db.refresh(w)
    return warehouses


def _seed_products(
    db: Session, rng: random.Random, n: int, suppliers: list[Supplier]
) -> list[Product]:
    products = []
    for i in range(n):
        category = rng.choice(CATEGORIES)
        cost = round(rng.uniform(5, 800), 2)
        price = round(cost * rng.uniform(1.25, 2.4), 2)
        products.append(
            Product(
                sku=f"SKU-{category[:3].upper()}-{i + 1:04d}",
                name=f"{fake.color_name()} {fake.word().capitalize()} {category[:-1] if category.endswith('s') else category}",
                category=category,
                unit_cost=cost,
                unit_price=price,
                lead_time_days=rng.choice([7, 10, 14, 21, 30, 45]),
                supplier_id=rng.choice(suppliers).id,
            )
        )
    db.add_all(products)
    db.commit()
    for p in products:
        db.refresh(p)
    return products


def _seed_inventory(
    db: Session,
    rng: random.Random,
    warehouses: list[Warehouse],
    products: list[Product],
    history_snapshots: int,
    log,
) -> int:
    """Create one current row per (warehouse, product) plus historical snapshots.

    Uses bulk_insert_mappings for throughput. Returns total inventory rows.
    """
    now = datetime.now(timezone.utc)
    current_rows: list[dict] = []
    # Per-product demand profile keeps snapshots coherent over time.
    demand_profile: dict[int, float] = {
        p.id: round(max(0.5, rng.gauss(18, 12)), 1) for p in products
    }

    for w in warehouses:
        for p in products:
            avg_demand = demand_profile[p.id] * rng.uniform(0.5, 1.5)
            avg_demand = round(max(0.2, avg_demand), 1)
            safety_stock = int(avg_demand * rng.uniform(5, 12))
            reorder_point = safety_stock + int(avg_demand * rng.uniform(4, 10))
            max_stock = reorder_point + int(avg_demand * rng.uniform(25, 60))
            # Distribute states: ~12% low/stockout, ~10% overstock, rest healthy.
            roll = rng.random()
            if roll < 0.06:
                qty = 0
            elif roll < 0.12:
                qty = rng.randint(1, max(1, reorder_point))
            elif roll < 0.22:
                qty = rng.randint(max_stock, int(max_stock * 1.2))
            else:
                qty = rng.randint(reorder_point + 1, max_stock)
            current_rows.append(
                {
                    "warehouse_id": w.id,
                    "product_id": p.id,
                    "quantity": qty,
                    "reorder_point": reorder_point,
                    "safety_stock": safety_stock,
                    "max_stock": max_stock,
                    "avg_daily_demand": avg_demand,
                    "snapshot_date": now,
                    "is_current": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    db.bulk_insert_mappings(Inventory, current_rows)
    db.commit()
    total = len(current_rows)

    # Historical snapshots: vary quantity around the current value with seasonality.
    history_rows: list[dict] = []
    batch = 0
    for snap in range(1, history_snapshots + 1):
        snap_date = now - timedelta(weeks=snap)
        seasonal = 1.0 + 0.18 * (rng.random() - 0.5) - 0.01 * snap
        for row in current_rows:
            base_qty = row["quantity"] or row["reorder_point"]
            qty = max(0, int(base_qty * seasonal * rng.uniform(0.7, 1.3)))
            history_rows.append(
                {
                    "warehouse_id": row["warehouse_id"],
                    "product_id": row["product_id"],
                    "quantity": qty,
                    "reorder_point": row["reorder_point"],
                    "safety_stock": row["safety_stock"],
                    "max_stock": row["max_stock"],
                    "avg_daily_demand": row["avg_daily_demand"],
                    "snapshot_date": snap_date,
                    "is_current": False,
                    "created_at": snap_date,
                    "updated_at": snap_date,
                }
            )
            if len(history_rows) >= 20_000:
                db.bulk_insert_mappings(Inventory, history_rows)
                db.commit()
                total += len(history_rows)
                batch += 1
                log(f"  inventory history batch {batch} ({total} rows)")
                history_rows = []
    if history_rows:
        db.bulk_insert_mappings(Inventory, history_rows)
        db.commit()
        total += len(history_rows)
    return total


def _seed_shipments(
    db: Session,
    rng: random.Random,
    n: int,
    suppliers: list[Supplier],
    warehouses: list[Warehouse],
    products: list[Product],
    log,
) -> int:
    now = datetime.now(timezone.utc)
    status_weights = [
        (ShipmentStatus.DELIVERED, 0.52),
        (ShipmentStatus.IN_TRANSIT, 0.24),
        (ShipmentStatus.DELAYED, 0.10),
        (ShipmentStatus.AT_WAREHOUSE, 0.08),
        (ShipmentStatus.CUSTOMS_HOLD, 0.06),
    ]
    statuses = [s for s, _ in status_weights]
    weights = [w for _, w in status_weights]
    city_names = [c[0] for c in CITIES]

    shipment_rows: list[dict] = []
    for i in range(n):
        supplier = rng.choice(suppliers)
        warehouse = rng.choice(warehouses)
        product = rng.choice(products)
        status = rng.choices(statuses, weights=weights, k=1)[0]
        origin = rng.choice(city_names)
        destination = warehouse.location

        shipped_at = now - timedelta(days=rng.randint(1, 120), hours=rng.randint(0, 23))
        transit_days = rng.randint(5, 45)
        eta = shipped_at + timedelta(days=transit_days)

        # delay behavior influenced by supplier reliability
        reliability_gap = max(0.0, (95 - supplier.delivery_reliability)) / 95
        delay_days = 0.0
        delivered_at = None
        current_location = rng.choice(city_names)

        if status == ShipmentStatus.DELIVERED:
            on_time = rng.random() > (0.18 + reliability_gap * 0.5)
            delay_days = 0.0 if on_time else round(rng.uniform(0.5, 9), 1)
            delivered_at = eta + timedelta(days=delay_days)
            current_location = destination
        elif status == ShipmentStatus.DELAYED:
            delay_days = round(rng.uniform(1, 14), 1)
            eta = now + timedelta(days=rng.randint(1, 10))
        elif status == ShipmentStatus.AT_WAREHOUSE:
            current_location = destination
        elif status == ShipmentStatus.CUSTOMS_HOLD:
            current_location = rng.choice(city_names)
            delay_days = round(rng.uniform(0.5, 6), 1)

        risk = _delay_risk(status, supplier.delivery_reliability, delay_days, rng)
        units = rng.randint(50, 5000)
        value = round(units * product.unit_price * rng.uniform(0.8, 1.2), 2)

        shipment_rows.append(
            {
                "reference": f"SHP-{shipped_at.year}-{i + 1:05d}",
                "origin": origin,
                "destination": destination,
                "carrier": rng.choice(CARRIERS),
                "current_location": current_location,
                "status": status,
                "delay_risk_score": risk,
                "units": units,
                "value_usd": value,
                "shipped_at": shipped_at,
                "eta": eta,
                "delivered_at": delivered_at,
                "delay_days": delay_days,
                "supplier_id": supplier.id,
                "warehouse_id": warehouse.id,
                "product_id": product.id,
                "created_at": shipped_at,
                "updated_at": now,
            }
        )

    db.bulk_insert_mappings(Shipment, shipment_rows)
    db.commit()
    log(f"  shipments inserted: {len(shipment_rows)}")

    # Events for a representative subset (latest 1,500 shipments) to keep volume sane.
    recent = db.scalars(
        select(Shipment).order_by(Shipment.id.desc()).limit(1500)
    ).all()
    event_rows: list[dict] = []
    for sh in recent:
        timeline = _event_timeline(sh, rng, city_names)
        for ev in timeline:
            event_rows.append(
                {
                    "shipment_id": sh.id,
                    "status": ev["status"],
                    "location": ev["location"],
                    "note": ev["note"],
                    "occurred_at": ev["occurred_at"],
                }
            )
    db.bulk_insert_mappings(ShipmentEvent, event_rows)
    db.commit()
    log(f"  shipment events inserted: {len(event_rows)}")
    return len(shipment_rows)


def _delay_risk(status, reliability, delay_days, rng) -> float:
    base = {
        ShipmentStatus.DELIVERED: 5,
        ShipmentStatus.AT_WAREHOUSE: 10,
        ShipmentStatus.IN_TRANSIT: 35,
        ShipmentStatus.CUSTOMS_HOLD: 65,
        ShipmentStatus.DELAYED: 85,
    }[status]
    score = base + (95 - reliability) * 0.4 + delay_days * 2 + rng.uniform(-5, 5)
    return round(max(0.0, min(100.0, score)), 1)


def _event_timeline(sh: Shipment, rng, city_names) -> list[dict]:
    events = []
    t = sh.shipped_at
    events.append(
        {"status": ShipmentStatus.IN_TRANSIT, "location": sh.origin, "note": "Departed origin", "occurred_at": t}
    )
    hops = rng.randint(1, 2)
    for _ in range(hops):
        t = t + timedelta(days=rng.randint(2, 8))
        events.append(
            {
                "status": ShipmentStatus.IN_TRANSIT,
                "location": rng.choice(city_names),
                "note": "In transit checkpoint",
                "occurred_at": t,
            }
        )
    if sh.status == ShipmentStatus.CUSTOMS_HOLD:
        t = t + timedelta(days=rng.randint(1, 4))
        events.append(
            {"status": ShipmentStatus.CUSTOMS_HOLD, "location": sh.current_location, "note": "Held at customs", "occurred_at": t}
        )
    elif sh.status == ShipmentStatus.DELAYED:
        t = t + timedelta(days=rng.randint(1, 5))
        events.append(
            {"status": ShipmentStatus.DELAYED, "location": sh.current_location, "note": "Delay reported by carrier", "occurred_at": t}
        )
    elif sh.status in (ShipmentStatus.DELIVERED, ShipmentStatus.AT_WAREHOUSE):
        if sh.delivered_at:
            events.append(
                {"status": sh.status, "location": sh.destination, "note": "Arrived at destination", "occurred_at": sh.delivered_at}
            )
    return events
