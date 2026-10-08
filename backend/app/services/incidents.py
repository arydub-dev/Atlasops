"""Incident management — first-class ops incidents linked to graph entities."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Incident, RiskAssessment
from app.models.enums import AlertStatus, IncidentSeverity, IncidentStatus
from app.services import ai_orchestration, graph, timeline
from app.services.timeline import record_event


def create_incident_from_alerts(
    db: Session,
    org_id: UUID,
    *,
    title: str,
    alert_ids: list[UUID] | None = None,
    severity: IncidentSeverity = IncidentSeverity.HIGH,
    owner_user_id: UUID | None = None,
) -> Incident:
    alerts: list[Alert] = []
    if alert_ids:
        alerts = list(
            db.scalars(
                select(Alert).where(
                    Alert.organization_id == org_id,
                    Alert.id.in_(alert_ids),
                )
            ).all()
        )
    else:
        alerts = list(
            db.scalars(
                select(Alert)
                .where(
                    Alert.organization_id == org_id,
                    Alert.status != AlertStatus.RESOLVED,
                )
                .order_by(Alert.created_at.desc())
                .limit(5)
            ).all()
        )

    affected = []
    for a in alerts:
        if a.entity_type and a.entity_id:
            affected.append({"type": a.entity_type, "id": str(a.entity_id), "via": "alert"})

    risks = list(
        db.scalars(
            select(RiskAssessment)
            .where(RiskAssessment.organization_id == org_id)
            .order_by(RiskAssessment.score.desc())
            .limit(3)
        ).all()
    )

    inc = Incident(
        organization_id=org_id,
        title=title,
        severity=severity,
        status=IncidentStatus.OPEN,
        owner_user_id=owner_user_id,
        summary="; ".join(a.title for a in alerts[:3]) or title,
        recommendations=[],
        affected_entities=affected,
        linked_alert_ids=[str(a.id) for a in alerts],
        linked_risk_ids=[str(r.id) for r in risks],
    )
    db.add(inc)
    db.flush()

    # AI summary (best-effort)
    try:
        orch = ai_orchestration.orchestrate(
            db,
            f"incident summary for: {title}. Alerts: {inc.summary}",
        )
        inc.ai_summary = orch["response"][:4000]
        inc.recommendations = [
            {"text": "Triage linked alerts", "priority": "high"},
            {"text": "Review graph impact neighborhood", "priority": "medium"},
        ]
    except Exception:
        inc.ai_summary = inc.summary

    record_event(
        db,
        organization_id=org_id,
        title=f"Incident opened: {title}",
        event_type="alert",
        entity_type="incident",
        entity_id=inc.id,
        severity=severity.value,
        payload={"incident_id": str(inc.id)},
    )
    db.commit()
    db.refresh(inc)
    return inc


def incident_detail(db: Session, org_id: UUID, incident_id: UUID) -> dict[str, Any] | None:
    inc = db.get(Incident, incident_id)
    if inc is None or inc.organization_id != org_id:
        return None

    tl = timeline.entity_timeline(
        db, org_id, entity_type="incident", entity_id=incident_id, limit=40
    )
    # Also pull timelines for affected entities
    for ent in (inc.affected_entities or [])[:5]:
        try:
            tl.extend(
                timeline.entity_timeline(
                    db,
                    org_id,
                    entity_type=ent.get("type"),
                    entity_id=UUID(ent["id"]),
                    limit=10,
                )
            )
        except Exception:
            continue
    tl.sort(key=lambda x: x.get("occurred_at") or "", reverse=True)

    impact = None
    if inc.affected_entities:
        first = inc.affected_entities[0]
        try:
            impact = graph.impact_analysis(
                db, org_id, first["type"], UUID(first["id"])  # type: ignore[arg-type]
            )
        except Exception:
            impact = None

    return {
        "id": str(inc.id),
        "title": inc.title,
        "severity": inc.severity.value,
        "status": inc.status.value,
        "owner_user_id": str(inc.owner_user_id) if inc.owner_user_id else None,
        "summary": inc.summary,
        "ai_summary": inc.ai_summary,
        "recommendations": [
            item if isinstance(item, str) else str(item.get("text", ""))
            for item in (inc.recommendations or []) if isinstance(item, (str, dict))
        ],
        "affected_entities": inc.affected_entities,
        "linked_alert_ids": inc.linked_alert_ids,
        "linked_risk_ids": inc.linked_risk_ids,
        "resolution": inc.resolution,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "timeline": tl[:50],
        "impact": impact,
    }


def resolve_incident(
    db: Session,
    org_id: UUID,
    incident_id: UUID,
    *,
    resolution: str,
) -> Incident | None:
    inc = db.scalar(select(Incident).where(Incident.id == incident_id, Incident.organization_id == org_id).with_for_update())
    if inc is None or inc.organization_id != org_id:
        return None
    inc.status = IncidentStatus.RESOLVED
    inc.resolution = resolution
    inc.resolved_at = datetime.now(timezone.utc)
    record_event(
        db,
        organization_id=org_id,
        title=f"Incident resolved: {inc.title}",
        event_type="alert",
        entity_type="incident",
        entity_id=inc.id,
        severity="info",
        payload={"resolution": resolution[:500]},
    )
    db.commit()
    db.refresh(inc)
    return inc
