"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    APP_NAME: str = "ATLASOPS"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # --- Database ---
    # Managed Postgres providers inject the connection string under different
    # names (Render: DATABASE_URL; Vercel Postgres: POSTGRES_URL*; Neon:
    # DATABASE_URL_UNPOOLED). Accept the common ones, preferring a direct/
    # non-pooled endpoint which plays nicest with short-lived serverless
    # connections. The scheme is normalized to psycopg in core/database.py.
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://atlasops:atlasops@localhost:5432/atlasops",
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "DATABASE_URL_UNPOOLED",
            "POSTGRES_URL_NON_POOLING",
            "POSTGRES_URL",
        ),
    )

    # --- Auth ---
    JWT_SECRET_KEY: str = "change-me-in-production-please-32chars-min"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # --- CORS ---
    # NoDecode prevents pydantic-settings from JSON-decoding the env value, so we
    # can accept a plain comma-separated string (handled by the validator below).
    CORS_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000"]

    # --- AI ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # --- Seeding ---
    SEED_ON_STARTUP: bool = False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def ai_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
