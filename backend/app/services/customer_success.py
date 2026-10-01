"""Customer success / onboarding tooling."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Connection,
    ImportJob,
    Invitation,
    Membership,
    Organization,
    Simulation,
    Supplier,
    Warehouse,
)
from app.models.enums import ConnectorStatus, InvitationStatus, MembershipStatus
from app.services import data_quality, metrics


def onboarding_checklist(db: Session, org_id: UUID) -> dict[str, Any]:
    org = db.get(Organization, org_id)
    members = (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == org_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        or 0
    )
    connections = db.scalars(select(Connection).where(Connection.organization_id == org_id)).all()
    connected = sum(1 for c in connections if c.status == ConnectorStatus.CONNECTED)
    imports = (
        db.scalar(select(func.count()).select_from(ImportJob).where(ImportJob.organization_id == org_id))
        or 0
    )
    suppliers = (
        db.scalar(select(func.count()).select_from(Supplier).where(Supplier.organization_id == org_id))
        or 0
    )
    warehouses = (
        db.scalar(select(func.count()).select_from(Warehouse).where(Warehouse.organization_id == org_id))
        or 0
    )
    sims = (
        db.scalar(select(func.count()).select_from(Simulation).where(Simulation.organization_id == org_id))
        or 0
    )
    pending_invites = (
        db.scalar(
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.organization_id == org_id,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        or 0
    )

    steps = [
        {"id": "org_profile", "label": "Organization profile", "done": bool(org and org.name)},
        {"id": "invite_team", "label": "Invite team members", "done": members >= 2 or pending_invites > 0},
        {"id": "install_connector", "label": "Install a connector", "done": len(connections) > 0},
        {"id": "connect_source", "label": "Complete connector auth", "done": connected > 0},
        {"id": "import_data", "label": "Import operational data", "done": imports > 0 or suppliers > 0},
        {"id": "warehouses", "label": "Confirm warehouses", "done": warehouses > 0},
        {"id": "mission_control", "label": "Review Mission Control", "done": suppliers > 0 or warehouses > 0},
        {"id": "simulation", "label": "Run a simulation", "done": sims > 0},
    ]
    done = sum(1 for s in steps if s["done"])
    return {
        "organization": org.name if org else None,
        "progress_pct": round(100 * done / len(steps), 1),
        "completed": done,
        "total": len(steps),
        "steps": steps,
    }


def health_report(db: Session, org_id: UUID) -> dict[str, Any]:
    checklist = onboarding_checklist(db, org_id)
    dq = data_quality.latest(db, org_id) or data_quality.assess(db, org_id, persist=True)
    kpis = metrics.compute_kpis(db, org_id)
    adoption = adoption_score(db, org_id)
    return {
        "onboarding": checklist,
        "data_health": dq,
        "operational_kpis": {
            "active_shipments": kpis.get("active_shipments"),
            "open_alerts": kpis.get("open_alerts"),
            "supplier_reliability_score": kpis.get("supplier_reliability_score"),
        },
        "adoption": adoption,
        "recommendations": _recommendations(checklist, dq, adoption),
    }


def adoption_score(db: Session, org_id: UUID) -> dict[str, Any]:
    modules = {
        "connectors": (
            db.scalar(select(func.count()).select_from(Connection).where(Connection.organization_id == org_id))
            or 0
        )
        > 0,
        "imports": (
            db.scalar(select(func.count()).select_from(ImportJob).where(ImportJob.organization_id == org_id))
            or 0
        )
        > 0,
        "simulations": (
            db.scalar(select(func.count()).select_from(Simulation).where(Simulation.organization_id == org_id))
            or 0
        )
        > 0,
        "suppliers": (
            db.scalar(select(func.count()).select_from(Supplier).where(Supplier.organization_id == org_id))
            or 0
        )
        > 0,
        "warehouses": (
            db.scalar(select(func.count()).select_from(Warehouse).where(Warehouse.organization_id == org_id))
            or 0
        )
        > 0,
    }
    used = sum(1 for v in modules.values() if v)
    unused = [k for k, v in modules.items() if not v]
    score = round(100 * used / max(len(modules), 1), 1)
    return {"score": score, "modules": modules, "unused_modules": unused}


def _recommendations(checklist: dict, dq: dict, adoption: dict) -> list[str]:
    recs: list[str] = []
    for step in checklist.get("steps") or []:
        if not step.get("done"):
            recs.append(f"Complete onboarding step: {step['label']}")
            if len(recs) >= 3:
                break
    if (dq.get("overall_score") or 100) < 75:
        recs.append("Improve data health via Connector Studio field mappings")
    for mod in (adoption.get("unused_modules") or [])[:2]:
        recs.append(f"Enable unused module: {mod}")
    return recs[:6]
