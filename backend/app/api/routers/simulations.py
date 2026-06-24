"""Scenario Simulator endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import AuditLog, Simulation, User
from app.models.enums import UserRole
from app.schemas.entities import SimulationOut, SimulationRequest
from app.services import simulation_engine

router = APIRouter(prefix="/simulations", tags=["Scenario Simulator"])


@router.post("/run", response_model=SimulationOut)
def run_simulation(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.OPERATIONS_MANAGER, UserRole.ANALYST, UserRole.EXECUTIVE)),
) -> Simulation:
    result = simulation_engine.run_simulation(db, payload)
    impacts = result.get("impacts", {})
    sim = Simulation(
        name=payload.name or result.get("scenario", payload.simulation_type.value),
        simulation_type=payload.simulation_type,
        parameters=payload.model_dump(mode="json"),
        results=result,
        inventory_impact=float(impacts.get("inventory_impact_pct", 0.0)),
        shipment_impact=float(impacts.get("shipment_impact_pct", 0.0)),
        revenue_impact_usd=float(impacts.get("revenue_impact_usd", 0.0)),
        created_by=user.id,
    )
    db.add(sim)
    db.add(
        AuditLog(
            user_id=user.id,
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
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(25, ge=1, le=100),
) -> list[Simulation]:
    return list(
        db.scalars(select(Simulation).order_by(Simulation.created_at.desc()).limit(limit)).all()
    )


@router.get("/{simulation_id}", response_model=SimulationOut)
def get_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Simulation:
    sim = db.get(Simulation, simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim
