"""CSRF Origin/Referer middleware tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_csrf_blocks_cross_origin_cookie_mutation(monkeypatch, owner_client: TestClient):
    monkeypatch.setattr(settings, "CSRF_ORIGIN_CHECK", True)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://app.example.com"])

    # owner_client already has session cookie from fixture
    r = owner_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403
    assert "CSRF" in r.json()["detail"]


def test_csrf_allows_matching_origin(monkeypatch, owner_client: TestClient):
    monkeypatch.setattr(settings, "CSRF_ORIGIN_CHECK", True)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://app.example.com"])

    r = owner_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://app.example.com"},
    )
    assert r.status_code in {200, 204}


def test_csrf_skips_when_disabled(monkeypatch, owner_client: TestClient):
    monkeypatch.setattr(settings, "CSRF_ORIGIN_CHECK", False)
    r = owner_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code in {200, 204}
