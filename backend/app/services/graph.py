"""Operational Knowledge Graph — relationship traversal over canonical entities.

PostgreSQL remains the system of record. This module projects a typed graph
for Mission Control, AI, risk, and impact analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Inventory,
    OperationalEvent,
    Product,
    PurchaseOrder,
    RiskAssessment,
    SalesOrder,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import AlertStatus

EntityType = Literal[
    "supplier",
    "warehouse",
    "product",
    "inventory",
    "shipment",
    "purchase_order",
    "sales_order",
    "alert",
    "risk",
    "event",
]


@dataclass
class GraphNode:
    id: str
    entity_id: str
    type: EntityType
    label: str
    status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    risk_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "type": self.type,
            "label": self.label,
            "status": self.status,
            "metadata": self.metadata,
            "risk_score": self.risk_score,
            "relationships": [],  # filled by callers when needed
        }


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "metadata": self.metadata,
        }


def _nid(etype: str, eid: UUID | str) -> str:
    return f"{etype}:{eid}"


def get_node(db: Session, org_id: UUID, entity_type: EntityType, entity_id: UUID) -> GraphNode | None:
    if entity_type == "supplier":
        row = db.get(Supplier, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("supplier", row.id),
            entity_id=str(row.id),
            type="supplier",
            label=row.name,
            status="active" if row.is_active else "inactive",
            metadata={
                "score": row.supplier_score,
                "region": row.region,
                "country": row.country,
            },
            risk_score=round(max(0.0, 100.0 - float(row.supplier_score)), 1),
        )
    if entity_type == "warehouse":
        row = db.get(Warehouse, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("warehouse", row.id),
            entity_id=str(row.id),
            type="warehouse",
            label=row.name,
            status=row.risk_level.value if hasattr(row.risk_level, "value") else str(row.risk_level),
            metadata={
                "location": row.location,
                "utilization": row.utilization,
                "capacity": row.capacity,
            },
            risk_score=None,
        )
    if entity_type == "shipment":
        row = db.get(Shipment, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("shipment", row.id),
            entity_id=str(row.id),
            type="shipment",
            label=row.reference,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            metadata={
                "origin": row.origin,
                "destination": row.destination,
                "value_usd": row.value_usd,
                "delay_days": row.delay_days,
            },
        )
    if entity_type == "purchase_order":
        row = db.get(PurchaseOrder, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("purchase_order", row.id),
            entity_id=str(row.id),
            type="purchase_order",
            label=row.reference,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            metadata={"total_amount": row.total_amount, "currency": row.currency},
        )
    if entity_type == "sales_order":
        row = db.get(SalesOrder, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("sales_order", row.id),
            entity_id=str(row.id),
            type="sales_order",
            label=row.reference,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            metadata={
                "customer_name": row.customer_name,
                "total_amount": row.total_amount,
            },
        )
    if entity_type == "product":
        row = db.get(Product, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("product", row.id),
            entity_id=str(row.id),
            type="product",
            label=row.name,
            status="active",
            metadata={"sku": getattr(row, "sku", None)},
        )
    if entity_type == "alert":
        row = db.get(Alert, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("alert", row.id),
            entity_id=str(row.id),
            type="alert",
            label=row.title,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            metadata={"priority": row.priority.value if hasattr(row.priority, "value") else str(row.priority)},
        )
    if entity_type == "risk":
        row = db.get(RiskAssessment, entity_id)
        if not row or row.organization_id != org_id:
            return None
        return GraphNode(
            id=_nid("risk", row.id),
            entity_id=str(row.id),
            type="risk",
            label=row.title,
            status=row.level.value if hasattr(row.level, "value") else str(row.level),
            metadata={"score": row.score},
            risk_score=float(row.score),
        )
    return None


def neighbors(
    db: Session,
    org_id: UUID,
    entity_type: EntityType,
    entity_id: UUID,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """One-hop relationships from a seed entity."""
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def add(node: GraphNode | None, source: str, relation: str) -> None:
        if node is None:
            return
        nodes[node.id] = node
        edges.append(GraphEdge(source=source, target=node.id, relation=relation))

    seed = get_node(db, org_id, entity_type, entity_id)
    if seed is None:
        return [], []
    nodes[seed.id] = seed
    sid = seed.id

    if entity_type == "supplier":
        for po in db.scalars(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.organization_id == org_id,
                PurchaseOrder.supplier_id == entity_id,
            )
            .limit(40)
        ).all():
            add(get_node(db, org_id, "purchase_order", po.id), sid, "issues")
        for sh in db.scalars(
            select(Shipment)
            .where(Shipment.organization_id == org_id, Shipment.supplier_id == entity_id)
            .limit(40)
        ).all():
            add(get_node(db, org_id, "shipment", sh.id), sid, "ships")

    if entity_type == "purchase_order":
        po = db.get(PurchaseOrder, entity_id)
        if po and po.supplier_id:
            add(get_node(db, org_id, "supplier", po.supplier_id), sid, "from_supplier")
        if po and po.warehouse_id:
            add(get_node(db, org_id, "warehouse", po.warehouse_id), sid, "destined_for")

    if entity_type == "shipment":
        sh = db.get(Shipment, entity_id)
        if sh and sh.supplier_id:
            add(get_node(db, org_id, "supplier", sh.supplier_id), sid, "from_supplier")
        if sh and sh.warehouse_id:
            add(get_node(db, org_id, "warehouse", sh.warehouse_id), sid, "to_warehouse")
        for so in db.scalars(
            select(SalesOrder)
            .where(SalesOrder.organization_id == org_id, SalesOrder.shipment_id == entity_id)
            .limit(20)
        ).all():
            add(get_node(db, org_id, "sales_order", so.id), sid, "fulfills")

    if entity_type == "warehouse":
        for sh in db.scalars(
            select(Shipment)
            .where(Shipment.organization_id == org_id, Shipment.warehouse_id == entity_id)
            .limit(40)
        ).all():
            add(get_node(db, org_id, "shipment", sh.id), sid, "receives")
        for inv in db.scalars(
            select(Inventory)
            .where(
                Inventory.organization_id == org_id,
                Inventory.warehouse_id == entity_id,
                Inventory.is_current.is_(True),
            )
            .limit(40)
        ).all():
            node = GraphNode(
                id=_nid("inventory", inv.id),
                entity_id=str(inv.id),
                type="inventory",
                label=f"Inventory {inv.quantity}",
                status="current",
                metadata={"quantity": inv.quantity, "product_id": str(inv.product_id)},
            )
            add(node, sid, "holds")
            if inv.product_id:
                add(get_node(db, org_id, "product", inv.product_id), node.id, "of_product")

    if entity_type == "sales_order":
        so = db.get(SalesOrder, entity_id)
        if so and so.warehouse_id:
            add(get_node(db, org_id, "warehouse", so.warehouse_id), sid, "fulfilled_from")
        if so and so.shipment_id:
            add(get_node(db, org_id, "shipment", so.shipment_id), sid, "via_shipment")

    # Linked alerts / risks for any entity
    for alert in db.scalars(
        select(Alert)
        .where(
            Alert.organization_id == org_id,
            Alert.entity_type == entity_type,
            Alert.entity_id == entity_id,
            Alert.status != AlertStatus.RESOLVED,
        )
        .limit(15)
    ).all():
        add(get_node(db, org_id, "alert", alert.id), sid, "has_alert")

    for risk in db.scalars(
        select(RiskAssessment)
        .where(
            RiskAssessment.organization_id == org_id,
            RiskAssessment.entity_type == entity_type,
            RiskAssessment.entity_id == entity_id,
        )
        .limit(10)
    ).all():
        add(get_node(db, org_id, "risk", risk.id), sid, "has_risk")

    return list(nodes.values()), edges


def traverse(
    db: Session,
    org_id: UUID,
    entity_type: EntityType,
    entity_id: UUID,
    *,
    depth: int = 2,
    limit: int = 120,
) -> dict[str, Any]:
    """Multi-hop BFS traversal."""
    depth = max(1, min(depth, 4))
    seen: set[str] = set()
    all_nodes: dict[str, GraphNode] = {}
    all_edges: list[GraphEdge] = []
    frontier: list[tuple[EntityType, UUID]] = [(entity_type, entity_id)]

    for _ in range(depth):
        next_frontier: list[tuple[EntityType, UUID]] = []
        for etype, eid in frontier:
            key = _nid(etype, eid)
            if key in seen:
                continue
            seen.add(key)
            nodes, edges = neighbors(db, org_id, etype, eid)
            for n in nodes:
                all_nodes[n.id] = n
            all_edges.extend(edges)
            if len(all_nodes) >= limit:
                break
            for n in nodes:
                if n.id in seen:
                    continue
                try:
                    next_frontier.append((n.type, UUID(n.entity_id)))  # type: ignore[arg-type]
                except ValueError:
                    continue
        frontier = next_frontier
        if len(all_nodes) >= limit or not frontier:
            break

    # Dedupe edges
    edge_keys = set()
    unique_edges = []
    for e in all_edges:
        k = (e.source, e.target, e.relation)
        if k in edge_keys:
            continue
        edge_keys.add(k)
        unique_edges.append(e)

    return {
        "root": _nid(entity_type, entity_id),
        "depth": depth,
        "nodes": [n.to_dict() for n in all_nodes.values()],
        "edges": [e.to_dict() for e in unique_edges],
        "stats": {"node_count": len(all_nodes), "edge_count": len(unique_edges)},
    }


def impact_analysis(
    db: Session,
    org_id: UUID,
    entity_type: EntityType,
    entity_id: UUID,
) -> dict[str, Any]:
    """Downstream / upstream summary from a seed node."""
    graph = traverse(db, org_id, entity_type, entity_id, depth=3, limit=200)
    by_type: dict[str, int] = {}
    for n in graph["nodes"]:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

    delayed = [
        n
        for n in graph["nodes"]
        if n["type"] == "shipment" and (n.get("status") or "") == "delayed"
    ]
    open_alerts = [n for n in graph["nodes"] if n["type"] == "alert"]
    high_risk = [
        n
        for n in graph["nodes"]
        if n.get("risk_score") is not None and float(n["risk_score"]) >= 60
    ]

    return {
        "seed": {"type": entity_type, "id": str(entity_id)},
        "graph": graph,
        "impact": {
            "by_type": by_type,
            "delayed_shipments": len(delayed),
            "open_alerts": len(open_alerts),
            "elevated_risk_nodes": len(high_risk),
            "summary": (
                f"Impact neighborhood spans {graph['stats']['node_count']} entities "
                f"({graph['stats']['edge_count']} links). "
                f"{len(delayed)} delayed shipments, {len(open_alerts)} open alerts, "
                f"{len(high_risk)} elevated-risk nodes."
            ),
        },
    }


def graph_stats(db: Session, org_id: UUID) -> dict[str, Any]:
    counts = {
        "suppliers": db.scalar(
            select(func.count()).select_from(Supplier).where(Supplier.organization_id == org_id)
        )
        or 0,
        "warehouses": db.scalar(
            select(func.count()).select_from(Warehouse).where(Warehouse.organization_id == org_id)
        )
        or 0,
        "shipments": db.scalar(
            select(func.count()).select_from(Shipment).where(Shipment.organization_id == org_id)
        )
        or 0,
        "purchase_orders": db.scalar(
            select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.organization_id == org_id)
        )
        or 0,
        "sales_orders": db.scalar(
            select(func.count()).select_from(SalesOrder).where(SalesOrder.organization_id == org_id)
        )
        or 0,
        "events": db.scalar(
            select(func.count())
            .select_from(OperationalEvent)
            .where(OperationalEvent.organization_id == org_id)
        )
        or 0,
    }
    total = sum(counts.values())
    return {
        "organization_id": str(org_id),
        "entities": counts,
        "node_counts": counts,
        "total_nodes": total,
        "total_edges": None,
        "note": "Edges are computed on traverse; counts reflect canonical entity populations.",
    }
