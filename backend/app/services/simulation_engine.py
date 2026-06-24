"""Scenario simulation engine.

Given a disruption scenario, estimate inventory, shipment and revenue impacts
against the live dataset and produce a mitigation playbook. Deterministic so
that results are reproducible for the same parameters.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Inventory, Product, Shipment, Supplier, Warehouse
from app.models.enums import ShipmentStatus, SimulationType
from app.schemas.entities import SimulationRequest


def run_simulation(db: Session, req: SimulationRequest) -> dict:
    if req.simulation_type == SimulationType.SUPPLIER_SHUTDOWN:
        return _supplier_shutdown(db, req)
    if req.simulation_type == SimulationType.PORT_CLOSURE:
        return _port_closure(db, req)
    if req.simulation_type == SimulationType.DEMAND_SPIKE:
        return _demand_spike(db, req)
    if req.simulation_type == SimulationType.WEATHER_DISRUPTION:
        return _weather_disruption(db, req)
    if req.simulation_type == SimulationType.WAREHOUSE_OUTAGE:
        return _warehouse_outage(db, req)
    raise ValueError(f"Unsupported simulation type: {req.simulation_type}")


def _active_value(db: Session, where=None) -> float:
    stmt = select(func.coalesce(func.sum(Shipment.value_usd), 0.0)).where(
        Shipment.status != ShipmentStatus.DELIVERED
    )
    if where is not None:
        stmt = stmt.where(where)
    return float(db.scalar(stmt) or 0.0)


def _supplier_shutdown(db: Session, req: SimulationRequest) -> dict:
    supplier = db.get(Supplier, req.supplier_id) if req.supplier_id else None
    if supplier is None:
        supplier = db.scalars(
            select(Supplier).order_by(Supplier.supplier_score.asc())
        ).first()
    if supplier is None:
        return _empty_result("No suppliers available to simulate.")

    affected_shipments = db.scalars(
        select(Shipment).where(
            Shipment.supplier_id == supplier.id,
            Shipment.status != ShipmentStatus.DELIVERED,
        )
    ).all()
    affected_products = db.scalars(
        select(Product).where(Product.supplier_id == supplier.id)
    ).all()
    product_ids = [p.id for p in affected_products]

    inv_units = 0
    if product_ids:
        inv_units = int(
            db.scalar(
                select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                    Inventory.is_current.is_(True),
                    Inventory.product_id.in_(product_ids),
                )
            )
            or 0
        )
    daily_demand = 0.0
    if product_ids:
        daily_demand = float(
            db.scalar(
                select(func.coalesce(func.sum(Inventory.avg_daily_demand), 0.0)).where(
                    Inventory.is_current.is_(True),
                    Inventory.product_id.in_(product_ids),
                )
            )
            or 0.0
        )

    days_cover = round(inv_units / daily_demand, 1) if daily_demand else 999.0
    shipment_value = sum(s.value_usd for s in affected_shipments)
    # Revenue at risk = shipments in flight + lost sales during shutdown beyond cover
    unmet_days = max(0, req.duration_days - days_cover)
    avg_unit_price = (
        sum(p.unit_price for p in affected_products) / len(affected_products)
        if affected_products
        else 0.0
    )
    lost_sales = unmet_days * daily_demand * avg_unit_price * req.severity
    revenue_impact = round(shipment_value * req.severity + lost_sales, 2)

    return {
        "summary": (
            f"Shutdown of {supplier.name} for {req.duration_days} days affects "
            f"{len(affected_products)} SKUs and {len(affected_shipments)} in-flight shipments. "
            f"Current inventory covers ~{days_cover} days of demand."
        ),
        "scenario": f"Supplier shutdown: {supplier.name}",
        "metrics": {
            "affected_suppliers": 1,
            "affected_products": len(affected_products),
            "affected_shipments": len(affected_shipments),
            "days_of_cover": days_cover,
            "inventory_units_at_risk": inv_units,
            "unmet_demand_days": round(unmet_days, 1),
        },
        "impacts": {
            "inventory_impact_pct": round(min(100.0, (unmet_days / max(req.duration_days, 1)) * 100), 1),
            "shipment_impact_pct": round(min(100.0, len(affected_shipments) / 50 * 100), 1),
            "revenue_impact_usd": revenue_impact,
        },
        "timeline": _decay_timeline(req.duration_days, days_cover),
        "mitigations": [
            f"Activate qualified backup suppliers for {len(affected_products)} affected SKUs.",
            "Reallocate safety stock from low-velocity warehouses to high-demand regions.",
            "Negotiate expedited freight for substitute supplier shipments.",
            "Communicate revised ETAs to affected customers proactively.",
        ],
    }


def _port_closure(db: Session, req: SimulationRequest) -> dict:
    region = req.region or "APAC"
    affected = db.scalars(
        select(Shipment).where(
            Shipment.status != ShipmentStatus.DELIVERED,
            (Shipment.origin.ilike(f"%{region}%")) | (Shipment.current_location.ilike(f"%{region}%")),
        )
    ).all()
    if not affected:
        # fall back to a representative slice of active shipments
        affected = db.scalars(
            select(Shipment).where(Shipment.status != ShipmentStatus.DELIVERED).limit(120)
        ).all()
    value = sum(s.value_usd for s in affected)
    added_delay = round(req.duration_days * req.severity, 1)
    revenue_impact = round(value * 0.18 * req.severity, 2)
    return {
        "summary": (
            f"Port closure impacting {region} for {req.duration_days} days delays "
            f"{len(affected)} shipments by ~{added_delay} days each."
        ),
        "scenario": f"Port closure: {region}",
        "metrics": {
            "affected_shipments": len(affected),
            "added_delay_days": added_delay,
            "shipment_value_usd": round(value, 2),
        },
        "impacts": {
            "inventory_impact_pct": round(min(100.0, req.severity * 45), 1),
            "shipment_impact_pct": round(min(100.0, len(affected) / 150 * 100), 1),
            "revenue_impact_usd": revenue_impact,
        },
        "timeline": _decay_timeline(req.duration_days, req.duration_days * 0.3),
        "mitigations": [
            f"Reroute {region} freight through alternate ports and inland corridors.",
            "Shift to air freight for high-value, time-critical shipments.",
            "Increase buffer stock at destination warehouses ahead of the closure.",
            "Prioritize customs pre-clearance for queued containers.",
        ],
    }


def _demand_spike(db: Session, req: SimulationRequest) -> dict:
    mult = req.demand_multiplier
    items = db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.is_current.is_(True))
    ).all()
    at_risk = 0
    extra_revenue_opportunity = 0.0
    lost_revenue = 0.0
    for inv, product in items:
        new_demand = inv.avg_daily_demand * mult
        cover = inv.quantity / new_demand if new_demand else 999
        if cover < req.duration_days:
            at_risk += 1
            unmet = (req.duration_days - cover) * new_demand
            lost_revenue += unmet * product.unit_price
        extra_revenue_opportunity += inv.avg_daily_demand * (mult - 1) * req.duration_days * product.unit_price
    total_lines = len(items)
    return {
        "summary": (
            f"A {mult:.1f}x demand spike over {req.duration_days} days puts {at_risk} of "
            f"{total_lines} inventory lines below required cover."
        ),
        "scenario": f"Demand spike x{mult:.1f}",
        "metrics": {
            "inventory_lines_at_risk": at_risk,
            "total_inventory_lines": total_lines,
            "revenue_opportunity_usd": round(extra_revenue_opportunity, 2),
        },
        "impacts": {
            "inventory_impact_pct": round(min(100.0, at_risk / max(total_lines, 1) * 100), 1),
            "shipment_impact_pct": round(min(100.0, (mult - 1) * 40), 1),
            "revenue_impact_usd": round(lost_revenue, 2),
        },
        "timeline": _growth_timeline(req.duration_days, mult),
        "mitigations": [
            "Expedite replenishment for top-velocity SKUs nearing stockout.",
            "Temporarily raise safety stock and reorder points for affected lines.",
            "Allocate constrained inventory to highest-margin channels first.",
            "Coordinate with suppliers to pull forward open purchase orders.",
        ],
    }


def _weather_disruption(db: Session, req: SimulationRequest) -> dict:
    region = req.region or "US-Gulf"
    warehouses = db.scalars(
        select(Warehouse).where(Warehouse.region.ilike(f"%{region}%"))
    ).all()
    if not warehouses:
        warehouses = db.scalars(select(Warehouse).limit(6)).all()
    wh_ids = [w.id for w in warehouses]
    affected_shipments = db.scalars(
        select(Shipment).where(
            Shipment.status != ShipmentStatus.DELIVERED,
            Shipment.warehouse_id.in_(wh_ids) if wh_ids else False,
        )
    ).all()
    value = sum(s.value_usd for s in affected_shipments)
    revenue_impact = round(value * 0.22 * req.severity, 2)
    return {
        "summary": (
            f"Severe weather in {region} for {req.duration_days} days disrupts "
            f"{len(warehouses)} warehouses and {len(affected_shipments)} shipments."
        ),
        "scenario": f"Weather disruption: {region}",
        "metrics": {
            "affected_warehouses": len(warehouses),
            "affected_shipments": len(affected_shipments),
            "shipment_value_usd": round(value, 2),
        },
        "impacts": {
            "inventory_impact_pct": round(min(100.0, req.severity * 50), 1),
            "shipment_impact_pct": round(min(100.0, len(affected_shipments) / 80 * 100), 1),
            "revenue_impact_usd": revenue_impact,
        },
        "timeline": _decay_timeline(req.duration_days, req.duration_days * 0.4),
        "mitigations": [
            f"Pre-position critical inventory outside the {region} impact zone.",
            "Switch to alternate distribution centers for order fulfillment.",
            "Activate carrier contingency contracts for rerouting.",
            "Issue proactive delay notifications and adjust customer SLAs.",
        ],
    }


def _warehouse_outage(db: Session, req: SimulationRequest) -> dict:
    warehouse = db.get(Warehouse, req.warehouse_id) if req.warehouse_id else None
    if warehouse is None:
        warehouse = db.scalars(
            select(Warehouse).order_by(
                (Warehouse.current_inventory * 1.0 / Warehouse.capacity).desc()
            )
        ).first()
    if warehouse is None:
        return _empty_result("No warehouses available to simulate.")

    affected_shipments = db.scalars(
        select(Shipment).where(
            Shipment.warehouse_id == warehouse.id,
            Shipment.status != ShipmentStatus.DELIVERED,
        )
    ).all()
    stranded_units = int(
        db.scalar(
            select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                Inventory.is_current.is_(True),
                Inventory.warehouse_id == warehouse.id,
            )
        )
        or 0
    )
    shipment_value = sum(s.value_usd for s in affected_shipments)
    # outage forces re-routing; revenue impact scales with severity and fulfillment loss
    revenue_impact = round(shipment_value * 0.30 * req.severity, 2)

    return {
        "summary": (
            f"A {req.duration_days}-day outage at {warehouse.name} strands ~{stranded_units:,} units "
            f"and disrupts {len(affected_shipments)} inbound/outbound shipments. Fulfillment must "
            f"reroute to alternate distribution centers."
        ),
        "scenario": f"Warehouse outage: {warehouse.name}",
        "metrics": {
            "affected_warehouse_capacity": warehouse.capacity,
            "stranded_units": stranded_units,
            "affected_shipments": len(affected_shipments),
            "current_utilization_pct": warehouse.utilization,
        },
        "impacts": {
            "inventory_impact_pct": round(min(100.0, warehouse.utilization * req.severity), 1),
            "shipment_impact_pct": round(min(100.0, len(affected_shipments) / 60 * 100), 1),
            "revenue_impact_usd": revenue_impact,
        },
        "timeline": _decay_timeline(req.duration_days, req.duration_days * 0.5),
        "mitigations": [
            f"Reroute {warehouse.name} fulfillment to the nearest alternate DC with spare capacity.",
            "Divert inbound shipments in transit to backup warehouses before arrival.",
            "Prioritize high-margin and time-critical orders during constrained capacity.",
            "Stand up temporary cross-dock operations to bridge the outage window.",
        ],
    }


def _decay_timeline(duration_days: int, recovery_start: float) -> list[dict]:
    out = []
    peak = min(100.0, 40 + duration_days * 3)
    for d in range(0, duration_days + 1, max(1, duration_days // 10 or 1)):
        if d < recovery_start:
            impact = min(peak, 20 + d * (peak / max(recovery_start, 1)))
        else:
            decay = (d - recovery_start) / max(duration_days - recovery_start, 1)
            impact = max(0.0, peak * (1 - decay))
        out.append({"day": d, "impact": round(impact, 1)})
    return out


def _growth_timeline(duration_days: int, mult: float) -> list[dict]:
    out = []
    for d in range(0, duration_days + 1, max(1, duration_days // 10 or 1)):
        impact = min(100.0, (mult - 1) * 30 + d * 2.0)
        out.append({"day": d, "impact": round(impact, 1)})
    return out


def _empty_result(message: str) -> dict:
    return {
        "summary": message,
        "scenario": "n/a",
        "metrics": {},
        "impacts": {"inventory_impact_pct": 0, "shipment_impact_pct": 0, "revenue_impact_usd": 0},
        "timeline": [],
        "mitigations": [],
    }
