"""SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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

_is_sqlite = DATABASE_URL.startswith("sqlite")
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if _is_sqlite:
    # SQLite (used for tests/smoke checks) doesn't accept server-style pool sizing.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
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
