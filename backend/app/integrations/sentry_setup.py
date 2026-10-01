"""Sentry error monitoring (optional)."""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("supply.sentry")
_initialized = False


def scrub_event(event, hint):
    """Keep stack/type and correlation tags without request bodies or local values."""
    request = event.get("request") or {}
    for key in ("data", "cookies", "query_string", "headers", "env"):
        request.pop(key, None)
    if request.get("url"):
        from urllib.parse import urlsplit, urlunsplit
        url = urlsplit(request["url"])
        request["url"] = urlunsplit((url.scheme, url.netloc.split("@")[-1], url.path, "", ""))
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    event.pop("extra", None)
    event.pop("message", None)
    event.pop("logentry", None)
    for exception in (event.get("exception") or {}).get("values", []):
        exception["value"] = "Exception details omitted; inspect exception type and stack"
        for frame in (exception.get("stacktrace") or {}).get("frames", []):
            frame.pop("vars", None)
    return event


def init_sentry() -> bool:
    """Initialize Sentry SDK when SENTRY_DSN is set. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return True
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=float(settings.SENTRY_TRACES_SAMPLE_RATE),
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
            include_local_variables=False,
            before_send=scrub_event,
            before_send_transaction=scrub_event,
        )
        _initialized = True
        logger.info("sentry_initialized environment=%s", settings.ENVIRONMENT)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("sentry_init_failed")
        return False
