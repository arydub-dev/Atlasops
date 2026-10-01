"""Salesforce sync hardening: import job states + supplier upsert index.

Revision ID: 0014_salesforce_sync_hardening
Revises: 0013_stripe_customer_index
Create Date: 2026-08-18

Adds ``queued`` / ``retrying`` to ``import_status`` so ARQ jobs can be tracked
before the worker starts and during bounded retries.

Adds a partial unique index on ``suppliers (organization_id, external_id)`` so
connector retries cannot insert duplicate tenant records.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_salesforce_sync_hardening"
down_revision: Union[str, None] = "0013_stripe_customer_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pg_add_enum_value(enum_name: str, value: str) -> None:
    """Add a PostgreSQL enum value if missing (idempotent)."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}' AND e.enumlabel = '{value}'
            ) THEN
                ALTER TYPE {enum_name} ADD VALUE '{value}';
            END IF;
        END$$;
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for value in ("queued", "retrying"):
            _pg_add_enum_value("import_status", value)

    insp = sa.inspect(bind)
    existing = {idx["name"] for idx in insp.get_indexes("suppliers")}
    if "uq_suppliers_org_external_id" not in existing:
        op.create_index(
            "uq_suppliers_org_external_id",
            "suppliers",
            ["organization_id", "external_id"],
            unique=True,
            postgresql_where=sa.text("external_id IS NOT NULL"),
            sqlite_where=sa.text("external_id IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {idx["name"] for idx in insp.get_indexes("suppliers")}
    if "uq_suppliers_org_external_id" in existing:
        op.drop_index("uq_suppliers_org_external_id", table_name="suppliers")
    # PostgreSQL cannot easily remove enum values; leave queued/retrying in place.
