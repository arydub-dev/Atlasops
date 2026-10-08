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
    from app.models import Warehouse
    assert db.scalar(select(Warehouse).where(Warehouse.organization_id == org_a[0].id)).current_inventory == 20


def test_shipment_eta_update_and_incident_progress(owner_client, db, org_a):
    upload(owner_client, "shipments", "reference,origin,destination,carrier,eta\nSHP-1042,Mumbai,Bengaluru,Demo Freight,2026-10-12T00:00:00Z\n")
    raw = b"reference,origin,destination,carrier,eta\nSHP-1042,Mumbai,Bengaluru,Demo Freight,2026-10-15T00:00:00Z\n"
    for _ in range(2):
        response = owner_client.post('/api/v1/data/import/commit', data={
            'entity':'shipments','mode':'update', 'mapping':json.dumps({k:k for k in ['reference','origin','destination','carrier','eta']})},
            files={'file':('shipment-update.csv', raw, 'text/csv')})
        assert response.status_code == 200, response.text
        assert response.json()['rows_imported'] == 1
    from app.models import Shipment
    set_session_org(db, org_a[0].id)
    shipments = db.scalars(select(Shipment).where(Shipment.organization_id == org_a[0].id)).all()
    assert len(shipments) == 1
    from datetime import timezone
    eta = shipments[0].eta
    eta = eta.replace(tzinfo=timezone.utc) if eta.tzinfo is None else eta.astimezone(timezone.utc)
    assert eta.isoformat() == '2026-10-15T00:00:00+00:00'
    incident = owner_client.post('/api/v1/incidents', json={'title':'ETA requires review', 'severity':'high'}).json()
    path = '/api/v1/incidents/' + incident['id']
    assert owner_client.patch(path, json={'status':'mitigating'}).status_code == 409
    response = owner_client.patch(path, json={'status':'investigating','assign_to_me':True})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'investigating'
    assert response.json()['owner_user_id']
    assert owner_client.patch(path, json={'status':'mitigating'}).status_code == 200
    assert owner_client.post(path+'/resolve', json={'resolution':'Planner confirmed new ETA'}).status_code == 200
    assert owner_client.patch(path, json={'status':'investigating'}).status_code == 409


def test_repeated_product_update_preserves_unmapped_fields(owner_client, db, org_a):
    from app.models import Product
    upload(owner_client, "products", "sku,name,unit_cost,unit_price,category,lead_time_days\nDAILY-1,Part,10,20,Spare,7\n")
    payload = {"entity":"products", "mode":"update", "mapping":json.dumps({k:k for k in ("sku", "name", "unit_cost", "unit_price")})}
    raw = b"sku,name,unit_cost,unit_price\nDAILY-1,Updated part,11,22\n"
    for _ in range(2):
        response = owner_client.post("/api/v1/data/import/commit", data=payload,
            files={"file":("daily.csv", io.BytesIO(raw), "text/csv")})
        assert response.status_code == 200, response.text
        assert response.json()["rows_imported"] == 1
    set_session_org(db, org_a[0].id)
    rows = db.scalars(select(Product).where(Product.organization_id == org_a[0].id)).all()
    assert len(rows) == 1
    assert (rows[0].unit_price, rows[0].category, rows[0].lead_time_days) == (22, "Spare", 7)
    rows[0].external_id = "external-system"
    db.commit()
    response = owner_client.post("/api/v1/data/import/commit", data=payload,
        files={"file":("daily.csv", io.BytesIO(raw), "text/csv")})
    assert response.json()["rows_rejected"] == 1
    assert "Connector-managed" in response.json()["errors"][0]["errors"][0]


def test_inventory_import_rejects_ambiguous_warehouse(owner_client):
    upload(owner_client, "warehouses", "name,location,region,capacity\nSame,Chicago,US,1000\n")
    upload(owner_client, "warehouses", "name,location,region,capacity\nSAME,Boston,US,1000\n")
    upload(owner_client, "products", "sku,name,unit_cost,unit_price\nP,Part,1,2\n")
    response = owner_client.post('/api/v1/data/import/commit', data={
        'entity':'inventory', 'mapping':json.dumps({k:k for k in ['warehouse_name','product_sku','quantity']})},
        files={'file':('inventory.csv', b'warehouse_name,product_sku,quantity\nSame,P,10\n', 'text/csv')})
    assert response.status_code == 200
    assert response.json()['rows_rejected'] == 1
    assert 'ambiguous' in response.json()['errors'][0]['errors'][0]


def test_inventory_outcome_counts_reconcile(owner_client):
    upload(owner_client, "warehouses", "name,location,region,capacity\nDC,Chicago,US,1000\n")
    upload(owner_client, "products", "sku,name,unit_cost,unit_price\nP,Part,1,2\n")
    header = 'warehouse_name,product_sku,quantity\n'
    first = upload(owner_client, 'inventory', header + 'DC,P,10\n')
    again = upload(owner_client, 'inventory', header + 'DC,P,10\n')
    changed = upload(owner_client, 'inventory', header + 'DC,P,20\n')
    assert first['outcomes'] == {'created':1, 'updated':0, 'unchanged':0}
    assert again['outcomes'] == {'created':0, 'updated':0, 'unchanged':1}
    assert changed['outcomes'] == {'created':0, 'updated':1, 'unchanged':0}
