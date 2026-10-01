"""SSRF allowlist for connector URLs."""
from __future__ import annotations

import pytest

from app.connectors.ssrf import SSRFError, assert_safe_connector_url, validate_connector_config_urls
from app.models.enums import ConnectorType


def test_allows_salesforce_login():
    url = assert_safe_connector_url(
        "https://login.salesforce.com/services/oauth2/token",
        connector_type=ConnectorType.SALESFORCE,
    )
    assert url.startswith("https://")


def test_allows_salesforce_instance():
    assert_safe_connector_url(
        "https://na1.salesforce.com/services/data/v59.0",
        connector_type=ConnectorType.SALESFORCE,
    )


def test_rejects_private_ip():
    with pytest.raises(SSRFError, match="Private|not allowed"):
        assert_safe_connector_url(
            "https://127.0.0.1/oauth",
            connector_type=ConnectorType.SALESFORCE,
        )


def test_rejects_http():
    with pytest.raises(SSRFError, match="https"):
        assert_safe_connector_url(
            "http://login.salesforce.com/token",
            connector_type=ConnectorType.SALESFORCE,
        )


def test_rejects_arbitrary_host():
    with pytest.raises(SSRFError, match="allowlist"):
        assert_safe_connector_url(
            "https://evil.example.com/steal",
            connector_type=ConnectorType.UPS,
        )


def test_rejects_metadata_ip():
    with pytest.raises(SSRFError):
        assert_safe_connector_url(
            "https://169.254.169.254/latest/meta-data",
            connector_type=ConnectorType.DYNAMICS_BC,
        )


def test_configure_rejects_evil_base_url(owner_client, org_a):
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
        json={"base_url": "https://169.254.169.254/"},
        headers=headers,
    )
    assert cfg.status_code == 400
    assert "allowlist" in cfg.json()["detail"].lower() or "not allowed" in cfg.json()["detail"].lower() or "Private" in cfg.json()["detail"]


def test_validate_config_urls_ok():
    validate_connector_config_urls(
        ConnectorType.DYNAMICS_BC,
        {"api_base": "https://api.businesscentral.dynamics.com/v2.0"},
    )
