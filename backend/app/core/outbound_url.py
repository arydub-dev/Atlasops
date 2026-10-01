"""SSRF-safe validation for user-supplied outbound webhook URLs.

Unlike connector URLs (strict vendor allowlists), org webhooks and Slack/Teams
hooks may target customer-controlled HTTPS endpoints. We still reject private /
link-local / metadata ranges and non-HTTPS schemes.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.connectors.ssrf import SSRFError

# Optional host suffixes for known chat providers (still must be HTTPS + public).
_KNOWN_CHAT_SUFFIXES = (
    "hooks.slack.com",
    "slack.com",
    "webhook.office.com",
    "office.com",
    "logic.azure.com",
    "powerautomate.com",
)


def _reject_private_ip(host: str) -> None:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if host.lower() in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
            raise SSRFError("Host is not allowed")
        return
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or ip in ipaddress.ip_network("169.254.0.0/16")
    ):
        raise SSRFError(f"Private or non-routable IP addresses are not allowed ({host})")


def _resolve_and_reject_private(host: str) -> None:
    """Resolve DNS and reject if any A/AAAA is non-public (DNS rebinding defense)."""
    _reject_private_ip(host)
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFError(f"Hostname could not be resolved ({host})") from exc
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        _reject_private_ip(sockaddr[0])


def assert_safe_outbound_url(
    url: str,
    *,
    field: str = "url",
    require_known_chat_host: bool = False,
) -> str:
    """Validate a user-supplied URL for server-side HTTP POST."""
    raw = (url or "").strip()
    if not raw:
        raise SSRFError(f"{field} is empty")
    if len(raw) > 1000:
        raise SSRFError(f"{field} exceeds maximum length")

    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise SSRFError(f"{field} must use https")
    if parsed.username or parsed.password:
        raise SSRFError(f"{field} must not include userinfo")
    if not parsed.hostname:
        raise SSRFError(f"{field} is missing a hostname")

    host = parsed.hostname.lower().rstrip(".")
    if re.search(r"[^a-z0-9.\-]", host):
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            raise SSRFError(f"{field} hostname contains invalid characters") from exc

    _resolve_and_reject_private(host)

    if require_known_chat_host:
        if not any(host == s or host.endswith("." + s) for s in _KNOWN_CHAT_SUFFIXES):
            raise SSRFError(
                f"{field} host '{host}' is not a recognized Slack/Teams webhook host"
            )
    return raw
