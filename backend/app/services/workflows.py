"""Workflow automation engine — trigger → conditions → actions (ARQ-compatible)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WorkflowRule, WorkflowRun
from app.models.enums import WorkflowRunStatus, WorkflowTrigger
from app.services import alert_channels, executive_reports, incidents as incident_service
from app.services.timeline import record_event

logger = logging.getLogger("supply.workflows")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_rules(db: Session, org_id: UUID) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(WorkflowRule)
        .where(WorkflowRule.organization_id == org_id)
        .order_by(WorkflowRule.created_at.desc())
    ).all()
    return [_rule_out(r) for r in rows]


def create_rule(
    db: Session,
    org_id: UUID,
    *,
    name: str,
    trigger: WorkflowTrigger | str,
    conditions: list[dict] | None = None,
    actions: list[dict] | None = None,
    description: str | None = None,
    schedule_cron: str | None = None,
    created_by_user_id: UUID | None = None,
) -> WorkflowRule:
    if isinstance(trigger, str):
        trigger = WorkflowTrigger(trigger)
    rule = WorkflowRule(
        organization_id=org_id,
        name=name,
        description=description,
        trigger=trigger,
        conditions=conditions or [],
        actions=actions or [],
        schedule_cron=schedule_cron,
        created_by_user_id=created_by_user_id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    record_event(
        db,
        organization_id=org_id,
        title=f"Workflow created: {name}",
        event_type="system",
        entity_type="workflow",
        entity_id=rule.id,
        severity="info",
        payload={"trigger": trigger.value},
    )
    db.commit()
    return rule


def update_rule(
    db: Session,
    org_id: UUID,
    rule_id: UUID,
    **fields: Any,
) -> WorkflowRule | None:
    rule = db.get(WorkflowRule, rule_id)
    if rule is None or rule.organization_id != org_id:
        return None
    for key in ("name", "description", "conditions", "actions", "schedule_cron", "is_active"):
        if key in fields and fields[key] is not None:
            setattr(rule, key, fields[key])
    if "trigger" in fields and fields["trigger"] is not None:
        t = fields["trigger"]
        rule.trigger = WorkflowTrigger(t) if isinstance(t, str) else t
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, org_id: UUID, rule_id: UUID) -> bool:
    rule = db.get(WorkflowRule, rule_id)
    if rule is None or rule.organization_id != org_id:
        return False
    db.delete(rule)
    db.commit()
    return True


def evaluate_conditions(conditions: list[dict], payload: dict[str, Any]) -> bool:
    if not conditions:
        return True
    for cond in conditions:
        field = cond.get("field")
        op = cond.get("op", "eq")
        expected = cond.get("value")
        actual = payload.get(field) if field else None
        if field and "." in str(field):
            actual = payload
            for part in str(field).split("."):
                actual = (actual or {}).get(part) if isinstance(actual, dict) else None
        if op == "eq" and actual != expected:
            return False
        if op == "neq" and actual == expected:
            return False
        if op == "gt":
            try:
                if float(actual) <= float(expected):
                    return False
            except (TypeError, ValueError):
                return False
        if op == "gte":
            try:
                if float(actual) < float(expected):
                    return False
            except (TypeError, ValueError):
                return False
        if op == "lt":
            try:
                if float(actual) >= float(expected):
                    return False
            except (TypeError, ValueError):
                return False
        if op == "contains":
            if expected not in str(actual or ""):
                return False
    return True


def execute_rule(
    db: Session,
    org_id: UUID,
    rule_id: UUID,
    *,
    payload: dict[str, Any] | None = None,
) -> WorkflowRun | None:
    rule = db.get(WorkflowRule, rule_id)
    if rule is None or rule.organization_id != org_id:
        return None
    payload = payload or {}
    run = WorkflowRun(
        organization_id=org_id,
        rule_id=rule.id,
        status=WorkflowRunStatus.RUNNING,
        trigger_payload=payload,
        started_at=_utcnow(),
    )
    db.add(run)
    db.flush()

    if not rule.is_active:
        run.status = WorkflowRunStatus.SKIPPED
        run.error = "Rule inactive"
        run.finished_at = _utcnow()
        db.commit()
        db.refresh(run)
        return run

    if not evaluate_conditions(rule.conditions or [], payload):
        run.status = WorkflowRunStatus.SKIPPED
        run.error = "Conditions not met"
        run.finished_at = _utcnow()
        db.commit()
        db.refresh(run)
        return run

    results: list[dict[str, Any]] = []
    try:
        for action in rule.actions or []:
            results.append(_run_action(db, org_id, action, payload))
        run.status = WorkflowRunStatus.SUCCEEDED
        run.result = {"actions": results}
        rule.run_count = int(rule.run_count or 0) + 1
        rule.last_run_at = _utcnow()
    except Exception as exc:  # noqa: BLE001
        logger.exception("workflow_action_failed rule=%s", rule_id)
        run.status = WorkflowRunStatus.FAILED
        run.error = str(exc)[:2000]
        run.result = {"actions": results}
    run.finished_at = _utcnow()
    db.add(rule)
    db.commit()
    db.refresh(run)
    return run


def dispatch_trigger(
    db: Session,
    org_id: UUID,
    trigger: WorkflowTrigger | str,
    payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if isinstance(trigger, str):
        trigger = WorkflowTrigger(trigger)
    payload = payload or {}
    rules = db.scalars(
        select(WorkflowRule).where(
            WorkflowRule.organization_id == org_id,
            WorkflowRule.trigger == trigger,
            WorkflowRule.is_active.is_(True),
        )
    ).all()
    outs: list[dict[str, Any]] = []
    for rule in rules:
        run = execute_rule(db, org_id, rule.id, payload=payload)
        if run:
            outs.append(
                {
                    "rule_id": str(rule.id),
                    "run_id": str(run.id),
                    "status": run.status.value,
                }
            )
    return outs


def _run_action(
    db: Session, org_id: UUID, action: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    atype = (action.get("type") or "").lower()
    if atype == "create_incident":
        from app.models.enums import IncidentSeverity

        sev_raw = action.get("severity") or "high"
        severity = (
            IncidentSeverity(sev_raw) if isinstance(sev_raw, str) else sev_raw
        )
        inc = incident_service.create_incident_from_alerts(
            db,
            org_id,
            title=action.get("title") or payload.get("title") or "Automated incident",
            severity=severity,
        )
        return {"type": atype, "incident_id": str(inc.id)}
    if atype in {"email", "notify_email"}:
        subject = action.get("subject") or "ATLASOPS workflow notification"
        body = action.get("body") or str(payload)
        alert_channels.notify_org_channels(
            db,
            org_id,
            subject=subject,
            body=body,
            channels=["email", "slack", "teams", "webhook"],
        )
        return {"type": atype, "ok": True, "subject": subject}
    if atype in {"slack", "teams", "webhook"}:
        alert_channels.notify_org_channels(
            db,
            org_id,
            subject=action.get("subject") or "Workflow",
            body=str(payload),
            channels=[atype],
        )
        return {"type": atype, "ok": True}
    if atype == "generate_report":
        kind = action.get("kind") or "operations"
        report = executive_reports.generate_report(db, org_id, kind)
        return {"type": atype, "kind": report.get("kind"), "title": report.get("title")}
    if atype == "run_ai_summary":
        from app.services import ai_orchestration

        prompt = action.get("prompt") or f"Summarize operational event: {payload}"
        result = ai_orchestration.orchestrate(db, prompt)
        return {"type": atype, "intent": result.get("intent"), "confidence": result.get("confidence")}
    if atype == "run_simulation":
        return {"type": atype, "queued": True, "note": "Enqueue simulation via /simulations API"}
    if atype == "escalate":
        return {"type": atype, "escalated": True, "level": action.get("level") or "leadership"}
    if atype == "close_incident":
        iid = action.get("incident_id") or payload.get("incident_id")
        if iid:
            incident_service.resolve_incident(
                db, org_id, UUID(str(iid)), resolution=action.get("resolution") or "Closed by workflow"
            )
            return {"type": atype, "incident_id": str(iid)}
        return {"type": atype, "ok": False, "error": "missing incident_id"}
    return {"type": atype or "unknown", "ok": False, "error": "unsupported_action"}


def list_runs(db: Session, org_id: UUID, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.organization_id == org_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "rule_id": str(r.rule_id),
            "status": r.status.value,
            "error": r.error,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _rule_out(r: WorkflowRule) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "name": r.name,
        "description": r.description,
        "trigger": r.trigger.value,
        "conditions": r.conditions,
        "actions": r.actions,
        "schedule_cron": r.schedule_cron,
        "is_active": r.is_active,
        "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
        "run_count": r.run_count,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
