"""Canonical orders, events, alert deliveries, connector DLQ + next_sync_at.

Revision ID: 0006_platform_foundation
Revises: 0005_auth_enterprise_sessions
Create Date: 2026-07-28

Idempotent: safe when 0002 ``create_all`` already materialised these tables
from current ORM metadata (greenfield ``alembic upgrade head``).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.migration_helpers import (
    add_column_if_missing,
    column_exists,
    create_index_if_missing,
    create_table_if_missing,
    table_exists,
)

revision: str = "0006_platform_foundation"
down_revision: Union[str, None] = "0005_auth_enterprise_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.String(36)

    add_column_if_missing(
        "connections",
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
    )

    create_table_if_missing(
        "connector_dead_letters",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", uuid_type, sa.ForeignKey("connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("connector_type", sa.String(64), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_connector_dlq_org_created",
        "connector_dead_letters",
        ["organization_id", "created_at"],
    )

    create_table_if_missing(
        "purchase_orders",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("supplier_id", uuid_type, sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", uuid_type, sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("source_connection_id", uuid_type, sa.ForeignKey("connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "reference", name="uq_po_org_reference"),
    )
    create_index_if_missing("ix_po_org_status", "purchase_orders", ["organization_id", "status"])

    create_table_if_missing(
        "sales_orders",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("warehouse_id", uuid_type, sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_id", uuid_type, sa.ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("source_connection_id", uuid_type, sa.ForeignKey("connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "reference", name="uq_so_org_reference"),
    )
    create_index_if_missing("ix_so_org_status", "sales_orders", ["organization_id", "status"])

    create_table_if_missing(
        "operational_events",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False, server_default="system"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", uuid_type, nullable=True),
        sa.Column("severity", sa.String(32), nullable=False, server_default="info"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_opevents_org_time",
        "operational_events",
        ["organization_id", "occurred_at"],
    )
    create_index_if_missing(
        "ix_opevents_entity",
        "operational_events",
        ["organization_id", "entity_type", "entity_id"],
    )

    create_table_if_missing(
        "alert_deliveries",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_id", uuid_type, sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("destination", sa.String(500), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_alert_deliveries_alert",
        "alert_deliveries",
        ["alert_id", "channel"],
    )


def downgrade() -> None:
    if table_exists("alert_deliveries"):
        op.drop_index("ix_alert_deliveries_alert", table_name="alert_deliveries")
        op.drop_table("alert_deliveries")
    if table_exists("operational_events"):
        op.drop_index("ix_opevents_entity", table_name="operational_events")
        op.drop_index("ix_opevents_org_time", table_name="operational_events")
        op.drop_table("operational_events")
    if table_exists("sales_orders"):
        op.drop_index("ix_so_org_status", table_name="sales_orders")
        op.drop_table("sales_orders")
    if table_exists("purchase_orders"):
        op.drop_index("ix_po_org_status", table_name="purchase_orders")
        op.drop_table("purchase_orders")
    if table_exists("connector_dead_letters"):
        op.drop_index("ix_connector_dlq_org_created", table_name="connector_dead_letters")
        op.drop_table("connector_dead_letters")
    if column_exists("connections", "next_sync_at"):
        op.drop_column("connections", "next_sync_at")
