"""Connector Studio API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.services import connector_studio
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/connector-studio", tags=["Connector Studio"])


class StudioConfigUpdate(BaseModel):
    field_mappings: list[dict] | None = None
    transforms: list[dict] | None = None
    validation_rules: list[dict] | None = None
    conflict_resolution: str | None = None
    retry_policy: dict | None = None
    schedule: dict | None = None
    manual_overrides: dict | None = None
    webhook_url: str | None = None
    sync_frequency: str | None = None


@router.get("/catalogue")
def get_catalogue(
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    _ = ctx
    return {"items": connector_studio.catalogue()}


@router.get("/diagnostics")
def diagnostics(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    return connector_studio.diagnostics_summary(db, ctx.organization_id)


@router.get("/connections/{connection_id}")
def studio_detail(
    connection_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    detail = connector_studio.connection_studio_detail(db, ctx.organization_id, connection_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return detail


@router.put("/connections/{connection_id}/config")
def update_config(
    connection_id: UUID,
    payload: StudioConfigUpdate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.update")),
) -> dict:
    conn = connector_studio.update_studio_config(
        db,
        ctx.organization_id,
        connection_id,
        **payload.model_dump(exclude_unset=True),
    )
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    detail = connector_studio.connection_studio_detail(db, ctx.organization_id, connection_id)
    assert detail is not None
    return detail


@router.post("/connections/{connection_id}/preview")
def preview_sync(
    connection_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    preview = connector_studio.sync_preview(db, ctx.organization_id, connection_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return preview
