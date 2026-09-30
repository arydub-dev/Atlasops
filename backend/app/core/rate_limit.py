"""Rate limiting for auth and general API routes.

Uses Redis when available (shared across API replicas). Falls back to a
process-local sliding window so local/dev and CI keep working without Redis.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger("supply.rate_limit")


class InMemoryRateLimiter:
    """Sliding-window counter keyed by arbitrary string."""

    def __init__(self) -> None:
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded ({limit} requests per {int(window_seconds)}s)",
                    headers={"Retry-After": str(int(window_seconds))},
                )
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_memory = InMemoryRateLimiter()
_redis_client = None
_redis_next_retry_at = 0.0
_REDIS_RETRY_SECONDS = 30.0


def _redis():
    """Lazy Redis client; None when unavailable (retries after cooldown)."""
    global _redis_client, _redis_next_retry_at
    now = time.monotonic()
    if _redis_client is not None:
        return _redis_client
    if now < _redis_next_retry_at:
        return None
    try:
        from redis import Redis

        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.4,
            socket_timeout=0.4,
            decode_responses=True,
        )
        client.ping()
        _redis_client = client
        _redis_next_retry_at = 0.0
        return _redis_client
    except Exception:  # noqa: BLE001
        _redis_client = None
        _redis_next_retry_at = now + _REDIS_RETRY_SECONDS
        logger.debug("rate_limit_redis_unavailable", exc_info=True)
        return None


def _check(
    key: str,
    limit: int,
    window_seconds: float = 60.0,
    *,
    fail_closed: bool = False,
) -> None:
    client = _redis()
    if client is None:
        if fail_closed and settings.requires_secure_boot and settings.RATE_LIMIT_AUTH_FAIL_CLOSED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting unavailable",
                headers={"Retry-After": "30"},
            )
        _memory.check(key, limit, window_seconds)
        return

    redis_key = f"rl:{key}:{int(time.time() // window_seconds)}"
    try:
        count = int(client.incr(redis_key))
        if count == 1:
            client.expire(redis_key, int(window_seconds) + 1)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit} requests per {int(window_seconds)}s)",
                headers={"Retry-After": str(int(window_seconds))},
            )
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        global _redis_client, _redis_next_retry_at
        _redis_client = None
        _redis_next_retry_at = time.monotonic() + _REDIS_RETRY_SECONDS
        logger.debug("rate_limit_redis_error_fallback", exc_info=True)
        if fail_closed and settings.requires_secure_boot and settings.RATE_LIMIT_AUTH_FAIL_CLOSED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting unavailable",
                headers={"Retry-After": "30"},
            )
        _memory.check(key, limit, window_seconds)


def get_client_ip(request: Request) -> str:
    """Resolve client IP.

    ``X-Forwarded-For`` is only trusted when ``TRUST_PROXY=true`` (set behind a
    known reverse proxy). Otherwise spoofed headers cannot bypass rate limits.
    """
    if settings.TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit_auth(request: Request) -> None:
    """FastAPI dependency — apply AUTH_RATE_LIMIT_PER_MINUTE per IP."""
    ip = get_client_ip(request)
    _check(
        f"auth:{ip}",
        settings.AUTH_RATE_LIMIT_PER_MINUTE,
        60.0,
        fail_closed=True,
    )


def rate_limit_general(request: Request) -> None:
    """FastAPI dependency — apply RATE_LIMIT_PER_MINUTE per IP."""
    # Read-heavy GETs still count; keep limit generous for dashboards.
    ip = get_client_ip(request)
    _check(f"api:{ip}", settings.RATE_LIMIT_PER_MINUTE, 60.0)


def rate_limit_ai(request: Request) -> None:
    """Stricter limit for AI / orchestrate endpoints."""
    ip = get_client_ip(request)
    _check(f"ai:{ip}", settings.AI_RATE_LIMIT_PER_MINUTE, 60.0)


def rate_limit_upload(request: Request) -> None:
    """Limit file import / document upload abuse."""
    ip = get_client_ip(request)
    _check(f"upload:{ip}", settings.UPLOAD_RATE_LIMIT_PER_MINUTE, 60.0)


def rate_limit_export(request: Request) -> None:
    """Limit expensive export endpoints."""
    ip = get_client_ip(request)
    _check(f"export:{ip}", settings.EXPORT_RATE_LIMIT_PER_MINUTE, 60.0)


def reset_rate_limiter() -> None:
    """Test helper."""
    global _redis_client, _redis_next_retry_at
    _memory.reset()
    _redis_client = None
    _redis_next_retry_at = 0.0
