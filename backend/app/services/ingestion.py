"""Data ingestion layer for Connected Mode.

CSV / Excel import into tenant-owned domain tables. Connector sync simulation
and mock SAP seeding have been removed — real connectors are stubs at the API.
"""
from __future__ import annotations

import csv
import io
import math
import zipfile
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    Connection,
    ImportJob,
    Inventory,
    OrgSetting,
    Product,
    Shipment,
    Supplier,
    Warehouse,
)
from app.models.enums import (
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    ImportStatus,
    ShipmentStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Integration template catalog (matches ConnectorType enum)
# --------------------------------------------------------------------------- #
INTEGRATION_TEMPLATES: list[dict] = [
    {
        "type": ConnectorType.DYNAMICS_BC.value,
        "name": "Microsoft Dynamics 365 Business Central",
        "category": "ERP",
        "description": "Connect Dynamics 365 BC for orders and inventory positions.",
        "auth_methods": ["OAuth2", "API Key"],
    },
    {
        "type": ConnectorType.SALESFORCE.value,
        "name": "Salesforce",
        "category": "CRM",
        "description": "Pull demand signals, accounts and order pipeline from Salesforce.",
        "auth_methods": ["OAuth2", "API Key"],
    },
    {
        "type": ConnectorType.UPS.value,
        "name": "UPS",
        "category": "Transportation",
        "description": "Ingest shipment tracking and ETAs from UPS.",
        "auth_methods": ["OAuth2", "API Key"],
    },
    {
        "type": ConnectorType.CSV_UPLOAD.value,
        "name": "CSV Upload",
        "category": "File",
        "description": "Import domain data from CSV files.",
        "auth_methods": ["None"],
    },
    {
        "type": ConnectorType.EXCEL_UPLOAD.value,
        "name": "Excel Upload",
        "category": "File",
        "description": "Import domain data from Excel workbooks.",
        "auth_methods": ["None"],
    },
    {
        "type": ConnectorType.JSON_UPLOAD.value,
        "name": "JSON Upload",
        "category": "File",
        "description": "Import domain data from JSON payloads.",
        "auth_methods": ["None"],
    },
]


# --------------------------------------------------------------------------- #
# Importable entity field specs
# --------------------------------------------------------------------------- #
ENTITY_SPECS: dict[str, dict] = {
    "suppliers": {
        "label": "Suppliers",
        "fields": [
            {"name": "name", "label": "Name", "required": True, "type": "str"},
            {"name": "country", "label": "Country", "required": True, "type": "str"},
            {"name": "region", "label": "Region", "required": True, "type": "str"},
            {"name": "category", "label": "Category", "required": False, "type": "str", "default": "General"},
            {"name": "supplier_score", "label": "Supplier Score", "required": False, "type": "float", "default": 80.0},
            {"name": "delivery_reliability", "label": "Delivery Reliability", "required": False, "type": "float", "default": 90.0},
            {"name": "average_delay_days", "label": "Avg Delay (days)", "required": False, "type": "float", "default": 1.0},
            {"name": "order_fulfillment_rate", "label": "Fulfillment Rate", "required": False, "type": "float", "default": 95.0},
            {"name": "defect_rate", "label": "Defect Rate", "required": False, "type": "float", "default": 1.0},
        ],
    },
    "warehouses": {
        "label": "Warehouses",
        "fields": [
            {"name": "name", "label": "Name", "required": True, "type": "str"},
            {"name": "location", "label": "Location", "required": True, "type": "str"},
            {"name": "region", "label": "Region", "required": True, "type": "str"},
            {"name": "latitude", "label": "Latitude", "required": False, "type": "float", "default": 0.0},
            {"name": "longitude", "label": "Longitude", "required": False, "type": "float", "default": 0.0},
            {"name": "capacity", "label": "Capacity", "required": True, "type": "int"},
            {"name": "current_inventory", "label": "Current Inventory", "required": False, "type": "int", "default": 0},
        ],
    },
    "products": {
        "label": "Products",
        "fields": [
            {"name": "sku", "label": "SKU", "required": True, "type": "str", "unique": True},
            {"name": "name", "label": "Name", "required": True, "type": "str"},
            {"name": "category", "label": "Category", "required": False, "type": "str", "default": "General"},
            {"name": "unit_cost", "label": "Unit Cost", "required": True, "type": "float"},
            {"name": "unit_price", "label": "Unit Price", "required": True, "type": "float"},
            {"name": "lead_time_days", "label": "Lead Time (days)", "required": False, "type": "int", "default": 14},
        ],
    },
    "shipments": {
        "label": "Shipments",
        "fields": [
            {"name": "reference", "label": "Reference", "required": True, "type": "str", "unique": True},
            {"name": "origin", "label": "Origin", "required": True, "type": "str"},
            {"name": "destination", "label": "Destination", "required": True, "type": "str"},
            {"name": "carrier", "label": "Carrier", "required": True, "type": "str"},
            {"name": "status", "label": "Status", "required": False, "type": "enum:ShipmentStatus", "default": "in_transit"},
            {"name": "units", "label": "Units", "required": False, "type": "int", "default": 0},
            {"name": "value_usd", "label": "Value (USD)", "required": False, "type": "float", "default": 0.0},
        ],
    },
    "inventory": {
        "label": "Inventory",
        "fields": [
            {"name": "warehouse_name", "label": "Warehouse Name", "required": True, "type": "str", "fk": "warehouse"},
            {"name": "product_sku", "label": "Product SKU", "required": True, "type": "str", "fk": "product"},
            {"name": "quantity", "label": "Quantity", "required": True, "type": "int"},
            {"name": "reorder_point", "label": "Reorder Point", "required": False, "type": "int", "default": 0},
            {"name": "safety_stock", "label": "Safety Stock", "required": False, "type": "int", "default": 0},
            {"name": "max_stock", "label": "Max Stock", "required": False, "type": "int", "default": 0},
            {"name": "avg_daily_demand", "label": "Avg Daily Demand", "required": False, "type": "float", "default": 0.0},
        ],
    },
}


def entity_spec(entity: str) -> dict:
    if entity not in ENTITY_SPECS:
        raise ValueError(f"Unknown entity '{entity}'")
    return ENTITY_SPECS[entity]


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
MAX_IMPORT_ROWS = 10000
MAX_IMPORT_COLUMNS = 100
MAX_EXPANDED_BYTES = 50 * 1024 * 1024


def _columns(values) -> list[str]:
    columns = [str(v).strip() if v is not None else "" for v in values]
    if not columns or len(columns) > MAX_IMPORT_COLUMNS or any(not c for c in columns):
        raise ValueError("Provide 1–100 non-empty column names")
    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate column names are not allowed")
    return columns


def parse_upload(filename: str, content: bytes, sheet: str | None = None) -> dict:
    lower = (filename or "").lower()
    if lower.endswith(".xlsx"):
        return _parse_excel(content, sheet)
    if lower.endswith(".csv"):
        return _parse_csv(content)
    raise ValueError("Use CSV or macro-free XLSX; convert legacy Excel files before uploading")


def _parse_csv(content: bytes) -> dict:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Save the CSV with UTF-8 encoding") from exc
    if "\x00" in text:
        raise ValueError("Binary contents are not valid CSV")
    reader = csv.reader(io.StringIO(text), strict=True)
    columns = _columns(next(reader, []))
    rows = []
    for raw in reader:
        if not raw or all(not c.strip() for c in raw):
            continue
        if len(raw) != len(columns):
            raise ValueError(f"Row {reader.line_num} has a different number of columns")
        if len(rows) >= MAX_IMPORT_ROWS:
            raise ValueError("Import limit is 10,000 rows; split the file")
        rows.append(dict(zip(columns, raw)))
    return {"columns": columns, "rows": rows, "sheets": []}


def _parse_excel(content: bytes, sheet: str | None) -> dict:
    from openpyxl import load_workbook

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(i.file_size for i in entries) > MAX_EXPANDED_BYTES:
            raise ValueError("Workbook exceeds expanded size limit (50MB)")
        if any("vbaproject" in i.filename.lower() for i in entries):
            raise ValueError("Macro-enabled workbooks are not supported")
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    try:
        sheets = wb.sheetnames
        if sheet and sheet not in sheets:
            raise ValueError("Selected sheet does not exist")
        ws = wb[sheet or sheets[0]]
        if (ws.max_row or 0) > MAX_IMPORT_ROWS + 1 or (ws.max_column or 0) > MAX_IMPORT_COLUMNS:
            raise ValueError("Workbook exceeds 10,000 rows or 100 columns")
        rows_iter = ws.iter_rows()
        header = next(rows_iter, [])
        columns = _columns([c.value for c in header])
        rows = []
        for cells in rows_iter:
            if all(c.value is None for c in cells):
                continue
            if len(rows) >= MAX_IMPORT_ROWS or len(cells) > MAX_IMPORT_COLUMNS:
                raise ValueError("Workbook exceeds import limits")
            if any(c.data_type == "f" for c in cells):
                raise ValueError("Replace formulas with values before importing")
            rows.append({columns[i]: c.value for i, c in enumerate(cells)})
        return {"columns": columns, "rows": rows, "sheets": sheets}
    finally:
        wb.close()


def validate_mapping(entity: str, mapping, columns: list[str]) -> dict:
    if not isinstance(mapping, dict):
        raise ValueError("Mapping must be a JSON object")
    fields = {f["name"] for f in entity_spec(entity)["fields"]}
    if any(k not in fields or (v is not None and (not isinstance(v, str) or v not in columns))
           for k, v in mapping.items()):
        raise ValueError("Mapping must reference supported fields and uploaded columns")
    return mapping


# --------------------------------------------------------------------------- #
# Mapping suggestion
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def suggest_mapping(entity: str, columns: list[str]) -> dict[str, str | None]:
    spec = entity_spec(entity)
    norm_cols = {_norm(c): c for c in columns}
    mapping: dict[str, str | None] = {}
    for field in spec["fields"]:
        fn = field["name"]
        candidates = {_norm(fn), _norm(field["label"])}
        candidates |= {_norm(fn.replace("_", " "))}
        match = next((norm_cols[c] for c in candidates if c in norm_cols), None)
        mapping[fn] = match
    return mapping


# --------------------------------------------------------------------------- #
# Validation + transformation
# --------------------------------------------------------------------------- #
def _coerce(value, ftype: str):
    if value is None:
        raise ValueError("missing")
    s = str(value).strip()
    if s == "":
        raise ValueError("empty")
    if ftype == "str":
        return s
    if ftype == "int":
        number = Decimal(s)
        if not number.is_finite() or number != number.to_integral_value() or abs(number) > 2147483647:
            raise ValueError("expected a finite 32-bit integer")
        return int(number)
    if ftype == "float":
        number = float(s)
        if not math.isfinite(number):
            raise ValueError("expected a finite number")
        return number
    if ftype == "datetime":
        return datetime.fromisoformat(s)
    if ftype.startswith("enum:"):
        return ShipmentStatus(s.lower()).value
    return s


def validate_rows(entity: str, rows: list[dict], mapping: dict[str, str | None]) -> dict:
    """Validate (without writing). Returns sample of normalized rows + errors."""
    spec = entity_spec(entity)
    errors: list[dict] = []
    valid = 0
    normalized_sample: list[dict] = []

    for idx, raw in enumerate(rows):
        norm, row_errors = _transform_row(spec, raw, mapping)
        if row_errors:
            errors.append({"row": idx + 1, "errors": row_errors})
        else:
            valid += 1
            if len(normalized_sample) < 10:
                normalized_sample.append(norm)

    return {
        "total": len(rows),
        "valid": valid,
        "rejected": len(rows) - valid,
        "errors": errors[:50],
        "sample": normalized_sample,
    }


def _transform_row(spec: dict, raw: dict, mapping: dict[str, str | None]) -> tuple[dict, list[str]]:
    out: dict = {}
    errs: list[str] = []
    for field in spec["fields"]:
        fn = field["name"]
        col = mapping.get(fn)
        rawval = raw.get(col) if col else None
        has_value = rawval is not None and str(rawval).strip() != ""
        if not has_value:
            if field.get("required"):
                errs.append(f"{field['label']} is required")
            elif "default" in field:
                out[fn] = field["default"]
            continue
        try:
            value = _coerce(rawval, field["type"])
            if field["type"] in {"int", "float"}:
                minimum = -90 if fn == "latitude" else -180 if fn == "longitude" else 0
                maximum = 90 if fn == "latitude" else 180 if fn == "longitude" else 100 if fn in {
                    "supplier_score", "delivery_reliability", "order_fulfillment_rate", "defect_rate"
                } else 1e12
                if not minimum <= value <= maximum:
                    raise ValueError("outside allowed range")
            if isinstance(value, str) and len(value) > 255:
                raise ValueError("text exceeds 255 characters")
            out[fn] = value
        except (ValueError, TypeError, InvalidOperation, OverflowError):
            errs.append(f"{field['label']} has invalid value '{rawval}'")
    return out, errs


# --------------------------------------------------------------------------- #
# Commit
# --------------------------------------------------------------------------- #
def commit_import(
    db: Session,
    *,
    organization_id: UUID,
    entity: str,
    rows: list[dict],
    mapping: dict[str, str | None],
    source_name: str,
    source_type: str,
    user_id: UUID | None = None,
) -> dict:
    spec = entity_spec(entity)
    started = _utcnow()
    imported = 0
    rejected = 0
    errors: list[dict] = []

    wh_by_name = (
        {
            w.name.lower(): w
            for w in db.scalars(
                select(Warehouse).where(Warehouse.organization_id == organization_id)
            ).all()
        }
        if entity == "inventory"
        else {}
    )
    prod_by_sku = (
        {
            p.sku.lower(): p
            for p in db.scalars(
                select(Product).where(Product.organization_id == organization_id)
            ).all()
        }
        if entity == "inventory"
        else {}
    )

    for idx, raw in enumerate(rows):
        norm, row_errors = _transform_row(spec, raw, mapping)
        if row_errors:
            rejected += 1
            if len(errors) < 50:
                errors.append({"row": idx + 1, "errors": row_errors})
            continue
        try:
            obj = _build_entity(entity, norm, wh_by_name, prod_by_sku, organization_id)
            with db.begin_nested():
                if entity == "inventory":
                    # Serialize file imports for this warehouse before resolving a
                    # current position; two uploads must not create two positions.
                    db.scalar(select(Warehouse).where(
                        Warehouse.id == obj.warehouse_id,
                        Warehouse.organization_id == organization_id,
                    ).with_for_update())
                    current = db.scalars(select(Inventory).where(
                        Inventory.organization_id == organization_id,
                        Inventory.warehouse_id == obj.warehouse_id,
                        Inventory.product_id == obj.product_id,
                        Inventory.is_current.is_(True),
                    ).with_for_update()).all()
                    if len(current) > 1:
                        raise ValueError("Multiple current inventory positions exist; reconcile them before importing")
                    if current:
                        existing = current[0]
                        for field in ("quantity", "reorder_point", "safety_stock", "max_stock", "avg_daily_demand"):
                            setattr(existing, field, getattr(obj, field))
                        existing.snapshot_date = _utcnow()
                        obj = existing
                db.add(obj)
                db.flush()
            imported += 1
        except (ValueError, IntegrityError) as exc:
            rejected += 1
            if len(errors) < 50:
                errors.append({"row": idx + 1, "errors": ["Duplicate record or invalid reference" if isinstance(exc, IntegrityError) else str(exc)]})

    duration_ms = int((_utcnow() - started).total_seconds() * 1000)
    status = (
        ImportStatus.SUCCESS
        if rejected == 0 and imported > 0
        else ImportStatus.FAILED
        if imported == 0
        else ImportStatus.PARTIAL
    )
    job = ImportJob(
        organization_id=organization_id,
        source_name=source_name,
        source_type=source_type,
        entity_type=entity,
        status=status,
        mapping=mapping,
        rows_processed=len(rows),
        rows_imported=imported,
        rows_rejected=rejected,
        duration_ms=duration_ms,
        error_summary=errors or None,
        user_id=user_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": str(job.id),
        "entity": entity,
        "status": status.value,
        "rows_processed": len(rows),
        "rows_imported": imported,
        "rows_rejected": rejected,
        "duration_ms": duration_ms,
        "errors": errors,
    }


def _build_entity(
    entity: str,
    norm: dict,
    wh_by_name: dict,
    prod_by_sku: dict,
    organization_id: UUID,
):
    if entity == "suppliers":
        return Supplier(organization_id=organization_id, **norm)
    if entity == "warehouses":
        return Warehouse(organization_id=organization_id, **norm)
    if entity == "products":
        return Product(organization_id=organization_id, **norm)
    if entity == "shipments":
        status = norm.pop("status", "in_transit")
        try:
            status_enum = ShipmentStatus(status)
        except ValueError:
            status_enum = ShipmentStatus.IN_TRANSIT
        now = _utcnow()
        return Shipment(
            organization_id=organization_id,
            **norm,
            status=status_enum,
            current_location=norm.get("origin", ""),
            shipped_at=now,
            eta=now + timedelta(days=14),
        )
    if entity == "inventory":
        wh = wh_by_name.get(str(norm.pop("warehouse_name", "")).lower())
        prod = prod_by_sku.get(str(norm.pop("product_sku", "")).lower())
        if not wh:
            raise ValueError("warehouse not found")
        if not prod:
            raise ValueError("product SKU not found")
        return Inventory(
            organization_id=organization_id,
            warehouse_id=wh.id,
            product_id=prod.id,
            is_current=True,
            **norm,
        )
    raise ValueError(f"Unsupported entity {entity}")


# --------------------------------------------------------------------------- #
# Operating mode (per-org)
# --------------------------------------------------------------------------- #
def get_mode(db: Session, organization_id: UUID) -> str:
    row = db.scalar(
        select(OrgSetting).where(
            OrgSetting.organization_id == organization_id,
            OrgSetting.key == "operating_mode",
        )
    )
    return row.value if row else "connected"


def set_mode(db: Session, organization_id: UUID, mode: str) -> str:
    if mode not in {"demo", "connected"}:
        raise ValueError("Invalid mode")
    row = db.scalar(
        select(OrgSetting).where(
            OrgSetting.organization_id == organization_id,
            OrgSetting.key == "operating_mode",
        )
    )
    if row:
        row.value = mode
    else:
        db.add(OrgSetting(organization_id=organization_id, key="operating_mode", value=mode))
    db.commit()
    return mode


# --------------------------------------------------------------------------- #
# Dashboard summary + AI context
# --------------------------------------------------------------------------- #
def summary(db: Session, organization_id: UUID) -> dict:
    sources = db.scalars(
        select(Connection).where(Connection.organization_id == organization_id)
    ).all()
    connected = [s for s in sources if s.status == ConnectorStatus.CONNECTED]
    configured_types = {s.connector_type.value for s in sources}
    available = [t for t in INTEGRATION_TEMPLATES if t["type"] not in configured_types]

    last_sync = max((s.last_sync_at for s in sources if s.last_sync_at), default=None)
    total_records = sum(s.record_count for s in sources)

    today = _utcnow().date()
    imported_today = db.scalar(
        select(func.coalesce(func.sum(ImportJob.rows_imported), 0)).where(
            ImportJob.organization_id == organization_id,
            ImportJob.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
            ImportJob.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
        )
    ) or 0

    status_counts: dict[str, int] = {}
    for s in sources:
        status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1

    failures = [
        {"source": s.name, "health": s.health.value, "status": s.status.value}
        for s in sources
        if s.status == ConnectorStatus.ERROR or s.health == ConnectorHealth.DOWN
    ]

    return {
        "mode": get_mode(db, organization_id),
        "connected_systems": len(connected),
        "total_sources": len(sources),
        "available_integrations": len(available),
        "last_sync_at": last_sync.isoformat() if last_sync else None,
        "records_imported_total": int(total_records),
        "records_imported_today": int(imported_today),
        "status_counts": status_counts,
        "failures": failures,
    }


def ai_context(db: Session, organization_id: UUID | None = None) -> dict:
    """Compact connection snapshot for the Operations Copilot."""
    if organization_id is None:
        from app.tenancy.context import get_tenant_or_none

        tenant = get_tenant_or_none()
        if tenant is None:
            return {
                "mode": "connected",
                "connected_systems": 0,
                "available_integrations": len(INTEGRATION_TEMPLATES),
                "last_sync_at": None,
                "records_imported_today": 0,
                "records_imported_total": 0,
                "sources": [],
                "failures": [],
            }
        organization_id = tenant.organization_id

    s = summary(db, organization_id)
    sources = db.scalars(
        select(Connection).where(Connection.organization_id == organization_id)
    ).all()
    return {
        "mode": s["mode"],
        "connected_systems": s["connected_systems"],
        "available_integrations": s["available_integrations"],
        "last_sync_at": s["last_sync_at"],
        "records_imported_today": s["records_imported_today"],
        "records_imported_total": s["records_imported_total"],
        "sources": [
            {
                "name": d.name,
                "type": d.connector_type.value,
                "status": d.status.value,
                "health": d.health.value,
                "last_sync_at": d.last_sync_at.isoformat() if d.last_sync_at else None,
                "record_count": d.record_count,
            }
            for d in sources
        ],
        "failures": s["failures"],
    }
