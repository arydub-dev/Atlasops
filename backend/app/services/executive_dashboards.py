"""Role-specific executive dashboards with saved layouts."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Connection,
    DashboardLayout,
    Incident,
    Inventory,
    PurchaseOrder,
    SalesOrder,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import AlertStatus, IncidentStatus, OrderStatus, ShipmentStatus
from app.services import data_quality, metrics, predictions, risk_engine


ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "ceo": {
        "name": "CEO Command",
        "widgets": [
            "health",
            "data_health",
            "revenue_at_risk",
            "top_risks",
            "predictions",
            "incidents",
        ],
    },
    "coo": {
        "name": "COO Operations",
        "widgets": [
            "health",
            "shipments",
            "inventory_health",
            "supplier_reliability",
            "predictions",
            "timeline",
        ],
    },
    "supply_chain_director": {
        "name": "Supply Chain Director",
        "widgets": [
            "risk_heatmap",
            "delayed_shipments",
            "supplier_ranking",
            "purchase_orders",
            "predictions",
            "connectors",
        ],
    },
    "procurement": {
        "name": "Procurement",
        "widgets": ["purchase_orders", "supplier_ranking", "supplier_risk", "open_pos"],
    },
    "warehouse_operations": {
        "name": "Warehouse Operations",
        "widgets": ["inventory_health", "warehouse_util", "shortages", "inbound_shipments"],
    },
    "finance": {
        "name": "Finance",
        "widgets": ["revenue_at_risk", "shipment_value", "open_sos", "health"],
    },
    "it_administrator": {
        "name": "IT Administrator",
        "widgets": ["connectors", "data_health", "api_usage", "sync_failures"],
    },
    "security": {
        "name": "Security",
        "widgets": ["audit_recent", "sessions", "failed_logins", "api_tokens"],
    },
}


def role_catalogue() -> list[dict[str, Any]]:
    return [{"role_key": k, **v} for k, v in ROLE_PRESETS.items()]


def build_dashboard(
    db: Session,
    org_id: UUID,
    role_key: str,
    *,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    preset = ROLE_PRESETS.get(role_key) or ROLE_PRESETS["coo"]
    layout = None
    if user_id:
        layout = db.scalar(
            select(DashboardLayout).where(
                DashboardLayout.organization_id == org_id,
                DashboardLayout.user_id == user_id,
                DashboardLayout.role_key == role_key,
            )
        )
    widgets = (layout.widgets if layout else None) or preset["widgets"]
    kpis = metrics.compute_kpis(db, org_id)
    risk = risk_engine.summarize(db)
    dq = data_quality.latest(db, org_id) or data_quality.assess(db, org_id, persist=True)
    preds = predictions.list_active(db, org_id, limit=8)

    payload_widgets: dict[str, Any] = {}
    for w in widgets:
        payload_widgets[w] = _widget(db, org_id, w, kpis=kpis, risk=risk, dq=dq, preds=preds)

    return {
        "role_key": role_key,
        "name": layout.name if layout else preset["name"],
        "layout_id": str(layout.id) if layout else None,
        "widgets": widgets,
        "data": payload_widgets,
        "kpis": kpis,
        "health": {
            "operational": 100 - float(risk.get("overall_score") or 0),
            "data": dq.get("overall_score"),
            "data_grade": dq.get("grade"),
        },
    }


def save_layout(
    db: Session,
    org_id: UUID,
    *,
    user_id: UUID,
    role_key: str,
    name: str,
    widgets: list[str],
    is_default: bool = False,
) -> DashboardLayout:
    row = db.scalar(
        select(DashboardLayout).where(
            DashboardLayout.organization_id == org_id,
            DashboardLayout.user_id == user_id,
            DashboardLayout.role_key == role_key,
        )
    )
    if row is None:
        row = DashboardLayout(
            organization_id=org_id,
            user_id=user_id,
            role_key=role_key,
            name=name,
            widgets=widgets,
            is_default=is_default,
        )
    else:
        row.name = name
        row.widgets = widgets
        row.is_default = is_default
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _widget(
    db: Session,
    org_id: UUID,
    key: str,
    *,
    kpis: dict,
    risk: dict,
    dq: dict,
    preds: list,
) -> Any:
    if key == "health":
        return {"score": round(100 - float(risk.get("overall_score") or 0), 1)}
    if key == "data_health":
        return dq
    if key == "top_risks":
        return [
            {
                "title": r.title,
                "score": r.score,
                "level": r.level.value if hasattr(r.level, "value") else str(r.level),
            }
            for r in (risk.get("top_risks") or [])[:5]
        ]
    if key == "predictions":
        return preds[:6]
    if key == "risk_heatmap":
        return risk.get("by_category") or {}
    if key == "shipments":
        return {
            "active": kpis.get("active_shipments"),
            "delayed": kpis.get("delayed_shipments"),
            "on_time": kpis.get("on_time_delivery_rate"),
        }
    if key == "delayed_shipments":
        rows = db.scalars(
            select(Shipment)
            .where(Shipment.organization_id == org_id, Shipment.status == ShipmentStatus.DELAYED)
            .limit(8)
        ).all()
        return [{"id": str(s.id), "reference": s.reference, "delay_days": s.delay_days} for s in rows]
    if key == "inventory_health":
        return metrics.inventory_health_breakdown(db, org_id)
    if key == "supplier_reliability":
        return {"score": kpis.get("supplier_reliability_score")}
    if key == "supplier_ranking":
        rows = db.scalars(
            select(Supplier)
            .where(Supplier.organization_id == org_id)
            .order_by(Supplier.supplier_score.asc())
            .limit(5)
        ).all()
        return [{"name": s.name, "score": s.supplier_score} for s in rows]
    if key == "supplier_risk":
        return [r for r in (risk.get("top_risks") or []) if "supplier" in r.title.lower()][:5]
    if key == "purchase_orders" or key == "open_pos":
        n = (
            db.scalar(
                select(func.count())
                .select_from(PurchaseOrder)
                .where(
                    PurchaseOrder.organization_id == org_id,
                    PurchaseOrder.status.in_([OrderStatus.OPEN, OrderStatus.CONFIRMED]),
                )
            )
            or 0
        )
        return {"open_count": n}
    if key == "open_sos" or key == "sales_orders":
        n = (
            db.scalar(
                select(func.count())
                .select_from(SalesOrder)
                .where(
                    SalesOrder.organization_id == org_id,
                    SalesOrder.status.in_([OrderStatus.OPEN, OrderStatus.CONFIRMED, OrderStatus.IN_FULFILLMENT]),
                )
            )
            or 0
        )
        return {"open_count": n}
    if key == "incidents":
        rows = db.scalars(
            select(Incident)
            .where(
                Incident.organization_id == org_id,
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
            )
            .limit(5)
        ).all()
        return [{"id": str(i.id), "title": i.title, "severity": i.severity.value} for i in rows]
    if key == "connectors":
        rows = db.scalars(select(Connection).where(Connection.organization_id == org_id)).all()
        return {
            "total": len(rows),
            "error": sum(1 for c in rows if c.status.value == "error"),
        }
    if key == "warehouse_util":
        rows = db.scalars(select(Warehouse).where(Warehouse.organization_id == org_id)).all()
        return [{"name": w.name, "utilization": w.utilization} for w in rows]
    if key == "shortages":
        rows = db.scalars(
            select(Inventory).where(Inventory.organization_id == org_id, Inventory.is_current.is_(True))
        ).all()
        return sum(1 for r in rows if r.quantity <= r.reorder_point)
    if key == "inbound_shipments":
        return kpis.get("active_shipments")
    if key == "revenue_at_risk" or key == "shipment_value":
        val = (
            db.scalar(
                select(func.coalesce(func.sum(Shipment.value_usd), 0.0)).where(
                    Shipment.organization_id == org_id,
                    Shipment.status.in_([ShipmentStatus.DELAYED, ShipmentStatus.IN_TRANSIT]),
                )
            )
            or 0.0
        )
        return {"value_usd": round(float(val), 2)}
    if key == "sync_failures":
        return {
            "error_connectors": db.scalar(
                select(func.count())
                .select_from(Connection)
                .where(Connection.organization_id == org_id)
            )
        }
    if key in {"audit_recent", "sessions", "failed_logins", "api_tokens", "api_usage", "timeline"}:
        return {"href": f"/settings/{key}" if key != "timeline" else "/graph"}
    open_alerts = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.organization_id == org_id, Alert.status != AlertStatus.RESOLVED)
        )
        or 0
    )
    return {"open_alerts": open_alerts}
