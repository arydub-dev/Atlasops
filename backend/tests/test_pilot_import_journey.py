"""Representative file-based pilot: import, reconcile, act, refresh."""
import io
import json
from sqlalchemy import select
from app.models import Inventory
from app.tenancy.rls import set_session_org


def upload(client, entity, text):
    raw = text.encode()
    preview = client.post("/api/v1/data/import/preview", data={"entity": entity},
        files={"file": (entity + ".csv", io.BytesIO(raw), "text/csv")})
    assert preview.status_code == 200, preview.text
    response = client.post("/api/v1/data/import/commit",
        data={"entity":entity, "mapping":json.dumps(preview.json()["suggested_mapping"])},
        files={"file": (entity + ".csv", io.BytesIO(raw), "text/csv")})
    assert response.status_code == 200, response.text
    assert response.json()["rows_imported"] == 1, response.text
    return response.json()


def test_import_to_reorder_incident_and_inventory_refresh(owner_client, db, org_a):
    upload(owner_client, "warehouses", "name,location,region,capacity\nPilot DC,Chicago,US,1000\n")
    upload(owner_client, "products", "sku,name,unit_cost,unit_price\nPILOT-1,Replacement part,10,20\n")
    header = "warehouse_name,product_sku,quantity,reorder_point,safety_stock,max_stock,avg_daily_demand\n"
    upload(owner_client, "inventory", header + "Pilot DC,PILOT-1,5,10,2,30,1\n")
    low = owner_client.get("/api/v1/inventory/items?status=low_stock").json()
    assert low["total"] == 1
    item = low["items"][0]
    assert item["days_of_supply"] == 5
    assert item["reorder_recommendation"] == 25
    incident = owner_client.post("/api/v1/incidents", json={"title":"Replenish pilot part", "severity":"high"})
    assert incident.status_code == 201, incident.text
    incident_id = incident.json()["id"]
    resolved = owner_client.post(f"/api/v1/incidents/{incident_id}/resolve", json={"resolution":"Planner reviewed and approved replenishment"})
    assert resolved.status_code == 200, resolved.text
    # The next file is a current snapshot, not an additional stock position.
    upload(owner_client, "inventory", header + "Pilot DC,PILOT-1,20,10,2,30,1\n")
    items = owner_client.get("/api/v1/inventory/items").json()
    assert items["total"] == 1
    assert items["items"][0]["id"] == item["id"]
    assert items["items"][0]["quantity"] == 20
    assert items["items"][0]["reorder_recommendation"] == 0
    assert owner_client.get("/api/v1/inventory/health").json() == {"ok":1,"low_stock":0,"overstock":0,"stockout":0}
    set_session_org(db, org_a[0].id)
    assert len(db.scalars(select(Inventory).where(Inventory.organization_id == org_a[0].id)).all()) == 1
