"""Connector credential encrypt/decrypt — dict shape + legacy string compat."""
from __future__ import annotations

from app.connectors.credentials import decrypt_credentials, encrypt_credentials, merge_credentials
from app.core import crypto
from app.models import Connection
from app.models.enums import ConnectorStatus, ConnectorType


def test_encrypt_decrypt_roundtrip_dict():
    blob = encrypt_credentials(
        {"client_id": "abc", "client_secret": "secret", "tenant_id": "tid"}
    )
    out = decrypt_credentials(blob)
    assert out["client_id"] == "abc"
    assert out["client_secret"] == "secret"
    assert out["tenant_id"] == "tid"


def test_legacy_encrypt_str_blob_normalizes_to_api_key():
    """Pre-fix stored encrypt_str(api_key) must still decrypt for sync/test."""
    legacy = crypto.encrypt_str("legacy-api-key-value")
    out = decrypt_credentials(legacy)
    assert out == {"api_key": "legacy-api-key-value"}


def test_merge_credentials_preserves_existing():
    merged = merge_credentials(
        {"client_id": "a", "client_secret": "old"},
        {"client_secret": "new", "tenant_id": "t"},
    )
    assert merged == {
        "client_id": "a",
        "client_secret": "new",
        "tenant_id": "t",
    }


def test_configure_source_stores_credentials_dict(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "dynamics_bc", "name": "BC"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    source_id = create.json()["id"]

    cfg = owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={
            "credentials": {
                "client_id": "cid",
                "client_secret": "csecret",
                "tenant_id": "tenant-1",
            },
            "config": {"environment": "production"},
        },
        headers=headers,
    )
    assert cfg.status_code == 200, cfg.text
    body = cfg.json()
    assert body["credential_hints"].get("client_secret_masked")
    assert "csecret" not in str(body)

    row = db.get(Connection, __import__("uuid").UUID(source_id))
    assert row is not None
    db.refresh(row)
    creds = decrypt_credentials(row.credentials_encrypted)
    assert creds["client_id"] == "cid"
    assert creds["client_secret"] == "csecret"
    assert creds["tenant_id"] == "tenant-1"


def test_legacy_api_key_field_still_works(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "ups", "name": "UPS"},
        headers=headers,
    )
    source_id = create.json()["id"]
    cfg = owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={"api_key": "ups-key-1234"},
        headers=headers,
    )
    assert cfg.status_code == 200, cfg.text
    row = db.get(Connection, __import__("uuid").UUID(source_id))
    db.refresh(row)
    assert decrypt_credentials(row.credentials_encrypted)["api_key"] == "ups-key-1234"


def test_cross_org_cannot_configure_connection(owner_client, org_a, org_b, db):
    org, _ = org_a
    other, _, _ = org_b
    headers = {"X-Organization-Id": str(org.id)}
    create = owner_client.post(
        "/api/v1/data/sources",
        json={"connector_type": "salesforce", "name": "SF"},
        headers=headers,
    )
    source_id = create.json()["id"]

    # Attempt with org B session against org A's connection id
    from app.core.config import get_settings
    from app.identity.sessions import create_session

    _org_b, _m, user_b = org_b
    _s, raw = create_session(db, user=user_b, organization_id=other.id)
    db.commit()
    owner_client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)
    r = owner_client.put(
        f"/api/v1/data/sources/{source_id}/config",
        json={"api_key": "stolen"},
        headers={"X-Organization-Id": str(other.id)},
    )
    assert r.status_code == 404
