"""API-level production workflows that run in CI without external SaaS sandboxes.

Blocked for live credentials (documented, not skipped silently):
- WorkOS email verify / OAuth account creation
- Stripe Checkout + hosted portal
- Salesforce / Dynamics / UPS OAuth + live sync
"""
from __future__ import annotations

import io
import json
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.crypto import hash_token
from app.identity.sessions import create_session
from app.models import ApiToken, AuditLog, Invitation, Membership, Supplier, User
from app.models.enums import MembershipStatus


def test_workflow_invite_accept_permissions(owner_client, org_a, db, client):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}

    invite = owner_client.post(
        "/api/v1/orgs/current/invitations",
        json={"email": f"invitee-{uuid4().hex[:8]}@example.com", "role_slug": "viewer"},
        headers=headers,
    )
    assert invite.status_code == 201, invite.text
    inv_row = db.get(Invitation, UUID(invite.json()["id"]))
    assert inv_row is not None
    token = inv_row.token

    invitee = User(
        email=inv_row.email,
        full_name="Invitee",
        is_active=True,
    )
    db.add(invitee)
    db.flush()
    _session, raw = create_session(db, user=invitee, organization_id=None)
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)

    accepted = client.post("/api/v1/orgs/invitations/accept", json={"token": token})
    assert accepted.status_code == 200, accepted.text

    # Viewer can read shipments, cannot manage tokens
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)
    # Switch context: accept may not set org cookie; pass header
    r_ok = client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r_ok.status_code == 200
    r_deny = client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "nope"},
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r_deny.status_code == 403


def test_workflow_csv_import_audit(owner_client, org_a, db):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    csv_body = (
        "name,country,region,category\n"
        "Acme Parts,USA,West,Components\n"
    ).encode()

    preview = owner_client.post(
        "/api/v1/data/import/preview",
        data={"entity": "suppliers"},
        files={"file": ("suppliers.csv", io.BytesIO(csv_body), "text/csv")},
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    mapping = preview.json()["suggested_mapping"]

    commit = owner_client.post(
        "/api/v1/data/import/commit",
        data={"entity": "suppliers", "mapping": json.dumps(mapping)},
        files={"file": ("suppliers.csv", io.BytesIO(csv_body), "text/csv")},
        headers=headers,
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["rows_imported"] == 1

    suppliers = db.scalars(
        select(Supplier).where(Supplier.organization_id == org.id, Supplier.name == "Acme Parts")
    ).all()
    assert len(suppliers) == 1

    audits = db.scalars(
        select(AuditLog).where(
            AuditLog.organization_id == org.id,
            AuditLog.action == "import",
            AuditLog.resource == "import_job",
        )
    ).all()
    assert len(audits) >= 1


def test_workflow_api_token_rotate_and_org_binding(owner_client, org_a, org_b, db, owner_user):
    org, _ = org_a
    other, _, _ = org_b
    headers = {"X-Organization-Id": str(org.id)}

    # Owner also joins org B so soft binding would previously allow header switch
    db.add(
        Membership(
            organization_id=other.id,
            user_id=owner_user.id,
            role_slug="owner",
            status=MembershipStatus.ACTIVE,
        )
    )
    db.commit()

    created = owner_client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "ci-rotate", "scopes": ["shipments.read"]},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    old_raw = created.json()["token"]
    old_id = created.json()["id"]

    owner_client.cookies.clear()
    ok = owner_client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {old_raw}", "X-Organization-Id": str(org.id)},
    )
    assert ok.status_code == 200

    # Cross-org header must be rejected (token bound to org A)
    cross = owner_client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {old_raw}", "X-Organization-Id": str(other.id)},
    )
    assert cross.status_code == 403

    # Rotate: create new, revoke old
    owner_client.cookies.clear()
    # Re-auth via session for management
    from app.identity.sessions import create_session as cs

    _s, raw = cs(db, user=owner_user, organization_id=org.id)
    db.commit()
    owner_client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)

    created2 = owner_client.post(
        "/api/v1/orgs/current/tokens",
        json={"name": "ci-rotate-2"},
        headers=headers,
    )
    assert created2.status_code == 201
    new_raw = created2.json()["token"]
    assert (
        owner_client.delete(
            f"/api/v1/orgs/current/tokens/{old_id}", headers=headers
        ).status_code
        == 204
    )

    owner_client.cookies.clear()
    rejected = owner_client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {old_raw}", "X-Organization-Id": str(org.id)},
    )
    assert rejected.status_code == 401
    still = owner_client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {new_raw}", "X-Organization-Id": str(org.id)},
    )
    assert still.status_code == 200


def test_workflow_tenant_isolation(owner_client, org_a, shipment_a, shipment_b):
    org, _ = org_a
    r = owner_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert str(shipment_a.id) in ids
    assert str(shipment_b.id) not in ids


def test_workflow_logout_revokes_session(owner_client, org_a, db, owner_user):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    assert owner_client.get("/api/v1/auth/me").status_code == 200

    out = owner_client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    assert out.json().get("ok") is True

    owner_client.cookies.clear()
    # Even if cookie lingered, revoked session should fail — use a fresh revoked path
    _s, raw = create_session(db, user=owner_user, organization_id=org.id)
    db.commit()
    owner_client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)
    assert owner_client.get("/api/v1/auth/me").status_code == 200
    assert owner_client.post("/api/v1/auth/logout").status_code == 200
    # Cookie deleted by response; clear and reuse revoked raw token
    owner_client.cookies.clear()
    owner_client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)
    assert owner_client.get("/api/v1/shipments", headers=headers).status_code == 401
