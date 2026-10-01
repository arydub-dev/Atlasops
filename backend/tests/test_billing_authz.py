"""Billing authz regression tests — Critical P0.

Every money/org billing endpoint (except public plans + Stripe webhook) must
require authentication AND org-scoped ``org.billing.manage``.
"""
from __future__ import annotations

from uuid import uuid4

from app.billing.stripe_service import validate_frontend_url
from app.core.config import get_settings
import pytest


PROTECTED = [
    ("get", "/api/v1/billing/usage/{org_id}"),
    ("get", "/api/v1/billing/account/{org_id}"),
    ("post", "/api/v1/billing/checkout/{org_id}"),
    ("post", "/api/v1/billing/portal/{org_id}"),
    ("post", "/api/v1/billing/cancel/{org_id}"),
    ("get", "/api/v1/billing/usage"),
    ("get", "/api/v1/billing/account"),
]


def _path(template: str, org_id) -> str:
    return template.replace("{org_id}", str(org_id))


def test_billing_plans_remain_public(client):
    r = client.get("/api/v1/billing/plans")
    assert r.status_code == 200


@pytest.mark.parametrize("method,template", PROTECTED)
def test_billing_requires_authentication(client, org_a, method, template):
    org, _ = org_a
    url = _path(template, org.id)
    if method == "get":
        r = client.get(url)
    else:
        body = {"plan": "starter", "customer_email": "x@example.com"} if "checkout" in url else {}
        if "cancel" in url:
            body = {"at_period_end": True}
        if "portal" in url:
            body = {}
        r = client.request(method.upper(), url, json=body)
    assert r.status_code == 401, f"{method} {url} -> {r.status_code} {r.text}"


@pytest.mark.parametrize("method,template", PROTECTED)
def test_viewer_cannot_manage_billing(viewer_client, org_a, method, template):
    org, _ = org_a
    url = _path(template, org.id)
    headers = {"X-Organization-Id": str(org.id)}
    if method == "get":
        r = viewer_client.get(url, headers=headers)
    else:
        body = {"plan": "starter", "customer_email": "x@example.com"} if "checkout" in url else {}
        if "cancel" in url:
            body = {"at_period_end": True}
        if "portal" in url:
            body = {}
        r = viewer_client.request(method.upper(), url, json=body, headers=headers)
    assert r.status_code == 403, f"{method} {url} -> {r.status_code} {r.text}"


def test_cross_org_billing_path_denied(owner_client, org_a, org_b):
    org, _ = org_a
    other, _, _ = org_b
    headers = {"X-Organization-Id": str(org.id)}
    r = owner_client.get(
        f"/api/v1/billing/account/{other.id}",
        headers=headers,
    )
    assert r.status_code == 403
    assert "does not match" in r.json()["detail"]


def test_spoofed_org_header_denied(owner_client, org_a, org_b):
    """Session for org A cannot act as org B via X-Organization-Id."""
    _org, _ = org_a
    other, _, _ = org_b
    r = owner_client.get(
        f"/api/v1/billing/account/{other.id}",
        headers={"X-Organization-Id": str(other.id)},
    )
    assert r.status_code == 403
    assert "Not a member" in r.json()["detail"]


def test_owner_can_read_own_billing_account(owner_client, org_a):
    org, _ = org_a
    r = owner_client.get(
        f"/api/v1/billing/account/{org.id}",
        headers={"X-Organization-Id": str(org.id)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["plan"] in {"trial", "starter", "professional", "enterprise"}


def test_open_redirect_urls_rejected():
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        validate_frontend_url("https://evil.example/phish")
    ok = validate_frontend_url("/settings/billing")
    assert ok.startswith(get_settings().FRONTEND_URL)
