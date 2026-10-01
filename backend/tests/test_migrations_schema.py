"""Schema migration / ensure-schema regression tests."""
from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text


def _alembic_cfg() -> Config:
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    return cfg


def test_alembic_upgrade_empty_sqlite(tmp_path, monkeypatch):
    """Empty SQLite DB can be migrated to head."""
    from app.core.config import settings

    db_path = tmp_path / "empty.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)

    command.upgrade(_alembic_cfg(), "head")

    engine = create_engine(url)
    insp = sa.inspect(engine)
    tables = set(insp.get_table_names())
    assert "organizations" in tables
    assert "connections" in tables
    assert "alembic_version" in tables
    cols = {c["name"] for c in insp.get_columns("connections")}
    assert "next_sync_at" in cols
    sess_cols = {c["name"] for c in insp.get_columns("sessions")}
    assert "device_label" in sess_cols
    with engine.connect() as conn:
        ver = conn.execute(text("select version_num from alembic_version")).scalar()
    assert ver == ScriptDirectory.from_config(_alembic_cfg()).get_current_head()


def test_stamp_and_upgrade_legacy_db(tmp_path, monkeypatch):
    """Legacy create_all DB can be stamped then upgraded without destructive rebuild."""
    from app.core.config import settings
    from app.core.database import Base
    import app.models  # noqa: F401

    db_path = tmp_path / "legacy.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)

    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)

    cfg = _alembic_cfg()
    command.stamp(cfg, "0009_ensure_tenant_rls")
    command.upgrade(cfg, "head")

    cols = {c["name"] for c in sa.inspect(engine).get_columns("connections")}
    assert "next_sync_at" in cols
    with engine.connect() as conn:
        ver = conn.execute(text("select version_num from alembic_version")).scalar()
    assert ver == ScriptDirectory.from_config(_alembic_cfg()).get_current_head()
