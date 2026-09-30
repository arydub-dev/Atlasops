"""Platform-wide data quality engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Connection,
    DataQualitySnapshot,
    ImportJob,
    Inventory,
    PurchaseOrder,
    SalesOrder,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import ConnectorStatus, ImportStatus, ShipmentStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _pct(numer: float, denom: float) -> float:
    if denom <= 0:
        return 100.0
    return round(max(0.0, min(100.0, (numer / denom) * 100.0)), 1)


def assess(db: Session, org_id: UUID, *, persist: bool = True) -> dict[str, Any]:
    now = _utcnow()
    suppliers = db.scalars(select(Supplier).where(Supplier.organization_id == org_id)).all()
    warehouses = db.scalars(select(Warehouse).where(Warehouse.organization_id == org_id)).all()
    shipments = db.scalars(select(Shipment).where(Shipment.organization_id == org_id)).all()
    inventory = db.scalars(select(Inventory).where(Inventory.organization_id == org_id)).all()
    connections = db.scalars(select(Connection).where(Connection.organization_id == org_id)).all()

    # Completeness — required fields populated
    complete_checks = 0
    complete_ok = 0
    for s in suppliers:
        complete_checks += 3
        complete_ok += int(bool(s.name)) + int(bool(s.country)) + int(bool(s.category))
    for w in warehouses:
        complete_checks += 3
        complete_ok += int(bool(w.name)) + int(w.capacity > 0) + int(w.latitude is not None)
    for sh in shipments:
        complete_checks += 3
        complete_ok += int(bool(sh.reference)) + int(bool(sh.origin)) + int(bool(sh.destination))
    completeness = _pct(complete_ok, complete_checks) if complete_checks else 100.0

    # Freshness — recent syncs / shipment updates
    recent_cutoff = now - timedelta(hours=48)
    fresh_conn = sum(
        1
        for c in connections
        if c.last_sync_at and c.last_sync_at.replace(tzinfo=timezone.utc) >= recent_cutoff
    )
    freshness = _pct(fresh_conn, max(len(connections), 1)) if connections else 70.0
    if not connections:
        # Demo / seeded orgs: use shipment activity as proxy
        recent_ship = sum(
            1
            for sh in shipments
            if sh.updated_at and sh.updated_at.replace(tzinfo=timezone.utc) >= now - timedelta(days=14)
        )
        freshness = _pct(recent_ship, max(len(shipments), 1)) if shipments else 80.0

    # Consistency — inventory within capacity, scores in range
    cons_ok = 0
    cons_n = 0
    for w in warehouses:
        cons_n += 1
        cons_ok += int(0 <= w.current_inventory <= w.capacity)
    for s in suppliers:
        cons_n += 1
        cons_ok += int(0 <= s.supplier_score <= 100)
    consistency = _pct(cons_ok, cons_n) if cons_n else 100.0

    # Duplicates — same supplier name
    names = [s.name.strip().lower() for s in suppliers if s.name]
    dup_rate = 0.0
    if names:
        dup_rate = (len(names) - len(set(names))) / len(names)
    duplicates = round(100.0 - (dup_rate * 100.0), 1)

    # Missing relationships
    orphan_shipments = sum(1 for sh in shipments if sh.supplier_id is None and sh.warehouse_id is None)
    missing_relationships = _pct(len(shipments) - orphan_shipments, max(len(shipments), 1))

    # Invalid values
    invalid = 0
    checks = 0
    for sh in shipments:
        checks += 1
        invalid += int(sh.delay_risk_score < 0 or sh.delay_risk_score > 100)
    for inv in inventory:
        checks += 1
        invalid += int(inv.quantity < 0)
    invalid_values = _pct(checks - invalid, max(checks, 1))

    # Failed mappings / imports
    failed_jobs = (
        db.scalar(
            select(func.count())
            .select_from(ImportJob)
            .where(ImportJob.organization_id == org_id, ImportJob.status == ImportStatus.FAILED)
        )
        or 0
    )
    total_jobs = (
        db.scalar(
            select(func.count()).select_from(ImportJob).where(ImportJob.organization_id == org_id)
        )
        or 0
    )
    failed_mappings = _pct(total_jobs - failed_jobs, max(total_jobs, 1)) if total_jobs else 95.0

    # Sync latency score
    error_conns = sum(1 for c in connections if c.status == ConnectorStatus.ERROR)
    sync_latency_score = _pct(len(connections) - error_conns, max(len(connections), 1)) if connections else 90.0

    overall = round(
        0.18 * completeness
        + 0.16 * freshness
        + 0.14 * consistency
        + 0.12 * duplicates
        + 0.12 * missing_relationships
        + 0.10 * invalid_values
        + 0.10 * failed_mappings
        + 0.08 * sync_latency_score,
        1,
    )
    confidence = 0.85 if (suppliers or shipments or warehouses) else 0.55

    remediations: list[dict[str, str]] = []
    if completeness < 85:
        remediations.append(
            {
                "priority": "high",
                "action": "Backfill missing supplier/warehouse required fields via Connector Studio mappings",
            }
        )
    if freshness < 70:
        remediations.append(
            {
                "priority": "high",
                "action": "Increase connector sync frequency or investigate stalled connections",
            }
        )
    if missing_relationships < 80:
        remediations.append(
            {
                "priority": "medium",
                "action": "Link orphan shipments to suppliers/warehouses in field mapping",
            }
        )
    if failed_jobs:
        remediations.append(
            {
                "priority": "medium",
                "action": f"Review {failed_jobs} failed import jobs and replay DLQ payloads",
            }
        )
    if duplicates < 95:
        remediations.append(
            {
                "priority": "low",
                "action": "Merge duplicate supplier records and enable conflict resolution=source_wins",
            }
        )

    details = {
        "counts": {
            "suppliers": len(suppliers),
            "warehouses": len(warehouses),
            "shipments": len(shipments),
            "inventory_rows": len(inventory),
            "connections": len(connections),
            "purchase_orders": db.scalar(
                select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.organization_id == org_id)
            )
            or 0,
            "sales_orders": db.scalar(
                select(func.count()).select_from(SalesOrder).where(SalesOrder.organization_id == org_id)
            )
            or 0,
            "delayed_shipments": sum(1 for sh in shipments if sh.status == ShipmentStatus.DELAYED),
        },
        "failed_import_jobs": failed_jobs,
    }

    payload = {
        "overall_score": overall,
        "grade": _grade(overall),
        "completeness": completeness,
        "freshness": freshness,
        "consistency": consistency,
        "duplicates": duplicates,
        "missing_relationships": missing_relationships,
        "invalid_values": invalid_values,
        "failed_mappings": failed_mappings,
        "sync_latency_score": sync_latency_score,
        "confidence": confidence,
        "details": details,
        "remediations": remediations,
        "assessed_at": now.isoformat(),
    }

    if persist:
        snap = DataQualitySnapshot(
            organization_id=org_id,
            overall_score=overall,
            completeness=completeness,
            freshness=freshness,
            consistency=consistency,
            duplicates=duplicates,
            missing_relationships=missing_relationships,
            invalid_values=invalid_values,
            failed_mappings=failed_mappings,
            sync_latency_score=sync_latency_score,
            confidence=confidence,
            details=details,
            remediations=remediations,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        payload["snapshot_id"] = str(snap.id)

    return payload


def latest(db: Session, org_id: UUID) -> dict[str, Any] | None:
    row = db.scalar(
        select(DataQualitySnapshot)
        .where(DataQualitySnapshot.organization_id == org_id)
        .order_by(DataQualitySnapshot.created_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    return {
        "snapshot_id": str(row.id),
        "overall_score": row.overall_score,
        "grade": _grade(row.overall_score),
        "completeness": row.completeness,
        "freshness": row.freshness,
        "consistency": row.consistency,
        "duplicates": row.duplicates,
        "missing_relationships": row.missing_relationships,
        "invalid_values": row.invalid_values,
        "failed_mappings": row.failed_mappings,
        "sync_latency_score": row.sync_latency_score,
        "confidence": row.confidence,
        "details": row.details,
        "remediations": row.remediations,
        "assessed_at": row.created_at.isoformat() if row.created_at else None,
    }


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"
