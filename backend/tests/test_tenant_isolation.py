"""Tenant isolation: two orgs cannot see each other's operational data."""
from __future__ import annotations


def test_org_a_sees_only_own_shipments(owner_client, shipment_a, shipment_b, org_a):
    org, _ = org_a
    r = owner_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    ids = {item["id"] for item in body["items"]}
    assert str(shipment_a.id) in ids
    assert str(shipment_b.id) not in ids


def test_org_b_cannot_fetch_org_a_shipment(org_b_client, shipment_a, org_b):
    org, _membership, _user = org_b
    r = org_b_client.get(
        f"/api/v1/shipments/{shipment_a.id}",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 404


def test_org_b_list_excludes_org_a(org_b_client, shipment_a, shipment_b, org_b):
    org, _membership, _user = org_b
    r = org_b_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert ids == {str(shipment_b.id)}


def test_spoofed_org_header_cannot_access_other_tenant(
    owner_client, org_a, org_b, shipment_b
):
    """User of org A must not read org B data by spoofing X-Organization-Id."""
    org_a_row, _ = org_a
    org_b_row, _, _ = org_b
    r = owner_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert r.status_code in {403, 400, 404}
    r2 = owner_client.get(
        f"/api/v1/shipments/{shipment_b.id}",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert r2.status_code in {403, 400, 404}
    ok = owner_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org_a_row.id)},
    )
    assert ok.status_code == 200


def test_cross_org_suppliers_and_alerts_isolated(db, org_a, org_b):
    """Separate TestClients so session cookies do not overwrite each other."""
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.identity.sessions import create_session
    from app.main import app

    org_a_row, _ = org_a
    org_b_row, membership_b, user_b = org_b
    # owner of org_a is membership via create_organization — resolve user from membership
    from app.models import Membership, User
    from sqlalchemy import select

    mem_a = db.scalar(
        select(Membership).where(Membership.organization_id == org_a_row.id)
    )
    user_a = db.get(User, mem_a.user_id)

    with TestClient(app) as client_a, TestClient(app) as client_b:
        _s, raw_a = create_session(db, user=user_a, organization_id=org_a_row.id)
        _s2, raw_b = create_session(db, user=user_b, organization_id=org_b_row.id)
        db.commit()
        client_a.cookies.set(get_settings().SESSION_COOKIE_NAME, raw_a)
        client_b.cookies.set(get_settings().SESSION_COOKIE_NAME, raw_b)
        for path in ("/api/v1/suppliers", "/api/v1/alerts", "/api/v1/risks", "/api/v1/simulations"):
            a = client_a.get(path, headers={"X-Organization-Id": str(org_a_row.id)})
            b = client_b.get(path, headers={"X-Organization-Id": str(org_b_row.id)})
            assert a.status_code == 200, f"{path} a={a.text}"
            assert b.status_code == 200, f"{path} b={b.text}"
