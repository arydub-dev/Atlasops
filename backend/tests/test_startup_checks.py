"""Production/staging boot / configuration safety checks."""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.startup_checks import ConfigurationError, assert_safe_to_boot, validate_settings


def _secure_kwargs(**overrides):
    base = dict(
        ENVIRONMENT="production",
        SESSION_SECRET="a-unique-session-secret-value-32ch!!",
        CREDENTIALS_ENCRYPTION_KEY="prod-fernet-or-passphrase-key!!",
        SESSION_COOKIE_SECURE=True,
        WORKOS_COOKIE_PASSWORD="a-unique-workos-cookie-password!!",
        WORKOS_API_KEY="sk_test_workos",
        WORKOS_CLIENT_ID="client_test",
        WORKOS_REDIRECT_URI="https://api.example.com/api/v1/auth/callback",
        FRONTEND_URL="https://app.example.com",
        REDIS_URL="redis://:ci-redis-password@localhost:6379/0",
        DATABASE_URL="postgresql+psycopg://atlasops:atlasops@localhost:5432/atlasops",
        METRICS_TOKEN="metrics-token-value",
        FEATURE_BILLING_ENFORCE=True,
        CSRF_ORIGIN_CHECK=True,
        SEED_ON_STARTUP=False,
        FEATURE_DEMO_SANDBOX=False,
        ALLOW_CREATE_ALL_ON_STARTUP=False,
        CONNECTOR_SYNC_INLINE=False,
        CORS_ORIGINS=["https://app.example.com"],
    )
    base.update(overrides)
    return base


def test_development_allows_default_secrets():
    s = Settings(
        ENVIRONMENT="development",
        SESSION_SECRET="change-me-session-secret-min-32-chars!!",
        CREDENTIALS_ENCRYPTION_KEY="",
        SESSION_COOKIE_SECURE=False,
    )
    assert_safe_to_boot(s)


def test_production_rejects_default_session_secret():
    s = Settings(**_secure_kwargs(SESSION_SECRET="change-me-session-secret-min-32-chars!!"))
    with pytest.raises(ConfigurationError):
        assert_safe_to_boot(s)


def test_production_rejects_missing_encryption_key():
    s = Settings(**_secure_kwargs(CREDENTIALS_ENCRYPTION_KEY=""))
    problems = validate_settings(s)
    assert any("CREDENTIALS_ENCRYPTION_KEY" in p for p in problems)


def test_production_happy_path():
    s = Settings(**_secure_kwargs())
    assert_safe_to_boot(s)


def test_staging_requires_metrics_token():
    s = Settings(**_secure_kwargs(ENVIRONMENT="staging", METRICS_TOKEN=""))
    with pytest.raises(ConfigurationError, match="METRICS_TOKEN"):
        assert_safe_to_boot(s)


def test_staging_happy_path():
    s = Settings(**_secure_kwargs(ENVIRONMENT="staging"))
    assert_safe_to_boot(s)


def test_staging_rejects_inline_sync():
    s = Settings(**_secure_kwargs(ENVIRONMENT="staging", CONNECTOR_SYNC_INLINE=True))
    with pytest.raises(ConfigurationError, match="CONNECTOR_SYNC_INLINE"):
        assert_safe_to_boot(s)


def test_production_requires_billing_enforce():
    s = Settings(**_secure_kwargs(FEATURE_BILLING_ENFORCE=False))
    with pytest.raises(ConfigurationError, match="FEATURE_BILLING_ENFORCE"):
        assert_safe_to_boot(s)


def test_unknown_environment_fail_closed():
    s = Settings(**_secure_kwargs(ENVIRONMENT="prodction"))  # typo
    # Treated as hardened — still needs all secrets (happy path kwargs OK)
    assert_safe_to_boot(s)
    s2 = Settings(**_secure_kwargs(ENVIRONMENT="prodction", METRICS_TOKEN=""))
    with pytest.raises(ConfigurationError):
        assert_safe_to_boot(s2)


def test_staging_requires_csrf():
    s = Settings(**_secure_kwargs(ENVIRONMENT="staging", CSRF_ORIGIN_CHECK=False))
    with pytest.raises(ConfigurationError, match="CSRF_ORIGIN_CHECK"):
        assert_safe_to_boot(s)


def test_production_rejects_unauthenticated_redis():
    s = Settings(**_secure_kwargs(REDIS_URL="redis://localhost:6379/0"))
    with pytest.raises(ConfigurationError, match="REDIS_URL"):
        assert_safe_to_boot(s)


def test_staging_allows_local_redis_without_auth():
    s = Settings(
        **_secure_kwargs(
            ENVIRONMENT="staging",
            REDIS_URL="redis://localhost:6379/0",
        )
    )
    assert_safe_to_boot(s)


def test_worker_role_skips_workos():
    s = Settings(
        DATABASE_URL="postgresql+psycopg://worker@localhost/test",
        ENVIRONMENT="production",
        SESSION_SECRET="a-unique-session-secret-value-32ch!!",
        CREDENTIALS_ENCRYPTION_KEY="prod-fernet-or-passphrase-key!!",
        REDIS_URL="redis://:ci-redis-password@localhost:6379/0",
        SEED_ON_STARTUP=False,
        FEATURE_DEMO_SANDBOX=False,
        ALLOW_CREATE_ALL_ON_STARTUP=False,
        CONNECTOR_SYNC_INLINE=False,
        WORKOS_API_KEY="",
        WORKOS_CLIENT_ID="",
        METRICS_TOKEN="",
        FEATURE_BILLING_ENFORCE=False,
        SESSION_COOKIE_SECURE=False,
    )
    assert_safe_to_boot(s, role="worker")
    with pytest.raises(ConfigurationError):
        assert_safe_to_boot(s, role="api")


@pytest.mark.parametrize('field,value', [
    ('FRONTEND_URL', 'http://app.example.com'),
    ('WORKOS_REDIRECT_URI', 'http://api.example.com/callback'),
    ('FRONTEND_URL', 'https://user:password@app.example.com'),
    ('CORS_ORIGINS', ['http://app.example.com']),
    ('DATABASE_URL', 'sqlite:///production.db'),
])
def test_insecure_production_urls_rejected(field, value):
    with pytest.raises(ConfigurationError, match=field):
        assert_safe_to_boot(Settings(**_secure_kwargs(**{field: value})))
