"""Unified operational timeline across events, shipments, alerts, and risks."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, OperationalEvent, RiskAssessment, Shipment, ShipmentEvent


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def entity_timeline(
    db: Session,
    org_id: UUID,
    *,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Merge OperationalEvent + domain events into a sorted timeline."""
    items: list[dict[str, Any]] = []

    q = select(OperationalEvent).where(OperationalEvent.organization_id == org_id)
    if entity_type:
        q = q.where(OperationalEvent.entity_type == entity_type)
    if entity_id:
        q = q.where(OperationalEvent.entity_id == entity_id)
    if severity:
        q = q.where(OperationalEvent.severity == severity)
    for ev in db.scalars(q.order_by(OperationalEvent.occurred_at.desc()).limit(limit)).all():
        items.append(
            {
                "id": str(ev.id),
                "source": "operational_event",
                "event_type": ev.event_type.value
                if hasattr(ev.event_type, "value")
                else str(ev.event_type),
                "title": ev.title,
                "message": ev.message,
                "severity": ev.severity,
                "entity_type": ev.entity_type,
                "entity_id": str(ev.entity_id) if ev.entity_id else None,
                "occurred_at": _iso(ev.occurred_at),
                "actor": None,
                "connector_source": (ev.payload or {}).get("connector"),
                "payload": ev.payload or {},
            }
        )

    # Shipment event trail when scoped to a shipment
    if entity_type == "shipment" and entity_id:
        for se in db.scalars(
            select(ShipmentEvent)
            .where(ShipmentEvent.shipment_id == entity_id)
            .order_by(ShipmentEvent.event_time.desc())
            .limit(limit)
        ).all():
            items.append(
                {
                    "id": str(se.id),
                    "source": "shipment_event",
                    "event_type": "status_change",
                    "title": se.status or "Shipment update",
                    "message": se.description,
                    "severity": "info",
                    "entity_type": "shipment",
                    "entity_id": str(entity_id),
                    "occurred_at": _iso(se.event_time),
                    "actor": None,
                    "connector_source": se.location,
                    "payload": {},
                }
            )

    # Alerts touching the entity (or global recent)
    aq = select(Alert).where(Alert.organization_id == org_id)
    if entity_type and entity_id:
        aq = aq.where(Alert.entity_type == entity_type, Alert.entity_id == entity_id)
    for a in db.scalars(aq.order_by(Alert.created_at.desc()).limit(min(limit, 40))).all():
        items.append(
            {
                "id": str(a.id),
                "source": "alert",
                "event_type": "alert",
                "title": a.title,
                "message": a.message,
                "severity": a.priority.value if hasattr(a.priority, "value") else str(a.priority),
                "entity_type": a.entity_type,
                "entity_id": str(a.entity_id) if a.entity_id else None,
                "occurred_at": _iso(a.created_at),
                "actor": None,
                "connector_source": None,
                "payload": {"status": a.status.value if hasattr(a.status, "value") else str(a.status)},
            }
        )

    # Risk assessments
    rq = select(RiskAssessment).where(RiskAssessment.organization_id == org_id)
    if entity_type and entity_id:
        rq = rq.where(
            RiskAssessment.entity_type == entity_type,
            RiskAssessment.entity_id == entity_id,
        )
    for r in db.scalars(rq.order_by(RiskAssessment.created_at.desc()).limit(min(limit, 30))).all():
        items.append(
            {
                "id": str(r.id),
                "source": "risk",
                "event_type": "risk",
                "title": r.title,
                "message": r.recommendation,
                "severity": r.level.value if hasattr(r.level, "value") else str(r.level),
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "occurred_at": _iso(r.created_at),
                "actor": None,
                "connector_source": None,
                "payload": {"score": r.score},
            }
        )

    items.sort(key=lambda x: x.get("occurred_at") or "", reverse=True)
    return items[:limit]


def global_timeline(
    db: Session,
    org_id: UUID,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    return entity_timeline(db, org_id, limit=limit)


def record_event(
    db: Session,
    *,
    organization_id: UUID,
    title: str,
    event_type: str = "system",
    message: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    severity: str = "info",
    payload: dict | None = None,
) -> OperationalEvent:
    from app.models.enums import OperationalEventType

    try:
        et = OperationalEventType(event_type)
    except ValueError:
        et = OperationalEventType.SYSTEM
    row = OperationalEvent(
        organization_id=organization_id,
        event_type=et,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        payload=payload or {},
    )
    db.add(row)
    db.flush()
    return row
