"""ARQ jobs for Phase C enterprise operations."""
from __future__ import annotations

import logging
import json
from uuid import UUID

from app.core.database import SessionLocal
from app.core.job_security import verify_tenant_job
from app.models import Organization, WorkflowRule
from app.models.enums import OrgStatus, WorkflowTrigger
from app.services import predictions, workflows
from app.tenancy.rls import set_session_org
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def run_workflow(
    ctx: dict | None,
    organization_id: str | UUID,
    rule_id: str | UUID,
    payload: dict | None = None,
    signature: str | None = None,
) -> dict:
    verify_tenant_job("run_workflow", signature, str(organization_id), str(rule_id),
                      json.dumps(payload or {}, sort_keys=True, separators=(",", ":")))
    db = SessionLocal()
    try:
        org_id = UUID(str(organization_id))
        set_session_org(db, org_id)
        run = workflows.execute_rule(
            db, org_id, UUID(str(rule_id)), payload=payload or {}
        )
        if run is None:
            return {"ok": False, "error": "rule_not_found"}
        return {"ok": True, "run_id": str(run.id), "status": run.status.value}
    finally:
        db.close()


async def generate_org_predictions(ctx: dict | None, organization_id: str | UUID, signature: str | None = None) -> dict:
    verify_tenant_job("generate_org_predictions", signature, str(organization_id))
    db = SessionLocal()
    try:
        org_id = UUID(str(organization_id))
        set_session_org(db, org_id)
        items = predictions.generate(db, org_id)
        return {"ok": True, "count": len(items)}
    finally:
        db.close()


async def enqueue_scheduled_workflows(ctx: dict | None) -> dict:
    """Cron: fire schedule-trigger workflows for active orgs."""
    db = SessionLocal()
    fired = 0
    try:
        orgs = db.scalars(
            select(Organization).where(Organization.status.in_([OrgStatus.ACTIVE, OrgStatus.TRIALING]))
        ).all()
        for org in orgs:
            try:
                set_session_org(db, org.id)
                rules = db.scalars(
                    select(WorkflowRule).where(
                        WorkflowRule.organization_id == org.id,
                        WorkflowRule.trigger == WorkflowTrigger.SCHEDULE,
                        WorkflowRule.is_active.is_(True),
                    )
                ).all()
                for rule in rules:
                    workflows.execute_rule(db, org.id, rule.id, payload={"source": "cron"})
                    fired += 1
            except Exception:  # noqa: BLE001
                db.rollback()
                logger.exception("scheduled_workflow_failed org=%s", org.id)
        return {"ok": True, "fired": fired}
    finally:
        db.close()


async def refresh_predictions_all(ctx: dict | None) -> dict:
    db = SessionLocal()
    count = 0
    try:
        orgs = db.scalars(
            select(Organization).where(Organization.status.in_([OrgStatus.ACTIVE, OrgStatus.TRIALING]))
        ).all()
        for org in orgs:
            try:
                set_session_org(db, org.id)
                predictions.generate(db, org.id)
                count += 1
            except Exception:  # noqa: BLE001
                db.rollback()
                logger.exception("prediction_refresh_failed org=%s", org.id)
        return {"ok": True, "orgs": count}
    finally:
        db.close()
