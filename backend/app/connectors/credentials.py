"""Encrypt/decrypt connector credentials — single path for the Connector SDK.

Canonical on-disk format: Fernet(JSON object of string keys → string/secret values).

Backwards compatibility:
- Legacy blobs produced by ``encrypt_str(api_key)`` (raw UTF-8, not JSON) are
  accepted by ``decrypt_credentials`` and normalized to ``{"api_key": "<value>"}``.
  Callers should re-save via ``encrypt_credentials`` on the next successful
  configure/sync so blobs migrate forward.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core import crypto

logger = logging.getLogger("supply.connectors.credentials")

# Keys that must never be copied into Connection.config (non-secret metadata only).
SECRET_KEYS = frozenset(
    {
        "api_key",
        "client_secret",
        "password",
        "refresh_token",
        "access_token",
        "security_token",
        "private_key",
        "secret",
        "username",
        "company_db",
    }
)


def encrypt_credentials(credentials: dict[str, Any]) -> bytes:
    """Serialize credentials dict to encrypted bytes for Connection.credentials_encrypted."""
    if not isinstance(credentials, dict):
        raise TypeError("credentials must be a dict")
    cleaned = {str(k): v for k, v in credentials.items() if v is not None and v != ""}
    payload = json.dumps(cleaned, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return crypto.encrypt_bytes(payload)


def decrypt_credentials(blob: bytes | None) -> dict[str, Any]:
    """Decrypt Connection.credentials_encrypted back to a dict.

    Supports legacy single-string blobs (pre-v2.0.1) by wrapping as ``api_key``.
    """
    if not blob:
        return {}
    raw = crypto.decrypt_bytes(blob)
    text = raw.decode("utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.info("Migrating legacy connector credential blob to JSON dict shape")
        return {"api_key": text}
    if not isinstance(data, dict):
        raise ValueError(
            "Decrypted credentials must be a JSON object. "
            "Reconfigure the connection with a credentials dict."
        )
    return data


def merge_credentials(
    existing: dict[str, Any] | None,
    updates: dict[str, Any] | None,
) -> dict[str, Any]:
    """Shallow-merge credential updates onto existing secrets (empty values ignored)."""
    merged = dict(existing or {})
    for key, value in (updates or {}).items():
        if value is None or value == "":
            continue
        merged[str(key)] = value
    return merged


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) < 4:
        return "••••"
    return "••••••••" + value[-4:]


def public_credential_hints(credentials: dict[str, Any]) -> dict[str, str]:
    """Non-secret hints for API responses (which keys are set / masked tails)."""
    hints: dict[str, str] = {}
    for key, value in credentials.items():
        if key in SECRET_KEYS and isinstance(value, str):
            hints[f"{key}_masked"] = mask_secret(value) or "••••"
        elif key not in SECRET_KEYS:
            hints[key] = str(value)
    return hints
