"""Enumerations for Supply v2."""
from __future__ import annotations

import enum


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class OrgStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class BillingPlan(str, enum.Enum):
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingInterval(str, enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    UNPAID = "unpaid"


class ShipmentStatus(str, enum.Enum):
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    AT_WAREHOUSE = "at_warehouse"
    CUSTOMS_HOLD = "customs_hold"


class WarehouseRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SimulationType(str, enum.Enum):
    SUPPLIER_SHUTDOWN = "supplier_shutdown"
    SUPPLIER_DELAY = "supplier_delay"
    PORT_CLOSURE = "port_closure"
    DEMAND_SPIKE = "demand_spike"
    WEATHER_DISRUPTION = "weather_disruption"
    WAREHOUSE_OUTAGE = "warehouse_outage"
    TRANSPORTATION_DISRUPTION = "transportation_disruption"


class ConnectorType(str, enum.Enum):
    DYNAMICS_BC = "dynamics_bc"
    SALESFORCE = "salesforce"
    SAP_BUSINESS_ONE = "sap_business_one"
    UPS = "ups"
    CSV_UPLOAD = "csv_upload"
    EXCEL_UPLOAD = "excel_upload"
    JSON_UPLOAD = "json_upload"


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
    ROLLED_BACK = "rolled_back"
    QUEUED = "queued"
    RETRYING = "retrying"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CONFIRMED = "confirmed"
    IN_FULFILLMENT = "in_fulfillment"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class OperationalEventType(str, enum.Enum):
    INGEST = "ingest"
    STATUS_CHANGE = "status_change"
    RISK = "risk"
    ALERT = "alert"
    SYNC = "sync"
    USER = "user"
    SYSTEM = "system"


class AlertChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class WorkflowTrigger(str, enum.Enum):
    CONNECTOR_SYNC = "connector_sync"
    RISK_CHANGE = "risk_change"
    INVENTORY = "inventory"
    SHIPMENT = "shipment"
    PURCHASE_ORDER = "purchase_order"
    INCIDENT = "incident"
    SCHEDULE = "schedule"
    MANUAL = "manual"


class WorkflowRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class PredictionKind(str, enum.Enum):
    SHIPMENT_DELAY = "shipment_delay"
    SUPPLIER_DETERIORATION = "supplier_deterioration"
    INVENTORY_SHORTAGE = "inventory_shortage"
    DEMAND_SPIKE = "demand_spike"
    WAREHOUSE_CONGESTION = "warehouse_congestion"
    LEAD_TIME_CHANGE = "lead_time_change"
    ANOMALY = "anomaly"


class DocumentEntityType(str, enum.Enum):
    PURCHASE_ORDER = "purchase_order"
    SALES_ORDER = "sales_order"
    SHIPMENT = "shipment"
    SUPPLIER = "supplier"
    WAREHOUSE = "warehouse"
    INCIDENT = "incident"
    ASSET = "asset"
    ORGANIZATION = "organization"


# --------------------------------------------------------------------------- #
# Legacy alias — removed from User; kept briefly for migration scripts only.
# Prefer Membership.role_slug + permissions.
# --------------------------------------------------------------------------- #
class UserRole(str, enum.Enum):
    """Deprecated: use Membership.role_slug."""

    ADMIN = "admin"
    OPERATIONS_MANAGER = "operations_manager"
    ANALYST = "analyst"
    EXECUTIVE = "executive"
