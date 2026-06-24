"""Supply Chain Network View — geo nodes (warehouses, suppliers) and route edges."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Alert, RiskAssessment, Shipment, Supplier, User, Warehouse
from app.models.enums import AlertStatus, ShipmentStatus
from app.services import geo

router = APIRouter(prefix="/network", tags=["Network View"])


@router.get("")
def network(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    warehouses = db.scalars(select(Warehouse)).all()

    # active shipments per warehouse
    active_by_wh = dict(
        db.execute(
            select(Shipment.warehouse_id, func.count(Shipment.id))
            .where(Shipment.status != ShipmentStatus.DELIVERED)
            .group_by(Shipment.warehouse_id)
        ).all()
    )
    # open alerts per warehouse
    alerts_by_wh = dict(
        db.execute(
            select(Alert.entity_id, func.count(Alert.id))
            .where(Alert.entity_type == "warehouse", Alert.status != AlertStatus.RESOLVED)
            .group_by(Alert.entity_id)
        ).all()
    )
    # risk score per warehouse
    risk_by_wh = dict(
        db.execute(
            select(RiskAssessment.entity_id, func.max(RiskAssessment.score))
            .where(RiskAssessment.entity_type == "warehouse")
            .group_by(RiskAssessment.entity_id)
        ).all()
    )

    nodes: list[dict] = []
    for w in warehouses:
        nodes.append(
            {
                "id": f"wh-{w.id}",
                "entity_id": w.id,
                "type": "warehouse",
                "name": w.name,
                "location": w.location,
                "region": w.region,
                "lat": w.latitude,
                "lon": w.longitude,
                "capacity": w.capacity,
                "utilization": w.utilization,
                "risk_level": w.risk_level.value,
                "risk_score": round(float(risk_by_wh.get(w.id, 0.0)), 1),
                "active_shipments": active_by_wh.get(w.id, 0),
                "open_alerts": alerts_by_wh.get(w.id, 0),
                "current_inventory": w.current_inventory,
            }
        )

    # supplier nodes — placed at region centroid with deterministic jitter
    supplier_rows = db.execute(
        select(
            Supplier.id,
            Supplier.name,
            Supplier.region,
            Supplier.country,
            Supplier.supplier_score,
            func.count(Shipment.id),
        )
        .join(Shipment, Shipment.supplier_id == Supplier.id, isouter=True)
        .where(Supplier.is_active.is_(True))
        .group_by(Supplier.id)
        .order_by(func.count(Shipment.id).desc())
        .limit(30)
    ).all()
    for sid, name, region, country, score, ship_count in supplier_rows:
        base_lat, base_lon = geo.region_centroid(region)
        dlat, dlon = geo.jitter(sid, scale=14.0)
        nodes.append(
            {
                "id": f"sup-{sid}",
                "entity_id": sid,
                "type": "supplier",
                "name": name,
                "location": country,
                "region": region,
                "lat": round(base_lat + dlat, 3),
                "lon": round(base_lon + dlon, 3),
                "supplier_score": round(float(score), 1),
                "active_shipments": ship_count,
                "risk_score": round(max(0.0, 100.0 - float(score)), 1),
            }
        )

    # route edges — aggregate active shipments by (origin city -> destination warehouse)
    wh_coords = {w.id: (w.latitude, w.longitude, w.name, w.location) for w in warehouses}
    route_rows = db.execute(
        select(
            Shipment.origin,
            Shipment.warehouse_id,
            func.count(Shipment.id),
        )
        .where(Shipment.status != ShipmentStatus.DELIVERED)
        .group_by(Shipment.origin, Shipment.warehouse_id)
    ).all()

    # delayed counts per (origin, warehouse) in a single pass
    delayed_rows = db.execute(
        select(Shipment.origin, Shipment.warehouse_id, func.count(Shipment.id))
        .where(Shipment.status == ShipmentStatus.DELAYED)
        .group_by(Shipment.origin, Shipment.warehouse_id)
    ).all()
    delayed_map = {(o, w): c for o, w, c in delayed_rows}

    edges: list[dict] = []
    hotspots: dict[str, int] = defaultdict(int)
    for origin, wid, count in route_rows:
        if wid not in wh_coords:
            continue
        oc = geo.city_coords(origin)
        if not oc:
            continue
        dlat, dlon, dname, dloc = wh_coords[wid]
        delayed = delayed_map.get((origin, wid), 0)
        edges.append(
            {
                "from": {"name": origin, "lat": oc[0], "lon": oc[1]},
                "to": {"name": dname, "lat": dlat, "lon": dlon},
                "volume": count,
                "delayed": delayed,
                "delay_rate": round(delayed / count * 100, 1) if count else 0.0,
            }
        )
        if delayed:
            hotspots[origin] += delayed

    edges.sort(key=lambda e: e["volume"], reverse=True)
    edges = edges[:80]

    hotspot_list = [
        {"city": c, "delayed": n, "coords": geo.city_coords(c)}
        for c, n in sorted(hotspots.items(), key=lambda x: x[1], reverse=True)[:8]
        if geo.city_coords(c)
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "hotspots": hotspot_list,
        "summary": {
            "warehouses": len(warehouses),
            "suppliers": len(supplier_rows),
            "active_routes": len(edges),
        },
    }
