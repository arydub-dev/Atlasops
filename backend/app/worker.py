"""ARQ worker entrypoint: ``arq app.worker.WorkerSettings``.

Keeps Redis/ARQ (not Celery) per MASTER_PLATFORM decisions.
"""
from __future__ import annotations

import os

from arq import cron
from arq.connections import RedisSettings

from app.connectors.jobs import sync_connection
from app.connectors.schedule import enqueue_due_connector_syncs
from app.core.config import settings
from app.core.startup_checks import assert_safe_to_boot
from app.jobs.enterprise import (
    enqueue_scheduled_workflows,
    generate_org_predictions,
    refresh_predictions_all,
    run_workflow,
)

# Fail closed for worker process (encryption, redis URL, no seed/inline).
assert_safe_to_boot(settings, role="worker")

try:
    from app.integrations.sentry_setup import init_sentry

    init_sentry()
except Exception:  # noqa: BLE001
    pass


async def startup(ctx):
    if settings.requires_secure_boot:
        from app.core.database import engine
        from app.core.startup_checks import assert_safe_database_role
        assert_safe_database_role(engine)


class WorkerSettings:
    on_startup = startup
    functions = [
        sync_connection,
        enqueue_due_connector_syncs,
        run_workflow,
        generate_org_predictions,
        enqueue_scheduled_workflows,
        refresh_predictions_all,
    ]
    cron_jobs = [
        # Every 15 minutes — respects Connection.sync_frequency / next_sync_at
        cron(enqueue_due_connector_syncs, minute={0, 15, 30, 45}, run_at_startup=False),
        # Hourly scheduled workflows
        cron(enqueue_scheduled_workflows, minute={5}, run_at_startup=False),
        # Nightly predictive refresh (00:20 UTC)
        cron(refresh_predictions_all, hour={0}, minute={20}, run_at_startup=False),
    ]
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", settings.REDIS_URL)
    )
    # Bounded retries; retry_jobs recovers in-progress work after a worker crash.
    max_tries = 5
    job_timeout = 600
    retry_jobs = True
    health_check_interval = 30
