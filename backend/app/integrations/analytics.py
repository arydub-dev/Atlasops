"""Product analytics via PostHog (optional, server-side)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("supply.analytics")


def posthog_configured() -> bool:
    return bool(settings.POSTHOG_API_KEY)


def capture(
    *,
    distinct_id: str,
    event: str,
    properties: dict[str, Any] | None = None,
) -> None:
    if not posthog_configured():
        return
    host = (settings.POSTHOG_HOST or "https://us.i.posthog.com").rstrip("/")
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"{host}/capture/",
                json={
                    "api_key": settings.POSTHOG_API_KEY,
                    "event": event,
                    "distinct_id": distinct_id,
                    "properties": properties or {},
                },
            )
    except Exception:  # noqa: BLE001
        logger.debug("posthog_capture_failed event=%s", event, exc_info=True)
