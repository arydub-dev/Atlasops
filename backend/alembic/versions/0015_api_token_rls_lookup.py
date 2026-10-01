"""API token lookup function for FORCE RLS authentication.

Revision ID: 0015_api_token_rls_lookup
Revises: 0014_salesforce_sync_hardening
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0015_api_token_rls_lookup"
down_revision: Union[str, None] = "0014_salesforce_sync_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_lookup_api_token_by_hash(p_hash text)
        RETURNS TABLE (
            id uuid,
            organization_id uuid,
            created_by_user_id uuid,
            scopes jsonb,
            expires_at timestamptz,
            revoked_at timestamptz
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public
        STABLE
        AS $$
          SELECT id, organization_id, created_by_user_id, scopes, expires_at, revoked_at
          FROM api_tokens
          WHERE token_hash = p_hash
          LIMIT 1;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION app_lookup_api_token_by_hash(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION app_lookup_api_token_by_hash(text) TO PUBLIC")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP FUNCTION IF EXISTS app_lookup_api_token_by_hash(text)")
