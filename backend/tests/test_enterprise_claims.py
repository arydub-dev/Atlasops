"""Prevent missing data and heuristic scores from becoming fabricated evidence."""
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
from app.services.metrics import supplier_performance_trend
from app.services.predictions import _out


def test_missing_supplier_data_has_no_invented_average():
    db = MagicMock()
    db.scalar.side_effect = [None, None]
    assert supplier_performance_trend(db, uuid4()) == []


def test_zero_supplier_scores_are_preserved():
    db = MagicMock()
    db.scalar.side_effect = [0.0, 0.0]
    item = supplier_performance_trend(db, uuid4())[0]
    assert item["supplier_score"] == 0.0
    assert item["delivery_reliability"] == 0.0


def test_heuristic_confidence_is_not_exposed_as_probability():
    prediction = SimpleNamespace(id=uuid4(), kind=SimpleNamespace(value="shipment_delay"),
        title="Risk", confidence=0.95, reasoning="Rule threshold", contributing_factors=[],
        recommended_actions=[], linked_entities=[], horizon_hours=24, score=90, created_at=None)
    result = _out(prediction)
    assert result["confidence"] is None
    assert result["method"] == "rule_based"
    assert result["calibration_status"] == "not_calibrated"
