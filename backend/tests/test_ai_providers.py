"""AI provider abstraction tests."""
from __future__ import annotations

from app.services.ai_providers import LocalEngineProvider, get_ai_provider


def test_get_ai_provider_defaults_to_local(monkeypatch):
    from app.core.config import get_settings, settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    get_settings.cache_clear()
    provider = get_ai_provider()
    assert provider.name == "local-engine"


def test_local_engine_grounds_in_context():
    ctx = {
        "kpis": {
            "total_shipments": 10,
            "active_shipments": 4,
            "delayed_shipments": 2,
            "on_time_delivery_rate": 80,
            "inventory_health_score": 70,
            "supplier_reliability_score": 75,
            "open_alerts": 3,
            "critical_risks": 1,
        },
        "risk": {"overall_score": 55, "overall_level": "medium", "counts": {"critical": 1}},
        "top_risks": [
            {
                "title": "Supplier delay",
                "level": "high",
                "score": 80,
                "recommendation": "Activate backup",
            }
        ],
    }
    text = LocalEngineProvider().answer("Give me an executive summary", ctx)
    assert "Shipments" in text
    assert "Supplier delay" in text


def test_simulation_prompt_does_not_invent_numbers(owner_client):
    r = owner_client.post(
        "/api/v1/ai/chat",
        json={"prompt": "What happens if Supplier ABC is unavailable for 10 days?"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    text = body.get("response") or ""
    assert "Simulation" in text or "simulator" in text.lower()


def test_provider_has_bounded_timeout_output_and_no_retries(monkeypatch):
    from unittest.mock import MagicMock
    import openai
    from app.services.ai_providers import OpenAIProvider
    from app.core.config import settings
    factory = MagicMock()
    factory.return_value.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content='Observed data only'))]
    monkeypatch.setattr(openai, 'OpenAI', factory)
    assert OpenAIProvider().answer('Question', {'kpis': {}}) == 'Observed data only'
    assert factory.call_args.kwargs['timeout'] == settings.AI_TIMEOUT_SECONDS
    assert factory.call_args.kwargs['max_retries'] == 0
    assert factory.return_value.chat.completions.create.call_args.kwargs['max_completion_tokens'] == settings.AI_MAX_OUTPUT_TOKENS
    factory.return_value.close.assert_called_once()


def test_provider_context_limit_prevents_request(monkeypatch):
    from unittest.mock import MagicMock
    import openai
    import pytest
    from app.services.ai_providers import OpenAIProvider
    factory = MagicMock(); monkeypatch.setattr(openai, 'OpenAI', factory)
    with pytest.raises(ValueError, match='context'):
        OpenAIProvider().answer('Question', {'payload': 'x' * 100001})
    factory.assert_not_called()


def test_orchestration_uses_retrieved_context_without_fake_confidence(owner_client, monkeypatch):
    from app.services import ai_advisor
    seen = {}
    def answer(db, prompt, *, context=None):
        seen.update(context or {})
        return 'Review the supplied records.', 'test-provider', context
    monkeypatch.setattr(ai_advisor, 'answer', answer)
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Executive briefing'})
    assert response.status_code == 200
    assert 'timeline' in seen
    assert response.json()['confidence'] is None
