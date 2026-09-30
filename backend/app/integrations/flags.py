"""Feature flags via Flagsmith (optional). Falls back to local defaults."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("supply.flags")

# Local defaults when Flagsmith is unset — keep product working offline.
_DEFAULTS: dict[str, bool] = {
    "billing_enforce": False,
    "connector_scheduled_sync": True,
    "alert_email_delivery": True,
    "ai_copilot": True,
}


def flagsmith_configured() -> bool:
    return bool(settings.FLAGSMITH_ENVIRONMENT_KEY)


def is_enabled(flag: str, *, default: bool | None = None) -> bool:
    if flag in _DEFAULTS and default is None:
        default = _DEFAULTS[flag]
    if default is None:
        default = False
    if not flagsmith_configured():
        return bool(default)
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{settings.FLAGSMITH_API_URL.rstrip('/')}/flags/",
                headers={"X-Environment-Key": settings.FLAGSMITH_ENVIRONMENT_KEY},
            )
            if resp.status_code >= 400:
                return bool(default)
            for item in resp.json():
                if item.get("feature", {}).get("name") == flag:
                    return bool(item.get("enabled"))
    except Exception:  # noqa: BLE001
        logger.debug("flagsmith_lookup_failed flag=%s", flag, exc_info=True)
    return bool(default)


def all_flags() -> dict[str, Any]:
    return {k: is_enabled(k) for k in _DEFAULTS}
