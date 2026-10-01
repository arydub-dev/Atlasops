"""CSRF defenses for cookie-authenticated mutating requests.

Relies on Origin/Referer allowlisting against FRONTEND_URL + CORS_ORIGINS.
Bearer API-token requests are exempt (no ambient cookie auth).
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger("supply.csrf")

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_EXEMPT_SUFFIXES = (
    "/auth/callback",
    "/billing/webhooks/stripe",
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
)


def _allowed_origins() -> set[str]:
    origins = {o.rstrip("/") for o in settings.CORS_ORIGINS if o and o != "*"}
    if settings.FRONTEND_URL:
        origins.add(settings.FRONTEND_URL.rstrip("/"))
    return origins


def _origin_of(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _is_exempt(path: str) -> bool:
    for suffix in _EXEMPT_SUFFIXES:
        if path.endswith(suffix) or path == suffix:
            return True
    return False


class CsrfOriginMiddleware(BaseHTTPMiddleware):
    """Reject cross-site cookie mutations when CSRF_ORIGIN_CHECK is enabled."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not getattr(settings, "CSRF_ORIGIN_CHECK", False):
            return await call_next(request)
        if request.method in _SAFE_METHODS:
            return await call_next(request)
        if _is_exempt(request.url.path):
            return await call_next(request)

        # Bearer tokens are not ambient browser cookies — skip Origin check.
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            return await call_next(request)

        # Only enforce when a session cookie is present (browser session).
        cookie_name = settings.SESSION_COOKIE_NAME
        if cookie_name not in request.cookies:
            return await call_next(request)

        origin = _origin_of(request.headers.get("origin"))
        if origin is None:
            origin = _origin_of(request.headers.get("referer"))

        allowed = _allowed_origins()
        if origin is None or origin not in allowed:
            logger.warning(
                "csrf_rejected path=%s origin=%s allowed=%s",
                request.url.path,
                origin,
                sorted(allowed),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed (Origin/Referer)"},
            )
        return await call_next(request)
