"""Enterprise auth: OAuth login state + session device label.

Revision ID: 0005_auth_enterprise_sessions
Revises: 0004_stripe_events_idempotency
Create Date: 2026-07-25
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_auth_enterprise_sessions"
down_revision: Union[str, None] = "0004_stripe_events_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.core.migration_helpers import (
        add_column_if_missing,
        create_index_if_missing,
        create_table_if_missing,
        table_exists,
    )

    bind = op.get_bind()
    uuid_type = (
        postgresql.UUID(as_uuid=True)
        if bind.dialect.name == "postgresql"
        else sa.String(36)
    )
    add_column_if_missing(
        "sessions",
        sa.Column("device_label", sa.String(length=120), nullable=True),
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
        sa.Column("remember_device", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("return_path", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("state", name="uq_oauth_login_states_state"),
    )
    if table_exists("oauth_login_states"):
        create_index_if_missing(
            "ix_oauth_login_states_expires",
            "oauth_login_states",
            ["expires_at"],
        )


def downgrade() -> None:
    from app.core.migration_helpers import column_exists, table_exists

    if table_exists("oauth_login_states"):
        op.drop_index("ix_oauth_login_states_expires", table_name="oauth_login_states")
        op.drop_table("oauth_login_states")
    if column_exists("sessions", "device_label"):
        op.drop_column("sessions", "device_label")
