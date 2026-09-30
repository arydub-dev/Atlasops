"""Enterprise unified search across operational entities."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Incident,
    Inventory,
    Product,
    PurchaseOrder,
    RiskAssessment,
    SalesOrder,
    Shipment,
    Supplier,
    User,
    Warehouse,
)
from app.models.enums import AlertStatus
from app.services import graph


def search(
    db: Session,
    org_id: UUID,
    query: str,
    *,
    limit: int = 40,
) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    results: list[dict[str, Any]] = []

    def push(
        *,
        entity_type: str,
        entity_id: UUID,
        title: str,
        summary: str,
        risk_score: float | None = None,
        status: str | None = None,
    ) -> None:
        results.append(
            {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "title": title,
                "summary": summary,
                "status": status,
                "risk_score": risk_score,
                "href": _href(entity_type, entity_id),
            }
        )

    for s in db.scalars(
        select(Supplier)
        .where(
            Supplier.organization_id == org_id,
            or_(Supplier.name.ilike(like), Supplier.country.ilike(like)),
        )
        .limit(10)
    ).all():
        push(
            entity_type="supplier",
            entity_id=s.id,
            title=s.name,
            summary=f"Score {s.supplier_score:.0f} · {s.country or s.region or ''}",
            risk_score=round(max(0.0, 100.0 - float(s.supplier_score)), 1),
            status="active" if s.is_active else "inactive",
        )

    for w in db.scalars(
        select(Warehouse)
        .where(
            Warehouse.organization_id == org_id,
            or_(Warehouse.name.ilike(like), Warehouse.location.ilike(like)),
        )
        .limit(10)
    ).all():
        push(
            entity_type="warehouse",
            entity_id=w.id,
            title=w.name,
            summary=f"{w.location} · util {w.utilization}%",
            status=w.risk_level.value if hasattr(w.risk_level, "value") else str(w.risk_level),
        )

    for sh in db.scalars(
        select(Shipment)
        .where(
            Shipment.organization_id == org_id,
            or_(
                Shipment.reference.ilike(like),
                Shipment.origin.ilike(like),
                Shipment.destination.ilike(like),
            ),
        )
        .limit(10)
    ).all():
        push(
            entity_type="shipment",
            entity_id=sh.id,
            title=sh.reference,
            summary=f"{sh.origin} → {sh.destination}",
            status=sh.status.value if hasattr(sh.status, "value") else str(sh.status),
        )

    for po in db.scalars(
        select(PurchaseOrder)
        .where(PurchaseOrder.organization_id == org_id, PurchaseOrder.reference.ilike(like))
        .limit(8)
    ).all():
        push(
            entity_type="purchase_order",
            entity_id=po.id,
            title=po.reference,
            summary=f"{po.currency} {po.total_amount:,.0f}",
            status=po.status.value if hasattr(po.status, "value") else str(po.status),
        )

    for so in db.scalars(
        select(SalesOrder)
        .where(
            SalesOrder.organization_id == org_id,
            or_(SalesOrder.reference.ilike(like), SalesOrder.customer_name.ilike(like)),
        )
        .limit(8)
    ).all():
        push(
            entity_type="sales_order",
            entity_id=so.id,
            title=so.reference,
            summary=so.customer_name or "Sales order",
            status=so.status.value if hasattr(so.status, "value") else str(so.status),
        )

    for p in db.scalars(
        select(Product)
        .where(
            Product.organization_id == org_id,
            or_(Product.name.ilike(like), Product.sku.ilike(like)),
        )
        .limit(8)
    ).all():
        push(
            entity_type="product",
            entity_id=p.id,
            title=p.name,
            summary=getattr(p, "sku", None) or "Product",
        )

    for a in db.scalars(
        select(Alert)
        .where(
            Alert.organization_id == org_id,
            Alert.status != AlertStatus.RESOLVED,
            or_(Alert.title.ilike(like), Alert.message.ilike(like)),
        )
        .limit(8)
    ).all():
        push(
            entity_type="alert",
            entity_id=a.id,
            title=a.title,
            summary=a.message[:160],
            status=a.status.value if hasattr(a.status, "value") else str(a.status),
        )

    for r in db.scalars(
        select(RiskAssessment)
        .where(
            RiskAssessment.organization_id == org_id,
            or_(RiskAssessment.title.ilike(like), RiskAssessment.recommendation.ilike(like)),
        )
        .limit(8)
    ).all():
        push(
            entity_type="risk",
            entity_id=r.id,
            title=r.title,
            summary=r.recommendation or "",
            risk_score=float(r.score),
            status=r.level.value if hasattr(r.level, "value") else str(r.level),
        )

    try:
        for inc in db.scalars(
            select(Incident)
            .where(
                Incident.organization_id == org_id,
                or_(Incident.title.ilike(like), Incident.summary.ilike(like)),
            )
            .limit(8)
        ).all():
            push(
                entity_type="incident",
                entity_id=inc.id,
                title=inc.title,
                summary=inc.summary or "",
                status=inc.status.value if hasattr(inc.status, "value") else str(inc.status),
            )
    except Exception:
        # Table may not exist yet in older DBs before create_all/migration
        pass

    # Enrich top results with relationship counts (cheap 1-hop)
    for item in results[:12]:
        try:
            nodes, edges = graph.neighbors(
                db,
                org_id,
                item["entity_type"],  # type: ignore[arg-type]
                UUID(item["entity_id"]),
            )
            item["relationships"] = len(edges)
            item["related_preview"] = [
                {"type": n.type, "label": n.label} for n in nodes[:4] if n.type != item["entity_type"]
            ]
        except Exception:
            item["relationships"] = 0
            item["related_preview"] = []

    return results[:limit]


def _href(entity_type: str, entity_id: UUID) -> str:
    mapping = {
        "supplier": f"/suppliers",
        "warehouse": f"/warehouses",
        "shipment": f"/shipments/{entity_id}",
        "alert": "/alerts",
        "risk": "/risk",
        "incident": f"/incidents/{entity_id}",
        "purchase_order": "/mission-control",
        "sales_order": "/mission-control",
        "product": "/inventory",
    }
    return mapping.get(entity_type, "/mission-control")
