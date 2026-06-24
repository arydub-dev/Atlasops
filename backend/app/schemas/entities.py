"""Pydantic schemas for core supply-chain entities."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AlertPriority,
    AlertStatus,
    AlertType,
    RiskCategory,
    RiskLevel,
    ShipmentStatus,
    SimulationType,
    WarehouseRiskLevel,
)

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


# --------------------------------------------------------------------------- #
# Supplier
# --------------------------------------------------------------------------- #
class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str
    region: str
    category: str
    supplier_score: float
    delivery_reliability: float
    average_delay_days: float
    order_fulfillment_rate: float
    defect_rate: float
    is_active: bool


class SupplierScorecard(SupplierOut):
    rank: int
    total_shipments: int
    delayed_shipments: int
    on_time_rate: float
    monthly_trend: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Warehouse / Inventory
# --------------------------------------------------------------------------- #
class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    region: str
    latitude: float
    longitude: float
    capacity: int
    current_inventory: int
    utilization: float
    risk_level: WarehouseRiskLevel


class InventoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
    product_id: int
    quantity: int
    reorder_point: int
    safety_stock: int
    max_stock: int
    avg_daily_demand: float


class InventoryEnriched(BaseModel):
    id: int
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_sku: str
    product_name: str
    quantity: int
    reorder_point: int
    safety_stock: int
    max_stock: int
    avg_daily_demand: float
    days_of_supply: float
    status: str  # ok | low_stock | overstock | stockout
    reorder_recommendation: int


# --------------------------------------------------------------------------- #
# Shipment
# --------------------------------------------------------------------------- #
class ShipmentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ShipmentStatus
    location: str
    note: str | None
    occurred_at: datetime


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    origin: str
    destination: str
    carrier: str
    current_location: str
    status: ShipmentStatus
    delay_risk_score: float
    units: int
    value_usd: float
    shipped_at: datetime
    eta: datetime
    delivered_at: datetime | None
    delay_days: float
    supplier_id: int | None
    warehouse_id: int | None
    product_id: int | None


class ShipmentDetail(ShipmentOut):
    supplier_name: str | None = None
    warehouse_name: str | None = None
    events: list[ShipmentEventOut] = Field(default_factory=list)


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus
    current_location: str | None = None
    note: str | None = None


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: AlertType
    priority: AlertPriority
    status: AlertStatus
    title: str
    message: str
    entity_type: str | None
    entity_id: int | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime


class AlertUpdate(BaseModel):
    status: AlertStatus
    resolution_note: str | None = None


# --------------------------------------------------------------------------- #
# Risk
# --------------------------------------------------------------------------- #
class RiskAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: RiskCategory
    level: RiskLevel
    score: float
    title: str
    description: str
    recommendation: str
    entity_type: str | None
    entity_id: int | None
    factors: dict[str, Any] | None
    created_at: datetime


class RiskSummary(BaseModel):
    overall_score: float
    overall_level: RiskLevel
    by_category: dict[str, float]
    counts: dict[str, int]
    top_risks: list[RiskAssessmentOut]


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
class SimulationRequest(BaseModel):
    name: str | None = None
    simulation_type: SimulationType
    # generic parameters; meaning depends on simulation_type
    supplier_id: int | None = None
    warehouse_id: int | None = None
    region: str | None = None
    severity: float = Field(default=0.7, ge=0.0, le=1.0)
    duration_days: int = Field(default=14, ge=1, le=180)
    demand_multiplier: float = Field(default=1.5, ge=1.0, le=5.0)


class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    simulation_type: SimulationType
    parameters: dict[str, Any]
    results: dict[str, Any]
    inventory_impact: float
    shipment_impact: float
    revenue_impact_usd: float
    created_at: datetime


# --------------------------------------------------------------------------- #
# AI
# --------------------------------------------------------------------------- #
class AIChatRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=2000)
    report_type: str = "chat"


class AIReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt: str
    response: str
    report_type: str
    model: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# Dashboard / Analytics
# --------------------------------------------------------------------------- #
class KPISet(BaseModel):
    total_shipments: int
    active_shipments: int
    delayed_shipments: int
    on_time_delivery_rate: float
    inventory_health_score: float
    supplier_reliability_score: float
    open_alerts: int
    critical_risks: int


class TrendPoint(BaseModel):
    label: str
    value: float


class DashboardResponse(BaseModel):
    kpis: KPISet
    shipment_trend: list[dict[str, Any]]
    inventory_trend: list[dict[str, Any]]
    delay_trend: list[dict[str, Any]]
    supplier_performance_trend: list[dict[str, Any]]
    critical_alerts: list[AlertOut]
    top_risks: list[RiskAssessmentOut]
    recommended_actions: list[dict[str, Any]]
