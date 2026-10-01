"""Supply v2 multi-tenant schema rebuild.

Revision ID: 0002_supply_v2_multitenant
Revises: 77ea022a336b
Create Date: 2026-07-24

Greenfield strategy
-------------------
This revision refuses populated or RLS-protected schemas, then DROPS empty existing
tables (legacy v1 integer-PK schema) and recreates the full Supply v2
multi-tenant model from ``app.models``, then enables PostgreSQL RLS +
tenant isolation policies on every table listed in ``TENANT_TABLES``.

Do **not** run this against a database you need to keep. For local/dev
and empty staging, ``alembic upgrade head`` is the intended path.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import TENANT_TABLES
from app.tenancy.rls import ENABLE_RLS_SQL, FORCE_RLS_SQL, RLS_POLICY_SQL

revision: str = "0002_supply_v2_multitenant"
down_revision: Union[str, None] = "77ea022a336b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Legacy v1 tables from 77ea022a336b (drop order respects FKs).
_LEGACY_TABLES = (
    "shipment_events",
    "inventory",
    "shipments",
    "products",
    "warehouses",
    "import_jobs",
    "data_sources",
    "ai_reports",
    "simulations",
    "alerts",
    "risk_assessments",
    "app_settings",
    "audit_logs",
    "suppliers",
    "users",
)


def _drop_legacy(bind) -> None:
    """Drop all public tables (legacy + any partial v2) for a clean rebuild."""
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # Audit every table before the first DROP. Never rely on the historical
    # assumption that no customer data exists. RLS could hide rows from an owner,
    # so protected/partial v2 schemas require an explicit recovery migration.
    if bind.dialect.name == "postgresql":
        protected = bind.execute(sa.text(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=current_schema() AND c.relrowsecurity LIMIT 1"
        )).first()
        if protected:
            raise RuntimeError("Refusing legacy rebuild of a row-security-protected schema")
    for name in sorted(existing - {"alembic_version"}):
        populated = bind.execute(sa.select(sa.literal(1)).select_from(sa.table(name)).limit(1)).first()
        if populated:
            raise RuntimeError("Refusing legacy rebuild: existing data requires a preservation migration")

    # Prefer explicit legacy order, then anything else remaining.
    for name in _LEGACY_TABLES:
        if name in existing:
            op.drop_table(name)
            existing.discard(name)

    # Drop remaining application tables (keep alembic_version).
    for name in list(existing):
        if name == "alembic_version":
            continue
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{name}" CASCADE'))

    # Drop leftover enum types from v1 so recreate is clean on Postgres.
    if bind.dialect.name == "postgresql":
        for enum_name in (
            "alert_type",
            "alert_priority",
            "alert_status",
            "risk_category",
            "risk_level",
            "user_role",
            "shipment_status",
            "warehouse_risk_level",
            "simulation_type",
            "connector_type",
            "connector_status",
            "connector_health",
            "import_status",
        ):
            op.execute(sa.text(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE'))


def upgrade() -> None:
    bind = op.get_bind()
    _drop_legacy(bind)

    # Create all Supply v2 tables from current metadata.
    from app.core.database import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=bind)

    if bind.dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(sa.text(ENABLE_RLS_SQL.format(table=table)))
            op.execute(sa.text(FORCE_RLS_SQL.format(table=table)))
            # Drop policy if re-run partially, then create.
            op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
            op.execute(sa.text(RLS_POLICY_SQL.format(table=table)))


def downgrade() -> None:
    """Downgrade is intentionally destructive — drops v2 schema only.

    Re-applying 77ea022a336b is required to restore the legacy schema.
    """
    bind = op.get_bind()
    from app.core.database import Base
    import app.models  # noqa: F401

    if bind.dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))

    Base.metadata.drop_all(bind=bind)
