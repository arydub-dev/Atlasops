"""Alert Center endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import Alert, AuditLog, User
from app.models.enums import AlertPriority, AlertStatus, AlertType, UserRole
from app.schemas.entities import AlertOut, AlertUpdate, Page
from app.services import alert_engine

router = APIRouter(prefix="/alerts", tags=["Alert Center"])


@router.get("", response_model=Page[AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    status_filter: AlertStatus | None = Query(None, alias="status"),
    priority: AlertPriority | None = None,
    alert_type: AlertType | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[AlertOut]:
    stmt = select(Alert)
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
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    by_priority = dict(
        db.execute(
            select(Alert.priority, func.count(Alert.id))
            .where(Alert.status != AlertStatus.RESOLVED)
            .group_by(Alert.priority)
        ).all()
    )
    by_type = dict(
        db.execute(
            select(Alert.alert_type, func.count(Alert.id))
            .where(Alert.status != AlertStatus.RESOLVED)
            .group_by(Alert.alert_type)
        ).all()
    )
    return {
        "open": db.scalar(select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN)) or 0,
        "acknowledged": db.scalar(
            select(func.count(Alert.id)).where(Alert.status == AlertStatus.ACKNOWLEDGED)
        ) or 0,
        "resolved": db.scalar(
            select(func.count(Alert.id)).where(Alert.status == AlertStatus.RESOLVED)
        ) or 0,
        "by_priority": {k.value: v for k, v in by_priority.items()},
        "by_type": {k.value: v for k, v in by_type.items()},
    }


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.OPERATIONS_MANAGER, UserRole.ANALYST)),
) -> Alert:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = payload.status
    if payload.resolution_note is not None:
        alert.resolution_note = payload.resolution_note
    if payload.status == AlertStatus.RESOLVED:
        alert.resolved_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            user_id=user.id,
            action="update_alert",
            resource="alert",
            detail=f"{alert.id} -> {payload.status.value}",
        )
    )
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/generate", response_model=dict)
def generate(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.OPERATIONS_MANAGER, UserRole.ANALYST)),
) -> dict:
    count = alert_engine.generate_alerts(db)
    return {"alerts_created": count}
