import pytest
from app.core.config import Settings, settings
from app.core.startup_checks import validate_settings
from test_startup_checks import _secure_kwargs
from test_private_demo_login import demo, login


def test_profile_requires_isolated_staging_credentials():
    errors=validate_settings(Settings(**_secure_kwargs(REVIEWER_DEMO_ONLY=True)))
    assert any("requires ENVIRONMENT=staging" in e for e in errors)
    assert any("Reviewer credentials" in e for e in errors)
    assert any("valid UUIDs" in e for e in errors)


def test_profile_does_not_allow_insecure_inline_mode():
    errors=validate_settings(Settings(**_secure_kwargs(REVIEWER_DEMO_ONLY=True,CONNECTOR_SYNC_INLINE=True)))
    assert any("CONNECTOR_SYNC_INLINE must be false" in e for e in errors)


def test_profile_keeps_tenant_and_role_boundaries(client,demo,org_b,monkeypatch):
    monkeypatch.setattr(settings,'REVIEWER_DEMO_ONLY',True)
    assert login(client).status_code==200
    assert client.get('/api/v1/auth/me').status_code==200
    assert client.get('/api/v1/inventory/items').status_code==200
    assert client.get('/api/v1/inventory/items',headers={'X-Organization-Id':str(org_b[0].id)}).status_code==403
    assert client.post('/api/v1/incidents',json={'title':'Denied to viewer','severity':'high'}).status_code==403
    assert client.post('/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/auth/me').status_code==401


@pytest.mark.parametrize('path',['/auth/continue','/auth/dev-login','/data/sources','/data/demo/reset','/data/sources/00000000-0000-0000-0000-000000000001/sync'])
def test_profile_blocks_external_and_privileged_actions(client,demo,monkeypatch,path):
    monkeypatch.setattr(settings,'REVIEWER_DEMO_ONLY',True)
    assert login(client).status_code==200
    assert client.post('/api/v1'+path,json={}).status_code==403


def test_profile_readiness_requires_redis_and_preserves_normal_worker_check(client,demo,monkeypatch):
    import app.core.startup_checks as checks
    monkeypatch.setattr(settings,'REVIEWER_DEMO_ONLY',True)
    monkeypatch.setattr(settings,'CONNECTOR_SYNC_INLINE',False)
    def unavailable(*args): raise RuntimeError('unavailable')
    monkeypatch.setattr(checks,'ping_redis',unavailable)
    assert client.get('/health/ready').json()['detail']=='not_ready:redis'
    monkeypatch.setattr(checks,'ping_redis',lambda *args:None)
    monkeypatch.setattr(checks,'assert_worker_heartbeat',unavailable)
    result=client.get('/health/ready')
    assert result.status_code==200
    assert result.json()['mode']=='restricted_reviewer_demo'
    monkeypatch.setattr(settings,'REVIEWER_DEMO_ONLY',False)
    assert client.get('/health/ready').json()['detail']=='not_ready:worker'
