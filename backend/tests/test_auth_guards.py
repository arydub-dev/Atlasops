"""Auth negative paths, header spoofing, and cross-resource tenant isolation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import get_settings
from app.core.rate_limit import reset_rate_limiter
from app.identity.sessions import create_session
from app.models import Alert, Connection, Supplier
from app.models.enums import (
    AlertPriority,
    AlertStatus,
    AlertType,
    ConnectorStatus,
    ConnectorType,
)
from app.tenancy.rls import set_session_org


def test_unauthenticated_domain_apis_return_401(client, shipment_a):
    assert client.get("/api/v1/shipments").status_code == 401
    assert client.get("/api/v1/alerts").status_code == 401
    assert client.get("/api/v1/data/sources").status_code == 401
    assert client.get(f"/api/v1/shipments/{shipment_a.id}").status_code == 401


def test_invalid_org_header_returns_400(owner_client):
    r = owner_client.get("/api/v1/shipments", headers={"X-Organization-Id": "not-a-uuid"})
    assert r.status_code == 400


def test_non_member_org_header_returns_403(owner_client, org_b):
    other, _, _ = org_b
    r = owner_client.get(
        "/api/v1/shipments",
        headers={"X-Organization-Id": str(other.id)},
    )
    assert r.status_code == 403
    assert "Not a member" in r.json()["detail"]


def test_logout_revokes_session(client, db, owner_user, org_a):
    org, _ = org_a
    _session, raw = create_session(db, user=owner_user, organization_id=org.id)
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_cross_org_alert_and_connection_isolation(client, db, org_a, org_b, owner_user):
    org, _ = org_a
    other, _, user_b = org_b

    set_session_org(db, org.id)
    alert_a = Alert(
        organization_id=org.id,
        alert_type=AlertType.DELAYED_SHIPMENT,
        priority=AlertPriority.HIGH,
        status=AlertStatus.OPEN,
        title="A alert",
        message="org a",
    )
    conn_a = Connection(
        organization_id=org.id,
        name="Conn A",
        connector_type=ConnectorType.SALESFORCE,
        status=ConnectorStatus.CONNECTED,
    )
    db.add_all([alert_a, conn_a])
    db.flush()

    set_session_org(db, other.id)
    alert_b = Alert(
        organization_id=other.id,
        alert_type=AlertType.DELAYED_SHIPMENT,
        priority=AlertPriority.HIGH,
        status=AlertStatus.OPEN,
        title="B alert",
        message="org b",
    )
    db.add(alert_b)
    db.commit()
    set_session_org(db, org.id)
    db.refresh(alert_a)
    db.refresh(conn_a)
    set_session_org(db, other.id)
    db.refresh(alert_b)

    # Org A session
    _s, raw_a = create_session(db, user=owner_user, organization_id=org.id)
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw_a)
    alerts_resp = client.get(
        "/api/v1/alerts", headers={"X-Organization-Id": str(org.id)}
    )
    assert alerts_resp.status_code == 200, alerts_resp.text
    items = alerts_resp.json().get("items", alerts_resp.json())
    ids = {str(i["id"]) for i in items}
    assert str(alert_a.id) in ids
    assert str(alert_b.id) not in ids

    # Org B session (overwrite cookie deliberately)
    _s2, raw_b = create_session(db, user=user_b, organization_id=other.id)
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw_b)
    assert (
        client.get(
            f"/api/v1/data/sources/{conn_a.id}",
            headers={"X-Organization-Id": str(other.id)},
        ).status_code
        == 404
    )


def test_invite_accept_http_flow(owner_client, client, db, org_a, owner_user):
    org, _ = org_a
    headers = {"X-Organization-Id": str(org.id)}
    email = f"invitee-{uuid4().hex[:8]}@example.com"
    inv = owner_client.post(
        "/api/v1/orgs/current/invitations",
        json={"email": email, "role_slug": "viewer"},
        headers=headers,
    )
    assert inv.status_code == 201, inv.text
    token = None
    # Token is not returned in InvitationOut — fetch from DB for test
    from app.models import Invitation

    row = db.get(Invitation, __import__("uuid").UUID(inv.json()["id"]))
    db.refresh(row)
    token = row.token

    # Invitee signs in via dev-login (creates own org) then accept
    r = client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "full_name": "Invitee"},
    )
    assert r.status_code == 200
    accept = client.post("/api/v1/orgs/invitations/accept", json={"token": token})
    assert accept.status_code == 200, accept.text
    assert accept.json()["role_slug"] == "viewer"
    assert accept.json()["email"] == email


def test_cannot_escalate_to_owner_via_patch(owner_client, viewer_user, org_a, db):
    org, _ = org_a
    from app.models import Membership
    from sqlalchemy import select

    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == org.id,
            Membership.user_id == viewer_user.id,
        )
    )
    r = owner_client.patch(
        f"/api/v1/orgs/current/members/{membership.id}",
        json={"role_slug": "owner"},
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 400
    assert "transfer-ownership" in r.json()["detail"]


def test_auth_rate_limit_triggers(client, monkeypatch):
    reset_rate_limiter()
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()
    from app.core.config import settings as s

    # Patch settings object used by limiter
    object.__setattr__(s, "AUTH_RATE_LIMIT_PER_MINUTE", 3)

    codes = []
    for i in range(5):
        r = client.post(
            "/api/v1/auth/dev-login",
            json={"email": f"rate-{i}-{uuid4().hex[:6]}@example.com", "full_name": "R"},
        )
        codes.append(r.status_code)
    assert 429 in codes
    reset_rate_limiter()
    get_settings.cache_clear()
