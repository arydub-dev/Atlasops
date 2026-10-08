"""Strict, explicitly mapped connector ingestion. No inferred business values."""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.connectors.base import ConnectorError, SyncResult
from app.models import Organization, Product, SalesOrder, Supplier
from app.models.enums import OrderStatus

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
MODELS = {"products": Product, "sales_orders": SalesOrder, "suppliers": Supplier}
FIELDS = {
    "products": {"sku", "name", "category", "unit_cost", "unit_price", "lead_time_days"},
    "sales_orders": {"reference", "status", "customer_name", "currency", "total_amount", "ordered_at", "promised_at"},
    "suppliers": {"name", "country", "region", "category", "supplier_score", "delivery_reliability", "average_delay_days", "order_fulfillment_rate", "defect_rate"},
}
REQUIRED = {"products": FIELDS["products"], "sales_orders": {"reference", "status", "currency", "total_amount", "ordered_at"}, "suppliers": FIELDS["suppliers"]}
NUMBERS = {"unit_cost", "unit_price", "total_amount", "supplier_score", "delivery_reliability", "average_delay_days", "order_fulfillment_rate", "defect_rate"}


def invalid(message):
    return ConnectorError(message, retryable=False, failure_class="data_validation_failure")


def validate_mappings(config):
    specs = config.get("sync_entities")
    if not isinstance(specs, list) or not 1 <= len(specs) <= 3:
        raise invalid("Configure between one and three explicit sync_entities mappings")
    targets = set()
    for spec in specs:
        if not isinstance(spec, dict):
            raise invalid("Each mapping must be an object")
        target = spec.get("target")
        if not isinstance(target, str) or target not in MODELS or target in targets:
            raise invalid("Mapping targets must be unique: suppliers, products, sales_orders")
        targets.add(target)
        fields = spec.get("fields")
        if not isinstance(fields, dict) or not REQUIRED[target] <= fields.keys() or not fields.keys() <= FIELDS[target]:
            raise invalid(f"Invalid or missing destination fields for {target}; consult the connector mapping guide")
        for name in [spec.get("source"), spec.get("id_field"), *fields.values()]:
            if not isinstance(name, str) or not IDENT.fullmatch(name):
                raise invalid("Source objects and fields must be simple API identifiers")
        equals = spec.get("filter_equals", {})
        if not isinstance(equals, dict) or len(equals) > 5 or any(not IDENT.fullmatch(k) or not isinstance(v, (str, bool, int)) for k, v in equals.items()):
            raise invalid("filter_equals must contain up to five source-field equality conditions")
        if target == "suppliers" and not equals:
            raise invalid("Supplier mapping requires filter_equals to explicitly select supplier accounts")
        if target == "sales_orders":
            statuses = spec.get("status_map")
            if not isinstance(statuses, dict) or not statuses or any(v not in {s.value for s in OrderStatus} for v in statuses.values()):
                raise invalid("Sales orders require an explicit status_map")
    return specs


def apply_records(db, connector, spec, records, result: SyncResult):
    """One atomic batch, serialized by tenant. Caller owns commit and rollback."""
    connection_id = connector.config.get("_connection_id")
    if not connection_id:
        raise invalid("Connector execution requires a server-assigned connection ID")
    UUID(str(connection_id))
    db.scalar(select(Organization).where(Organization.id == connector.organization_id).with_for_update())
    model = MODELS[spec["target"]]
    for rec in records:
        if not isinstance(rec, dict):
            raise invalid("Remote collection contains an invalid record")
        if any(rec.get(k) != v for k, v in spec.get("filter_equals", {}).items()):
            continue
        result.records_processed += 1
        remote_id = rec.get(spec["id_field"])
        if remote_id is None or not str(remote_id).strip():
            raise invalid("Remote record is missing its stable ID")
        identity = f"{connector.connector_type.value}:{connection_id}:{spec['source']}:{remote_id}"
        external = 'mapped:' + hashlib.sha256(identity.encode()).hexdigest()
        values = {}
        for dest, source in spec["fields"].items():
            value = rec.get(source)
            if value is None or value == "":
                if dest in REQUIRED[spec["target"]]:
                    raise invalid(f"Remote record is missing required mapped field {source}")
                values[dest] = None
                continue
            if dest in NUMBERS or dest == "lead_time_days":
                try:
                    if isinstance(value, bool):
                        raise ValueError()
                    value = float(value)
                    if not math.isfinite(value) or value < 0 or value > 1e12:
                        raise ValueError()
                    if dest in {"supplier_score", "delivery_reliability", "order_fulfillment_rate", "defect_rate"} and value > 100:
                        raise ValueError()
                    if dest == "lead_time_days":
                        if not value.is_integer() or value > 3650:
                            raise ValueError()
                        value = int(value)
                except (TypeError, ValueError, OverflowError):
                    raise invalid(f"Invalid numeric field {source}") from None
            elif dest in {"ordered_at", "promised_at"}:
                try:
                    value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                except ValueError:
                    raise invalid(f"Invalid date field {source}") from None
            elif dest == "status":
                if str(value) not in spec["status_map"]:
                    raise invalid("Unmapped remote order status; update status_map")
                value = OrderStatus(spec["status_map"][str(value)])
            else:
                value = str(value).strip()
                maximum = model.__table__.columns[dest].type.length
                if not value or len(value) > maximum:
                    raise invalid(f"Invalid text field {source}")
                if dest == "currency" and not re.fullmatch(r"[A-Z]{3}", value):
                    raise invalid("Currency must be an explicit three-letter code")
            values[dest] = value
        existing = db.scalars(select(model).where(model.organization_id == connector.organization_id, model.external_id == external)).all()
        if len(existing) > 1:
            raise invalid("Duplicate source identities need reconciliation")
        obj = existing[0] if existing else model(organization_id=connector.organization_id, external_id=external)
        # Never silently merge another system's product or order by display key.
        key = {"products": "sku", "sales_orders": "reference"}.get(spec["target"])
        if key:
            conflict = db.scalar(select(model).where(model.organization_id == connector.organization_id, getattr(model, key) == values[key]))
            if conflict is not None and conflict is not obj:
                raise invalid(f"Existing {key} belongs to a different source; reconcile before sync")
        for key, value in values.items():
            setattr(obj, key, value)
        if spec["target"] == "sales_orders":
            obj.source_connection_id = UUID(str(connection_id))
            obj.meta = {**(obj.meta or {}), "source_object": spec["source"], "source_id": str(remote_id), "scope": "order_header_only"}
        db.add(obj)
        db.flush()
        result.records_imported += 1
