"""Data Sources / ingestion API (Connected Mode).

All endpoints are additive — Demo Mode and the seeded dataset are untouched.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import DataSource, ImportJob, User
from app.models.enums import (
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    UserRole,
)
from app.services import ingestion

router = APIRouter(prefix="/data", tags=["Data Sources"])

WRITE_ROLES = (UserRole.OPERATIONS_MANAGER, UserRole.ANALYST)


# --------------------------------------------------------------------------- #
# Serialization
# --------------------------------------------------------------------------- #
def _source_dict(s: DataSource) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "connector_type": s.connector_type.value,
        "status": s.status.value,
        "health": s.health.value,
        "base_url": s.base_url,
        "auth_method": s.auth_method,
        "api_key_masked": s.api_key_masked,
        "sync_frequency": s.sync_frequency,
        "webhook_url": s.webhook_url,
        "record_count": s.record_count,
        "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
        "is_active": s.is_active,
    }


def _job_dict(j: ImportJob) -> dict:
    return {
        "id": j.id,
        "source_name": j.source_name,
        "source_type": j.source_type,
        "entity_type": j.entity_type,
        "status": j.status.value,
        "rows_processed": j.rows_processed,
        "rows_imported": j.rows_imported,
        "rows_rejected": j.rows_rejected,
        "duration_ms": j.duration_ms,
        "error_summary": j.error_summary,
        "created_at": j.created_at.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Operating mode
# --------------------------------------------------------------------------- #
class ModeBody(BaseModel):
    mode: str


@router.get("/mode", response_model=dict)
def get_mode(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    return {"mode": ingestion.get_mode(db)}


@router.put("/mode", response_model=dict)
def set_mode(
    body: ModeBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    try:
        return {"mode": ingestion.set_mode(db, body.mode)}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode")


# --------------------------------------------------------------------------- #
# Dashboard summary
# --------------------------------------------------------------------------- #
@router.get("/summary", response_model=dict)
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    return ingestion.summary(db)


# --------------------------------------------------------------------------- #
# Integration templates
# --------------------------------------------------------------------------- #
@router.get("/integrations", response_model=list[dict])
def integrations(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[dict]:
    configured = {s.connector_type.value for s in db.scalars(select(DataSource)).all()}
    return [{**t, "configured": t["type"] in configured} for t in ingestion.INTEGRATION_TEMPLATES]


@router.get("/entities", response_model=dict)
def entities(_: User = Depends(get_current_user)) -> dict:
    return {
        name: {"label": spec["label"], "fields": spec["fields"]}
        for name, spec in ingestion.ENTITY_SPECS.items()
    }


# --------------------------------------------------------------------------- #
# Connectors (data sources)
# --------------------------------------------------------------------------- #
@router.get("/sources", response_model=list[dict])
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[dict]:
    return [_source_dict(s) for s in db.scalars(select(DataSource).order_by(DataSource.id)).all()]


@router.get("/sources/{source_id}", response_model=dict)
def get_source(source_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    s = db.get(DataSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    return _source_dict(s)


class CreateSourceBody(BaseModel):
    connector_type: str
    name: str | None = None


@router.post("/sources", response_model=dict, status_code=201)
def create_source(
    body: CreateSourceBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    try:
        ctype = ConnectorType(body.connector_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connector type")
    template = next((t for t in ingestion.INTEGRATION_TEMPLATES if t["type"] == ctype.value), None)
    source = DataSource(
        name=body.name or (template["name"] if template else ctype.value),
        connector_type=ctype,
        status=ConnectorStatus.NOT_CONFIGURED,
        health=ConnectorHealth.UNKNOWN,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _source_dict(source)


class ConfigBody(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    auth_method: str | None = None
    sync_frequency: str | None = None
    webhook_url: str | None = None


@router.put("/sources/{source_id}/config", response_model=dict)
def configure_source(
    source_id: int,
    body: ConfigBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    s = db.get(DataSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    if body.base_url is not None:
        s.base_url = body.base_url
    if body.auth_method is not None:
        s.auth_method = body.auth_method
    if body.sync_frequency is not None:
        s.sync_frequency = body.sync_frequency
    if body.webhook_url is not None:
        s.webhook_url = body.webhook_url
    if body.api_key:
        # never store raw secrets in this demo platform — keep a masked tail only
        tail = body.api_key[-4:] if len(body.api_key) >= 4 else "****"
        s.api_key_masked = "••••••••" + tail
    if s.status == ConnectorStatus.NOT_CONFIGURED:
        s.status = ConnectorStatus.DISCONNECTED
    db.commit()
    db.refresh(s)
    return _source_dict(s)


@router.post("/sources/{source_id}/test", response_model=dict)
def test_connection(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    import random

    s = db.get(DataSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    if not s.base_url:
        return {"ok": False, "latency_ms": 0, "message": "No base URL configured."}
    latency = random.randint(45, 320)
    ok = s.status != ConnectorStatus.ERROR
    return {
        "ok": ok,
        "latency_ms": latency,
        "message": f"Connection {'successful' if ok else 'failed'} ({latency} ms).",
    }


@router.post("/sources/{source_id}/sync", response_model=dict)
def sync_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    s = db.get(DataSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ingestion.sync_connector(db, s)


@router.delete("/sources/{source_id}", response_model=dict)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    s = db.get(DataSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    db.delete(s)
    db.commit()
    return {"deleted": True}


# --------------------------------------------------------------------------- #
# CSV / Excel import
# --------------------------------------------------------------------------- #
@router.post("/import/preview", response_model=dict)
def import_preview(
    entity: str = Form(...),
    sheet: str | None = Form(None),
    mapping: str | None = Form(None),
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> dict:
    if entity not in ingestion.ENTITY_SPECS:
        raise HTTPException(status_code=400, detail="Unknown entity")
    content = file.file.read()
    try:
        parsed = ingestion.parse_upload(file.filename or "upload.csv", content, sheet)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    columns = parsed["columns"]
    if not columns:
        raise HTTPException(status_code=400, detail="No columns detected in file.")

    suggested = ingestion.suggest_mapping(entity, columns)
    active_mapping = json.loads(mapping) if mapping else suggested
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
    mapping: str = Form(...),
    sheet: str | None = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    if entity not in ingestion.ENTITY_SPECS:
        raise HTTPException(status_code=400, detail="Unknown entity")
    try:
        mapping_dict = json.loads(mapping)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid mapping JSON")

    content = file.file.read()
    try:
        parsed = ingestion.parse_upload(file.filename or "upload.csv", content, sheet)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    source_type = "excel" if (file.filename or "").lower().endswith((".xlsx", ".xlsm")) else "csv"
    result = ingestion.commit_import(
        db,
        entity=entity,
        rows=parsed["rows"],
        mapping=mapping_dict,
        source_name=file.filename or f"{source_type} upload",
        source_type=source_type,
        user_id=user.id,
    )
    return result


# --------------------------------------------------------------------------- #
# Import history + pipeline monitor
# --------------------------------------------------------------------------- #
@router.get("/imports", response_model=list[dict])
def import_history(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[dict]:
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.source_type.in_(["csv", "excel"]))
        .order_by(ImportJob.created_at.desc())
        .limit(50)
    ).all()
    return [_job_dict(j) for j in jobs]


@router.get("/pipeline", response_model=list[dict])
def pipeline_runs(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[dict]:
    jobs = db.scalars(
        select(ImportJob).order_by(ImportJob.created_at.desc()).limit(60)
    ).all()
    return [_job_dict(j) for j in jobs]
