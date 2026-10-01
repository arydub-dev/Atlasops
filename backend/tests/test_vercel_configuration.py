"""Serverless database connection selection must not bypass the pooler."""
from app.core.config import Settings


def test_marketplace_prefers_pooled_database(monkeypatch):
    for key in ("DATABASE_URL", "DATABASE_URL_UNPOOLED", "POSTGRES_URL", "POSTGRES_URL_NON_POOLING"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("POSTGRES_URL", "postgresql://pooled.example/db")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "postgresql://direct.example/db")
    monkeypatch.setenv("POSTGRES_URL_NON_POOLING", "postgresql://direct2.example/db")
    assert "pooled.example" in Settings(_env_file=None).DATABASE_URL


def test_explicit_runtime_database_takes_precedence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://runtime.example/db")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://pooled.example/db")
    assert "runtime.example" in Settings(_env_file=None).DATABASE_URL
