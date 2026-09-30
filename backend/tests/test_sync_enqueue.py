"""Connector sync is enqueued to ARQ (not inline) unless CONNECTOR_SYNC_INLINE."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.connectors.credentials import encrypt_credentials
from app.core import config
from app.models import Connection
from app.models.enums import ConnectorStatus


def test_sync_enqueues_when_not_inline(owner_client, org_a, db, monkeypatch):
    monkeypatch.setattr(config.settings, "CONNECTOR_SYNC_INLINE", False)

    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "salesforce", "name": "SF"},
        headers=headers,
    )
    source_id = create.json()["id"]
    row = db.get(Connection, UUID(source_id))
    assert row is not None
    row.credentials_encrypted = encrypt_credentials(
        {"client_id": "c", "client_secret": "s"}
    )
    row.status = ConnectorStatus.CONNECTED
    db.commit()

    with patch(
        "app.connectors.queue.enqueue_sync_connection",
        new_callable=AsyncMock,
        return_value="job-abc",
    ) as enq:
        r = owner_client.post(
            f"/api/v1/data/sources/{source_id}/sync",
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "queued"
        assert body["job_id"] == "job-abc"
        enq.assert_awaited_once()

    db.refresh(row)
    assert row.status == ConnectorStatus.SYNCING
