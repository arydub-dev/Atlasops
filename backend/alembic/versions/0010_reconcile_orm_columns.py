"""Reconcile ORM columns that create_all cannot add to existing tables.

Revision ID: 0010_reconcile_orm_columns
Revises: 0009_ensure_tenant_rls
Create Date: 2026-08-10

Idempotent additive migration for local SQLite DBs created via create_all and
any Postgres environment that skipped intermediate revisions. Ensures columns
required by the current ORM exist without destructive rebuilds.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.migration_helpers import (
    add_column_if_missing,
    create_index_if_missing,
    create_table_if_missing,
)

revision: str = "0010_reconcile_orm_columns"
down_revision: Union[str, None] = "0009_ensure_tenant_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sessions — enterprise device tracking (0005 + ORM)
    add_column_if_missing(
        "sessions",
        sa.Column("device_label", sa.String(length=120), nullable=True),
    )
    add_column_if_missing(
        "sessions",
        sa.Column(
            "device_trusted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Connections — scheduled sync (0006)
    add_column_if_missing(
        "connections",
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    create_index_if_missing(
        "ix_connections_next_sync_at",
        "connections",
        ["next_sync_at"],
    )

    # OAuth login states (0005) — create_all may have created this already
    bind = op.get_bind()
    from sqlalchemy.dialects import postgresql

    uuid_type = (
        postgresql.UUID(as_uuid=True)
        if bind.dialect.name == "postgresql"
        else sa.String(36)
    )

    create_table_if_missing(
        "oauth_login_states",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("workos_organization_id", sa.String(length=128), nullable=True),
        sa.Column("invite_token", sa.String(length=128), nullable=True),
        sa.Column(
            "remember_device",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("return_path", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("state", name="uq_oauth_login_states_state"),
    )
    create_index_if_missing(
        "ix_oauth_login_states_expires",
        "oauth_login_states",
        ["expires_at"],
    )


def downgrade() -> None:
    # Non-destructive downgrade: leave columns in place (safe for prod rollbacks
    # that only need code revert). Index can be dropped.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {ix["name"] for ix in inspector.get_indexes("connections")} if "connections" in inspector.get_table_names() else set()
    if "ix_connections_next_sync_at" in indexes:
        op.drop_index("ix_connections_next_sync_at", table_name="connections")
