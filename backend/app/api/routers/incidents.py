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


class IncidentProgress(BaseModel):
    status: IncidentStatus | None = None
    assign_to_me: bool = False
    note: str = Field(default="", max_length=4000)


@router.patch("/{incident_id}")
def update_progress(incident_id: UUID, payload: IncidentProgress,
                    db: Session = Depends(get_db_with_tenant),
                    ctx: TenantContext = Depends(require_permission("alerts.resolve"))) -> dict:
    inc = db.scalar(select(Incident).where(Incident.id==incident_id,
        Incident.organization_id==ctx.organization_id).with_for_update())
    if inc is None:
        raise HTTPException(status_code=404,detail="Incident not found")
    if inc.status in {IncidentStatus.RESOLVED,IncidentStatus.CLOSED}:
        raise HTTPException(status_code=409,detail="Resolved incidents cannot be changed through progress updates")
    if payload.status is not None:
        allowed = {IncidentStatus.OPEN:{IncidentStatus.INVESTIGATING},
            IncidentStatus.INVESTIGATING:{IncidentStatus.MITIGATING},IncidentStatus.MITIGATING:set()}
        if payload.status != inc.status and payload.status not in allowed.get(inc.status,set()):
            raise HTTPException(status_code=409,detail="Use the next progress step or resolve the incident with a resolution")
        inc.status = payload.status
    if payload.assign_to_me:
        inc.owner_user_id = ctx.user_id
    from app.services.audit import write_audit
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,
        action="incident_progress",resource="incident",resource_id=str(inc.id),detail=inc.status.value)
    from app.services.timeline import record_event
    record_event(db, organization_id=ctx.organization_id, title=f"Incident progress: {inc.status.value}",
        event_type="alert", entity_type="incident", entity_id=inc.id, severity="info",
        message=payload.note.strip() or None,
        payload={"status":inc.status.value,"owner_user_id":str(inc.owner_user_id) if inc.owner_user_id else None})
    db.commit()
    return incident_service.incident_detail(db,ctx.organization_id,inc.id)
