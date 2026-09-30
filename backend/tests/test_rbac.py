"""RBAC: viewer cannot write."""
from __future__ import annotations


def test_viewer_can_read_shipments(viewer_client, shipment_a, org_a):
    org, _ = org_a
    r = viewer_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 200
    assert any(i["id"] == str(shipment_a.id) for i in r.json()["items"])


def test_viewer_cannot_update_shipment(viewer_client, shipment_a, org_a):
    org, _ = org_a
    r = viewer_client.patch(
        f"/api/v1/shipments/{shipment_a.id}/status",
        headers={"X-Organization-Id": str(org.id)},
        json={"status": "delivered"},
    )
    assert r.status_code == 403
    assert "shipments.update" in r.json()["detail"]


def test_owner_can_update_shipment(owner_client, shipment_a, org_a):
    org, _ = org_a
    r = owner_client.patch(
        f"/api/v1/shipments/{shipment_a.id}/status",
        headers={"X-Organization-Id": str(org.id)},
        json={"status": "delivered", "current_location": "Dock 4"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "delivered"
