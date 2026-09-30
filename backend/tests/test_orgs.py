"""Organization create + invite / accept token flow (no WorkOS/Stripe required)."""
from __future__ import annotations

from uuid import uuid4

from app.core.config import get_settings
from app.identity.orgs import accept_invitation, invite_member
from app.identity.sessions import create_session
from app.models import User
from app.models.enums import MembershipStatus


def test_create_org_via_api(client, db, owner_user, org_a):
    # owner already has org_a; create a second org via API
    org, _ = org_a
    _session, raw = create_session(db, user=owner_user, organization_id=org.id)
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)

    r = client.post("/api/v1/orgs", json={"name": "Second Workspace"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Second Workspace"
    assert body["slug"]


def test_invite_and_accept_token_flow(db, org_a, owner_user):
    org, _ = org_a
    email = f"invitee-{uuid4().hex[:8]}@example.com"
    inv = invite_member(
        db,
        organization_id=org.id,
        email=email,
        role_slug="viewer",
        invited_by=owner_user.id,
    )
    db.commit()
    assert inv.token
    assert inv.status.value == "pending"

    invitee = User(email=email, full_name="Invitee", is_active=True)
    db.add(invitee)
    db.flush()

    membership = accept_invitation(db, token=inv.token, user=invitee)
    db.commit()

    assert membership.organization_id == org.id
    assert membership.role_slug == "viewer"
    assert membership.status == MembershipStatus.ACTIVE

    # Token cannot be reused
    try:
        accept_invitation(db, token=inv.token, user=invitee)
        assert False, "expected ValueError on reused invite"
    except ValueError:
        pass


def test_dev_login_without_workos(client):
    """Dev login works when WorkOS keys are empty and ENVIRONMENT=development."""
    email = f"devlogin-{uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "full_name": "Dev Login"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert body["current_organization"] is not None
    assert get_settings().SESSION_COOKIE_NAME in client.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email


def test_billing_plans_without_stripe(client):
    r = client.get("/api/v1/billing/plans")
    assert r.status_code == 200
    slugs = {p["slug"] for p in r.json()}
    assert {"starter", "professional", "enterprise"} <= slugs


def test_stripe_checkout_fails_clearly_without_key(client, org_a, owner_client):
    org, _ = org_a
    r = owner_client.post(
        f"/api/v1/billing/checkout/{org.id}",
        json={
            "plan": "starter",
            "customer_email": "owner@example.com",
        },
    )
    assert r.status_code == 503
    assert "STRIPE_SECRET_KEY" in r.json()["detail"]
