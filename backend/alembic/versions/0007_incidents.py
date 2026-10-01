"""Incidents table for Phase B incident management.

Revision ID: 0007_incidents
Revises: 0006_platform_foundation
Create Date: 2026-07-28

Idempotent: safe when 0002 ``create_all`` already materialised ``incidents``.
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

revision: str = "0007_incidents"
down_revision: Union[str, None] = "0006_platform_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = (
        postgresql.UUID(as_uuid=True)
        if bind.dialect.name == "postgresql"
        else sa.String(36)
    )
    create_table_if_missing(
        "incidents",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column(
            "owner_user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("affected_entities", sa.JSON(), nullable=False),
        sa.Column("linked_alert_ids", sa.JSON(), nullable=False),
        sa.Column("linked_risk_ids", sa.JSON(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing(
        "ix_incidents_org_status",
        "incidents",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    if table_exists("incidents"):
        op.drop_index("ix_incidents_org_status", table_name="incidents")
        op.drop_table("incidents")
