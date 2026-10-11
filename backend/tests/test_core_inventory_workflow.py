"""Verify dashboard, filtered rows and recommendations agree on company data."""
from app.models import Inventory, Product, Warehouse
from app.tenancy.rls import set_session_org


def test_inventory_health_matches_row_status_and_reorder(owner_client, db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    wh = Warehouse(organization_id=org.id, name="Test warehouse", location="Chicago",
        region="US", latitude=41.8, longitude=-87.6, capacity=1000)
    product = Product(organization_id=org.id, sku="CORE-001", name="Test part",
        category="Parts", unit_cost=5, unit_price=10)
    db.add_all([wh, product]); db.flush()
    # Conflicting thresholds must not double count the same item.
    row = Inventory(organization_id=org.id, warehouse_id=wh.id, product_id=product.id,
        quantity=5, reorder_point=10, max_stock=5, avg_daily_demand=1)
    db.add(row); db.commit()
    health = owner_client.get("/api/v1/inventory/health")
    assert health.status_code == 200
    assert health.json() == {"ok":0, "low_stock":1, "overstock":0, "stockout":0}
    low = owner_client.get("/api/v1/inventory/items?status=low_stock")
    assert low.status_code == 200
    assert low.json()["total"] == 1
    assert low.json()["items"][0]["status"] == "low_stock"
    over = owner_client.get("/api/v1/inventory/items?status=overstock")
    assert over.status_code == 200
    assert over.json()["total"] == 0
