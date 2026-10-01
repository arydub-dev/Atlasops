"""SSRF protection for connector outbound HTTP.

Rejects non-HTTPS URLs, private/link-local hosts, and hostnames outside the
per-connector allowlist. User-supplied ``base_url`` / ``token_url`` / ``api_base``
/ ``instance_url`` values must pass the same checks before storage or use.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from app.models.enums import ConnectorType

# Host patterns: exact match or ``*.example.com`` (suffix including the apex).
_ALLOWLIST: dict[ConnectorType, tuple[str, ...]] = {
    ConnectorType.SALESFORCE: (
        "login.salesforce.com",
        "test.salesforce.com",
        "*.salesforce.com",
        "*.force.com",
        "*.my.salesforce.com",
        "*.cloudforce.com",
    ),
    ConnectorType.DYNAMICS_BC: (
        "login.microsoftonline.com",
        "*.microsoftonline.com",
        "*.dynamics.com",
        "*.api.businesscentral.dynamics.com",
        "*.businesscentral.dynamics.com",
    ),
    ConnectorType.UPS: (
        "onlinetools.ups.com",
        "wwwcie.ups.com",
        "wwwapps.ups.com",
        "*.ups.com",
    ),
}


class SSRFError(ValueError):
    """Raised when a URL is not safe for server-side fetch."""


def _host_allowed(host: str, patterns: tuple[str, ...]) -> bool:
    host = host.lower().rstrip(".")
    for pattern in patterns:
        p = pattern.lower()
        if p.startswith("*."):
            suffix = p[1:]  # .example.com
            apex = p[2:]
            if host == apex or host.endswith(suffix):
                return True
        elif host == p:
            return True
    return False


def _reject_private_ip(host: str) -> None:
    """Reject literal IP addresses that are not globally routable."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Hostname — not a literal IP. DNS rebinding is mitigated by allowlist.
        if host.lower() in {"localhost", "localhost.localdomain"}:
            raise SSRFError("Host localhost is not allowed")
        return
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise SSRFError(f"Private or non-routable IP addresses are not allowed ({host})")


def assert_safe_connector_url(
    url: str,
    *,
    connector_type: ConnectorType,
    field: str = "url",
) -> str:
    """Validate ``url`` for outbound connector use. Returns normalized URL."""
    raw = (url or "").strip()
    if not raw:
        raise SSRFError(f"{field} is empty")

    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise SSRFError(f"{field} must use https")
    if parsed.username or parsed.password:
        raise SSRFError(f"{field} must not include userinfo")
    if not parsed.hostname:
        raise SSRFError(f"{field} is missing a hostname")

    host = parsed.hostname.lower()
    if re.search(r"[^a-z0-9.\-]", host) and not _is_ip_literal(host):
        raise SSRFError(f"{field} hostname contains invalid characters")

    _reject_private_ip(host)

    patterns = _ALLOWLIST.get(connector_type)
    if not patterns:
        raise SSRFError(f"No URL allowlist configured for {connector_type.value}")
    if not _host_allowed(host, patterns):
        raise SSRFError(
            f"{field} host '{host}' is not on the allowlist for {connector_type.value}"
        )
    return raw


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def validate_connector_config_urls(
    connector_type: ConnectorType,
    config: dict,
) -> None:
    """Validate known URL keys in a connection config dict (mutates nothing)."""
    url_keys = (
        "base_url",
        "token_url",
        "api_base",
        "instance_url",
        "track_url",
        "login_url",
    )
    for key in url_keys:
        value = config.get(key)
        if value:
            assert_safe_connector_url(str(value), connector_type=connector_type, field=key)
