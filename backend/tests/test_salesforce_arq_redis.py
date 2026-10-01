"""Real Redis to ARQ worker path for Salesforce sync.

Skipped when Redis is not reachable. Mocked Salesforce HTTP still used.
Hosted Salesforce org validation is reported separately.
"""
from __future__ import annotations

import asyncio
import os

import httpx
import pytest
from sqlalchemy import select

from app.connectors.credentials import encrypt_credentials
from app.connectors.jobs import sync_connection
from app.connectors.queue import enqueue_sync_connection
from app.core.config import settings
from app.models import Connection, ImportJob, Supplier
from app.models.enums import ConnectorHealth, ConnectorStatus, ConnectorType, ImportStatus
from app.tenancy.rls import set_session_org

INSTANCE = "https://acme.my.salesforce.com"
ACCOUNT = {
    "Id": "001ARQ000001",
    "Name": "ARQ Tenant Supplier",
    "BillingCountry": "US",
    "BillingState": "NY",
    "Type": "Vendor",
    "SystemModstamp": "2026-03-01T00:00:00.000+0000",
}


def _redis_up() -> bool:
    try:
        from redis import Redis

        url = os.environ.get("REDIS_URL") or settings.REDIS_URL or "redis://127.0.0.1:6379/0"
        client = Redis.from_url(url, socket_connect_timeout=0.4, socket_timeout=0.4)
        try:
            return bool(client.ping())
        finally:
            client.close()
    except Exception:  # noqa: BLE001
        return False


pytestmark = [pytest.mark.skipif(not _redis_up(), reason="Redis is not reachable")]


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if request.method == "POST" and "/oauth2/token" in url:
        return httpx.Response(200, json={"access_token": "tok", "instance_url": INSTANCE})
    if "/query" in url:
        return httpx.Response(200, json={"records": [ACCOUNT], "done": True})
    return httpx.Response(200, json={"ok": True})


def test_enqueue_and_arq_worker_processes_salesforce_sync(monkeypatch, db, org_a):
    from arq.connections import RedisSettings
    from arq.worker import Worker

    org, _ = org_a
    set_session_org(db, org.id)
    conn = Connection(
        organization_id=org.id,
        name="Salesforce ARQ",
        connector_type=ConnectorType.SALESFORCE,
        status=ConnectorStatus.CONNECTED,
        health=ConnectorHealth.UNKNOWN,
        config={"http_retries": 0},
        credentials_encrypted=encrypt_credentials({"client_id": "cid", "client_secret": "sec"}),
        is_active=True,
    )
    db.add(conn)
    db.commit()
    set_session_org(db, org.id)
    db.refresh(conn)

    transport = httpx.MockTransport(_handler)
    orig = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        return orig(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    redis_url = os.environ.get("REDIS_URL") or settings.REDIS_URL

    async def _go():
        job_id = await enqueue_sync_connection(
            connection_id=conn.id, organization_id=org.id, mode="incremental"
        )
        assert job_id
        worker = Worker(
            functions=[sync_connection],
            redis_settings=RedisSettings.from_dsn(redis_url),
            burst=True,
            max_burst_jobs=8,
            max_tries=2,
            job_timeout=60,
        )
        await worker.async_run()
        return job_id

    asyncio.run(_go())
    set_session_org(db, org.id)
    db.expire_all()
    row = db.get(Connection, conn.id)
    assert row is not None
    assert row.status == ConnectorStatus.CONNECTED
    suppliers = db.scalars(select(Supplier).where(Supplier.organization_id == org.id)).all()
    assert any(s.external_id == ACCOUNT["Id"] for s in suppliers)
    jobs = db.scalars(select(ImportJob).where(ImportJob.organization_id == org.id)).all()
    assert any(j.status == ImportStatus.SUCCESS for j in jobs)
