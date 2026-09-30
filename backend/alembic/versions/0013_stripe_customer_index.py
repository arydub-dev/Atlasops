"""Stripe customer→org index for FORCE RLS-safe webhook lookups.

Revision ID: 0013_stripe_customer_index
Revises: 0012_stripe_customer_lookup
Create Date: 2026-08-12

Under FORCE RLS, a SECURITY DEFINER function owned by the application role
still evaluates RLS policies (GUCs from the caller apply). App roles cannot
``SET LOCAL row_security = off`` without BYPASSRLS.

Solution (least privilege, no app-role BYPASSRLS):
1. ``stripe_customer_index`` — system mapping table with **no RLS**.
2. Trigger on ``billing_accounts`` maintains the index when tenant-scoped
   writes already satisfy RLS.
3. ``app_lookup_org_by_stripe_customer`` reads **only** that index
   (SECURITY DEFINER + fixed ``search_path``; no arbitrary SQL).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0013_stripe_customer_index"
down_revision: Union[str, None] = "0012_stripe_customer_lookup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stripe_customer_index (
            stripe_customer_id varchar(128) PRIMARY KEY,
            organization_id uuid NOT NULL
                REFERENCES organizations(id) ON DELETE CASCADE,
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_stripe_customer_index_org
            ON stripe_customer_index (organization_id);
        """
    )
    # Explicit: this is a system index, not a tenant table — never enable RLS.
    op.execute("ALTER TABLE stripe_customer_index DISABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_sync_stripe_customer_index()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = public
        AS $$
        BEGIN
          IF NEW.stripe_customer_id IS NOT NULL
             AND btrim(NEW.stripe_customer_id) <> '' THEN
            INSERT INTO stripe_customer_index (
                stripe_customer_id, organization_id, updated_at
            )
            VALUES (
                btrim(NEW.stripe_customer_id), NEW.organization_id, now()
            )
            ON CONFLICT (stripe_customer_id) DO UPDATE
              SET organization_id = EXCLUDED.organization_id,
                  updated_at = now();
          END IF;

          IF TG_OP = 'UPDATE'
             AND OLD.stripe_customer_id IS DISTINCT FROM NEW.stripe_customer_id
             AND OLD.stripe_customer_id IS NOT NULL
             AND btrim(OLD.stripe_customer_id) <> '' THEN
            DELETE FROM stripe_customer_index
             WHERE stripe_customer_id = btrim(OLD.stripe_customer_id)
               AND organization_id = OLD.organization_id;
          END IF;

          RETURN NEW;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS billing_accounts_stripe_customer_index ON billing_accounts")
    op.execute(
        """
        CREATE TRIGGER billing_accounts_stripe_customer_index
        AFTER INSERT OR UPDATE OF stripe_customer_id, organization_id
        ON billing_accounts
        FOR EACH ROW
        EXECUTE FUNCTION trg_sync_stripe_customer_index();
        """
    )

    # Narrow lookup: only customer_id in, only organization_id out.
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
          FROM stripe_customer_index
          WHERE stripe_customer_id = NULLIF(btrim(p_customer_id), '')
          LIMIT 1;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION app_lookup_org_by_stripe_customer(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION app_lookup_org_by_stripe_customer(text) TO PUBLIC")

    # Best-effort backfill. Requires ability to read all billing_accounts
    # (superuser / BYPASSRLS). App-role migrations skip silently; trigger
    # backfills on subsequent tenant-scoped updates.
    op.execute(
        """
        DO $$
        BEGIN
          BEGIN
            EXECUTE 'SET LOCAL row_security = off';
            INSERT INTO stripe_customer_index (stripe_customer_id, organization_id, updated_at)
            SELECT btrim(stripe_customer_id), organization_id, now()
              FROM billing_accounts
             WHERE stripe_customer_id IS NOT NULL
               AND btrim(stripe_customer_id) <> ''
            ON CONFLICT (stripe_customer_id) DO UPDATE
              SET organization_id = EXCLUDED.organization_id,
                  updated_at = now();
          EXCEPTION WHEN insufficient_privilege OR others THEN
            RAISE NOTICE 'stripe_customer_index backfill skipped (need privileged migrator)';
          END;
        END $$;
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS billing_accounts_stripe_customer_index ON billing_accounts")
    op.execute("DROP FUNCTION IF EXISTS trg_sync_stripe_customer_index()")
    # Restore 0012 body (broken under FORCE RLS for app-owned definer) for rollback symmetry.
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
    op.execute("DROP TABLE IF EXISTS stripe_customer_index")
