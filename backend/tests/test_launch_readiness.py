"""Regression checks for readiness and honest operational calculations."""
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings, settings
from app.core.startup_checks import assert_worker_heartbeat, validate_settings
from app.services.inventory_logic import days_of_supply


@pytest.mark.parametrize('url', [
    'https://:password@redis.example.com',
    'redis://:password@redis.example.com',
    'rediss://user@redis.example.com',
    'redis://:password@localhost.attacker.example',
    'rediss://:password@redis.example.com?ssl_cert_reqs=none',
])
def test_invalid_or_insecure_redis_config_rejected(url):
    cfg = Settings(ENVIRONMENT='production', REDIS_URL=url)
    assert any('REDIS_URL' in issue for issue in validate_settings(cfg))


@pytest.mark.parametrize('ttl', [-2, -1, 0, 31001])
def test_stale_or_permanent_heartbeat_not_ready(monkeypatch, ttl):
    redis = MagicMock()
    redis.pttl.return_value = ttl
    monkeypatch.setattr('redis.Redis.from_url', lambda *a, **k: redis)
    with pytest.raises(RuntimeError):
        assert_worker_heartbeat('redis://localhost')
    redis.close.assert_called_once()


def test_redis_alive_without_worker_is_not_ready(client, monkeypatch):
    monkeypatch.setattr(settings, 'CONNECTOR_SYNC_INLINE', False)
    monkeypatch.setattr('app.core.startup_checks.ping_redis', lambda _: None)
    def missing(_):
        raise RuntimeError('missing')
    monkeypatch.setattr('app.core.startup_checks.assert_worker_heartbeat', missing)
    response = client.get('/health/ready')
    assert response.status_code == 503
    assert response.json()['detail'] == 'not_ready:worker'


def test_unknown_demand_is_not_infinite_supply():
    assert days_of_supply(100, 0) is None
    assert days_of_supply(100, -1) is None
    assert days_of_supply(2000, 1) == 2000
    assert days_of_supply(0, 1) == 0


@pytest.mark.parametrize('label,seconds', [('Every 15 min',900),('Weekly',604800),('Hourly',3600),('Daily',86400)])
def test_ui_schedule_matches_scheduler(label, seconds):
    from app.connectors.schedule import parse_sync_frequency
    assert parse_sync_frequency(label).total_seconds() == seconds


@pytest.mark.parametrize('label', ['Manual','Real-time','0m','0h','999999d'])
def test_invalid_or_manual_frequency_not_scheduled(label):
    from app.connectors.schedule import parse_sync_frequency
    assert parse_sync_frequency(label) is None
