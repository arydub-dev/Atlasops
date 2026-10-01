"""Phase C enterprise operations tables.

Revision ID: 0008_enterprise_ops
Revises: 0007_incidents
Create Date: 2026-07-28

Idempotent: safe when 0002 ``create_all`` already materialised these tables.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.migration_helpers import (
    create_index_if_missing,
    create_table_if_missing,
    table_exists,
)

revision: str = "0008_enterprise_ops"
down_revision: Union[str, None] = "0007_incidents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid(bind) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = _uuid(bind)

    create_table_if_missing(
        "workflow_rules",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger", sa.String(32), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("schedule_cron", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_workflow_rules_org_active",
        "workflow_rules",
        ["organization_id", "is_active"],
    )

    create_table_if_missing(
        "workflow_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", uuid_type, sa.ForeignKey("workflow_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("trigger_payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_workflow_runs_org_created",
        "workflow_runs",
        ["organization_id", "created_at"],
    )
    create_index_if_missing("ix_workflow_runs_rule_id", "workflow_runs", ["rule_id"])

    create_table_if_missing(
        "document_attachments",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", uuid_type, nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False, server_default="application/octet-stream"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("uploaded_by_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("virus_scan_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_documents_org_entity",
        "document_attachments",
        ["organization_id", "entity_type", "entity_id"],
    )

    create_table_if_missing(
        "predictions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("contributing_factors", sa.JSON(), nullable=False),
        sa.Column("recommended_actions", sa.JSON(), nullable=False),
        sa.Column("linked_entities", sa.JSON(), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False, server_default="72"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing("ix_predictions_org_kind", "predictions", ["organization_id", "kind"])

    create_table_if_missing(
        "data_quality_snapshots",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("completeness", sa.Float(), nullable=False),
        sa.Column("freshness", sa.Float(), nullable=False),
        sa.Column("consistency", sa.Float(), nullable=False),
        sa.Column("duplicates", sa.Float(), nullable=False),
        sa.Column("missing_relationships", sa.Float(), nullable=False),
        sa.Column("invalid_values", sa.Float(), nullable=False),
        sa.Column("failed_mappings", sa.Float(), nullable=False),
        sa.Column("sync_latency_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("remediations", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_dq_org_created",
        "data_quality_snapshots",
        ["organization_id", "created_at"],
    )

    create_table_if_missing(
        "dashboard_layouts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("widgets", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", "role_key", name="uq_dashboard_layout"),
    )

    create_table_if_missing(
        "connector_sync_logs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", uuid_type, sa.ForeignKey("connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False, server_default="incremental"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_connector_sync_logs_conn",
        "connector_sync_logs",
        ["organization_id", "connection_id", "created_at"],
    )


def downgrade() -> None:
    if table_exists("connector_sync_logs"):
        op.drop_index("ix_connector_sync_logs_conn", table_name="connector_sync_logs")
        op.drop_table("connector_sync_logs")
    if table_exists("dashboard_layouts"):
        op.drop_table("dashboard_layouts")
    if table_exists("data_quality_snapshots"):
        op.drop_index("ix_dq_org_created", table_name="data_quality_snapshots")
        op.drop_table("data_quality_snapshots")
    if table_exists("predictions"):
        op.drop_index("ix_predictions_org_kind", table_name="predictions")
        op.drop_table("predictions")
    if table_exists("document_attachments"):
        op.drop_index("ix_documents_org_entity", table_name="document_attachments")
        op.drop_table("document_attachments")
    if table_exists("workflow_runs"):
        op.drop_index("ix_workflow_runs_rule_id", table_name="workflow_runs")
        op.drop_index("ix_workflow_runs_org_created", table_name="workflow_runs")
        op.drop_table("workflow_runs")
    if table_exists("workflow_rules"):
        op.drop_index("ix_workflow_rules_org_active", table_name="workflow_rules")
        op.drop_table("workflow_rules")
