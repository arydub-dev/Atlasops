"""SQLAlchemy ORM models for Supply v2 (multi-tenant)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    AlertChannel,
    AlertPriority,
    AlertStatus,
    AlertType,
    BillingInterval,
    BillingPlan,
    ConnectorHealth,
    ConnectorStatus,
    ConnectorType,
    DeliveryStatus,
    DocumentEntityType,
    ImportStatus,
    IncidentSeverity,
    IncidentStatus,
    InvitationStatus,
    MembershipStatus,
    OperationalEventType,
    OrderStatus,
    OrgStatus,
    PredictionKind,
    RiskCategory,
    RiskLevel,
    ShipmentStatus,
    SimulationType,
    SubscriptionStatus,
    WarehouseRiskLevel,
    WorkflowRunStatus,
    WorkflowTrigger,
)
from app.tenancy.mixin import TenantOwned


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
# Identity & organizations
# --------------------------------------------------------------------------- #
class User(Base, TimestampMixin):
    """Global identity (WorkOS). Roles live on Membership."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workos_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (
        Index("ix_organizations_slug", "slug", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[OrgStatus] = mapped_column(
        SAEnum(OrgStatus, name="org_status"), default=OrgStatus.TRIALING, nullable=False
    )
    workos_organization_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    plan: Mapped[BillingPlan] = mapped_column(
        SAEnum(BillingPlan, name="billing_plan"), default=BillingPlan.TRIAL, nullable=False
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    branding: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    billing: Mapped["BillingAccount | None"] = relationship(back_populates="organization")


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        Index("ix_memberships_org_status", "organization_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_slug: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer")
    custom_permissions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[MembershipStatus] = mapped_column(
        SAEnum(MembershipStatus, name="membership_status"),
        default=MembershipStatus.ACTIVE,
        nullable=False,
    )
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_reason: Mapped[str | None] = mapped_column(String(500))

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class CustomRole(Base, TimestampMixin, TenantOwned):
    __tablename__ = "custom_roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_custom_role_slug"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Invitation(Base, TimestampMixin, TenantOwned):
    __tablename__ = "invitations"
    __table_args__ = (
        Index("ix_invitations_token", "token", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_slug: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer")
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        SAEnum(InvitationStatus, name="invitation_status"),
        default=InvitationStatus.PENDING,
        nullable=False,
    )
    invited_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Base, TimestampMixin):
    """Server-side session (httpOnly cookie stores opaque token)."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_token", "token_hash", unique=True),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    device_label: Mapped[str | None] = mapped_column(String(120))
    device_trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="sessions")


class OAuthLoginState(Base, TimestampMixin):
    """One-time PKCE + CSRF state for email-first WorkOS login."""

    __tablename__ = "oauth_login_states"
    __table_args__ = (
        Index("ix_oauth_login_states_expires", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    state: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    workos_organization_id: Mapped[str | None] = mapped_column(String(128))
    invite_token: Mapped[str | None] = mapped_column(String(128))
    remember_device: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    return_path: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiToken(Base, TimestampMixin, TenantOwned):
    __tablename__ = "api_tokens"
    __table_args__ = (Index("ix_api_tokens_prefix", "token_prefix", unique=True),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookEndpoint(Base, TimestampMixin, TenantOwned):
    __tablename__ = "webhook_endpoints"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# --------------------------------------------------------------------------- #
# Org hierarchy
# --------------------------------------------------------------------------- #
class Site(Base, TimestampMixin, TenantOwned):
    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_site_code"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))


class Facility(Base, TimestampMixin, TenantOwned):
    __tablename__ = "facilities"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    site_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(64), default="warehouse")


class Department(Base, TimestampMixin, TenantOwned):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("facilities.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Team(Base, TimestampMixin, TenantOwned):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    department_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


# --------------------------------------------------------------------------- #
# Billing
# --------------------------------------------------------------------------- #
class BillingAccount(Base, TimestampMixin, TenantOwned):
    __tablename__ = "billing_accounts"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_billing_org"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    plan: Mapped[BillingPlan] = mapped_column(
        SAEnum(BillingPlan, name="billing_plan_account", create_constraint=False),
        default=BillingPlan.TRIAL,
        nullable=False,
    )
    interval: Mapped[BillingInterval] = mapped_column(
        SAEnum(BillingInterval, name="billing_interval"),
        default=BillingInterval.MONTHLY,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.TRIALING,
        nullable=False,
    )
    seat_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_credits_included: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    ai_credits_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_bytes_used: Mapped[BigInteger] = mapped_column(BigInteger, default=0, nullable=False)
    api_requests_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="billing")


class StripeEvent(Base):
    """Processed Stripe webhook events (global idempotency; not tenant-RLS)."""

    __tablename__ = "stripe_events"
    __table_args__ = (
        UniqueConstraint("stripe_event_id", name="uq_stripe_events_event_id"),
        Index("ix_stripe_events_processed_at", "processed_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    stripe_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class UsageRecord(Base, TenantOwned):
    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_org_metric_time", "organization_id", "metric", "recorded_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)  # api, ai, storage, seats
    quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    meta: Mapped[dict | None] = mapped_column(JSON)


# --------------------------------------------------------------------------- #
# Domain — operational entities (tenant-owned)
# --------------------------------------------------------------------------- #
class Supplier(Base, TimestampMixin, TenantOwned):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint("supplier_score >= 0 AND supplier_score <= 100", name="ck_supplier_score"),
        Index("ix_suppliers_org_country", "organization_id", "country"),
        Index("ix_suppliers_org_name", "organization_id", "name"),
        # Idempotent connector upserts: same Salesforce Id in one tenant is one row.
        Index(
            "uq_suppliers_org_external_id",
            "organization_id",
            "external_id",
            unique=True,
            sqlite_where=text("external_id IS NOT NULL"),
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)

    supplier_score: Mapped[float] = mapped_column(Float, default=80.0, nullable=False)
    delivery_reliability: Mapped[float] = mapped_column(Float, default=90.0, nullable=False)
    average_delay_days: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_fulfillment_rate: Mapped[float] = mapped_column(Float, default=95.0, nullable=False)
    defect_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="supplier")


class Warehouse(Base, TimestampMixin, TenantOwned):
    __tablename__ = "warehouses"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_warehouse_capacity"),
        Index("ix_warehouses_org_region", "organization_id", "region"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    site_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)

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


class Product(Base, TimestampMixin, TenantOwned):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_product_org_sku"),
        Index("ix_products_org_category", "organization_id", "category"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)

    supplier_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), index=True
    )
    supplier: Mapped["Supplier | None"] = relationship(back_populates="products")
    inventory_records: Mapped[list["Inventory"]] = relationship(back_populates="product")


class Inventory(Base, TimestampMixin, TenantOwned):
    __tablename__ = "inventory"
    __table_args__ = (
        Index("ix_inventory_org_wh_product", "organization_id", "warehouse_id", "product_id"),
        Index("ix_inventory_org_current", "organization_id", "is_current"),
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_daily_demand: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory_records")
    product: Mapped["Product"] = relationship(back_populates="inventory_records")


class Shipment(Base, TimestampMixin, TenantOwned):
    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("organization_id", "reference", name="uq_shipment_org_ref"),
        CheckConstraint("delay_risk_score >= 0 AND delay_risk_score <= 100", name="ck_delay_risk"),
        Index("ix_shipments_org_status", "organization_id", "status"),
        Index("ix_shipments_org_eta", "organization_id", "eta"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    carrier: Mapped[str] = mapped_column(String(150), nullable=False)
    current_location: Mapped[str] = mapped_column(String(255), nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(128), index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)

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
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delay_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    supplier_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), index=True
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), index=True
    )

    supplier: Mapped["Supplier | None"] = relationship(back_populates="shipments")
    warehouse: Mapped["Warehouse | None"] = relationship(back_populates="shipments")
    events: Mapped[list["ShipmentEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )


class ShipmentEvent(Base, TenantOwned):
    __tablename__ = "shipment_events"
    __table_args__ = (Index("ix_events_shipment", "shipment_id", "occurred_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    shipment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus, name="shipment_status_event", create_constraint=False),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="events")


class Alert(Base, TimestampMixin, TenantOwned):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_org_status_priority", "organization_id", "status", "priority"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
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
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)


class RiskAssessment(Base, TimestampMixin, TenantOwned):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_risk_score"),
        Index("ix_risk_org_category", "organization_id", "category", "level"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[RiskCategory] = mapped_column(
        SAEnum(RiskCategory, name="risk_category"), nullable=False
    )
    level: Mapped[RiskLevel] = mapped_column(SAEnum(RiskLevel, name="risk_level"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    factors: Mapped[dict | None] = mapped_column(JSON)


class Simulation(Base, TimestampMixin, TenantOwned):
    __tablename__ = "simulations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    simulation_type: Mapped[SimulationType] = mapped_column(
        SAEnum(SimulationType, name="simulation_type"), nullable=False
    )
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    inventory_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shipment_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue_impact_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class AIReport(Base, TimestampMixin, TenantOwned):
    __tablename__ = "ai_reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="chat", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="local-engine", nullable=False)
    context_snapshot: Mapped[dict | None] = mapped_column(JSON)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class Connection(Base, TimestampMixin, TenantOwned):
    """Production connector instance (replaces DataSource)."""

    __tablename__ = "connections"
    __table_args__ = (Index("ix_connections_org_type", "organization_id", "connector_type"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
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
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    credentials_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    sync_frequency: Mapped[str | None] = mapped_column(String(50))
    webhook_url: Mapped[str | None] = mapped_column(String(500))
    cursor: Mapped[dict | None] = mapped_column(JSON)  # incremental sync state
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connector_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)


class ConnectorDeadLetter(Base, TimestampMixin, TenantOwned):
    """Failed connector sync / transform payloads for replay."""

    __tablename__ = "connector_dead_letters"
    __table_args__ = (
        Index("ix_connector_dlq_org_created", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("connections.id", ondelete="SET NULL")
    )
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PurchaseOrder(Base, TimestampMixin, TenantOwned):
    """Canonical purchase order (procurement spine)."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_po_org_status", "organization_id", "status"),
        UniqueConstraint("organization_id", "reference", name="uq_po_org_reference"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.OPEN,
        nullable=False,
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL")
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL")
    )
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source_connection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("connections.id", ondelete="SET NULL")
    )
    line_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SalesOrder(Base, TimestampMixin, TenantOwned):
    """Canonical sales / customer order (demand spine)."""

    __tablename__ = "sales_orders"
    __table_args__ = (
        Index("ix_so_org_status", "organization_id", "status"),
        UniqueConstraint("organization_id", "reference", name="uq_so_org_reference"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            name="order_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=OrderStatus.OPEN,
        nullable=False,
    )
    customer_name: Mapped[str | None] = mapped_column(String(255))
    warehouse_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL")
    )
    shipment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL")
    )
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    promised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source_connection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("connections.id", ondelete="SET NULL")
    )
    line_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class OperationalEvent(Base, TimestampMixin, TenantOwned):
    """First-class operational timeline event (graph-aware)."""

    __tablename__ = "operational_events"
    __table_args__ = (
        Index("ix_opevents_org_time", "organization_id", "occurred_at"),
        Index("ix_opevents_entity", "organization_id", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[OperationalEventType] = mapped_column(
        SAEnum(
            OperationalEventType,
            name="operational_event_type",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=OperationalEventType.SYSTEM,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AlertDelivery(Base, TimestampMixin, TenantOwned):
    """Outbound alert delivery attempt (email / webhook / future Slack/Teams)."""

    __tablename__ = "alert_deliveries"
    __table_args__ = (Index("ix_alert_deliveries_alert", "alert_id", "channel"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[AlertChannel] = mapped_column(
        SAEnum(
            AlertChannel,
            name="alert_channel",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(
            DeliveryStatus,
            name="delivery_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )
    destination: Mapped[str | None] = mapped_column(String(500))
    response: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Incident(Base, TimestampMixin, TenantOwned):
    """First-class operational incident linking alerts, risks, and graph entities."""

    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_org_status", "organization_id", "status"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(
        SAEnum(
            IncidentSeverity,
            name="incident_severity",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=IncidentSeverity.MEDIUM,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(
            IncidentStatus,
            name="incident_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=IncidentStatus.OPEN,
        nullable=False,
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    summary: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_entities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linked_alert_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linked_risk_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowRule(Base, TimestampMixin, TenantOwned):
    """Automation rule: trigger → conditions → actions."""

    __tablename__ = "workflow_rules"
    __table_args__ = (Index("ix_workflow_rules_org_active", "organization_id", "is_active"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trigger: Mapped[WorkflowTrigger] = mapped_column(
        SAEnum(
            WorkflowTrigger,
            name="workflow_trigger",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    conditions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    schedule_cron: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class WorkflowRun(Base, TimestampMixin, TenantOwned):
    __tablename__ = "workflow_runs"
    __table_args__ = (Index("ix_workflow_runs_org_created", "organization_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflow_rules.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[WorkflowRunStatus] = mapped_column(
        SAEnum(
            WorkflowRunStatus,
            name="workflow_run_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=WorkflowRunStatus.PENDING,
        nullable=False,
    )
    trigger_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentAttachment(Base, TimestampMixin, TenantOwned):
    """Enterprise document metadata; bytes live in R2/S3."""

    __tablename__ = "document_attachments"
    __table_args__ = (
        Index("ix_documents_org_entity", "organization_id", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[DocumentEntityType] = mapped_column(
        SAEnum(
            DocumentEntityType,
            name="document_entity_type",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    virus_scan_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Prediction(Base, TimestampMixin, TenantOwned):
    """Predictive intelligence outputs grounded in operational history."""

    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_org_kind", "organization_id", "kind"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[PredictionKind] = mapped_column(
        SAEnum(
            PredictionKind,
            name="prediction_kind",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_factors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linked_entities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    horizon_hours: Mapped[int] = mapped_column(Integer, default=72, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DataQualitySnapshot(Base, TimestampMixin, TenantOwned):
    """Point-in-time data health assessment."""

    __tablename__ = "data_quality_snapshots"
    __table_args__ = (Index("ix_dq_org_created", "organization_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness: Mapped[float] = mapped_column(Float, nullable=False)
    freshness: Mapped[float] = mapped_column(Float, nullable=False)
    consistency: Mapped[float] = mapped_column(Float, nullable=False)
    duplicates: Mapped[float] = mapped_column(Float, nullable=False)
    missing_relationships: Mapped[float] = mapped_column(Float, nullable=False)
    invalid_values: Mapped[float] = mapped_column(Float, nullable=False)
    failed_mappings: Mapped[float] = mapped_column(Float, nullable=False)
    sync_latency_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    remediations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class DashboardLayout(Base, TimestampMixin, TenantOwned):
    """Saved role-specific / personal dashboard layouts."""

    __tablename__ = "dashboard_layouts"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "role_key", name="uq_dashboard_layout"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    role_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    widgets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ConnectorSyncLog(Base, TimestampMixin, TenantOwned):
    """Connector Studio diagnostics / sync history."""

    __tablename__ = "connector_sync_logs"
    __table_args__ = (
        Index("ix_connector_sync_logs_conn", "organization_id", "connection_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("connections.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(32), default="incremental", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ImportJob(Base, TenantOwned):
    __tablename__ = "import_jobs"
    __table_args__ = (Index("ix_import_jobs_org_created", "organization_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        SAEnum(ImportStatus, name="import_status"), default=ImportStatus.RUNNING, nullable=False
    )
    mapping: Mapped[dict | None] = mapped_column(JSON)
    preview: Mapped[dict | None] = mapped_column(JSON)
    snapshot: Mapped[dict | None] = mapped_column(JSON)  # for rollback
    rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[list | dict | None] = mapped_column(JSON)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class OrgSetting(Base, TimestampMixin, TenantOwned):
    __tablename__ = "org_settings"
    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_org_setting"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(2000), nullable=False)


class AuditLog(Base, TenantOwned):
    """Append-oriented audit trail (application never updates rows)."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_org_time", "organization_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    request_id: Mapped[str | None] = mapped_column(String(64))
    integrity_hash: Mapped[str | None] = mapped_column(String(128))  # chain hash
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


# Tables with PostgreSQL RLS. Memberships/invitations/sessions are enforced in
# application code because identity flows (list-my-orgs, accept-invite) are
# cross-tenant by nature.
TENANT_TABLES: tuple[str, ...] = (
    "custom_roles",
    "api_tokens",
    "webhook_endpoints",
    "sites",
    "facilities",
    "departments",
    "teams",
    "billing_accounts",
    "usage_records",
    "suppliers",
    "warehouses",
    "products",
    "inventory",
    "shipments",
    "shipment_events",
    "purchase_orders",
    "sales_orders",
    "operational_events",
    "alerts",
    "alert_deliveries",
    "incidents",
    "workflow_rules",
    "workflow_runs",
    "document_attachments",
    "predictions",
    "data_quality_snapshots",
    "dashboard_layouts",
    "connector_sync_logs",
    "risk_assessments",
    "simulations",
    "ai_reports",
    "connections",
    "connector_dead_letters",
    "import_jobs",
    "org_settings",
    "audit_logs",
)


class SalesLead(Base):
    """Operator-only pre-customer inquiry; deliberately outside tenant data."""
    __tablename__ = "sales_leads"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    details_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
