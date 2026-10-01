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
    LEAD_CAPTURE_ENABLED: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://atlasops:atlasops@localhost:5432/atlasops",
        validation_alias=AliasChoices(
            "DATABASE_URL",
            # Prefer the pooled connection when Marketplace supplies both.
            "POSTGRES_URL",
            "DATABASE_URL_UNPOOLED",
            "POSTGRES_URL_NON_POOLING",
        ),
    )

    # --- Sessions / cookies (opaque server-managed; not JWT) ---
    SESSION_SECRET: str = "change-me-session-secret-min-32-chars!!"
    SESSION_COOKIE_NAME: str = "supply_session"
    SESSION_TTL_HOURS: int = 12  # absolute TTL without "remember device"
    SESSION_REMEMBER_TTL_HOURS: int = 720  # 30 days when remember_device
    SESSION_IDLE_MINUTES: int = 60  # revoke after idle; remembered devices use 2x
    SESSION_SLIDING_ENABLED: bool = True  # extend expiry on activity
    SESSION_COOKIE_SECURE: bool = False  # True in production
    MAX_CONCURRENT_SESSIONS: int = 10

    # --- Credential encryption (Fernet key or passphrase) ---
    CREDENTIALS_ENCRYPTION_KEY: str = ""

    # --- WorkOS ---
    WORKOS_API_KEY: str = ""
    WORKOS_CLIENT_ID: str = ""
    WORKOS_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"
    WORKOS_COOKIE_PASSWORD: str = "change-me-workos-cookie-password-32ch"

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER_MONTHLY: str = ""
    STRIPE_PRICE_STARTER_ANNUAL: str = ""
    STRIPE_PRICE_PROFESSIONAL_MONTHLY: str = ""
    STRIPE_PRICE_PROFESSIONAL_ANNUAL: str = ""
    STRIPE_PRICE_ENTERPRISE_MONTHLY: str = ""
    STRIPE_PRICE_AI_CREDIT: str = ""

    # --- Redis / workers ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- CORS ---
    CORS_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000"]

    # --- AI ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_TIMEOUT_SECONDS: float = Field(default=20, gt=0, le=60)
    AI_MAX_OUTPUT_TOKENS: int = Field(default=1200, ge=64, le=4096)
    AI_MAX_CONTEXT_CHARS: int = Field(default=40000, ge=1000, le=100000)

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 120
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20
    AI_RATE_LIMIT_PER_MINUTE: int = 30
    EXPORT_RATE_LIMIT_PER_MINUTE: int = 20
    UPLOAD_RATE_LIMIT_PER_MINUTE: int = 30
    # In hardened envs, auth rate limiting fails closed if Redis is down.
    RATE_LIMIT_AUTH_FAIL_CLOSED: bool = True
    TRUST_PROXY: bool = False  # only trust X-Forwarded-For when behind a known proxy

    # --- Feature flags ---
    FEATURE_BILLING_ENFORCE: bool = False
    FEATURE_DEMO_SANDBOX: bool = False
    SEED_ON_STARTUP: bool = False  # never true in production
    ALLOW_CREATE_ALL_ON_STARTUP: bool = True  # False in production — use Alembic
    # Run connector sync inside the HTTP request (tests / emergency only).
    CONNECTOR_SYNC_INLINE: bool = False

    # --- Third-party integrations (optional; no-op when unset) ---
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""  # e.g. ATLASOPS <ops@notifications.example.com>
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.05
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://us.i.posthog.com"
    S3_BUCKET: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""  # R2 / MinIO endpoint; empty = AWS
    S3_REGION: str = "auto"
    FLAGSMITH_ENVIRONMENT_KEY: str = ""
    FLAGSMITH_API_URL: str = "https://edge.api.flagsmith.com/api/v1"
    INTERCOM_APP_ID: str = ""
    MAPBOX_TOKEN: str = ""
    MEILISEARCH_URL: str = ""
    MEILISEARCH_KEY: str = ""
    TERMLY_WEBSITE_UUID: str = ""

    # --- Observability ---
    METRICS_TOKEN: str = ""  # if set (or in production), /metrics requires this bearer token
    ENABLE_API_DOCS: bool | None = None  # None = auto (on in non-prod)

    # --- CSRF (cookie session Origin/Referer check) ---
    CSRF_ORIGIN_CHECK: bool = False  # true in production via compose / env

    # --- Connectors ---
    UPS_CLIENT_ID: str = ""
    UPS_CLIENT_SECRET: str = ""
    UPS_BASE_URL: str = "https://onlinetools.ups.com"

    # Legacy (removed from auth path; kept so old env files don't crash)
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    SEED_TOKEN: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_postgres_driver(cls, value):
        if isinstance(value, str):
            for prefix in ("postgres://", "postgresql://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def ai_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def workos_configured(self) -> bool:
        return bool(self.WORKOS_API_KEY and self.WORKOS_CLIENT_ID)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def requires_secure_boot(self) -> bool:
        """Any non-development/test environment fails closed on insecure configuration.

        Unknown environment names (typos) are treated as hardened — never as open.
        """
        return self.ENVIRONMENT.lower().strip() not in {
            "development",
            "dev",
            "test",
            "testing",
        }

    @property
    def api_docs_enabled(self) -> bool:
        if self.ENABLE_API_DOCS is not None:
            return self.ENABLE_API_DOCS
        return not self.requires_secure_boot


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
