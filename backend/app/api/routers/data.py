"""Connections / ingestion API (Connected Mode)."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.connectors.credentials import (
    SECRET_KEYS,
    decrypt_credentials,
    encrypt_credentials,
    merge_credentials,
    public_credential_hints,
)
from app.core.rate_limit import rate_limit_upload
from app.core.uploads import ALLOWED_IMPORT_EXTENSIONS, assert_safe_upload
from app.models import Connection, ImportJob
from app.models.enums import ConnectorHealth, ConnectorStatus, ConnectorType, ImportStatus
from app.services import ingestion
from app.services.platform_console import classify_failure, sanitize_error
from app.tenancy.context import TenantContext

MAX_IMPORT_BYTES = 15 * 1024 * 1024

router = APIRouter(prefix="/data", tags=["Data Sources"])


def _connection_dict(c: Connection) -> dict:
    config = dict(c.config or {})
    for key in list(config.keys()):
        if key in SECRET_KEYS:
            config.pop(key, None)
    hints: dict = {}
    try:
        if c.credentials_encrypted:
            hints = public_credential_hints(decrypt_credentials(c.credentials_encrypted))
    except ValueError:
        hints = {"credentials_status": "unreadable"}
    return {
        "id": str(c.id),
        "name": c.name,
        "connector_type": c.connector_type.value,
        "status": c.status.value,
        "health": c.health.value,
        "config": config,
        "base_url": config.get("base_url"),
        "auth_method": config.get("auth_method"),
        "api_key_masked": config.get("api_key_masked") or hints.get("api_key_masked"),
        "credential_hints": hints,
        "sync_frequency": c.sync_frequency,
        "webhook_url": c.webhook_url,
        "record_count": c.record_count,
        "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
        "last_error": sanitize_error(c.last_error),
        "failure_class": classify_failure(c.last_error),
        "is_active": c.is_active,
    }


def _job_dict(j: ImportJob) -> dict:
    mapping = dict(j.mapping or {})
    err = j.error_summary
    if isinstance(err, list):
        err = [sanitize_error(str(x)) for x in err[:10]]
    elif isinstance(err, dict):
        err = {k: sanitize_error(str(v)) if isinstance(v, str) else v for k, v in err.items()}
    elif isinstance(err, str):
        err = sanitize_error(err)
    return {
        "id": str(j.id),
        "source_name": j.source_name,
        "source_type": j.source_type,
        "entity_type": j.entity_type,
        "status": j.status.value,
        "rows_processed": j.rows_processed,
        "rows_imported": j.rows_imported,
        "rows_rejected": j.rows_rejected,
        "duration_ms": j.duration_ms,
        "error_summary": err,
        "created_at": j.created_at.isoformat(),
        "started_at": mapping.get("started_at"),
        "finished_at": mapping.get("finished_at"),
        "retry_count": int(mapping.get("retry_count") or 0),
        "failure_class": mapping.get("failure_class") or classify_failure(
            err[0] if isinstance(err, list) and err else None
        ),
        "connection_id": mapping.get("connection_id"),
    }


class ModeBody(BaseModel):
    mode: str


@router.get("/mode", response_model=dict)
def get_mode(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    return {"mode": ingestion.get_mode(db, ctx.organization_id)}


@router.put("/mode", response_model=dict)
def set_mode(
    body: ModeBody,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.update")),
) -> dict:
    try:
        return {"mode": ingestion.set_mode(db, ctx.organization_id, body.mode)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mode") from exc


@router.get("/summary", response_model=dict)
def summary(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    return ingestion.summary(db, ctx.organization_id)


@router.get("/integrations", response_model=list[dict])
def integrations(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> list[dict]:
    configured = {
        c.connector_type.value
        for c in db.scalars(
            select(Connection).where(Connection.organization_id == ctx.organization_id)
        ).all()
    }
    return [{**t, "configured": t["type"] in configured} for t in ingestion.INTEGRATION_TEMPLATES]


@router.get("/entities", response_model=dict)
def entities(
    ctx: TenantContext = Depends(require_permission("imports.read")),
) -> dict:
    _ = ctx
    return {
        name: {"label": spec["label"], "fields": spec["fields"]}
        for name, spec in ingestion.ENTITY_SPECS.items()
    }


@router.get("/sources", response_model=list[dict])
def list_sources(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> list[dict]:
    rows = db.scalars(
        select(Connection)
        .where(Connection.organization_id == ctx.organization_id)
        .order_by(Connection.created_at.desc())
    ).all()
    return [_connection_dict(c) for c in rows]


@router.get("/sources/{source_id}", response_model=dict)
def get_source(
    source_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    c = db.scalar(
        select(Connection).where(
            Connection.id == source_id,
            Connection.organization_id == ctx.organization_id,
        )
    )
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _connection_dict(c)


class CreateSourceBody(BaseModel):
    connector_type: str
    name: str | None = None


@router.post("/sources", response_model=dict, status_code=201)
def create_source(
    body: CreateSourceBody,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.create")),
) -> dict:
    from app.billing.enforce import enforce_connector_limit

    try:
        ctype = ConnectorType(body.connector_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid connector type") from exc
    enforce_connector_limit(db, ctx.organization_id, additional=1)
    template = next((t for t in ingestion.INTEGRATION_TEMPLATES if t["type"] == ctype.value), None)
    conn = Connection(
        organization_id=ctx.organization_id,
        name=body.name or (template["name"] if template else ctype.value),
        connector_type=ctype,
        status=ConnectorStatus.NOT_CONFIGURED,
        health=ConnectorHealth.UNKNOWN,
        config={},
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return _connection_dict(conn)


class ConfigBody(BaseModel):
    """Configure a connection.

    Backwards compatible: ``api_key`` alone still works (stored as
    ``credentials.api_key``). Prefer ``credentials`` dict for OAuth connectors
    (client_id, client_secret, tenant_id, refresh_token, …).
    Non-secret settings go in ``config`` / top-level fields.
    """

    base_url: str | None = None
    api_key: str | None = None  # legacy
    credentials: dict[str, str] | None = None
    config: dict | None = None
    auth_method: str | None = None
    sync_frequency: str | None = None
    webhook_url: str | None = None


@router.put("/sources/{source_id}/config", response_model=dict)
def configure_source(
    source_id: UUID,
    body: ConfigBody,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.update")),
) -> dict:
    from app.connectors.ssrf import SSRFError, validate_connector_config_urls

    c = db.scalar(
        select(Connection).where(
            Connection.id == source_id,
            Connection.organization_id == ctx.organization_id,
        )
    )
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    config = dict(c.config or {})
    if body.config:
        leaked = sorted(k for k in body.config if k in SECRET_KEYS and body.config[k] is not None)
        if leaked:
            raise HTTPException(
                status_code=400,
                detail=f"Secret fields must be sent via credentials, not config: {', '.join(leaked)}",
            )
        config.update(
            {
                k: v
                for k, v in body.config.items()
                if v is not None and k not in SECRET_KEYS
            }
        )
    if body.base_url is not None:
        config["base_url"] = body.base_url
    if body.auth_method is not None:
        config["auth_method"] = body.auth_method
    if body.sync_frequency is not None:
        from app.connectors.schedule import parse_sync_frequency
        if body.sync_frequency.lower() not in {"manual", ""} and parse_sync_frequency(body.sync_frequency) is None:
            raise HTTPException(status_code=400, detail="Choose a supported periodic frequency or Manual")
        c.sync_frequency = body.sync_frequency or None
    if body.webhook_url is not None:
        c.webhook_url = body.webhook_url

    updates: dict = dict(body.credentials or {})
    if body.api_key:
        updates["api_key"] = body.api_key
        config["api_key_masked"] = "••••••••" + (
            body.api_key[-4:] if len(body.api_key) >= 4 else "****"
        )

    if updates:
        existing: dict = {}
        if c.credentials_encrypted:
            try:
                existing = decrypt_credentials(c.credentials_encrypted)
            except ValueError:
                existing = {}
        merged = merge_credentials(existing, updates)
        c.credentials_encrypted = encrypt_credentials(merged)
        # Keep tenant_id / instance_url in config when provided as credentials
        # but they are not secrets — also mirror non-secret keys into config.
        for key in ("tenant_id", "instance_url", "company_id", "environment"):
            if key in merged and merged[key]:
                config[key] = merged[key]

    try:
        validate_connector_config_urls(c.connector_type, config)
        if "sync_entities" in config:
            from app.connectors.mapped_sync import validate_mappings
            from app.connectors.base import ConnectorError
            try:
                validate_mappings(config)
            except ConnectorError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SSRFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    c.config = config
    if c.status == ConnectorStatus.NOT_CONFIGURED:
        c.status = ConnectorStatus.DISCONNECTED
    db.commit()
    db.refresh(c)
    return _connection_dict(c)


@router.post("/sources/{source_id}/test", response_model=dict)
async def test_connection(
    source_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.sync")),
) -> dict:
    import time

    from app.connectors.base import ConnectorError
    from app.connectors.credentials import decrypt_credentials
    from app.connectors.registry import create_connector

    c = db.scalar(
        select(Connection).where(
            Connection.id == source_id,
            Connection.organization_id == ctx.organization_id,
        )
    )
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    if not c.credentials_encrypted:
        raise HTTPException(status_code=400, detail="Credentials not configured")
    started = time.perf_counter()
    try:
        credentials = decrypt_credentials(c.credentials_encrypted)
        connector = create_connector(
            c.connector_type,
            organization_id=ctx.organization_id,
            config={**(c.config or {}), "_connection_id": str(c.id)},
            credentials=credentials,
        )
        ok = await connector.test_connection()
        latency_ms = int((time.perf_counter() - started) * 1000)
        c.status = ConnectorStatus.CONNECTED if ok else ConnectorStatus.ERROR
        if not ok:
            c.health = ConnectorHealth.DOWN
            c.last_error = "Connection test failed"
        else:
            c.last_error = None
            # Reachable credentials are not a successful sync.
            if c.last_sync_at and c.health != ConnectorHealth.DOWN:
                c.health = ConnectorHealth.HEALTHY
            else:
                c.health = ConnectorHealth.UNKNOWN
        # Forward-migrate legacy credential blobs after a successful decrypt path.
        c.credentials_encrypted = encrypt_credentials(credentials)
        db.commit()
        return {
            "ok": ok,
            "latency_ms": latency_ms,
            "message": "Connection successful" if ok else "Connection test failed",
        }
    except ConnectorError as exc:
        c.health = ConnectorHealth.DOWN
        c.status = ConnectorStatus.ERROR
        c.last_error = sanitize_error(str(exc))
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=sanitize_error(str(exc)) or "Connection test failed",
        ) from exc


@router.post("/sources/{source_id}/sync", response_model=dict)
async def sync_source(
    source_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.sync")),
) -> dict:
    from app.connectors.base import ConnectorError
    from app.connectors.jobs import sync_connection
    from app.connectors.queue import enqueue_sync_connection
    from app.core.config import settings
    from app.models.enums import ConnectorStatus
    from app.services.audit import write_audit

    c = db.scalar(
        select(Connection).where(
            Connection.id == source_id,
            Connection.organization_id == ctx.organization_id,
        )
    )
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    if not c.credentials_encrypted:
        raise HTTPException(status_code=400, detail="Credentials not configured")

    # Tests / emergency only — never enabled in staging/production (fail-closed).
    if settings.CONNECTOR_SYNC_INLINE:
        from app.core.job_security import sign_tenant_job

        try:
            sig = sign_tenant_job(
                "sync_connection",
                str(c.id),
                str(ctx.organization_id),
                "incremental",
            )
            return await sync_connection(
                None,
                connection_id=c.id,
                organization_id=ctx.organization_id,
                mode="incremental",
                signature=sig,
            )
        except ConnectorError as exc:
            raise HTTPException(
                status_code=400,
                detail=sanitize_error(str(exc)) or "Sync failed",
            ) from exc

    from app.connectors.jobs import create_queued_import_job

    import_job = create_queued_import_job(db, c, mode="incremental")
    write_audit(
        db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="enqueue_sync",
        resource="connection",
        resource_id=str(c.id),
        detail=c.connector_type.value,
    )
    db.commit()

    existing_arq = (import_job.mapping or {}).get("arq_job_id")
    if existing_arq:
        return {
            "status": "queued",
            "job_id": existing_arq,
            "import_job_id": str(import_job.id),
            "connection_id": str(c.id),
            "message": "Sync already queued. Progress appears in pipeline / connection status.",
        }

    try:
        job_id = await enqueue_sync_connection(
            connection_id=c.id,
            organization_id=ctx.organization_id,
            mode="incremental",
        )
    except Exception as exc:  # noqa: BLE001 — map any Redis failure to 503
        c.status = ConnectorStatus.ERROR
        c.last_error = "Failed to enqueue sync"
        import_job.status = ImportStatus.FAILED
        mapping = dict(import_job.mapping or {})
        mapping["failure_class"] = "worker_failure"
        mapping["phase"] = "failed"
        import_job.mapping = mapping
        import_job.error_summary = ["Sync queue unavailable"]
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Sync queue unavailable. Ensure Redis and the worker are running.",
        ) from exc

    mapping = dict(import_job.mapping or {})
    mapping["arq_job_id"] = job_id
    import_job.mapping = mapping
    db.commit()

    return {
        "status": "queued",
        "job_id": job_id,
        "import_job_id": str(import_job.id),
        "connection_id": str(c.id),
        "message": "Sync enqueued. Progress appears in pipeline / connection status.",
    }


@router.delete("/sources/{source_id}", response_model=dict)
def delete_source(
    source_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.delete")),
) -> dict:
    c = db.scalar(
        select(Connection).where(
            Connection.id == source_id,
            Connection.organization_id == ctx.organization_id,
        )
    )
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    c.credentials_encrypted = None
    c.cursor = None
    db.flush()
    db.delete(c)
    db.commit()
    return {"deleted": True}


@router.post("/sources/{source_id}/disconnect", response_model=dict)
def disconnect_source(
    source_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.update")),
) -> dict:
    """Invalidate stored credentials without deleting the connector row."""
    c = db.scalar(
        select(Connection).where(
            Connection.id == source_id,
            Connection.organization_id == ctx.organization_id,
        )
    )
    if not c:
        raise HTTPException(status_code=404, detail="Connection not found")
    c.credentials_encrypted = None
    c.cursor = None
    c.status = ConnectorStatus.DISCONNECTED
    c.health = ConnectorHealth.UNKNOWN
    c.last_error = None
    db.commit()
    db.refresh(c)
    return _connection_dict(c)


@router.post("/import/preview", response_model=dict)
def import_preview(
    entity: str = Form(...),
    sheet: str | None = Form(None),
    mapping: str | None = Form(None),
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("imports.create")),
    _: None = Depends(rate_limit_upload),
) -> dict:
    _ = ctx
    if entity not in ingestion.ENTITY_SPECS:
        raise HTTPException(status_code=400, detail="Unknown entity")
    content = file.file.read(MAX_IMPORT_BYTES + 1)
    safe_name = assert_safe_upload(
        filename=file.filename or "upload.csv",
        content_type=file.content_type,
        size=len(content),
        max_bytes=MAX_IMPORT_BYTES,
        allowed_extensions=ALLOWED_IMPORT_EXTENSIONS,
    )
    try:
        parsed = ingestion.parse_upload(safe_name, content, sheet)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not parse file. Use UTF-8 CSV or macro-free XLSX with unique headers, values only, up to 10,000 rows and 100 columns.") from exc

    columns = parsed["columns"]
    if not columns:
        raise HTTPException(status_code=400, detail="No columns detected in file.")

    suggested = ingestion.suggest_mapping(entity, columns)
    try:
        active_mapping = ingestion.validate_mapping(entity, json.loads(mapping) if mapping else suggested, columns)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid column mapping") from exc
    validation = ingestion.validate_rows(entity, parsed["rows"], active_mapping)

    return {
        "entity": entity,
        "columns": columns,
        "sheets": parsed["sheets"],
        "suggested_mapping": suggested,
        "row_count": len(parsed["rows"]),
        "preview_rows": parsed["rows"][:10],
        "validation": validation,
    }


@router.post("/import/commit", response_model=dict)
def import_commit(
    entity: str = Form(...),
    mode: str = Form("create"),
    mapping: str = Form(...),
    sheet: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("imports.create")),
    _: None = Depends(rate_limit_upload),
) -> dict:
    if entity not in ingestion.ENTITY_SPECS:
        raise HTTPException(status_code=400, detail="Unknown entity")
    if mode not in {"create", "update"} or (mode == "update" and entity not in {"products", "shipments"}):
        raise HTTPException(status_code=400, detail="Update mode supports products and shipments only")
    try:
        mapping_dict = json.loads(mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid mapping JSON") from exc

    content = file.file.read(MAX_IMPORT_BYTES + 1)
    safe_name = assert_safe_upload(
        filename=file.filename or "upload.csv",
        content_type=file.content_type,
        size=len(content),
        max_bytes=MAX_IMPORT_BYTES,
        allowed_extensions=ALLOWED_IMPORT_EXTENSIONS,
    )
    try:
        parsed = ingestion.parse_upload(safe_name, content, sheet)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not parse file. Use UTF-8 CSV or macro-free XLSX with unique headers, values only, up to 10,000 rows and 100 columns.") from exc

    try:
        mapping_dict = ingestion.validate_mapping(entity, mapping_dict, parsed["columns"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid column mapping") from exc

    source_type = "excel" if safe_name.lower().endswith((".xlsx", ".xlsm")) else "csv"
    result = ingestion.commit_import(
        db,
        organization_id=ctx.organization_id,
        entity=entity,
        rows=parsed["rows"],
        mapping=mapping_dict,
        source_name=safe_name or f"{source_type} upload",
        source_type=source_type,
        user_id=ctx.user_id,
        mode=mode,
    )
    from app.services.audit import write_audit

    write_audit(
        db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="import",
        resource="import_job",
        resource_id=str(result.get("job_id") or ""),
        detail=f"{entity}:{mode}:{result.get('status')}:{result.get('rows_imported', 0)}",
        request=None,
    )
    db.commit()
    return result


@router.get("/imports", response_model=list[dict])
def import_history(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("imports.read")),
) -> list[dict]:
    jobs = db.scalars(
        select(ImportJob)
        .where(
            ImportJob.organization_id == ctx.organization_id,
            ImportJob.source_type.in_(["csv", "excel"]),
        )
        .order_by(ImportJob.created_at.desc())
        .limit(50)
    ).all()
    return [_job_dict(j) for j in jobs]


@router.get("/pipeline", response_model=list[dict])
def pipeline_runs(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("imports.read")),
) -> list[dict]:
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.organization_id == ctx.organization_id)
        .order_by(ImportJob.created_at.desc())
        .limit(60)
    ).all()
    return [_job_dict(j) for j in jobs]


@router.post("/demo/reset")
def reset_demo(db: Session = Depends(get_db_with_tenant),
               ctx: TenantContext = Depends(require_permission("org.update"))) -> dict:
    from app.seed.yc_demo import reset_workspace
    try:
        return reset_workspace(db, ctx.organization_id, ctx.user_id)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
