"""Ensure FORCE RLS + tenant_isolation on every TENANT_TABLES entry.

Revision ID: 0009_ensure_tenant_rls
Revises: 0008_enterprise_ops
Create Date: 2026-07-30

0002 applies RLS for whatever tables exist in ``TENANT_TABLES`` at migrate time.
Additive revisions 0006–0008 may create tenant tables without enabling RLS when
they run against a database that already applied an older 0002. This revision
idempotently enables FORCE RLS and recreates the standard policy for every
table currently listed in ``TENANT_TABLES``.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.migration_helpers import table_exists
from app.models import TENANT_TABLES
from app.tenancy.rls import ENABLE_RLS_SQL, FORCE_RLS_SQL, RLS_POLICY_SQL

revision: str = "0009_ensure_tenant_rls"
down_revision: Union[str, None] = "0008_enterprise_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in TENANT_TABLES:
        if not table_exists(table):
            continue
        op.execute(sa.text(ENABLE_RLS_SQL.format(table=table)))
        op.execute(sa.text(FORCE_RLS_SQL.format(table=table)))
        op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
        op.execute(sa.text(RLS_POLICY_SQL.format(table=table)))


def downgrade() -> None:
    """No-op: removing RLS from tenant tables is unsafe for multi-tenant DBs."""
    return
