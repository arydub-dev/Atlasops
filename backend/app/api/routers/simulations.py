"""Scenario Simulator endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.models import AuditLog, Simulation
from app.schemas.entities import SimulationOut, SimulationRequest
from app.services import simulation_engine
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/simulations", tags=["Scenario Simulator"])


@router.post("/run", response_model=SimulationOut)
def run_simulation(
    payload: SimulationRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("simulations.create")),
) -> Simulation:
    from app.billing.enforce import enforce_feature

    enforce_feature(db, ctx.organization_id, "simulations")
    result = simulation_engine.run_simulation(db, payload)
    impacts = result.get("impacts", {})
    sim = Simulation(
        organization_id=ctx.organization_id,
        name=payload.name or result.get("scenario", payload.simulation_type.value),
        simulation_type=payload.simulation_type,
        parameters=payload.model_dump(mode="json"),
        results=result,
        inventory_impact=float(impacts.get("inventory_impact_pct", 0.0)),
        shipment_impact=float(impacts.get("shipment_impact_pct", 0.0)),
        revenue_impact_usd=float(impacts.get("revenue_impact_usd", 0.0)),
        created_by=ctx.user_id,
    )
    db.add(sim)
    db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="run_simulation",
            resource="simulation",
            detail=payload.simulation_type.value,
        )
    )
    db.commit()
    db.refresh(sim)
    return sim


@router.get("", response_model=list[SimulationOut])
def list_simulations(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("simulations.read")),
    limit: int = Query(25, ge=1, le=100),
) -> list[Simulation]:
    return list(
        db.scalars(
            select(Simulation)
            .where(Simulation.organization_id == ctx.organization_id)
            .order_by(Simulation.created_at.desc())
            .limit(limit)
        ).all()
    )


@router.get("/{simulation_id}", response_model=SimulationOut)
def get_simulation(
    simulation_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("simulations.read")),
) -> Simulation:
    sim = db.scalar(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.organization_id == ctx.organization_id,
        )
    )
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim
