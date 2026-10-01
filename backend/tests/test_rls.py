"""PostgreSQL RLS isolation tests — skipped on SQLite.

Requires DATABASE_URL pointing at Postgres with Alembic 0002 policies applied.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.database import engine
from app.models import TENANT_TABLES
from app.tenancy.rls import set_session_org


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


pytestmark = pytest.mark.skipif(
    not _is_postgres(),
    reason="RLS tests require PostgreSQL (run in CI postgres job)",
)


def test_rls_policies_exist(db):
    rows = db.execute(
        text(
            """
            SELECT tablename, policyname
            FROM pg_policies
            WHERE schemaname = 'public'
            """
        )
    ).all()
    tables_with_policy = {r[0] for r in rows}
    for table in TENANT_TABLES:
        assert table in tables_with_policy, f"Missing RLS policy on {table}"


def test_rls_blocks_without_guc(db, org_a, shipment_a):
    """With RLS forced, a session without app.current_org_id sees no tenant rows."""
    org, _ = org_a
    # Clear GUC
    db.execute(text("SELECT set_config('app.current_org_id', '', true)"))
    count = db.execute(text("SELECT count(*) FROM shipments")).scalar()
    assert count == 0

    set_session_org(db, org.id)
    count = db.execute(text("SELECT count(*) FROM shipments")).scalar()
    assert count >= 1


def test_app_role_does_not_bypass_rls(db):
    """Application DB role must never have BYPASSRLS (defense-in-depth gate)."""
    row = db.execute(
        text(
            """
            SELECT rolname, rolbypassrls, rolsuper
            FROM pg_roles
            WHERE oid = (SELECT current_user::regrole)
            """
        )
    ).mappings().one()
    assert row["rolbypassrls"] is False
    assert row["rolsuper"] is False
