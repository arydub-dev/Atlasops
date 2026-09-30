"""Pilot re-audit: permission boundaries, provider failures and error telemetry."""
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services import ai_advisor, ai_orchestration
from app.services.ai_providers import OpenAIProvider
from app.core import telemetry


def test_network_permission_does_not_unlock_mission_context(monkeypatch):
    monkeypatch.setattr(ai_orchestration, 'get_tenant', lambda: SimpleNamespace(
        organization_id=uuid4(), permissions={'ai.chat', 'network.read'}))
    monkeypatch.setattr(ai_advisor, 'build_context', lambda _: {})
    timeline = MagicMock()
    graph = MagicMock()
    monkeypatch.setattr(ai_orchestration.timeline, 'global_timeline', timeline)
    monkeypatch.setattr(ai_orchestration.graph, 'graph_stats', graph)
    context = ai_orchestration.build_orchestrated_context(None, 'mission summary', 'mission_summary')
    assert 'timeline' not in context
    timeline.assert_not_called()
    graph.assert_not_called()


@pytest.mark.parametrize('output', [None, '', '   ', 42])
def test_invalid_provider_output_is_rejected(monkeypatch, output):
    import openai
    factory = MagicMock()
    factory.return_value.chat.completions.create.return_value.choices = [SimpleNamespace(message=SimpleNamespace(content=output))]
    monkeypatch.setattr(openai, 'OpenAI', factory)
    with pytest.raises(ValueError, match='no usable text'):
        OpenAIProvider().answer('Status?', {})
    factory.return_value.close.assert_called_once()


@pytest.mark.parametrize('error', [TimeoutError, ConnectionError, ValueError, IndexError])
def test_provider_failures_fall_back_without_exception_details(monkeypatch, error):
    from app.services import ai_providers
    provider = MagicMock(name='provider')
    provider.answer.side_effect = error('sensitive-provider-response')
    monkeypatch.setattr(ai_providers, 'get_ai_provider', lambda: provider)
    text, model, _ = ai_advisor.answer(None, 'Status?', context={})
    assert model == 'local-engine'
    assert 'sensitive-provider-response' not in text
    assert text.strip()


def test_error_requests_counted_and_ids_sanitized(monkeypatch):
    count = MagicMock()
    monkeypatch.setattr(telemetry, 'REQUEST_COUNT', count)
    app = FastAPI()
    telemetry.install_request_id_middleware(app)
    @app.get('/broken')
    def broken():
        raise RuntimeError('test-only-failure')
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/broken').status_code == 500
    count.labels.assert_called_with('GET', '/broken', '500')


def test_request_id_length_is_bounded(client):
    response = client.get('/health/live', headers={'X-Request-ID': 'x' * 1000})
    assert len(response.headers['X-Request-ID']) == 36
    response = client.get('/health/live', headers={'X-Request-ID': 'pilot-123'})
    assert response.headers['X-Request-ID'] == 'pilot-123'



def test_hardened_upload_never_acknowledges_missing_bytes(monkeypatch):
    from app.services import documents
    from app.core.config import settings
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'production')
    monkeypatch.setattr(documents.storage, 'upload_bytes', lambda **_: None)
    db = MagicMock()
    db.scalar.return_value = None
    with pytest.raises(documents.DocumentStorageUnavailable):
        documents.upload_document(db, uuid4(), entity_type='shipment', entity_id=uuid4(),
                                  filename='bill.pdf', content=b'%PDF-test')
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_connectors_validate_final_urls_before_sending_tokens():
    from app.connectors.ups import UPSConnector
    from app.connectors.dynamics_bc import DynamicsBCConnector
    from app.connectors.ssrf import SSRFError
    ups = UPSConnector(organization_id=uuid4(), config={'track_url': 'https://127.0.0.1/private'})
    ups._access_token = 'must-not-leave-process'
    with pytest.raises(SSRFError):
        await ups._track('1Z123')
    dynamics = DynamicsBCConnector(organization_id=uuid4())
    dynamics._access_token = 'must-not-leave-process'
    with pytest.raises(SSRFError):
        await dynamics._request('GET', 'https://169.254.169.254/metadata')


@pytest.mark.asyncio
@pytest.mark.parametrize('connector_name', ['ups', 'dynamics'])
async def test_connector_errors_do_not_echo_provider_secrets(monkeypatch, connector_name):
    import httpx
    from app.connectors.ups import UPSConnector
    from app.connectors.dynamics_bc import DynamicsBCConnector
    from app.connectors.base import ConnectorError
    transport = httpx.MockTransport(lambda _: httpx.Response(401, text='secret-provider-token'))
    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=transport, **kw))
    cls = UPSConnector if connector_name == 'ups' else DynamicsBCConnector
    connector = cls(organization_id=uuid4(), credentials={'client_id': 'test', 'client_secret': 'test', 'tenant_id': 'test'})
    with pytest.raises(ConnectorError) as err:
        await connector.authenticate()
    assert 'secret-provider-token' not in str(err.value)


def test_sentry_removes_credentials_and_customer_payloads():
    import json
    from app.integrations.sentry_setup import scrub_event
    event = {'request': {'url': 'https://user:secret@example.com/api?token=secret',
                         'data': {'secret': 'secret'}, 'headers': {'Authorization': 'secret'},
                         'cookies': 'secret', 'query_string': 'secret'},
             'extra': {'secret': 'secret'}, 'breadcrumbs': [{'message': 'secret'}],
             'user': {'email': 'secret'}, 'exception': {'values': [{'type': 'ValueError',
              'value': 'secret', 'stacktrace': {'frames': [{'function': 'safe_name', 'vars': {'token': 'secret'}}]}}]}}
    result = scrub_event(event, None)
    assert 'secret' not in json.dumps(result)
    assert result['exception']['values'][0]['type'] == 'ValueError'


@pytest.mark.asyncio
async def test_dynamics_follows_pages_and_rejects_cycles(monkeypatch):
    from unittest.mock import AsyncMock
    from app.connectors.dynamics_bc import DynamicsBCConnector
    from app.connectors.base import ConnectorError
    connector = DynamicsBCConnector(organization_id=uuid4())
    request = AsyncMock(side_effect=[{'value':[{'id':'one'}], '@odata.nextLink':'https://api.businesscentral.dynamics.com/next'},
                                    {'value':[{'id':'two'}]}])
    monkeypatch.setattr(connector, '_request', request)
    assert await connector._collection('/items', {'$top':'200'}) == [{'id':'one'},{'id':'two'}]
    assert request.call_args.kwargs['params'] is None
    request.side_effect = None
    request.return_value = {'value':[], '@odata.nextLink':'/items'}
    with pytest.raises(ConnectorError, match='cycle'):
        await connector._collection('/items')


def test_legacy_rebuild_refuses_data_before_dropping_tables():
    import importlib.util
    from pathlib import Path
    from sqlalchemy import create_engine, text
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0002_supply_v2_multitenant.py'
    spec = importlib.util.spec_from_file_location('legacy_rebuild', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users (id integer primary key, email text)'))
        connection.execute(text("INSERT INTO users VALUES (1, 'synthetic@example.invalid')"))
        with pytest.raises(RuntimeError, match='existing data'):
            module._drop_legacy(connection)
        assert connection.scalar(text('SELECT count(*) FROM users')) == 1


def test_ai_provider_failures_are_observable(monkeypatch):
    from app.services import ai_providers
    counter = MagicMock()
    monkeypatch.setattr(telemetry, 'AI_PROVIDER_TOTAL', counter)
    provider = SimpleNamespace(name='openai', answer=MagicMock(side_effect=TimeoutError()))
    monkeypatch.setattr(ai_providers, 'get_ai_provider', lambda: provider)
    _, model, _ = ai_advisor.answer(None, 'Status?', context={})
    assert model == 'local-engine'
    counter.labels.assert_called_once_with('openai', 'fallback')
    counter.labels.return_value.inc.assert_called_once()
