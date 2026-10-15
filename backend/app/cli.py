"""Supply CLI — database init, migrations helper, sandbox seed, user bootstrap."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.database import Base, SessionLocal, engine
from app.identity.orgs import create_organization
from app.models import User


def _alembic_config():
    from alembic.config import Config

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    return cfg


def cmd_init_db(_: argparse.Namespace) -> None:
    """Dev helper: create missing tables only. Prefer ``ensure-schema`` / Alembic."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("Schema created via create_all (dev only; prefer: python -m app.cli ensure-schema)")


def cmd_ensure_schema(args: argparse.Namespace) -> None:
    """Apply Alembic migrations to head.

    Legacy local SQLite databases created with ``create_all`` (no alembic_version)
    are stamped at ``0009_ensure_tenant_rls`` then upgraded so additive revisions
    (e.g. ``0010`` adding ``connections.next_sync_at``) apply without a destructive
    rebuild from revision ``0002``.
    """
    import sqlalchemy as sa
    from alembic import command

    cfg = _alembic_config()
    inspector = sa.inspect(engine)
    tables = set(inspector.get_table_names())
    has_version = "alembic_version" in tables
    has_app_schema = "organizations" in tables

    if not has_version and has_app_schema:
        print(
            "Detected legacy create_all schema without alembic_version; "
            "stamping 0009_ensure_tenant_rls then upgrading…"
        )
        command.stamp(cfg, "0009_ensure_tenant_rls")
    elif not has_version and not has_app_schema:
        print("Empty database — running alembic upgrade head…")
    else:
        print("Running alembic upgrade head…")

    command.upgrade(cfg, "head")
    print("Schema at alembic head.")


def cmd_seed_sandbox(args: argparse.Namespace) -> None:
    from app.seed.synthetic import seed_sandbox

    db = SessionLocal()
    try:
        result = seed_sandbox(db, owner_email=args.email, org_name=args.org)
        print(result)
    finally:
        db.close()


def cmd_create_user(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email.lower()).first()
        if existing:
            print(f"User already exists: {existing.id}")
            user = existing
        else:
            user = User(email=args.email.lower(), full_name=args.name, is_active=True)
            db.add(user)
            db.flush()
            print(f"Created user {user.id}")

        if args.org:
            org, membership = create_organization(db, name=args.org, owner=user)
            print(f"Created org {org.slug} ({org.id}) membership={membership.role_slug}")
        db.commit()
    finally:
        db.close()


def cmd_force_disruption(args: argparse.Namespace) -> None:
    """Overlay the demo disruption scenario onto an existing organization."""
    from uuid import UUID

    from app.models import Organization
    from app.seed.synthetic import apply_disruption_scenario
    from sqlalchemy import select

    db = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.id == UUID(args.org_id)))
        if org is None:
            org = db.scalar(select(Organization).where(Organization.name == args.org))
        if org is None:
            raise SystemExit(f"Organization not found: {args.org_id or args.org}")
        result = apply_disruption_scenario(db, organization_id=org.id)
        db.commit()
        print({"organization_id": str(org.id), **result})
    finally:
        db.close()


def cmd_provision_yc_demo(args):
    from app.seed.yc_demo import provision
    with SessionLocal() as db:
        print(provision(db, args.email))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="supply")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="Create tables via create_all (dev only)")
    p_init.set_defaults(func=cmd_init_db)

    p_ensure = sub.add_parser(
        "ensure-schema",
        help="Apply Alembic migrations (stamps legacy create_all DBs safely)",
    )
    p_ensure.set_defaults(func=cmd_ensure_schema)

    p_seed = sub.add_parser("seed-sandbox", help="Seed optional demo org (never for prod)")
    p_seed.add_argument("--email", default="demo@example.com")
    p_seed.add_argument("--org", default="Demo Manufacturing Co")
    p_seed.set_defaults(func=cmd_seed_sandbox)

    p_dx = sub.add_parser(
        "force-disruption",
        help="Overlay supplier-delay disruption on an existing demo org",
    )
    p_dx.add_argument("--org-id", default="", help="Organization UUID")
    p_dx.add_argument("--org", default="Demo Manufacturing Co", help="Organization name fallback")
    p_dx.set_defaults(func=cmd_force_disruption)

    p_user = sub.add_parser("create-user", help="Create a user (WorkOS will link on login)")
    p_user.add_argument("email")
    p_user.add_argument("--name", default="User")
    p_user.add_argument("--org", default=None, help="Also create an organization as owner")
    p_user.set_defaults(func=cmd_create_user)

    p_demo = sub.add_parser("provision-yc-demo", help="Create fictional demo workspace for an existing verified WorkOS user")
    p_demo.add_argument("--email", required=True)
    p_demo.set_defaults(func=cmd_provision_yc_demo)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
