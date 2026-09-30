"""Enqueue connector sync jobs onto Redis/ARQ."""
from __future__ import annotations

import logging
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)


async def enqueue_sync_connection(
    *,
    connection_id: UUID,
    organization_id: UUID,
    mode: str = "incremental",
) -> str:
    """Enqueue ``sync_connection`` and return the ARQ job id.

    Raises ``RuntimeError`` if Redis is unavailable (callers map to HTTP 503).
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    from app.core.job_security import sign_tenant_job

    signature = sign_tenant_job(
        "sync_connection",
        str(connection_id),
        str(organization_id),
        mode,
    )
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    try:
        job = await redis.enqueue_job(
            "sync_connection",
            str(connection_id),
            str(organization_id),
            mode,
            signature,
        )
        try:
            from app.core.telemetry import CONNECTOR_ENQUEUE_TOTAL

            if CONNECTOR_ENQUEUE_TOTAL is not None:
                CONNECTOR_ENQUEUE_TOTAL.labels(
                    "duplicate" if job is None else "ok"
                ).inc()
        except Exception:  # noqa: BLE001
            pass
        if job is None:
            # Duplicate job id collision — treat as already queued
            logger.warning(
                "sync_connection enqueue returned None (duplicate?) conn=%s",
                connection_id,
            )
            return f"duplicate:{connection_id}"
        return job.job_id
    except Exception:
        try:
            from app.core.telemetry import CONNECTOR_ENQUEUE_TOTAL

            if CONNECTOR_ENQUEUE_TOTAL is not None:
                CONNECTOR_ENQUEUE_TOTAL.labels("error").inc()
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        await redis.aclose(close_connection_pool=True)
