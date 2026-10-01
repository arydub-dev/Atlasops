"""Phase B intelligence layer tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Alert, Shipment, Supplier, Warehouse
from app.models.enums import (
    AlertPriority,
    AlertStatus,
    AlertType,
    ShipmentStatus,
    WarehouseRiskLevel,
)
from app.services import graph, search as search_service, timeline
from app.tenancy.rls import set_session_org


def _utcnow():
    return datetime.now(timezone.utc)


def test_graph_neighbors_supplier(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    sup = Supplier(
        organization_id=org.id,
        name="Graph Supplier",
        country="US",
        region="NA",
        category="components",
        supplier_score=70,
        delivery_reliability=80,
        average_delay_days=1,
        defect_rate=1,
        is_active=True,
    )
    db.add(sup)
    db.flush()
    sh = Shipment(
        organization_id=org.id,
        reference="SH-GRAPH-1",
        origin="Shanghai",
        destination="LA",
        carrier="Ocean",
        current_location="Pacific",
        status=ShipmentStatus.IN_TRANSIT,
        supplier_id=sup.id,
        value_usd=10000,
        delay_days=0,
        shipped_at=_utcnow() - timedelta(days=3),
        eta=_utcnow() + timedelta(days=5),
    )
    db.add(sh)
    db.commit()

    nodes, edges = graph.neighbors(db, org.id, "supplier", sup.id)
    assert any(n.type == "shipment" for n in nodes)
    assert any(e.relation == "ships" for e in edges)

    traversed = graph.traverse(db, org.id, "supplier", sup.id, depth=2)
    assert traversed["stats"]["node_count"] >= 1


def test_timeline_includes_alerts(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    db.add(
        Alert(
            organization_id=org.id,
            alert_type=AlertType.DELAYED_SHIPMENT,
            priority=AlertPriority.HIGH,
            status=AlertStatus.OPEN,
            title="Timeline alert",
            message="delayed",
        )
    )
    db.commit()
    items = timeline.global_timeline(db, org.id, limit=20)
    assert any(i["title"] == "Timeline alert" for i in items)


def test_search_suppliers(db, org_a, owner_client):
    org, _ = org_a
    set_session_org(db, org.id)
    db.add(
        Supplier(
            organization_id=org.id,
            name="Acme Search Co",
            country="US",
            region="NA",
            category="raw",
            supplier_score=88,
            delivery_reliability=90,
            average_delay_days=0.5,
            defect_rate=0.2,
            is_active=True,
        )
    )
    db.commit()
    items = search_service.search(db, org.id, "Acme")
    assert any("Acme" in i["title"] for i in items)

    r = owner_client.get("/api/v1/search?q=Acme")
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_mission_control_v2_fields(owner_client):
    r = owner_client.get("/api/v1/mission-control")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "purchase_orders" in body
    assert "sales_orders" in body
    assert "operational_timeline" in body
    assert "connector_status" in body
    assert "graph" in body
    assert "upcoming_risks" in body


def test_incident_lifecycle(owner_client, db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    db.add(
        Alert(
            organization_id=org.id,
            alert_type=AlertType.SUPPLIER_FAILURE_RISK,
            priority=AlertPriority.CRITICAL,
            status=AlertStatus.OPEN,
            title="Supplier down",
            message="failure",
        )
    )
    db.commit()

    created = owner_client.post(
        "/api/v1/incidents",
        json={"title": "Supplier disruption incident", "severity": "critical"},
    )
    assert created.status_code == 201, created.text
    iid = created.json()["id"]

    detail = owner_client.get(f"/api/v1/incidents/{iid}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Supplier disruption incident"

    resolved = owner_client.post(
        f"/api/v1/incidents/{iid}/resolve",
        json={"resolution": "Alternate supplier activated"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_ai_orchestrate(owner_client):
    r = owner_client.post(
        "/api/v1/ai/orchestrate",
        json={"prompt": "Give me a mission summary of operations", "report_type": "orchestrate"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] in {"mission_summary", "operational_qa", "executive_report"}
    assert "response" in body
    assert "confidence" in body


def test_observability(owner_client):
    r = owner_client.get("/api/v1/observability/platform")
    assert r.status_code == 200
    assert "connectors" in r.json()
    assert "graph" in r.json()


def test_graph_api(owner_client, db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    wh = Warehouse(
        organization_id=org.id,
        name="Graph WH",
        location="Dallas",
        region="NA",
        capacity=1000,
        current_inventory=200,
        latitude=32.7,
        longitude=-96.8,
        risk_level=WarehouseRiskLevel.LOW,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)

    r = owner_client.get(f"/api/v1/graph/traverse/warehouse/{wh.id}?depth=2")
    assert r.status_code == 200
    assert "nodes" in r.json()


def test_timeline_api(owner_client):
    r = owner_client.get("/api/v1/timeline?limit=20")
    assert r.status_code == 200
    assert "items" in r.json()
