"""Shared HTTP retry for connector outbound calls."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

logger = logging.getLogger("supply.connectors.retry")

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 0.5,
    retry_on: tuple[type[BaseException], ...] = (httpx.TransportError, httpx.TimeoutException),
) -> T:
    """Retry an async callable with exponential backoff."""
    attempt = 0
    last_exc: BaseException | None = None
    while attempt <= retries:
        try:
            return await fn()
        except retry_on as exc:
            last_exc = exc
            if attempt >= retries:
                break
            delay = base_delay * (2**attempt)
            logger.warning("connector_retry attempt=%s delay=%.2fs err=%s", attempt + 1, delay, exc)
            await asyncio.sleep(delay)
            attempt += 1
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code if exc.response is not None else 0
            if status not in {408, 425, 429, 500, 502, 503, 504} or attempt >= retries:
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "connector_retry_http status=%s attempt=%s delay=%.2fs",
                status,
                attempt + 1,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1
    assert last_exc is not None
    raise last_exc
