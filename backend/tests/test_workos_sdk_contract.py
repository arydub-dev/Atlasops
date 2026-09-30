"""Exercise installed SDK signatures, without external identity requests."""
from types import SimpleNamespace
from unittest.mock import create_autospec
from urllib.parse import parse_qs, urlparse

from workos import WorkOSClient
from app.identity import workos


def test_authorization_url_includes_pkce_method(monkeypatch):
    client = WorkOSClient(api_key="sk_test_contract", client_id="client_contract")
    monkeypatch.setattr(workos, "_client", lambda: client)
    url = workos.get_authorization_url(state="state", code_challenge="challenge")
    query = parse_qs(urlparse(url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == ["challenge"]
    assert query["state"] == ["state"]


def test_authentication_matches_installed_sdk_signature(monkeypatch):
    client = WorkOSClient(api_key="sk_test_contract", client_id="client_contract")
    api = create_autospec(client.user_management, instance=True)
    profile = SimpleNamespace(user=SimpleNamespace(id="user_1", email="owner@example.com", email_verified=True))
    api.authenticate_with_code.return_value = profile
    api.authenticate_with_magic_auth.return_value = profile
    monkeypatch.setattr(workos, "_client", lambda: SimpleNamespace(user_management=api))
    assert workos.authenticate_with_code("code", code_verifier="verifier")["workos_user_id"] == "user_1"
    api.authenticate_with_code.assert_called_once_with(code="code", code_verifier="verifier")
    assert workos.authenticate_magic_auth(email="owner@example.com", code="123456")["email"] == "owner@example.com"
