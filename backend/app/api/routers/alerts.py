"""Alert Center endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import Alert, AuditLog
from app.models.enums import AlertPriority, AlertStatus, AlertType
from app.schemas.entities import AlertOut, AlertUpdate, Page
from app.services import alert_engine
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/alerts", tags=["Alert Center"])


@router.get("", response_model=Page[AlertOut])
def list_alerts(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.read")),
    status_filter: AlertStatus | None = Query(None, alias="status"),
    priority: AlertPriority | None = None,
    alert_type: AlertType | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[AlertOut]:
    stmt = select(Alert).where(Alert.organization_id == ctx.organization_id)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if priority:
        stmt = stmt.where(Alert.priority == priority)
    if alert_type:
        stmt = stmt.where(Alert.alert_type == alert_type)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())
    return Page[AlertOut](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats", response_model=dict)
def alert_stats(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.read")),
) -> dict:
    org = Alert.organization_id == ctx.organization_id
    by_priority = dict(
        db.execute(
            select(Alert.priority, func.count(Alert.id))
            .where(org, Alert.status != AlertStatus.RESOLVED)
            .group_by(Alert.priority)
        ).all()
    )
    by_type = dict(
        db.execute(
            select(Alert.alert_type, func.count(Alert.id))
            .where(org, Alert.status != AlertStatus.RESOLVED)
            .group_by(Alert.alert_type)
        ).all()
    )
    return {
        "open": db.scalar(
            select(func.count(Alert.id)).where(org, Alert.status == AlertStatus.OPEN)
        )
        or 0,
        "acknowledged": db.scalar(
            select(func.count(Alert.id)).where(org, Alert.status == AlertStatus.ACKNOWLEDGED)
        )
        or 0,
        "investigating": db.scalar(
            select(func.count(Alert.id)).where(org, Alert.status == AlertStatus.INVESTIGATING)
        )
        or 0,
        "resolved": db.scalar(
            select(func.count(Alert.id)).where(org, Alert.status == AlertStatus.RESOLVED)
        )
        or 0,
        "dismissed": db.scalar(
            select(func.count(Alert.id)).where(org, Alert.status == AlertStatus.DISMISSED)
        )
        or 0,
        "by_priority": {k.value: v for k, v in by_priority.items()},
        "by_type": {k.value: v for k, v in by_type.items()},
    }


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.update")),
) -> Alert:
    alert = db.scalar(
        select(Alert).where(Alert.id == alert_id, Alert.organization_id == ctx.organization_id)
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = payload.status
    if payload.resolution_note is not None:
        alert.resolution_note = payload.resolution_note
    if payload.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        alert.resolved_at = datetime.now(timezone.utc)
    elif payload.status in {
        AlertStatus.OPEN,
        AlertStatus.ACKNOWLEDGED,
        AlertStatus.INVESTIGATING,
    }:
        alert.resolved_at = None
    db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="update_alert",
            resource="alert",
            resource_id=str(alert.id),
            detail=f"{alert.id} -> {payload.status.value}",
        )
    )
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/generate", response_model=dict)
def generate(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("alerts.create")),
) -> dict:
    _ = ctx
    count = alert_engine.generate_alerts(db)
    return {"alerts_created": count}
