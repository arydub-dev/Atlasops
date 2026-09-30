"""Enterprise email-first auth, sessions, and invitation deep-link coverage."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import get_settings
from app.identity.discovery import discover_organization, extract_email_domain
from app.identity.oauth_state import consume_login_state, create_login_state, safe_return_path
from app.identity.orgs import invite_member
from app.identity.sessions import create_session, resolve_session
from app.models import AuditLog, OAuthLoginState
from sqlalchemy import select


def test_extract_email_domain():
    email, domain = extract_email_domain("John@TataMotors.com")
    assert email == "john@tatamotors.com"
    assert domain == "tatamotors.com"


def test_safe_return_path_blocks_open_redirects():
    assert safe_return_path("/mission-control") == "/mission-control"
    assert safe_return_path("https://evil.com") == "/auth/callback"
    assert safe_return_path("//evil.com") == "/auth/callback"


def test_discover_local_allowed_domain(db, org_a):
    org, _ = org_a
    org.settings = {**(org.settings or {}), "allowed_email_domains": ["acme.example"]}
    db.commit()
    result = discover_organization(db, email="ops@acme.example")
    assert result.domain == "acme.example"
    assert result.local_organization_id == str(org.id)


def test_continue_requires_workos(client):
    r = client.post("/api/v1/auth/continue", json={"email": "a@b.com"})
    assert r.status_code == 503


def test_oauth_state_pkce_consume_once(db):
    row, state, challenge = create_login_state(
        db,
        email="a@b.com",
        domain="b.com",
        remember_device=True,
    )
    db.commit()
    assert challenge
    assert len(row.code_verifier) >= 32
    first = consume_login_state(db, state)
    assert first is not None
    db.commit()
    second = consume_login_state(db, state)
    assert second is None


def test_callback_rejects_missing_or_bad_state(client):
    r = client.get("/api/v1/auth/callback", params={"code": "x"})
    assert r.status_code == 400
    r2 = client.get("/api/v1/auth/callback", params={"code": "x", "state": "nope"})
    assert r2.status_code == 400


def test_continue_email_first_sso_routing(client, db, monkeypatch):
    from app.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router.settings, "WORKOS_API_KEY", "sk_test")
    monkeypatch.setattr(auth_router.settings, "WORKOS_CLIENT_ID", "client_test")

    with patch(
        "app.identity.discovery.workos_client.find_organization_id_by_domain",
        return_value="org_workos_1",
    ):
        with patch(
            "app.api.routers.auth.workos_client.get_authorization_url",
            return_value="https://idp.example/auth",
        ) as auth_url:
            r = client.post(
                "/api/v1/auth/continue",
                json={"email": "john@tatamotors.com", "remember_device": True},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["authorization_url"] == "https://idp.example/auth"
            assert body["mode"] == "sso"
            assert body["domain"] == "tatamotors.com"
            kwargs = auth_url.call_args.kwargs
            assert kwargs["organization_id"] == "org_workos_1"
            assert kwargs["login_hint"] == "john@tatamotors.com"
            assert kwargs["code_challenge"]
            assert kwargs["state"]
            assert db.scalar(select(OAuthLoginState).limit(1)) is not None


def test_callback_with_pkce_creates_session(client, db, org_a, owner_user, monkeypatch):
    from app.api.routers import auth as auth_router

    org, _ = org_a
    org.workos_organization_id = "org_workos_1"
    db.commit()

    monkeypatch.setattr(auth_router.settings, "WORKOS_API_KEY", "sk_test")
    monkeypatch.setattr(auth_router.settings, "WORKOS_CLIENT_ID", "client_test")

    _row, state, _challenge = create_login_state(
        db,
        email=owner_user.email,
        domain="example.com",
        workos_organization_id="org_workos_1",
        remember_device=True,
    )
    db.commit()

    with patch(
        "app.api.routers.auth.workos_client.authenticate_with_code",
        return_value={
            "workos_user_id": "user_workos_1",
            "email": owner_user.email,
            "first_name": "Owner",
            "last_name": "User",
            "email_verified": True,
            "profile_picture_url": None,
            "organization_id": "org_workos_1",
        },
    ) as mock_auth:
        r = client.get(
            "/api/v1/auth/callback",
            params={"code": "authcode", "state": state},
            follow_redirects=False,
        )
    assert r.status_code == 302
    assert "/auth/callback" in r.headers["location"]
    cookie = r.cookies.get(get_settings().SESSION_COOKIE_NAME)
    assert cookie
    mock_auth.assert_called_once()
    assert mock_auth.call_args.kwargs.get("code_verifier")
    logs = db.scalars(select(AuditLog).where(AuditLog.action == "login")).all()
    assert logs


def test_session_idle_timeout(db, owner_user, org_a):
    org, _ = org_a
    session, raw = create_session(db, user=owner_user, organization_id=org.id)
    session.last_seen_at = datetime.now(timezone.utc) - timedelta(hours=5)
    db.commit()
    with patch("app.identity.sessions.settings.SESSION_IDLE_MINUTES", 30):
        assert resolve_session(db, raw) is None


def test_authenticated_get_persists_last_seen(owner_client, db, owner_user, org_a):
    """GET handlers must not roll back sliding-session last_seen updates."""
    from app.models import Session as UserSession
    from sqlalchemy import select

    org, _ = org_a
    before = db.scalar(
        select(UserSession)
        .where(UserSession.user_id == owner_user.id, UserSession.organization_id == org.id)
        .order_by(UserSession.created_at.desc())
    )
    assert before is not None
    stamped = before.last_seen_at - timedelta(minutes=10)
    before.last_seen_at = stamped
    db.commit()

    r = owner_client.get("/api/v1/mission-control")
    assert r.status_code == 200, r.text

    db.expire_all()
    after = db.get(UserSession, before.id)
    assert after is not None
    assert after.last_seen_at > stamped


def test_session_sliding_expiration(db, owner_user, org_a):
    org, _ = org_a
    session, raw = create_session(db, user=owner_user, organization_id=org.id)
    original = session.expires_at
    db.commit()
    with patch("app.identity.sessions.settings.SESSION_SLIDING_ENABLED", True):
        with patch("app.identity.sessions.settings.SESSION_IDLE_MINUTES", 120):
            row = resolve_session(db, raw)
            assert row is not None
            assert row.expires_at >= original


def test_list_revoke_logout_all_sessions(client, db, owner_user, org_a):
    org, _ = org_a
    _s1, raw1 = create_session(db, user=owner_user, organization_id=org.id, user_agent="Chrome")
    s2, _raw2 = create_session(db, user=owner_user, organization_id=org.id, user_agent="Firefox")
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw1)

    listed = client.get("/api/v1/auth/sessions")
    assert listed.status_code == 200
    assert len(listed.json()) >= 2
    assert any(x["is_current"] for x in listed.json())

    rev = client.delete(f"/api/v1/auth/sessions/{s2.id}")
    assert rev.status_code == 200
    db.refresh(s2)
    assert s2.revoked_at is not None

    all_out = client.post("/api/v1/auth/logout-all")
    assert all_out.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_dev_login_hidden_outside_development(client, monkeypatch):
    from app.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth_router.settings, "RATE_LIMIT_AUTH_FAIL_CLOSED", False)
    monkeypatch.setattr(auth_router.settings, "WORKOS_API_KEY", "")
    monkeypatch.setattr(auth_router.settings, "WORKOS_CLIENT_ID", "")
    r = client.post(
        "/api/v1/auth/dev-login",
        json={"email": "x@example.com", "full_name": "X"},
    )
    assert r.status_code == 404


def test_invitation_preview_and_accept_flow(client, db, org_a, owner_user):
    org, _ = org_a
    inv = invite_member(
        db,
        organization_id=org.id,
        email="invitee@example.com",
        role_slug="viewer",
        invited_by=owner_user.id,
    )
    db.commit()

    preview = client.get(f"/api/v1/orgs/invitations/preview?token={inv.token}")
    assert preview.status_code == 200
    assert preview.json()["email"] == "invitee@example.com"
    assert preview.json()["organization_name"] == org.name

    login = client.post(
        "/api/v1/auth/dev-login",
        json={"email": "invitee@example.com", "full_name": "Invitee"},
    )
    assert login.status_code == 200
    accept = client.post("/api/v1/orgs/invitations/accept", json={"token": inv.token})
    assert accept.status_code == 200
    assert accept.json()["role_slug"] == "viewer"


def test_invitation_create_returns_share_link(owner_client):
    r = owner_client.post(
        "/api/v1/orgs/current/invitations",
        json={"email": "newhire@example.com", "role_slug": "viewer"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token"]
    assert "/invite/" in body["invite_url"]


def test_security_login_history_and_settings(owner_client, db, org_a, owner_user):
    org, _ = org_a
    db.add(
        AuditLog(
            organization_id=org.id,
            user_id=owner_user.id,
            action="login",
            resource="auth",
            detail=owner_user.email,
            ip_address="127.0.0.1",
        )
    )
    db.commit()

    hist = owner_client.get("/api/v1/orgs/current/security/login-history")
    assert hist.status_code == 200
    assert any(x["action"] == "login" for x in hist.json())

    patched = owner_client.patch(
        "/api/v1/orgs/current/security/settings",
        json={"allowed_email_domains": ["Partner.Example", "partner.example"]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["allowed_email_domains"] == ["partner.example"]

    sessions = owner_client.get("/api/v1/orgs/current/security/sessions")
    assert sessions.status_code == 200


def test_unauthorized_session_admin(client):
    assert client.get("/api/v1/auth/sessions").status_code == 401
    assert client.get("/api/v1/orgs/current/security/sessions").status_code == 401
