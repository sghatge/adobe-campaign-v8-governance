import json

import pytest

from governance.portfolio import (
    append_history,
    assess_portfolio,
    latest_batch,
    load_portfolio,
    summarize_portfolio,
)

from acc_v8_qa.engine import load_json

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
POLICY = load_json(ROOT / "config" / "policy.json")


def campaigns():
    return load_portfolio(ROOT / "data" / "synthetic_campaign_portfolio.json")


def test_synthetic_portfolio_has_six_unique_campaigns():
    items = campaigns()
    assert len(items) == 6
    assert len({item["campaign_id"] for item in items}) == 6


def test_portfolio_assessment_preserves_deterministic_decisions():
    results = assess_portfolio(campaigns(), POLICY)
    assert len(results) == 6
    assert results[0]["decision"] == "APPROVE"
    assert results[1]["decision"] == "BLOCK"


def test_blocked_campaign_has_critical_risk():
    results = assess_portfolio(campaigns(), POLICY)
    blocked = next(x for x in results if x["campaign_id"] == "PORTFOLIO-002")
    assert blocked["risk_level"] == "CRITICAL"
    assert blocked["investigation_summary"]["human_review"] == "PENDING"


def test_portfolio_summary_counts_campaigns():
    results = assess_portfolio(campaigns(), POLICY)
    summary = summarize_portfolio(results)
    assert summary["campaign_count"] == 6
    assert summary["approved"] + summary["blocked"] == 6
    assert summary["critical_campaigns"] >= 1


def test_control_failure_frequency_is_aggregated():
    results = assess_portfolio(campaigns(), POLICY)
    summary = summarize_portfolio(results)
    assert summary["control_failures"]["CON-001"] >= 1
    assert summary["control_failures"]["AUD-001"] >= 1


def test_history_appends_without_overwriting(tmp_path):
    path = tmp_path / "history.json"
    first = assess_portfolio(campaigns()[:1], POLICY)
    second = assess_portfolio(campaigns()[1:2], POLICY)

    assert append_history(path, first) == 1
    assert append_history(path, second) == 2

    stored = json.loads(path.read_text())
    assert len(stored) == 2
    assert stored[0]["campaign_id"] == "PORTFOLIO-001"
    assert stored[1]["campaign_id"] == "PORTFOLIO-002"


def test_latest_batch_returns_only_latest_assessment():
    first = assess_portfolio(campaigns()[:1], POLICY)
    second = assess_portfolio(campaigns()[1:2], POLICY)
    assert len(latest_batch(first + second)) == 1
    assert latest_batch(first + second)[0]["campaign_id"] == "PORTFOLIO-002"


def test_non_synthetic_portfolio_rejected(tmp_path):
    path = tmp_path / "portfolio.json"
    path.write_text(json.dumps({
        "data_classification": "PRODUCTION",
        "campaigns": [{"campaign_id": "X"}],
    }))
    with pytest.raises(ValueError):
        load_portfolio(path)


def test_duplicate_campaign_ids_rejected(tmp_path):
    path = tmp_path / "portfolio.json"
    path.write_text(json.dumps({
        "data_classification": "SYNTHETIC",
        "campaigns": [
            {"campaign_id": "DUPLICATE"},
            {"campaign_id": "DUPLICATE"},
        ],
    }))
    with pytest.raises(ValueError):
        load_portfolio(path)


def test_empty_assessment_rejected():
    with pytest.raises(ValueError):
        assess_portfolio([], POLICY)
