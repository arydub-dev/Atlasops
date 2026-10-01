"""Incidents API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import Incident
from app.models.enums import IncidentSeverity, IncidentStatus
from app.services import incidents as incident_service
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    severity: IncidentSeverity = IncidentSeverity.HIGH
    alert_ids: list[UUID] = Field(default_factory=list)


class IncidentResolve(BaseModel):
    resolution: str = Field(min_length=3, max_length=4000)


@router.get("")
def list_incidents(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.read")),
) -> list[dict]:
    rows = db.scalars(
        select(Incident)
        .where(Incident.organization_id == ctx.organization_id)
        .order_by(Incident.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "severity": r.severity.value,
            "status": r.status.value,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "affected_count": len(r.affected_entities or []),
        }
        for r in rows
    ]


@router.post("", status_code=201)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.create")),
) -> dict:
    inc = incident_service.create_incident_from_alerts(
        db,
        ctx.organization_id,
        title=payload.title,
        alert_ids=payload.alert_ids or None,
        severity=payload.severity,
        owner_user_id=ctx.user_id,
    )
    detail = incident_service.incident_detail(db, ctx.organization_id, inc.id)
    assert detail is not None
    return detail


@router.get("/{incident_id}")
def get_incident(
    incident_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.read")),
) -> dict:
    detail = incident_service.incident_detail(db, ctx.organization_id, incident_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return detail


@router.post("/{incident_id}/resolve")
def resolve_incident(
    incident_id: UUID,
    payload: IncidentResolve,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.resolve")),
) -> dict:
    inc = incident_service.resolve_incident(
        db, ctx.organization_id, incident_id, resolution=payload.resolution
    )
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    detail = incident_service.incident_detail(db, ctx.organization_id, incident_id)
    assert detail is not None
    return detail
