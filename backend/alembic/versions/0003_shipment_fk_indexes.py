"""Reversible indexes for shipment FK filter columns + inventory uniqueness.

Revision ID: 0003_shipment_fk_indexes
Revises: 0002_supply_v2_multitenant
Create Date: 2026-07-24

Idempotent when 0002 ``create_all`` already created matching indexes.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.migration_helpers import create_index_if_missing, index_exists

revision: str = "0003_shipment_fk_indexes"
down_revision: Union[str, None] = "0002_supply_v2_multitenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    create_index_if_missing(
        "ix_shipments_org_supplier",
        "shipments",
        ["organization_id", "supplier_id"],
    )
    create_index_if_missing(
        "ix_shipments_org_warehouse",
        "shipments",
        ["organization_id", "warehouse_id"],
    )
    create_index_if_missing(
        "ix_shipments_org_product",
        "shipments",
        ["organization_id", "product_id"],
    )
    # Partial unique for current inventory lines (Postgres). On SQLite, skip.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_org_wh_product_current
                ON inventory (organization_id, warehouse_id, product_id)
                WHERE is_current IS TRUE
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS uq_inventory_org_wh_product_current"))
    for name in (
        "ix_shipments_org_product",
        "ix_shipments_org_warehouse",
        "ix_shipments_org_supplier",
    ):
        if index_exists("shipments", name):
            op.drop_index(name, table_name="shipments")
