"""ARQ-compatible async jobs for connector sync."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.base import ConnectorError, SyncMode
from app.connectors.credentials import decrypt_credentials
from app.connectors.registry import create_connector
from app.core.database import SessionLocal
from app.models import Connection, ImportJob, Supplier
from app.models.enums import ConnectorHealth, ConnectorStatus, ImportStatus
from app.tenancy.rls import set_session_org

logger = logging.getLogger(__name__)

# Bounded ARQ retries for a single sync_connection invocation chain.
SYNC_MAX_TRIES = 5
STALE_RUNNING = timedelta(minutes=30)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_error(exc: BaseException) -> str:
    from app.services.platform_console import sanitize_error

    return sanitize_error(str(exc), limit=280) or "Connector sync failed"


def _failure_class_for(exc: BaseException) -> str:
    from app.services.platform_console import classify_failure

    if isinstance(exc, ConnectorError) and exc.failure_class:
        return exc.failure_class
    return classify_failure(str(exc))


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ConnectorError):
        return bool(exc.retryable)
    return True


def _job_try(ctx: dict | None) -> int:
    if not ctx:
        return 1
    try:
        return max(1, int(ctx.get("job_try") or 1))
    except (TypeError, ValueError):
        return 1


def _arq_job_id(ctx: dict | None) -> str | None:
    if not ctx:
        return None
    raw = ctx.get("job_id")
    return str(raw) if raw else None


def _mapping(job: ImportJob) -> dict[str, Any]:
    return dict(job.mapping or {})


def _open_job_for_connection(
    db: Session, organization_id: UUID, connection_id: UUID
) -> ImportJob | None:
    rows = db.scalars(
        select(ImportJob)
        .where(
            ImportJob.organization_id == organization_id,
            ImportJob.status.in_(
                [ImportStatus.QUEUED, ImportStatus.RUNNING, ImportStatus.RETRYING]
            ),
        )
        .order_by(ImportJob.created_at.desc())
        .limit(40)
    ).all()
    cid = str(connection_id)
    for row in rows:
        if (_mapping(row).get("connection_id") or "") == cid:
            return row
    return None


def recover_stale_syncing_connections(
    db: Session,
    organization_id: UUID,
    *,
    now: datetime | None = None,
    stale_after: timedelta = STALE_RUNNING,
) -> int:
    """Mark SYNCING connections whose worker likely died so they are not stuck forever."""
    now = now or _utcnow()
    cutoff = now - stale_after
    recovered = 0
    conns = db.scalars(
        select(Connection).where(
            Connection.organization_id == organization_id,
            Connection.status == ConnectorStatus.SYNCING,
        )
    ).all()
    for conn in conns:
        updated = conn.updated_at
        if updated is None:
            continue
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if updated > cutoff:
            continue
        conn.status = ConnectorStatus.ERROR
        conn.health = ConnectorHealth.DOWN
        conn.last_error = "Worker interrupted before completion"
        job = _open_job_for_connection(db, organization_id, conn.id)
        if job is not None:
            job.status = ImportStatus.FAILED
            job.error_summary = ["Worker interrupted before completion"]
            mapping = _mapping(job)
            mapping["failure_class"] = "worker_failure"
            mapping["finished_at"] = now.isoformat()
            mapping["phase"] = "failed"
            job.mapping = mapping
        recovered += 1
        logger.warning(
            "stale_sync_recovered org_id=%s connection_id=%s job_id=%s",
            organization_id,
            conn.id,
            job.id if job is not None else None,
        )
    return recovered


def create_queued_import_job(
    db: Session,
    connection: Connection,
    *,
    mode: str = "incremental",
) -> ImportJob:
    """Create (or reuse) a queued ImportJob and mark the connection SYNCING."""
    recover_stale_syncing_connections(db, connection.organization_id)
    existing = _open_job_for_connection(db, connection.organization_id, connection.id)
    if existing is not None:
        connection.status = ConnectorStatus.SYNCING
        return existing
    job = ImportJob(
        organization_id=connection.organization_id,
        source_name=connection.name,
        source_type=connection.connector_type.value,
        entity_type="mixed",
        status=ImportStatus.QUEUED,
        mapping={
            "connection_id": str(connection.id),
            "mode": mode,
            "retry_count": 0,
            "phase": "queued",
        },
    )
    db.add(job)
    connection.status = ConnectorStatus.SYNCING
    connection.last_error = None
    db.flush()
    return job


def _attach_arq_id(job: ImportJob, arq_job_id: str | None) -> None:
    if not arq_job_id:
        return
    mapping = _mapping(job)
    mapping["arq_job_id"] = arq_job_id
    job.mapping = mapping


async def sync_connection(
    ctx: dict | None,
    connection_id: str | UUID,
    organization_id: str | UUID,
    mode: str = "incremental",
    signature: str | None = None,
) -> dict:
    """ARQ job: load Connection, decrypt creds, run connector, update health/cursor/ImportJob.

    ``ctx`` is the ARQ context (may be None when invoked directly in tests).
    ``signature`` is an HMAC over connection/org/mode — required in hardened envs.
    """
    from app.core.job_security import verify_tenant_job

    conn_id = UUID(str(connection_id))
    org_id = UUID(str(organization_id))
    try:
        verify_tenant_job(
            "sync_connection",
            signature,
            str(conn_id),
            str(org_id),
            mode,
        )
    except PermissionError as exc:
        raise ConnectorError(
            str(exc),
            retryable=False,
            failure_class="worker_failure",
        ) from exc

    sync_mode = SyncMode.FULL if mode == "full" else SyncMode.INCREMENTAL
    job_try = _job_try(ctx)
    arq_id = _arq_job_id(ctx)
    is_arq = ctx is not None

    db: Session = SessionLocal()
    job: ImportJob | None = None
    job_pk: UUID | None = None
    try:
        # Explicit per-job tenant bind. New SessionLocal each invocation so a
        # pooled connection cannot keep a previous job's org GUC.
        set_session_org(db, org_id)
        recover_stale_syncing_connections(db, org_id)

        connection = db.get(Connection, conn_id)
        if connection is None:
            raise ConnectorError(
                f"Connection {conn_id} not found",
                retryable=False,
                failure_class="unknown_failure",
            )
        if connection.organization_id != org_id:
            raise ConnectorError(
                "Connection does not belong to organization_id",
                retryable=False,
                failure_class="unknown_failure",
            )

        if not connection.credentials_encrypted:
            raise ConnectorError(
                f"Connection '{connection.name}' has no credentials configured. "
                "Store encrypted credentials before syncing.",
                retryable=False,
                failure_class="authentication_failure",
            )

        try:
            credentials = decrypt_credentials(connection.credentials_encrypted)
        except ValueError as exc:
            raise ConnectorError(
                "Failed to decrypt credentials",
                retryable=False,
                failure_class="authentication_failure",
            ) from exc

        if not credentials:
            raise ConnectorError(
                f"Connection '{connection.name}' credentials are empty after decrypt.",
                retryable=False,
                failure_class="authentication_failure",
            )

        job = _open_job_for_connection(db, org_id, conn_id)
        started = _utcnow()
        if job is None:
            job = ImportJob(
                organization_id=org_id,
                source_name=connection.name,
                source_type=connection.connector_type.value,
                entity_type="mixed",
                status=ImportStatus.RUNNING,
                mapping={
                    "connection_id": str(connection.id),
                    "mode": sync_mode.value,
                    "retry_count": max(0, job_try - 1),
                    "phase": "running",
                    "started_at": started.isoformat(),
                    "job_try": job_try,
                },
            )
            db.add(job)
        else:
            mapping = _mapping(job)
            mapping["mode"] = sync_mode.value
            mapping["job_try"] = job_try
            mapping["retry_count"] = max(int(mapping.get("retry_count") or 0), job_try - 1)
            mapping["started_at"] = mapping.get("started_at") or started.isoformat()
            mapping["phase"] = "retrying" if job_try > 1 else "running"
            if arq_id:
                mapping["arq_job_id"] = arq_id
            job.mapping = mapping
            job.status = ImportStatus.RETRYING if job_try > 1 else ImportStatus.RUNNING
        _attach_arq_id(job, arq_id)
        connection.status = ConnectorStatus.SYNCING
        connection.last_error = None
        db.commit()
        set_session_org(db, org_id)
        job_pk = job.id

        logger.info(
            "sync_start org_id=%s connection_id=%s job_id=%s arq_job_id=%s mode=%s try=%s",
            org_id,
            conn_id,
            job_pk,
            arq_id,
            sync_mode.value,
            job_try,
        )

        try:
            import sentry_sdk

            sentry_sdk.set_tag("organization_id", str(org_id))
            sentry_sdk.set_tag("connection_id", str(conn_id))
            sentry_sdk.set_tag("job_id", str(job_pk))
        except Exception:  # noqa: BLE001
            pass

        connector = create_connector(
            connection.connector_type,
            organization_id=org_id,
            config=connection.config or {},
            credentials=credentials,
            cursor=connection.cursor,
        )

        result = await connector.sync(db, mode=sync_mode)
        duration_ms = int((_utcnow() - started).total_seconds() * 1000)

        if result.incomplete:
            raise ConnectorError(
                result.errors[0] if result.errors else "Sync incomplete",
                retryable=False,
                failure_class=result.failure_class or "unknown_failure",
            )

        # Do not advance the incremental cursor unless the fetch finished.
        if result.cursor is not None:
            connection.cursor = result.cursor
        connection.record_count = int(
            db.scalar(
                select(func.count())
                .select_from(Supplier)
                .where(
                    Supplier.organization_id == org_id,
                    Supplier.external_id.isnot(None),
                )
            )
            or 0
        )
        connection.last_sync_at = _utcnow()
        connection.status = ConnectorStatus.CONNECTED
        connection.health = (
            ConnectorHealth.DEGRADED if result.errors else ConnectorHealth.HEALTHY
        )
        if result.errors:
            from app.services.platform_console import sanitize_error

            connection.last_error = sanitize_error("; ".join(result.errors[:5]))
            from app.connectors.dlq import enqueue_dead_letter

            enqueue_dead_letter(
                db,
                organization_id=org_id,
                connection_id=conn_id,
                connector_type=connection.connector_type.value,
                error=connection.last_error or "record errors",
                payload={"mode": sync_mode.value, "error_count": len(result.errors)},
            )
        else:
            connection.last_error = None
        from app.connectors.schedule import schedule_next

        connection.next_sync_at = schedule_next(connection)

        # Persist refreshed tokens if connector mutated credentials (e.g. refresh_token)
        if connector.credentials != credentials:
            from app.connectors.credentials import encrypt_credentials

            connection.credentials_encrypted = encrypt_credentials(connector.credentials)

        job.status = (
            ImportStatus.PARTIAL
            if result.errors and result.records_imported
            else ImportStatus.FAILED
            if result.errors and not result.records_imported
            else ImportStatus.SUCCESS
        )
        job.rows_processed = result.records_processed
        job.rows_imported = result.records_imported
        job.rows_rejected = result.records_rejected
        job.duration_ms = duration_ms
        job.error_summary = result.errors or None
        mapping = _mapping(job)
        mapping["finished_at"] = _utcnow().isoformat()
        mapping["phase"] = job.status.value
        mapping["failure_class"] = (
            "data_validation_failure" if result.errors else "none"
        )
        job.mapping = mapping
        db.commit()
        set_session_org(db, org_id)

        logger.info(
            "sync_complete org_id=%s connection_id=%s job_id=%s status=%s "
            "processed=%s imported=%s rejected=%s duration_ms=%s",
            org_id,
            conn_id,
            job_pk,
            job.status.value,
            result.records_processed,
            result.records_imported,
            result.records_rejected,
            duration_ms,
        )

        try:
            from app.services import connector_studio, workflows
            from app.models.enums import WorkflowTrigger

            connector_studio.record_sync_log(
                db,
                org_id=org_id,
                connection_id=conn_id,
                mode=sync_mode.value,
                status=job.status.value,
                records_processed=result.records_processed,
                records_imported=result.records_imported,
                records_rejected=result.records_rejected,
                latency_ms=duration_ms,
                message=connection.last_error,
                details={"errors": result.errors[:10] if result.errors else []},
            )
            workflows.dispatch_trigger(
                db,
                org_id,
                WorkflowTrigger.CONNECTOR_SYNC,
                payload={
                    "connection_id": str(conn_id),
                    "status": job.status.value,
                    "records_imported": result.records_imported,
                },
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "post_sync_hooks_failed org_id=%s connection_id=%s job_id=%s",
                org_id,
                conn_id,
                job_pk,
            )

        try:
            from app.core.telemetry import CONNECTOR_SYNC_DURATION, CONNECTOR_SYNC_TOTAL

            if CONNECTOR_SYNC_TOTAL is not None:
                CONNECTOR_SYNC_TOTAL.labels(
                    connection.connector_type.value, job.status.value
                ).inc()
            if CONNECTOR_SYNC_DURATION is not None:
                CONNECTOR_SYNC_DURATION.labels(connection.connector_type.value).observe(
                    duration_ms / 1000.0
                )
        except Exception:  # noqa: BLE001
            pass

        return {
            "connection_id": str(conn_id),
            "organization_id": str(org_id),
            "job_id": str(job_pk),
            "status": job.status.value,
            "records_processed": result.records_processed,
            "records_imported": result.records_imported,
            "records_rejected": result.records_rejected,
            "errors": result.errors,
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        safe = _safe_error(exc)
        failure_class = _failure_class_for(exc)
        retryable = _is_retryable(exc)
        logger.exception(
            "sync_connection_failed org_id=%s connection_id=%s job_id=%s "
            "try=%s retryable=%s failure_class=%s",
            org_id,
            conn_id,
            job_pk,
            job_try,
            retryable,
            failure_class,
        )
        db.rollback()
        set_session_org(db, org_id)
        will_retry = bool(is_arq and retryable and job_try < SYNC_MAX_TRIES)
        try:
            connection = db.get(Connection, conn_id)
            if job_pk is not None:
                job = db.get(ImportJob, job_pk)
            if connection:
                if will_retry:
                    connection.status = ConnectorStatus.SYNCING
                    connection.health = ConnectorHealth.DEGRADED
                else:
                    connection.status = ConnectorStatus.ERROR
                    connection.health = ConnectorHealth.DOWN
                connection.last_error = safe
                from app.connectors.dlq import enqueue_dead_letter

                enqueue_dead_letter(
                    db,
                    organization_id=org_id,
                    connection_id=conn_id,
                    connector_type=str(
                        connection.connector_type.value if connection else "unknown"
                    ),
                    error=safe,
                    payload={"mode": mode, "failure_class": failure_class, "job_try": job_try},
                )
            if job is None:
                job = ImportJob(
                    organization_id=org_id,
                    source_name=str(connection.name if connection else connection_id),
                    source_type=str(
                        connection.connector_type.value if connection else "unknown"
                    ),
                    entity_type="mixed",
                    status=ImportStatus.RETRYING if will_retry else ImportStatus.FAILED,
                    error_summary=[safe],
                    mapping={
                        "connection_id": str(conn_id),
                        "mode": mode,
                        "retry_count": job_try,
                        "failure_class": failure_class,
                        "phase": "retrying" if will_retry else "failed",
                        "finished_at": None if will_retry else _utcnow().isoformat(),
                    },
                )
                db.add(job)
            else:
                job.status = ImportStatus.RETRYING if will_retry else ImportStatus.FAILED
                job.error_summary = [safe]
                mapping = _mapping(job)
                mapping["failure_class"] = failure_class
                mapping["retry_count"] = job_try
                mapping["phase"] = "retrying" if will_retry else "failed"
                if not will_retry:
                    mapping["finished_at"] = _utcnow().isoformat()
                job.mapping = mapping
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception(
                "Failed to persist sync error state org_id=%s connection_id=%s job_id=%s",
                org_id,
                conn_id,
                job_pk,
            )

        if will_retry:
            from arq import Retry

            delay = min(60, 2 ** max(0, job_try - 1))
            raise Retry(defer=delay)

        if is_arq and not retryable:
            # Permanent failure: do not ask ARQ to retry.
            return {
                "connection_id": str(conn_id),
                "organization_id": str(org_id),
                "job_id": str(job_pk) if job_pk else None,
                "status": "failed",
                "retryable": False,
                "failure_class": failure_class,
                "error": safe,
            }
        raise
    finally:
        db.close()


# ARQ worker function table (import this from the worker entrypoint).
class WorkerSettings:
    functions = [sync_connection]
    redis_settings = None  # set from REDIS_URL in worker bootstrap
    max_tries = SYNC_MAX_TRIES
    job_timeout = 600
    retry_jobs = True
    health_check_interval = 30
