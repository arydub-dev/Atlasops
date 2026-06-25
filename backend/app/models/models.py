"""SQLAlchemy ORM models for ATLASOPS."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    AlertPriority,
    AlertStatus,
    AlertType,
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    ImportStatus,
    RiskCategory,
    RiskLevel,
    ShipmentStatus,
    SimulationType,
    UserRole,
    WarehouseRiskLevel,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), default=UserRole.ANALYST, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    ai_reports: Mapped[list["AIReport"]] = relationship(back_populates="user")


# --------------------------------------------------------------------------- #
# Suppliers
# --------------------------------------------------------------------------- #
class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint("supplier_score >= 0 AND supplier_score <= 100", name="ck_supplier_score"),
        Index("ix_suppliers_country", "country"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    supplier_score: Mapped[float] = mapped_column(Float, default=80.0, nullable=False)
    delivery_reliability: Mapped[float] = mapped_column(Float, default=90.0, nullable=False)
    average_delay_days: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_fulfillment_rate: Mapped[float] = mapped_column(Float, default=95.0, nullable=False)
    defect_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="supplier")


# --------------------------------------------------------------------------- #
# Warehouses
# --------------------------------------------------------------------------- #
class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_warehouse_capacity"),
        Index("ix_warehouses_region", "region"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_inventory: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[WarehouseRiskLevel] = mapped_column(
        SAEnum(WarehouseRiskLevel, name="warehouse_risk_level"),
        default=WarehouseRiskLevel.LOW,
        nullable=False,
    )

    inventory_records: Mapped[list["Inventory"]] = relationship(back_populates="warehouse")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="warehouse")

    @property
    def utilization(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return round(self.current_inventory / self.capacity * 100, 2)


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    supplier: Mapped["Supplier"] = relationship(back_populates="products")
    inventory_records: Mapped[list["Inventory"]] = relationship(back_populates="product")


# --------------------------------------------------------------------------- #
# Inventory  (warehouse x product, plus historical snapshots)
# --------------------------------------------------------------------------- #
class Inventory(Base, TimestampMixin):
    __tablename__ = "inventory"
    __table_args__ = (
        Index("ix_inventory_wh_product", "warehouse_id", "product_id"),
        Index("ix_inventory_snapshot", "snapshot_date"),
        Index("ix_inventory_current", "is_current"),
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_daily_demand: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # True for the live row of a (warehouse, product); historical snapshots are False.
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory_records")
    product: Mapped["Product"] = relationship(back_populates="inventory_records")


# --------------------------------------------------------------------------- #
# Shipments
# --------------------------------------------------------------------------- #
class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint("delay_risk_score >= 0 AND delay_risk_score <= 100", name="ck_delay_risk"),
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_eta", "eta"),
        Index("ix_shipments_supplier", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    carrier: Mapped[str] = mapped_column(String(150), nullable=False)
    current_location: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus, name="shipment_status"),
        default=ShipmentStatus.IN_TRANSIT,
        nullable=False,
    )
    delay_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    value_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    shipped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delay_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="shipments")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="shipments")
    events: Mapped[list["ShipmentEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"
    __table_args__ = (
        Index("ix_events_shipment", "shipment_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus, name="shipment_status_event"), nullable=False
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="events")


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status_priority", "status", "priority"),
        Index("ix_alerts_type", "alert_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type"), nullable=False
    )
    priority: Mapped[AlertPriority] = mapped_column(
        SAEnum(AlertPriority, name="alert_priority"), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, name="alert_status"), default=AlertStatus.OPEN, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# Risk assessments
# --------------------------------------------------------------------------- #
class RiskAssessment(Base, TimestampMixin):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_risk_score"),
        Index("ix_risk_category_level", "category", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[RiskCategory] = mapped_column(
        SAEnum(RiskCategory, name="risk_category"), nullable=False
    )
    level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risk_level"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# --------------------------------------------------------------------------- #
# Simulations
# --------------------------------------------------------------------------- #
class Simulation(Base, TimestampMixin):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    simulation_type: Mapped[SimulationType] = mapped_column(
        SAEnum(SimulationType, name="simulation_type"), nullable=False
    )
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    inventory_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shipment_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue_impact_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


# --------------------------------------------------------------------------- #
# AI reports
# --------------------------------------------------------------------------- #
class AIReport(Base, TimestampMixin):
    __tablename__ = "ai_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="chat", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="local-engine", nullable=False)
    context_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped["User"] = relationship(back_populates="ai_reports")


# --------------------------------------------------------------------------- #
# Data sources / connectors  (Connected Mode)
# --------------------------------------------------------------------------- #
class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"
    __table_args__ = (
        Index("ix_data_sources_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[ConnectorType] = mapped_column(
        SAEnum(ConnectorType, name="connector_type"), nullable=False
    )
    status: Mapped[ConnectorStatus] = mapped_column(
        SAEnum(ConnectorStatus, name="connector_status"),
        default=ConnectorStatus.NOT_CONFIGURED,
        nullable=False,
    )
    health: Mapped[ConnectorHealth] = mapped_column(
        SAEnum(ConnectorHealth, name="connector_health"),
        default=ConnectorHealth.UNKNOWN,
        nullable=False,
    )

    # configuration (api key stored masked — this is a demo platform)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    api_key_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# --------------------------------------------------------------------------- #
# Import / pipeline runs
# --------------------------------------------------------------------------- #
class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        Index("ix_import_jobs_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv / excel / connector
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # shipments / inventory / ...
    status: Mapped[ImportStatus] = mapped_column(
        SAEnum(ImportStatus, name="import_status"), default=ImportStatus.SUCCESS, nullable=False
    )

    rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


# --------------------------------------------------------------------------- #
# App settings  (key/value — e.g. operating mode)
# --------------------------------------------------------------------------- #
class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)


# --------------------------------------------------------------------------- #
# Audit logs
# --------------------------------------------------------------------------- #
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="audit_logs")
