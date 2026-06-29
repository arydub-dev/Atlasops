"""SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _normalize_db_url(url: str) -> str:
    """Ensure Postgres URLs use the psycopg (v3) driver.

    Managed hosts (Render, Railway, Heroku, etc.) hand out connection strings
    like ``postgres://`` or ``postgresql://``. SQLAlchemy maps the bare
    ``postgresql://`` scheme to psycopg2, which is not installed — this project
    uses psycopg v3. Rewrite the scheme so deployments work out of the box.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_db_url(settings.DATABASE_URL)

# Vercel (and most FaaS platforms) set this at runtime. Serverless functions are
# short-lived and scale horizontally, so a per-instance connection pool would
# quickly exhaust the database's connection limit.
_on_serverless = bool(os.environ.get("VERCEL"))

_is_sqlite = DATABASE_URL.startswith("sqlite")
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if _is_sqlite:
    # SQLite (used for tests/smoke checks) doesn't accept server-style pool sizing.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
elif _on_serverless:
    # No pooling on serverless; disable psycopg prepared statements so the
    # engine also works through transaction-mode poolers (e.g. PgBouncer).
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {"prepare_threshold": None}
else:
    _engine_kwargs.update(pool_size=10, max_overflow=20)

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
