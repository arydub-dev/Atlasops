"""AppSec hardening regressions — invite RBAC, SSRF, secrets, scopes."""
from __future__ import annotations

import pytest

from app.connectors.ssrf import SSRFError
from app.core.outbound_url import assert_safe_outbound_url
from app.rbac.permissions import can_invite_role


def test_cannot_invite_owner_via_any_role():
    assert can_invite_role("owner", "owner") is False
    assert can_invite_role("admin", "owner") is False
    assert can_invite_role("operations_director", "owner") is False


def test_operations_director_cannot_invite_admin():
    assert can_invite_role("operations_director", "admin") is False
    assert can_invite_role("operations_director", "viewer") is True
    assert can_invite_role("operations_director", "operations_manager") is True


def test_invite_owner_role_rejected_by_api(owner_client):
    # Owner inviting another owner must still be blocked (transfer ownership is separate).
    r = owner_client.post(
        "/api/v1/orgs/current/invitations",
        json={"email": "escalation@example.com", "role_slug": "owner"},
    )
    assert r.status_code == 400
    assert "owner" in r.json()["detail"].lower() or "assignable" in r.json()["detail"].lower()


def test_outbound_url_rejects_metadata_and_http():
    with pytest.raises(SSRFError):
        assert_safe_outbound_url("http://hooks.slack.com/services/x")
    with pytest.raises(SSRFError):
        assert_safe_outbound_url("https://169.254.169.254/latest/meta-data/")
    with pytest.raises(SSRFError):
        assert_safe_outbound_url("https://127.0.0.1/admin")


def test_slack_url_requires_known_host():
    with pytest.raises(SSRFError):
        assert_safe_outbound_url(
            "https://evil.example.com/hook",
            require_known_chat_host=True,
        )


def test_config_rejects_plaintext_secrets(owner_client, db, org_a):
    from app.models import Connection
    from app.models.enums import ConnectorType

    org, _ = org_a
    conn = Connection(
        organization_id=org.id,
        name="SF",
        connector_type=ConnectorType.SALESFORCE,
    )
    db.add(conn)
    db.commit()

    r = owner_client.put(
        f"/api/v1/data/sources/{conn.id}/config",
        json={"config": {"private_key": "SECRET-VALUE", "instance_url": "https://login.salesforce.com"}},
    )
    assert r.status_code == 400
    assert "credentials" in r.json()["detail"].lower()


def test_webhook_rejects_private_url(owner_client):
    r = owner_client.post(
        "/api/v1/orgs/current/webhooks",
        json={"url": "https://127.0.0.1:8080/hook", "events": ["alert.*"]},
    )
    assert r.status_code == 400
