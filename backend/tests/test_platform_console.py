"""Internal Admin Console — authorization, isolation, health, jobs, audit."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import AuditLog, Connection, ConnectorSyncLog, ImportJob
from app.models.enums import (
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    ImportStatus,
)
from app.services.platform_console import classify_failure, sanitize_error
from app.tenancy.rls import set_session_org


def _promote(db, user) -> None:
    user.is_platform_admin = True
    db.commit()


def test_sanitize_error_redacts_secrets():
    raw = "Salesforce failed api_key=SUPERSECRET token=abc Bearer xyz"
    out = sanitize_error(raw)
    assert out is not None
    assert "SUPERSECRET" not in out
    assert "[redacted]" in out


def test_classify_failure_kinds():
    assert classify_failure("401 unauthorized invalid_grant") == "authentication_failure"
    assert classify_failure("connection timed out") == "api_network_failure"
    assert classify_failure("HTTP 429 rate limit") == "rate_limiting"
    assert classify_failure("row validation failed") == "data_validation_failure"
    assert classify_failure("arq enqueue failed") == "worker_failure"
    assert classify_failure("something odd") == "unknown_failure"


def test_unauthenticated_admin_is_401(client):
    assert client.get("/api/v1/admin/health").status_code == 401
    assert client.get("/api/v1/admin/tenants").status_code == 401
    assert client.get("/api/v1/admin/connectors").status_code == 401
    assert client.get("/api/v1/admin/jobs").status_code == 401
    assert client.get("/api/v1/admin/errors").status_code == 401


def test_tenant_owner_cannot_access_admin(owner_client):
    r = owner_client.get("/api/v1/admin/health")
    assert r.status_code == 403
    assert owner_client.get("/api/v1/admin/tenants").status_code == 403


def test_platform_admin_can_access_health(owner_client, db, owner_user):
    _promote(db, owner_user)
    r = owner_client.get("/api/v1/admin/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["overall"] in {"healthy", "warning", "critical", "unknown"}
    names = {c["name"] for c in body["components"]}
    assert {"api", "postgres", "redis", "workers", "workos", "stripe", "sentry"} <= names
    dump = r.text.lower()
    assert "sk_live" not in dump
    assert "credentials_encrypted" not in dump


def test_non_admin_cannot_read_other_tenant_via_admin(owner_client, org_b):
    other, _, _ = org_b
    r = owner_client.get(f"/api/v1/admin/tenants/{other.id}")
    assert r.status_code == 403


def test_platform_admin_lists_both_tenants(owner_client, db, owner_user, org_a, org_b):
    _promote(db, owner_user)
    org, _ = org_a
    other, _, _ = org_b
    r = owner_client.get("/api/v1/admin/tenants")
    assert r.status_code == 200, r.text
    ids = {item["id"] for item in r.json()["items"]}
    assert str(org.id) in ids
    assert str(other.id) in ids
    for item in r.json()["items"]:
        assert "credentials" not in item
        assert "config" not in item


def test_platform_admin_tenant_detail_and_audit(owner_client, db, owner_user, org_a, org_b):
    _promote(db, owner_user)
    org, _ = org_a
    other, _, _ = org_b
    now = datetime.now(timezone.utc)
    set_session_org(db, other.id)
    db.add(
        Connection(
            organization_id=other.id,
            name="SF",
            connector_type=ConnectorType.SALESFORCE,
            status=ConnectorStatus.ERROR,
            health=ConnectorHealth.DOWN,
            last_error="401 unauthorized invalid_grant",
            last_sync_at=now - timedelta(hours=5),
            is_active=True,
        )
    )
    db.commit()

    r = owner_client.get(f"/api/v1/admin/tenants/{other.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["overview"]["id"] == str(other.id)
    assert body["connectors"]
    assert body["connectors"][0]["failure_class"] == "authentication_failure"
    assert "invalid_grant" in (body["connectors"][0]["last_error"] or "")
    dump = r.text
    assert "credentials_encrypted" not in dump
    assert "private_key" not in dump

    set_session_org(db, other.id)
    audit = db.query(AuditLog).filter(AuditLog.action == "admin.view_tenant").all()
    assert any(a.organization_id == other.id and a.user_id == owner_user.id for a in audit)


def test_api_token_cannot_use_admin_even_if_user_is_platform_admin(
    owner_client, db, owner_user, org_a
):
    _promote(db, owner_user)
    org, _ = org_a
    created = owner_client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "ops", "scopes": ["shipments.read"]},
        headers={"X-Organization-Id": str(org.id)},
    )
    assert created.status_code == 201, created.text
    raw = created.json()["token"]
    owner_client.cookies.clear()
    r = owner_client.get(
        "/api/v1/admin/health",
        headers={"Authorization": f"Bearer {raw}", "X-Organization-Id": str(org.id)},
    )
    assert r.status_code in (401, 403)


def test_postgres_health_failure(owner_client, db, owner_user, monkeypatch):
    _promote(db, owner_user)
    monkeypatch.setattr("app.services.platform_console._check_postgres", lambda _db: {
        "name": "postgres",
        "state": "critical",
        "detail": "Database query failed",
    })
    r = owner_client.get("/api/v1/admin/health")
    assert r.status_code == 200
    pg = next(c for c in r.json()["components"] if c["name"] == "postgres")
    assert pg["state"] == "critical"
    assert r.json()["overall"] == "critical"


def test_redis_unavailable_is_not_reported_healthy(owner_client, db, owner_user, monkeypatch):
    _promote(db, owner_user)
    monkeypatch.setattr(
        "app.services.platform_console._check_redis",
        lambda: {"name": "redis", "state": "critical", "detail": "Redis PING failed"},
    )
    monkeypatch.setattr(
        "app.services.platform_console._arq_worker_stats",
        lambda: {
            "state": "unknown",
            "detail": "Unable to inspect Redis/ARQ",
            "active_workers": 0,
            "queued_jobs": 0,
            "running_jobs": 0,
            "failed_jobs_heartbeat": None,
            "completed_jobs_heartbeat": None,
            "heartbeat_at": None,
            "heartbeat_raw": None,
        },
    )
    r = owner_client.get("/api/v1/admin/health")
    assert r.status_code == 200
    redis = next(c for c in r.json()["components"] if c["name"] == "redis")
    assert redis["state"] != "healthy"


def test_connector_and_job_reporting(owner_client, db, owner_user, org_a):
    _promote(db, owner_user)
    org, _ = org_a
    now = datetime.now(timezone.utc)
    set_session_org(db, org.id)
    conn = Connection(
        organization_id=org.id,
        name="UPS",
        connector_type=ConnectorType.UPS,
        status=ConnectorStatus.CONNECTED,
        health=ConnectorHealth.HEALTHY,
        last_sync_at=now - timedelta(minutes=4),
        is_active=True,
        credentials_encrypted=b"not-a-real-secret-blob",
    )
    db.add(conn)
    db.flush()
    db.add(
        ConnectorSyncLog(
            organization_id=org.id,
            connection_id=conn.id,
            mode="incremental",
            status="success",
            latency_ms=120,
            message="ok",
        )
    )
    db.add(
        ImportJob(
            organization_id=org.id,
            source_name="upload.csv",
            source_type="csv",
            entity_type="shipment",
            status=ImportStatus.FAILED,
            duration_ms=40,
            error_summary={"message": "validation failed on row 3"},
        )
    )
    db.commit()

    connectors = owner_client.get("/api/v1/admin/connectors")
    assert connectors.status_code == 200
    rows = connectors.json()["items"]
    assert any(c["name"] == "UPS" and c["status"] in {"healthy", "connected"} for c in rows)

    jobs = owner_client.get("/api/v1/admin/jobs")
    assert jobs.status_code == 200
    body = jobs.json()
    assert body["failed"] >= 1
    assert any(j["kind"] == "import" and j["status"] == "failed" for j in body["items"])
    assert any(j["kind"] == "connector_sync" and j["status"] == "success" for j in body["items"])

    errors = owner_client.get("/api/v1/admin/errors")
    assert errors.status_code == 200
    assert errors.json()["items"]


def test_stale_connector_is_warning(owner_client, db, owner_user, org_a):
    _promote(db, owner_user)
    org, _ = org_a
    set_session_org(db, org.id)
    db.add(
        Connection(
            organization_id=org.id,
            name="BC",
            connector_type=ConnectorType.DYNAMICS_BC,
            status=ConnectorStatus.CONNECTED,
            health=ConnectorHealth.HEALTHY,
            last_sync_at=datetime.now(timezone.utc) - timedelta(hours=8),
            is_active=True,
        )
    )
    db.commit()
    r = owner_client.get("/api/v1/admin/connectors")
    row = next(c for c in r.json()["items"] if c["name"] == "BC")
    assert row["status"] == "warning"


def test_retry_enqueues_and_audits(owner_client, db, owner_user, org_a, monkeypatch):
    _promote(db, owner_user)
    org, _ = org_a
    set_session_org(db, org.id)
    conn = Connection(
        organization_id=org.id,
        name="RetryMe",
        connector_type=ConnectorType.SALESFORCE,
        status=ConnectorStatus.ERROR,
        health=ConnectorHealth.DOWN,
        last_error="timeout talking to API",
        is_active=True,
        credentials_encrypted=b"blob",
    )
    db.add(conn)
    db.commit()

    async def fake_enqueue(**kwargs):
        assert kwargs["connection_id"] == conn.id
        assert kwargs["organization_id"] == org.id
        assert kwargs["mode"] == "incremental"
        return "job-test-1"

    monkeypatch.setattr(
        "app.connectors.queue.enqueue_sync_connection", fake_enqueue
    )
    r = owner_client.post(
        f"/api/v1/admin/connectors/{conn.id}/retry",
        params={"organization_id": str(org.id)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["queued"] is True
    set_session_org(db, org.id)
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "admin.retry_sync", AuditLog.resource_id == str(conn.id))
        .count()
        >= 1
    )


def test_retry_wrong_org_is_404(owner_client, db, owner_user, org_a, org_b):
    _promote(db, owner_user)
    org, _ = org_a
    other, _, _ = org_b
    set_session_org(db, org.id)
    conn = Connection(
        organization_id=org.id,
        name="A-only",
        connector_type=ConnectorType.UPS,
        credentials_encrypted=b"blob",
        is_active=True,
    )
    db.add(conn)
    db.commit()
    r = owner_client.post(
        f"/api/v1/admin/connectors/{conn.id}/retry",
        params={"organization_id": str(other.id)},
    )
    assert r.status_code == 404
