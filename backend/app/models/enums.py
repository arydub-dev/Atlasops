"""Enumerations shared across models and schemas."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATIONS_MANAGER = "operations_manager"
    ANALYST = "analyst"
    EXECUTIVE = "executive"


class ShipmentStatus(str, enum.Enum):
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    AT_WAREHOUSE = "at_warehouse"
    CUSTOMS_HOLD = "customs_hold"


class WarehouseRiskLevel(str, enum.Enum):
    LOW = "low"          # green
    MEDIUM = "medium"    # yellow
    HIGH = "high"        # red


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(str, enum.Enum):
    SUPPLIER = "supplier"
    SHIPMENT = "shipment"
    INVENTORY = "inventory"
    GEOGRAPHIC = "geographic"


class AlertType(str, enum.Enum):
    DELAYED_SHIPMENT = "delayed_shipment"
    INVENTORY_STOCKOUT_RISK = "inventory_stockout_risk"
    SUPPLIER_FAILURE_RISK = "supplier_failure_risk"
    FORECASTED_DEMAND_SPIKE = "forecasted_demand_spike"


class AlertPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class SimulationType(str, enum.Enum):
    SUPPLIER_SHUTDOWN = "supplier_shutdown"
    PORT_CLOSURE = "port_closure"
    DEMAND_SPIKE = "demand_spike"
    WEATHER_DISRUPTION = "weather_disruption"
    WAREHOUSE_OUTAGE = "warehouse_outage"


# --------------------------------------------------------------------------- #
# Data ingestion / connected-mode enums
# --------------------------------------------------------------------------- #
class ConnectorType(str, enum.Enum):
    SAP_ERP = "sap_erp"
    ORACLE_ERP = "oracle_erp"
    SALESFORCE_CRM = "salesforce_crm"
    MS_DYNAMICS = "ms_dynamics"
    WMS = "wms"
    TMS = "tms"
    REST_API = "rest_api"
    CSV_UPLOAD = "csv_upload"
    EXCEL_UPLOAD = "excel_upload"


class ConnectorStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


class ConnectorHealth(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class ImportStatus(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RUNNING = "running"


class OperatingMode(str, enum.Enum):
    DEMO = "demo"
    CONNECTED = "connected"
