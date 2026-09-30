"""Production/staging configuration validation — fail closed on insecure defaults."""
from __future__ import annotations

from urllib.parse import urlsplit

from app.core.config import Settings

_INSECURE_SESSION_SECRETS = {
    "",
    "change-me-session-secret-min-32-chars!!",
    "change-me-in-production-please-32chars-min",
}

_INSECURE_WORKOS_COOKIE = {
    "",
    "change-me-workos-cookie-password-32ch",
}

_DEV_ENVS = frozenset({"development", "dev", "test", "testing"})


class ConfigurationError(RuntimeError):
    """Raised when production settings are unsafe."""


def validate_settings(settings: Settings, *, role: str = "api") -> list[str]:
    """Return configuration problems. Empty = OK.

    ``role``:
      - ``api`` — full public-facing surface checks
      - ``worker`` — subset required to process jobs safely (no WorkOS/Stripe UI)
    """
    problems: list[str] = []
    env = settings.ENVIRONMENT.lower().strip()

    if env in _DEV_ENVS:
        if settings.SEED_ON_STARTUP:
            problems.append("warning: SEED_ON_STARTUP=true is discouraged even in development")
        return problems

    # Unknown environments fail closed (typos must not disable hardening).
    env_label = env or "unknown"

    if settings.SESSION_SECRET in _INSECURE_SESSION_SECRETS or len(settings.SESSION_SECRET) < 32:
        problems.append(
            f"SESSION_SECRET must be a unique secret of at least 32 characters in {env_label}"
        )
    if not settings.CREDENTIALS_ENCRYPTION_KEY:
        problems.append(f"CREDENTIALS_ENCRYPTION_KEY is required in {env_label}")
    if settings.SEED_ON_STARTUP:
        problems.append(f"SEED_ON_STARTUP must be false in {env_label}")
    if settings.FEATURE_DEMO_SANDBOX:
        problems.append(f"FEATURE_DEMO_SANDBOX must be false in {env_label}")
    if settings.ALLOW_CREATE_ALL_ON_STARTUP:
        problems.append(
            f"ALLOW_CREATE_ALL_ON_STARTUP must be false in {env_label} (use Alembic)"
        )
    if settings.CONNECTOR_SYNC_INLINE:
        problems.append(
            f"CONNECTOR_SYNC_INLINE must be false in {env_label} (use the ARQ worker)"
        )
    if not settings.REDIS_URL:
        problems.append(f"REDIS_URL is required in {env_label}")
    else:
        redis_url = settings.REDIS_URL.lower()
        # Require credentials in production always; in other hardened envs when not local.
        has_auth = "@" in redis_url.replace("redis://", "").replace("rediss://", "")
        is_local = "localhost" in redis_url or "127.0.0.1" in redis_url
        if not has_auth and (settings.is_production or not is_local):
            problems.append(
                f"REDIS_URL must include authentication credentials in {env_label} "
                "(e.g. rediss://:password@host:6379/0)"
            )
    if not (settings.DATABASE_URL or "").strip():
        problems.append(f"DATABASE_URL is required in {env_label}")

    if not settings.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        problems.append(f"DATABASE_URL must use PostgreSQL in {env_label}")

    if role == "worker":
        return problems

    # API-only hardened checks
    if not settings.SESSION_COOKIE_SECURE:
        problems.append(f"SESSION_COOKIE_SECURE must be true in {env_label} (HTTPS)")
    if settings.WORKOS_COOKIE_PASSWORD in _INSECURE_WORKOS_COOKIE:
        problems.append(
            f"WORKOS_COOKIE_PASSWORD must be changed from the default in {env_label}"
        )
    if "*" in settings.CORS_ORIGINS:
        problems.append("CORS_ORIGINS must not include '*' when credentials are enabled")
    if not settings.workos_configured:
        problems.append(f"WORKOS_API_KEY and WORKOS_CLIENT_ID are required in {env_label}")
    if settings.STRIPE_SECRET_KEY and not settings.STRIPE_WEBHOOK_SECRET:
        problems.append(
            "STRIPE_WEBHOOK_SECRET is required when STRIPE_SECRET_KEY is set"
        )
    if not settings.METRICS_TOKEN:
        problems.append(f"METRICS_TOKEN is required in {env_label} to protect /metrics")
    if settings.is_production and not settings.FEATURE_BILLING_ENFORCE:
        problems.append(
            "FEATURE_BILLING_ENFORCE must be true in production for paid commercial use"
        )
    # CSRF required for every hardened environment (staging + production).
    if not settings.CSRF_ORIGIN_CHECK:
        problems.append(f"CSRF_ORIGIN_CHECK must be true in {env_label}")
    for name, value in [("FRONTEND_URL", settings.FRONTEND_URL),
                        ("WORKOS_REDIRECT_URI", settings.WORKOS_REDIRECT_URI),
                        *[("CORS_ORIGINS", origin) for origin in settings.CORS_ORIGINS]]:
        try:
            url = urlsplit(value)
            valid = (url.scheme == "https" and bool(url.hostname)
                     and url.hostname not in {"localhost", "127.0.0.1", "::1"}
                     and not url.username and not url.password and not url.fragment)
            if name != "WORKOS_REDIRECT_URI":
                valid = valid and url.path in {"", "/"} and not url.query
            _ = url.port
        except ValueError:
            valid = False
        if not valid:
            problems.append(f"{name} must be a public HTTPS URL without credentials")
    return problems


def assert_safe_to_boot(settings: Settings, *, role: str = "api") -> None:
    """Raise ConfigurationError if hardened-env settings are unsafe."""
    problems = [
        p for p in validate_settings(settings, role=role) if not p.startswith("warning:")
    ]
    if problems:
        joined = "; ".join(problems)
        raise ConfigurationError(f"Refusing to start ({role}): {joined}")


def ping_redis(redis_url: str) -> None:
    """Raise if Redis does not respond to PING (sync; safe for readiness probes)."""
    from redis import Redis

    client = Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        if not client.ping():
            raise RuntimeError("Redis PING returned falsy")
    finally:
        client.close()


def assert_safe_database_role(engine) -> None:
    """Reject PostgreSQL roles that bypass the tenant boundary at runtime."""
    from sqlalchemy import text

    with engine.connect() as connection:
        role = connection.execute(text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )).one()
        if role.rolsuper or role.rolbypassrls:
            raise ConfigurationError("Runtime database role must be NOSUPERUSER NOBYPASSRLS")
