"""Platform foundation: orders API, schedule parse, email skip, DLQ."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from app.connectors.schedule import (
    enqueue_due_connector_syncs,
    parse_sync_frequency,
    schedule_next,
)
from app.integrations import email as email_client
from app.integrations import flags
from app.models import Connection
from app.models.enums import ConnectorStatus, ConnectorType
from app.tenancy.rls import set_session_org


def test_parse_sync_frequency():
    assert parse_sync_frequency("15m") == timedelta(minutes=15)
    assert parse_sync_frequency("hourly") == timedelta(hours=1)
    assert parse_sync_frequency("2h") == timedelta(hours=2)
    assert parse_sync_frequency("daily") == timedelta(days=1)
    assert parse_sync_frequency("bogus") is None


def test_schedule_next_sets_future(db, org_a):
    org, _ = org_a
    conn = Connection(
        organization_id=org.id,
        name="Test",
        connector_type=ConnectorType.SALESFORCE,
        sync_frequency="1h",
    )
    db.add(conn)
    db.flush()
    nxt = schedule_next(conn)
    assert nxt is not None


def test_enqueue_due_connector_syncs_scans_orgs(db, org_a, org_b):
    """Cron must discover due connections via per-org RLS binding."""
    org1, _ = org_a
    org2, _, _ = org_b
    for org, name in ((org1, "A"), (org2, "B")):
        set_session_org(db, org.id)
        db.add(
            Connection(
                organization_id=org.id,
                name=f"Conn {name}",
                connector_type=ConnectorType.SALESFORCE,
                status=ConnectorStatus.CONNECTED,
                sync_frequency="1h",
                next_sync_at=None,
                is_active=True,
            )
        )
        db.flush()
    db.commit()

    enqueued_ids: list[str] = []

    async def _fake_enqueue(*, connection_id, organization_id, mode):
        enqueued_ids.append(str(connection_id))
        return {"queued": True}

    with patch(
        "app.connectors.schedule.enqueue_sync_connection",
        new=AsyncMock(side_effect=_fake_enqueue),
    ):
        result = asyncio.run(enqueue_due_connector_syncs({}))

    assert result["enqueued"] == 2
    assert result["orgs_scanned"] >= 2
    assert len(enqueued_ids) == 2


def test_email_skips_without_resend():
    result = email_client.send_email(
        to="ops@example.com",
        subject="Test",
        html="<p>hi</p>",
    )
    assert result["skipped"] is True


def test_flags_defaults():
    assert flags.is_enabled("connector_scheduled_sync") is True
    assert flags.is_enabled("alert_email_delivery") is True


def test_purchase_and_sales_orders_api(owner_client):
    po = owner_client.post(
        "/api/v1/purchase-orders",
        json={"reference": "PO-1001", "total_amount": 12000, "line_items": [{"sku": "A", "qty": 10}]},
    )
    assert po.status_code == 201, po.text
    assert po.json()["reference"] == "PO-1001"

    listed = owner_client.get("/api/v1/purchase-orders")
    assert listed.status_code == 200
    assert any(x["reference"] == "PO-1001" for x in listed.json())

    so = owner_client.post(
        "/api/v1/sales-orders",
        json={"reference": "SO-2001", "customer_name": "Acme", "total_amount": 5000},
    )
    assert so.status_code == 201, so.text

    events = owner_client.get("/api/v1/events")
    assert events.status_code == 200
    titles = [e["title"] for e in events.json()]
    assert any("PO-1001" in t for t in titles)
    assert any("SO-2001" in t for t in titles)


def test_orders_require_auth(client):
    assert client.get("/api/v1/purchase-orders").status_code == 401
    assert client.get("/api/v1/events").status_code == 401
