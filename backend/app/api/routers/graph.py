"""Knowledge graph + unified timeline APIs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.services import graph, timeline
from app.tenancy.context import TenantContext

router = APIRouter(tags=["Knowledge Graph"])


@router.get("/graph/stats")
def graph_stats(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    return graph.graph_stats(db, ctx.organization_id)


@router.get("/graph/node/{entity_type}/{entity_id}")
def get_graph_node(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    node = graph.get_node(db, ctx.organization_id, entity_type, entity_id)  # type: ignore[arg-type]
    if node is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    nodes, edges = graph.neighbors(db, ctx.organization_id, entity_type, entity_id)  # type: ignore[arg-type]
    payload = node.to_dict()
    payload["relationships"] = [e.to_dict() for e in edges]
    payload["related_nodes"] = [n.to_dict() for n in nodes if n.id != node.id]
    return payload


@router.get("/graph/traverse/{entity_type}/{entity_id}")
def traverse_graph(
    entity_type: str,
    entity_id: UUID,
    depth: int = Query(2, ge=1, le=4),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    return graph.traverse(
        db, ctx.organization_id, entity_type, entity_id, depth=depth  # type: ignore[arg-type]
    )


@router.get("/graph/impact/{entity_type}/{entity_id}")
def impact(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    return graph.impact_analysis(
        db, ctx.organization_id, entity_type, entity_id  # type: ignore[arg-type]
    )


@router.get("/timeline")
def get_timeline(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    severity: str | None = None,
    limit: int = Query(80, ge=1, le=300),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    items = timeline.entity_timeline(
        db,
        ctx.organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        limit=limit,
    )
    return {"items": items, "count": len(items)}
