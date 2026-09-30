"""SECURITY DEFINER helper to resolve org from Stripe customer id under FORCE RLS.

Revision ID: 0012_stripe_customer_lookup
Revises: 0011_alert_sim_enums
Create Date: 2026-08-12

``SET LOCAL row_security = off`` requires BYPASSRLS/superuser. App roles subject
to FORCE RLS cannot disable RLS, so invoice/subscription webhooks that only
carry ``customer`` need a privileged lookup function.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0012_stripe_customer_lookup"
down_revision: Union[str, None] = "0011_alert_sim_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_lookup_org_by_stripe_customer(p_customer_id text)
        RETURNS uuid
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public
        STABLE
        AS $$
          SELECT organization_id
          FROM billing_accounts
          WHERE stripe_customer_id = p_customer_id
          LIMIT 1;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION app_lookup_org_by_stripe_customer(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION app_lookup_org_by_stripe_customer(text) TO PUBLIC")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP FUNCTION IF EXISTS app_lookup_org_by_stripe_customer(text)")
