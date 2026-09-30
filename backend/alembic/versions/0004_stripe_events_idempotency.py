"""Stripe webhook event idempotency table (reversible).

Revision ID: 0004_stripe_events_idempotency
Revises: 0003_shipment_fk_indexes
Create Date: 2026-07-24

Idempotent: 0002 ``create_all`` may already have created ``stripe_events``.
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

revision: str = "0004_stripe_events_idempotency"
down_revision: Union[str, None] = "0003_shipment_fk_indexes"
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
        "stripe_events",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("stripe_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("organization_id", uuid_type, nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("stripe_event_id", name="uq_stripe_events_event_id"),
    )
    create_index_if_missing(
        "ix_stripe_events_processed_at",
        "stripe_events",
        ["processed_at"],
    )


def downgrade() -> None:
    if table_exists("stripe_events"):
        op.drop_index("ix_stripe_events_processed_at", table_name="stripe_events")
        op.drop_table("stripe_events")
