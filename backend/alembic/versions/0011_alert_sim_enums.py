"""Extend alert_status and simulation_type enums for new lifecycle / scenarios.

Revision ID: 0011_alert_sim_enums
Revises: 0010_reconcile_orm_columns
Create Date: 2026-08-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0011_alert_sim_enums"
down_revision: Union[str, None] = "0010_reconcile_orm_columns"
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
    if bind.dialect.name != "postgresql":
        # SQLite / others store enum labels as strings — no DDL required.
        return
    for value in ("investigating", "dismissed"):
        _pg_add_enum_value("alert_status", value)
    for value in ("supplier_delay", "transportation_disruption"):
        _pg_add_enum_value("simulation_type", value)


def downgrade() -> None:
    # PostgreSQL cannot easily remove enum values; leave in place.
    pass
