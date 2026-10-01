"""Metrics org-scoping + scorecard batching regression tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import Inventory, Shipment, Supplier, Warehouse
from app.models.enums import ShipmentStatus, WarehouseRiskLevel
from app.services import metrics
from app.tenancy.rls import set_session_org


def _seed_two_orgs(db, org_a, org_b):
    org, _ = org_a
    other, _, _ = org_b
    now = datetime.now(timezone.utc)
    for oid, ref in ((org.id, "A"), (other.id, "B")):
        db.flush()
        set_session_org(db, oid)
        wh = Warehouse(
            organization_id=oid,
            name=f"W-{ref}",
            location="X",
            region="R",
            latitude=1.0,
            longitude=2.0,
            capacity=1000,
            current_inventory=100,
            risk_level=WarehouseRiskLevel.LOW,
        )
        db.add(wh)
        db.flush()
        db.add(
            Shipment(
                organization_id=oid,
                reference=f"REF-{ref}-{uuid4().hex[:6]}",
                origin="O",
                destination="D",
                carrier="C",
                current_location="L",
                status=ShipmentStatus.DELAYED if ref == "A" else ShipmentStatus.DELIVERED,
                shipped_at=now - timedelta(days=1),
                eta=now + timedelta(days=2),
                units=1,
                value_usd=10,
                delay_days=2 if ref == "A" else 0,
                warehouse_id=wh.id,
            )
        )
        # Need a product for inventory — skip if too heavy; KPIs still work
    db.commit()
    return org.id, other.id


def test_compute_kpis_scoped_to_org(db, org_a, org_b):
    org_id, other_id = _seed_two_orgs(db, org_a, org_b)
    set_session_org(db, org_id)
    kpis_a = metrics.compute_kpis(db, org_id)
    set_session_org(db, other_id)
    kpis_b = metrics.compute_kpis(db, other_id)
    assert kpis_a["total_shipments"] == 1
    assert kpis_b["total_shipments"] == 1
    assert kpis_a["delayed_shipments"] == 1
    assert kpis_b["delayed_shipments"] == 0


def test_supplier_ranking_uses_few_queries(owner_client, org_a, db):
    org, _ = org_a
    for i in range(10):
        db.add(
            Supplier(
                organization_id=org.id,
                name=f"S-{i}",
                country="US",
                region="W",
                category="c",
                supplier_score=80 + i,
            )
        )
    db.commit()
    from sqlalchemy import event
    from app.core.database import engine

    q = {"n": 0}

    def _count(conn, cursor, statement, parameters, context, executemany):
        q["n"] += 1

    target = engine.sync_engine if hasattr(engine, "sync_engine") else engine
    event.listen(target, "before_cursor_execute", _count)
    try:
        r = owner_client.get(
            "/api/v1/suppliers/ranking?limit=10",
            headers={"X-Organization-Id": str(org.id)},
        )
    finally:
        event.remove(target, "before_cursor_execute", _count)
    assert r.status_code == 200, r.text
    # Expect well under 4*N+1 (old N+1). Allow a small constant for session/auth.
    assert q["n"] < 25, f"too many queries: {q['n']}"
