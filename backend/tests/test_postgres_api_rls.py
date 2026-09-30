"""Postgres API request-path RLS isolation — must see real shipment IDs.

Skipped on SQLite. Requires SUPPLY_CI_POSTGRES=1 + alembic-migrated database.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import engine
from app.identity.sessions import create_session
from app.main import app
from app.models import Membership, User
from app.tenancy.rls import ORG_GUC, set_session_org


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


pytestmark = [
    pytest.mark.skipif(
        os.environ.get("SUPPLY_CI_POSTGRES") != "1" or not _is_postgres(),
        reason="Postgres API RLS regression requires SUPPLY_CI_POSTGRES=1",
    ),
]


def _dual_clients(db, org_a, org_b):
    """Separate TestClients so session cookies do not overwrite each other."""
    org_a_row, _ = org_a
    org_b_row, _membership_b, user_b = org_b
    mem_a = db.scalar(
        select(Membership).where(Membership.organization_id == org_a_row.id)
    )
    user_a = db.get(User, mem_a.user_id)
    client_a = TestClient(app)
    client_b = TestClient(app)
    _s, raw_a = create_session(db, user=user_a, organization_id=org_a_row.id)
    _s2, raw_b = create_session(db, user=user_b, organization_id=org_b_row.id)
    db.commit()
    cookie = get_settings().SESSION_COOKIE_NAME
    client_a.cookies.set(cookie, raw_a)
    client_b.cookies.set(cookie, raw_b)
    return client_a, client_b, org_a_row, org_b_row


def test_set_local_guc_cleared_by_commit_but_restored_after_begin(db, org_a):
    """Document the commit/SET LOCAL interaction and verify after_begin restore."""
    org, _ = org_a
    set_session_org(db, org.id)
    assert db.execute(text("SELECT current_setting(:k, true)"), {"k": ORG_GUC}).scalar() == str(
        org.id
    )
    db.commit()
    restored = db.execute(text("SELECT current_setting(:k, true)"), {"k": ORG_GUC}).scalar()
    assert restored == str(org.id)


def test_api_request_path_returns_owned_shipment_ids(db, org_a, org_b, shipment_a, shipment_b):
    """GET /shipments must return concrete IDs for the caller's org only."""
    client_a, client_b, org_a_row, org_b_row = _dual_clients(db, org_a, org_b)

    a = client_a.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org_a_row.id)},
    )
    assert a.status_code == 200, a.text
    a_ids = {item["id"] for item in a.json()["items"]}
    assert str(shipment_a.id) in a_ids
    assert str(shipment_b.id) not in a_ids

    b = client_b.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert b.status_code == 200, b.text
    b_ids = {item["id"] for item in b.json()["items"]}
    assert str(shipment_b.id) in b_ids
    assert str(shipment_a.id) not in b_ids


def test_api_cross_org_detail_invisible(db, org_a, org_b, shipment_a, shipment_b):
    client_a, client_b, org_a_row, org_b_row = _dual_clients(db, org_a, org_b)

    ok_a = client_a.get(
        f"/api/v1/shipments/{shipment_a.id}",
        headers={"X-Organization-Id": str(org_a_row.id)},
    )
    assert ok_a.status_code == 200
    assert ok_a.json()["id"] == str(shipment_a.id)

    miss_b = client_a.get(
        f"/api/v1/shipments/{shipment_b.id}",
        headers={"X-Organization-Id": str(org_a_row.id)},
    )
    assert miss_b.status_code == 404

    ok_b = client_b.get(
        f"/api/v1/shipments/{shipment_b.id}",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert ok_b.status_code == 200
    assert ok_b.json()["id"] == str(shipment_b.id)

    miss_a = client_b.get(
        f"/api/v1/shipments/{shipment_a.id}",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert miss_a.status_code == 404


def test_api_spoofed_org_header_rejected(db, org_a, org_b, shipment_a, shipment_b):
    client_a, _client_b, org_a_row, org_b_row = _dual_clients(db, org_a, org_b)

    spoof_list = client_a.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert spoof_list.status_code in {403, 400, 404}

    spoof_detail = client_a.get(
        f"/api/v1/shipments/{shipment_b.id}",
        headers={"X-Organization-Id": str(org_b_row.id)},
    )
    assert spoof_detail.status_code in {403, 400, 404}

    ok = client_a.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org_a_row.id)},
    )
    assert ok.status_code == 200
    assert str(shipment_a.id) in {i["id"] for i in ok.json()["items"]}


def test_missing_tenant_guc_sees_zero_protected_rows(db, shipment_a):
    """Without app.current_org_id, FORCE RLS must hide tenant rows."""
    db.info.pop("rls_organization_id", None)
    db.execute(text("SELECT set_config(:k, '', true)"), {"k": ORG_GUC})
    count = db.execute(text("SELECT count(*) FROM shipments")).scalar()
    assert count == 0
