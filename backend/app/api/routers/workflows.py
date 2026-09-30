"""Workflow automation API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models.enums import WorkflowTrigger
from app.services import workflows
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/workflows", tags=["Workflows"])


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    trigger: WorkflowTrigger
    conditions: list[dict] = Field(default_factory=list)
    actions: list[dict] = Field(default_factory=list)
    schedule_cron: str | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger: WorkflowTrigger | None = None
    conditions: list[dict] | None = None
    actions: list[dict] | None = None
    schedule_cron: str | None = None
    is_active: bool | None = None


class WorkflowExecute(BaseModel):
    payload: dict = Field(default_factory=dict)


@router.get("")
def list_workflows(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("workflows.read")),
) -> list[dict]:
    return workflows.list_rules(db, ctx.organization_id)


@router.post("", status_code=201)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("workflows.manage")),
) -> dict:
    rule = workflows.create_rule(
        db,
        ctx.organization_id,
        name=payload.name,
        description=payload.description,
        trigger=payload.trigger,
        conditions=payload.conditions,
        actions=payload.actions,
        schedule_cron=payload.schedule_cron,
        created_by_user_id=ctx.user_id,
    )
    items = workflows.list_rules(db, ctx.organization_id)
    for item in items:
        if item["id"] == str(rule.id):
            return item
    return {"id": str(rule.id), "name": rule.name}


@router.patch("/{rule_id}")
def update_workflow(
    rule_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("workflows.manage")),
) -> dict:
    rule = workflows.update_rule(
        db, ctx.organization_id, rule_id, **payload.model_dump(exclude_unset=True)
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    for item in workflows.list_rules(db, ctx.organization_id):
        if item["id"] == str(rule.id):
            return item
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.delete("/{rule_id}", status_code=204, response_class=Response)
def delete_workflow(
    rule_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("workflows.manage")),
) -> Response:
    if not workflows.delete_rule(db, ctx.organization_id, rule_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return Response(status_code=204)


@router.post("/{rule_id}/execute")
def execute_workflow(
    rule_id: UUID,
    payload: WorkflowExecute,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("workflows.execute")),
) -> dict:
    run = workflows.execute_rule(
        db, ctx.organization_id, rule_id, payload=payload.payload
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": str(run.id),
        "status": run.status.value,
        "result": run.result,
        "error": run.error,
    }


@router.get("/runs/recent")
def recent_runs(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("workflows.read")),
) -> dict:
    return {"items": workflows.list_runs(db, ctx.organization_id)}
