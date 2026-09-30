"""PostgreSQL RLS helpers — set session GUC for org isolation.

``SET LOCAL`` / ``set_config(..., is_local=true)`` is transaction-scoped.
Auth commits mid-request (sliding session / token last_used), which ends the
transaction and clears the GUC. We therefore:

1. Store the intended org id on ``session.info["rls_organization_id"]``.
2. Apply ``SET LOCAL`` immediately when binding.
3. Re-apply on every new transaction via SQLAlchemy ``after_begin``.

This keeps the GUC on the same connection/transaction used by subsequent ORM
queries without using session-level GUCs (which would leak across pooled
connections).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import event, text
from sqlalchemy.orm import Session

ORG_GUC = "app.current_org_id"
_SESSION_INFO_KEY = "rls_organization_id"


def _is_postgres(bind) -> bool:
    dialect = getattr(getattr(bind, "dialect", None), "name", "")
    return dialect == "postgresql"


def _apply_guc(connection, organization_id: UUID | None) -> None:
    value = str(organization_id) if organization_id else ""
    connection.execute(
        text("SELECT set_config(:key, :value, true)"),
        {"key": ORG_GUC, "value": value},
    )


def set_session_org(db: Session, organization_id: UUID | None) -> None:
    """Bind the current DB session to an organization for RLS.

    Uses SET LOCAL so the value is transaction-scoped. Also records the org on
    ``session.info`` so ``after_begin`` can re-apply after commit/rollback.
    No-op on non-PostgreSQL dialects (SQLite tests rely on app-level filters).
    """
    bind = db.get_bind()
    if not _is_postgres(bind):
        return

    if organization_id is None:
        db.info.pop(_SESSION_INFO_KEY, None)
    else:
        db.info[_SESSION_INFO_KEY] = organization_id

    # Ensure a transaction is open so SET LOCAL attaches to it.
    _apply_guc(db.connection(), organization_id)


def clear_session_org(db: Session) -> None:
    set_session_org(db, None)


@event.listens_for(Session, "after_begin")
def _rebind_rls_guc_after_begin(session: Session, transaction, connection) -> None:
    """Re-apply tenant GUC whenever a new transaction starts on this Session."""
    org_id = session.info.get(_SESSION_INFO_KEY)
    if org_id is None:
        return
    if not _is_postgres(connection):
        return
    _apply_guc(connection, org_id)


# Applied in Alembic migrations; kept here as the canonical policy body.
RLS_POLICY_SQL = """
CREATE POLICY tenant_isolation ON {table}
  AS PERMISSIVE
  FOR ALL
  TO PUBLIC
  USING (
    organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
  )
  WITH CHECK (
    organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
  );
"""

ENABLE_RLS_SQL = "ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"
FORCE_RLS_SQL = "ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"
