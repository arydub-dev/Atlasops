"""Command-line utilities for database lifecycle and seeding.

Usage:
    python -m app.cli init-db
    python -m app.cli seed [--if-empty] [--scale demo|full]
    python -m app.cli reset
    python -m app.cli create-user EMAIL NAME ROLE PASSWORD
"""
from __future__ import annotations

import argparse
import sys

from app.core.database import Base, SessionLocal, engine
from app.models import User  # noqa: F401  (ensures models are imported)
from app.models.enums import UserRole


def init_db() -> None:
    import app.models  # noqa: F401  registers all tables

    print("[cli] Creating tables (if not present)...", flush=True)
    Base.metadata.create_all(bind=engine)
    print("[cli] Done.", flush=True)


def drop_db() -> None:
    import app.models  # noqa: F401

    print("[cli] Dropping all tables...", flush=True)
    Base.metadata.drop_all(bind=engine)
    print("[cli] Done.", flush=True)


def seed(if_empty: bool, scale: str) -> None:
    from app.seed import synthetic

    db = SessionLocal()
    try:
        if if_empty and synthetic.is_seeded(db):
            print("[cli] Database already seeded; skipping (--if-empty).", flush=True)
            return
        history = 39 if scale == "full" else 12
        print(f"[cli] Seeding (scale={scale}, history_snapshots={history})...", flush=True)
        counts = synthetic.seed_all(db, inventory_history_snapshots=history)
        print(f"[cli] Seed complete: {counts}", flush=True)
    finally:
        db.close()


def create_user(email: str, name: str, role: str, password: str) -> None:
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            full_name=name,
            role=UserRole(role),
            hashed_password=hash_password(password),
        )
        db.add(user)
        db.commit()
        print(f"[cli] Created user {email} ({role}).", flush=True)
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ATLASOPS backend CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create database tables")
    sub.add_parser("reset", help="Drop and recreate all tables")

    seed_p = sub.add_parser("seed", help="Generate synthetic data")
    seed_p.add_argument("--if-empty", action="store_true", help="Only seed when empty")
    seed_p.add_argument("--scale", choices=["demo", "full"], default="full")

    user_p = sub.add_parser("create-user", help="Create a user")
    user_p.add_argument("email")
    user_p.add_argument("name")
    user_p.add_argument("role", choices=[r.value for r in UserRole])
    user_p.add_argument("password")

    args = parser.parse_args(argv)

    if args.command == "init-db":
        init_db()
    elif args.command == "reset":
        drop_db()
        init_db()
    elif args.command == "seed":
        init_db()
        seed(if_empty=args.if_empty, scale=args.scale)
    elif args.command == "create-user":
        create_user(args.email, args.name, args.role, args.password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
