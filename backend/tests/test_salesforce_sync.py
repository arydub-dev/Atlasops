"""Salesforce connector hardening: sync lifecycle, pagination, isolation, security."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select

from app.connectors.base import ConnectorError
from app.connectors.credentials import decrypt_credentials, encrypt_credentials
from app.connectors.jobs import (
    SYNC_MAX_TRIES,
    create_queued_import_job,
    recover_stale_syncing_connections,
    sync_connection,
)
from app.core.job_security import sign_tenant_job
from app.models import Connection, ImportJob, Supplier
from app.models.enums import ConnectorHealth, ConnectorStatus, ConnectorType, ImportStatus
from app.services.platform_console import connector_display_status
from app.tenancy.rls import set_session_org

INSTANCE = "https://acme.my.salesforce.com"

ACCOUNT_A = {
    "Id": "001AAA000001",
    "Name": "Acme Components",
    "BillingCountry": "US",
    "BillingState": "CA",
    "Type": "Manufacturer",
    "SystemModstamp": "2026-01-01T00:00:00.000+0000",
}
ACCOUNT_B = {
    "Id": "001BBB000002",
    "Name": "Beta Logistics",
    "BillingCountry": "DE",
    "BillingState": "BE",
    "Type": "Carrier",
    "SystemModstamp": "2026-01-02T00:00:00.000+0000",
}


def _patch_http(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    orig = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        return orig(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def _sf_handler(
    *,
    pages: list[list[dict]] | None = None,
    token_status: int = 200,
    query_status: int = 200,
    fail_on_page: int | None = None,
    token_body: dict | None = None,
    query_calls: list | None = None,
    raise_on_query: BaseException | None = None,
    malformed_query: bool = False,
):
    pages = pages or [[ACCOUNT_A]]
    query_calls = query_calls if query_calls is not None else []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "POST" and "/oauth2/token" in url:
            if token_status >= 400:
                return httpx.Response(
                    token_status,
                    json=token_body or {"error": "invalid_grant", "error_description": "expired"},
                )
            return httpx.Response(
                200,
                json=token_body
                or {
                    "access_token": "sf-access-token",
                    "instance_url": INSTANCE,
                    "token_type": "Bearer",
                },
            )
        if "/query" in url:
            query_calls.append(url)
            if raise_on_query is not None:
                raise raise_on_query
            page_idx = 0
            if "next-page-" in url:
                try:
                    page_idx = int(url.rsplit("next-page-", 1)[-1].split("?")[0])
                except ValueError:
                    page_idx = 1
            if fail_on_page is not None and page_idx + 1 == fail_on_page:
                return httpx.Response(500, json=[{"errorCode": "SERVER_ERROR"}])
            if query_status >= 400 and page_idx == 0:
                if query_status == 429:
                    return httpx.Response(429, json=[{"errorCode": "REQUEST_LIMIT_EXCEEDED"}])
                return httpx.Response(query_status, json=[{"errorCode": "ERROR"}])
            if malformed_query:
                return httpx.Response(200, text="<html>gateway</html>")
            recs = pages[page_idx] if page_idx < len(pages) else []
            next_url = None
            if page_idx + 1 < len(pages):
                next_url = f"/services/data/v59.0/query/next-page-{page_idx + 1}"
            return httpx.Response(
                200,
                json={
                    "records": recs,
                    "done": next_url is None,
                    "nextRecordsUrl": next_url,
                },
            )
        if request.method == "GET" and "/sobjects/" not in url and "/query" not in url:
            return httpx.Response(200, json={"identity": "/id/00Dxx", "maxBatchSize": 200})
        return httpx.Response(404, json={"error": "not_found"})

    return handler


def _creds() -> dict:
    return {
        "client_id": "cid",
        "client_secret": "super-secret-sf",
        "username": "user@x",
        "password": "pw",
    }


def _make_connection(db, org, *, config: dict | None = None) -> Connection:
    set_session_org(db, org.id)
    cfg = {"http_retries": 0, **(config or {})}
    conn = Connection(
        organization_id=org.id,
        name="Salesforce",
        connector_type=ConnectorType.SALESFORCE,
        status=ConnectorStatus.CONNECTED,
        health=ConnectorHealth.UNKNOWN,
        config=cfg,
        credentials_encrypted=encrypt_credentials(_creds()),
        is_active=True,
    )
    db.add(conn)
    db.commit()
    set_session_org(db, org.id)
    db.refresh(conn)
    return conn


def _run_sync(conn, org, mode: str = "incremental"):
    sig = sign_tenant_job("sync_connection", str(conn.id), str(org.id), mode)
    return asyncio.run(
        sync_connection(
            None,
            connection_id=conn.id,
            organization_id=org.id,
            mode=mode,
            signature=sig,
        )
    )


def test_successful_connection_and_sync(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A]]))
    out = _run_sync(conn, org)
    assert out["status"] == "success"
    assert out["records_imported"] == 1
    set_session_org(db, org.id)
    suppliers = db.scalars(select(Supplier).where(Supplier.organization_id == org.id)).all()
    assert len(suppliers) == 1
    assert suppliers[0].external_id == ACCOUNT_A["Id"]
    db.refresh(conn)
    assert conn.status == ConnectorStatus.CONNECTED
    assert conn.health == ConnectorHealth.HEALTHY
    assert conn.cursor and conn.cursor.get("system_modstamp")
    dump = str(out)
    assert "super-secret-sf" not in dump
    assert "sf-access-token" not in dump


def test_invalid_credentials_are_permanent(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(token_status=400))
    with pytest.raises(ConnectorError) as exc:
        _run_sync(conn, org)
    assert exc.value.retryable is False
    assert exc.value.failure_class == "authentication_failure"
    assert "super-secret" not in str(exc.value)
    set_session_org(db, org.id)
    db.refresh(conn)
    assert conn.status == ConnectorStatus.ERROR
    job = db.scalars(select(ImportJob).where(ImportJob.organization_id == org.id)).first()
    assert job is not None
    assert job.status == ImportStatus.FAILED


def test_empty_dataset_succeeds(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(pages=[[]]))
    out = _run_sync(conn, org)
    assert out["status"] == "success"
    assert out["records_imported"] == 0


def test_pagination_fetches_every_page(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    calls: list[str] = []
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A], [ACCOUNT_B]], query_calls=calls))
    out = _run_sync(conn, org)
    assert out["records_imported"] == 2
    assert any("next-page" in u for u in calls)
    set_session_org(db, org.id)
    ids = {
        s.external_id
        for s in db.scalars(select(Supplier).where(Supplier.organization_id == org.id)).all()
    }
    assert ids == {ACCOUNT_A["Id"], ACCOUNT_B["Id"]}


def test_large_dataset_multiple_pages(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    pages = []
    for p in range(3):
        batch = []
        for i in range(40):
            rec = dict(ACCOUNT_A)
            rec["Id"] = f"001LG{p:02d}{i:04d}"
            rec["Name"] = f"Supplier {p}-{i}"
            rec["SystemModstamp"] = f"2026-02-0{p+1}T00:00:00.000+0000"
            batch.append(rec)
        pages.append(batch)
    _patch_http(monkeypatch, _sf_handler(pages=pages))
    out = _run_sync(conn, org)
    assert out["records_imported"] == 120
    set_session_org(db, org.id)
    assert (
        db.scalar(select(func.count()).select_from(Supplier).where(Supplier.organization_id == org.id))
        == 120
    )


def test_duplicate_sync_is_idempotent(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A, ACCOUNT_B]]))
    _run_sync(conn, org)
    _run_sync(conn, org)
    set_session_org(db, org.id)
    rows = db.scalars(select(Supplier).where(Supplier.organization_id == org.id)).all()
    assert len(rows) == 2
    db.refresh(conn)
    assert conn.record_count == 2


def test_page_two_failure_does_not_report_success_or_advance_cursor(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    prior = {"system_modstamp": "2025-01-01T00:00:00.000+0000"}
    conn.cursor = prior
    db.commit()
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A], [ACCOUNT_B]], fail_on_page=2))
    with pytest.raises(ConnectorError):
        _run_sync(conn, org)
    set_session_org(db, org.id)
    db.refresh(conn)
    assert conn.status == ConnectorStatus.ERROR
    assert conn.cursor == prior
    assert (
        db.scalar(select(func.count()).select_from(Supplier).where(Supplier.organization_id == org.id))
        == 0
    )
    job = db.scalars(select(ImportJob).where(ImportJob.organization_id == org.id)).first()
    assert job.status == ImportStatus.FAILED


def test_incomplete_pagination_cap_is_not_success(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org, config={"max_pages": 1, "max_records": 1})
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A], [ACCOUNT_B]]))
    with pytest.raises(ConnectorError, match="did not finish"):
        _run_sync(conn, org)
    set_session_org(db, org.id)
    db.refresh(conn)
    assert conn.cursor is None
    assert conn.status == ConnectorStatus.ERROR


def test_incremental_cursor_filters_subsequent_query(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    calls: list[str] = []
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A]], query_calls=calls))
    _run_sync(conn, org)
    calls.clear()
    _patch_http(monkeypatch, _sf_handler(pages=[[]], query_calls=calls))
    _run_sync(conn, org)
    assert any("SystemModstamp" in u for u in calls)


def test_transient_429_retries_then_succeeds(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org, config={"http_retries": 2})
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "POST" and "/oauth2/token" in url:
            return httpx.Response(200, json={"access_token": "tok", "instance_url": INSTANCE})
        if "/query" in url:
            state["n"] += 1
            if state["n"] == 1:
                return httpx.Response(429, json=[{"errorCode": "REQUEST_LIMIT_EXCEEDED"}])
            return httpx.Response(200, json={"records": [ACCOUNT_A], "done": True})
        return httpx.Response(200, json={"ok": True})

    _patch_http(monkeypatch, handler)
    with patch("app.connectors.retry.asyncio.sleep", return_value=None):
        out = _run_sync(conn, org)
    assert out["status"] == "success"
    assert state["n"] == 2


def test_timeout_is_retryable(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(raise_on_query=httpx.TimeoutException("timed out")))
    with pytest.raises(ConnectorError) as exc:
        _run_sync(conn, org)
    assert exc.value.retryable is True
    assert exc.value.failure_class == "api_network_failure"


def test_connection_failure_is_retryable(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(raise_on_query=httpx.ConnectError("connection refused")))
    with pytest.raises(ConnectorError) as exc:
        _run_sync(conn, org)
    assert exc.value.retryable is True


def test_http_500_is_retryable(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(query_status=500))
    with pytest.raises(ConnectorError) as exc:
        _run_sync(conn, org)
    assert exc.value.retryable is True
    assert exc.value.status_code == 500


def test_malformed_response_is_permanent(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(malformed_query=True))
    with pytest.raises(ConnectorError) as exc:
        _run_sync(conn, org)
    assert exc.value.retryable is False
    assert "html" not in str(exc.value).lower()


def test_arq_permanent_failure_does_not_raise_retry(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(token_status=401))
    result = asyncio.run(
        sync_connection(
            {"job_try": 1, "job_id": "arq-1"},
            connection_id=conn.id,
            organization_id=org.id,
            mode="incremental",
        )
    )
    assert result["status"] == "failed"
    assert result["retryable"] is False


def test_arq_transient_failure_raises_retry(monkeypatch, db, org_a):
    from arq import Retry

    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(query_status=503))
    with pytest.raises(Retry):
        asyncio.run(
            sync_connection(
                {"job_try": 1, "job_id": "arq-2"},
                connection_id=conn.id,
                organization_id=org.id,
                mode="incremental",
            )
        )
    set_session_org(db, org.id)
    job = db.scalars(select(ImportJob).where(ImportJob.organization_id == org.id)).first()
    assert job.status == ImportStatus.RETRYING
    db.refresh(conn)
    assert conn.status == ConnectorStatus.SYNCING


def test_arq_max_tries_marks_failed(monkeypatch, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(query_status=502))
    with pytest.raises(ConnectorError):
        asyncio.run(
            sync_connection(
                {"job_try": SYNC_MAX_TRIES, "job_id": "arq-3"},
                connection_id=conn.id,
                organization_id=org.id,
                mode="incremental",
            )
        )
    set_session_org(db, org.id)
    job = db.scalars(select(ImportJob).where(ImportJob.organization_id == org.id)).first()
    assert job.status == ImportStatus.FAILED


def test_queued_job_created_on_enqueue(owner_client, org_a, db, monkeypatch):
    from app.core import config

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
    row.credentials_encrypted = encrypt_credentials(_creds())
    row.status = ConnectorStatus.CONNECTED
    db.commit()

    async def fake_enq(**kwargs):
        return "job-abc"

    with patch("app.connectors.queue.enqueue_sync_connection", fake_enq):
        r = owner_client.post(f"/api/v1/data/sources/{source_id}/sync", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued"
    assert r.json()["job_id"] == "job-abc"
    set_session_org(db, org.id)
    job = db.scalars(select(ImportJob).where(ImportJob.organization_id == org.id)).first()
    assert job is not None
    assert job.status == ImportStatus.QUEUED
    assert (job.mapping or {}).get("arq_job_id") == "job-abc"


def test_worker_restart_recovers_stale_syncing(db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    conn.status = ConnectorStatus.SYNCING
    conn.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    job = ImportJob(
        organization_id=org.id,
        source_name="Salesforce",
        source_type="salesforce",
        entity_type="mixed",
        status=ImportStatus.RUNNING,
        mapping={"connection_id": str(conn.id), "phase": "running"},
    )
    db.add(job)
    db.commit()
    set_session_org(db, org.id)
    n = recover_stale_syncing_connections(db, org.id)
    db.commit()
    assert n == 1
    db.refresh(conn)
    db.refresh(job)
    assert conn.status == ConnectorStatus.ERROR
    assert job.status == ImportStatus.FAILED
    assert "interrupted" in (conn.last_error or "").lower()


def test_cross_tenant_sync_isolation(monkeypatch, db, org_a, org_b):
    org, _ = org_a
    other, _, _ = org_b
    conn_a = _make_connection(db, org)
    conn_b = _make_connection(db, other)
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A]]))
    _run_sync(conn_a, org)
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_B]]))
    _run_sync(conn_b, other)
    set_session_org(db, org.id)
    a_rows = db.scalars(select(Supplier).where(Supplier.organization_id == org.id)).all()
    set_session_org(db, other.id)
    b_rows = db.scalars(select(Supplier).where(Supplier.organization_id == other.id)).all()
    assert {r.external_id for r in a_rows} == {ACCOUNT_A["Id"]}
    assert {r.external_id for r in b_rows} == {ACCOUNT_B["Id"]}
    assert all(r.organization_id == org.id for r in a_rows)
    assert all(r.organization_id == other.id for r in b_rows)


def test_credentials_never_in_api_response(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "salesforce", "name": "SF"},
        headers=headers,
    )
    source_id = create.json()["id"]
    cfg = owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={"credentials": _creds(), "config": {"sandbox": False}},
        headers=headers,
    )
    assert cfg.status_code == 200, cfg.text
    assert "super-secret-sf" not in cfg.text
    got = owner_client.get(f"/api/v1/data/sources/{source_id}", headers=headers)
    assert "super-secret-sf" not in got.text
    row = db.get(Connection, UUID(source_id))
    assert decrypt_credentials(row.credentials_encrypted)["client_secret"] == "super-secret-sf"


def test_disconnect_clears_credentials(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "salesforce", "name": "SF"},
        headers=headers,
    )
    source_id = create.json()["id"]
    owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={"credentials": _creds()},
        headers=headers,
    )
    r = owner_client.post(f"/api/v1/data/sources/{source_id}/disconnect", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "disconnected"
    set_session_org(db, org.id)
    row = db.get(Connection, UUID(source_id))
    assert row.credentials_encrypted is None
    assert row.cursor is None


def test_delete_wipes_credentials_then_removes_row(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "salesforce", "name": "SF"},
        headers=headers,
    )
    source_id = create.json()["id"]
    owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={"credentials": _creds()},
        headers=headers,
    )
    r = owner_client.delete(f"/api/v1/data/sources/{source_id}", headers=headers)
    assert r.status_code == 200
    set_session_org(db, org.id)
    assert db.get(Connection, UUID(source_id)) is None


def test_credentials_not_written_to_logs(monkeypatch, db, org_a, caplog):
    org, _ = org_a
    conn = _make_connection(db, org)
    _patch_http(
        monkeypatch,
        _sf_handler(
            token_status=400,
            token_body={"error": "invalid_grant", "error_description": "secret=super-secret-sf"},
        ),
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ConnectorError):
            _run_sync(conn, org)
    assert "super-secret-sf" not in caplog.text


def test_configured_without_sync_is_not_healthy():
    conn = Connection(
        id=uuid4(),
        organization_id=uuid4(),
        name="SF",
        connector_type=ConnectorType.SALESFORCE,
        status=ConnectorStatus.CONNECTED,
        health=ConnectorHealth.HEALTHY,
        last_sync_at=None,
        is_active=True,
    )
    assert connector_display_status(conn) != "healthy"


def test_non_admin_cannot_trigger_admin_retry(owner_client, db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    r = owner_client.post(
        f"/api/v1/admin/connectors/{conn.id}/retry",
        params={"organization_id": str(org.id)},
    )
    assert r.status_code == 403


def test_test_connection_sanitizes_error(monkeypatch, owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "salesforce", "name": "SF"},
        headers=headers,
    )
    source_id = create.json()["id"]
    owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={"credentials": _creds(), "config": {"http_retries": 0}},
        headers=headers,
    )
    _patch_http(monkeypatch, _sf_handler(token_status=400))
    r = owner_client.post(f"/api/v1/data/sources/{source_id}/test", headers=headers)
    assert r.status_code == 400
    assert "super-secret-sf" not in r.text


@pytest.mark.skipif(
    os.environ.get("SUPPLY_CI_POSTGRES") != "1",
    reason="Cross-tenant FORCE RLS contamination test requires Postgres",
)
def test_postgres_worker_session_cannot_see_other_tenant_suppliers(monkeypatch, db, org_a, org_b):
    org, _ = org_a
    other, _, _ = org_b
    conn_a = _make_connection(db, org)
    _patch_http(monkeypatch, _sf_handler(pages=[[ACCOUNT_A]]))
    _run_sync(conn_a, org)
    set_session_org(db, other.id)
    leaked = db.scalars(select(Supplier)).all()
    assert all(s.organization_id == other.id for s in leaked)
    assert ACCOUNT_A["Id"] not in {s.external_id for s in leaked}


def test_create_queued_job_reuses_open_job(db, org_a):
    org, _ = org_a
    conn = _make_connection(db, org)
    first = create_queued_import_job(db, conn, mode="incremental")
    db.commit()
    second = create_queued_import_job(db, conn, mode="incremental")
    assert first.id == second.id
    assert second.status == ImportStatus.QUEUED
