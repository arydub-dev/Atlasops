"""API token auth path — create, use, revoke; no orphaned-user fallback."""
from __future__ import annotations

from app.core.config import get_settings
from app.core.crypto import hash_token
from app.models import ApiToken
from sqlalchemy import select


def test_api_token_can_call_api(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    created = owner_client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "ci", "scopes": ["shipments.read"]},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    raw = created.json()["token"]
    assert raw.startswith("sup_")

    # Clear session cookie; use bearer only
    owner_client.cookies.clear()
    r = owner_client.get(
        "/api/v1/shipments",
        headers={
            "Authorization": f"Bearer {raw}",
            "X-Organization-Id": str(org.id),
        },
    )
    assert r.status_code == 200, r.text


def test_revoked_api_token_rejected(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    created = owner_client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "temp"},
        headers=headers,
    )
    token_id = created.json()["id"]
    raw = created.json()["token"]
    assert (
        owner_client.delete(
            f"/api/v1/orgs/current/tokens/{token_id}", headers=headers
        ).status_code
        == 204
    )
    owner_client.cookies.clear()
    r = owner_client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {raw}", "X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 401


def test_orphaned_token_creator_rejected(owner_client, org_a, db, owner_user):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    created = owner_client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "orphan"},
        headers=headers,
    )
    raw = created.json()["token"]
    row = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(raw)))
    assert row is not None
    row.created_by_user_id = None
    db.commit()

    owner_client.cookies.clear()
    r = owner_client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {raw}", "X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 401
