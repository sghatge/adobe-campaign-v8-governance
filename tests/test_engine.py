import json
from pathlib import Path
import pytest

from acc_v8_qa.engine import evaluate

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "config/policy.json").read_text())


def valid_campaign():
    return json.loads(
        (ROOT / "samples/campaign-pass.json").read_text()
    )


def rule(report, rule_id):
    return next(
        item for item in report["checks"]
        if item["rule_id"] == rule_id
    )


def test_valid_campaign_approved():
    assert evaluate(valid_campaign(), POLICY)["decision"] == "APPROVE"


def test_audience_drift_blocks():
    c = valid_campaign()
    c["audience_count"] = 1200
    assert rule(evaluate(c, POLICY), "AUD-001")["status"] == "FAIL"


def test_audience_missing_is_unknown():
    c = valid_campaign()
    del c["audience_count"]
    assert rule(evaluate(c, POLICY), "AUD-001")["status"] == "UNKNOWN"


def test_zero_baseline_is_unknown():
    c = valid_campaign()
    c["historical_average"] = 0
    assert rule(evaluate(c, POLICY), "AUD-001")["status"] == "UNKNOWN"


def test_consent_violation_blocks():
    c = valid_campaign()
    c["invalid_consent_count"] = 1
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_missing_consent_evidence_unknown():
    c = valid_campaign()
    del c["invalid_consent_count"]
    assert rule(evaluate(c, POLICY), "CON-001")["status"] == "UNKNOWN"


def test_suppression_violation_blocks():
    c = valid_campaign()
    c["suppressed_recipient_count"] = 1
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_missing_suppression_evidence_unknown():
    c = valid_campaign()
    del c["suppressed_recipient_count"]
    assert rule(evaluate(c, POLICY), "SUP-001")["status"] == "UNKNOWN"


def test_finished_workflow_passes():
    assert rule(evaluate(valid_campaign(), POLICY), "WF-001")["status"] == "PASS"


def test_running_workflow_blocks():
    c = valid_campaign()
    c["workflow_status"] = "Running"
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_missing_workflow_unknown():
    c = valid_campaign()
    del c["workflow_status"]
    assert rule(evaluate(c, POLICY), "WF-001")["status"] == "UNKNOWN"


def test_inactive_typology_blocks():
    c = valid_campaign()
    c["typology_active"] = False
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_missing_approval_blocks_as_unknown():
    c = valid_campaign()
    del c["proof_approved"]
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_pending_delivery_is_unknown():
    c = valid_campaign()
    c["delivery_status"] = "pending"
    assert rule(evaluate(c, POLICY), "ASYNC-001")["status"] == "UNKNOWN"


def test_in_progress_delivery_is_unknown():
    c = valid_campaign()
    c["delivery_status"] = "in-progress"
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_already_sent_delivery_is_not_preflight_ready():
    c = valid_campaign()
    c["delivery_status"] = "sent"
    assert evaluate(c, POLICY)["decision"] == "BLOCK"


def test_long_subject_is_warning_not_approval_block():
    c = valid_campaign()
    c["subject"] = "A" * 80
    report = evaluate(c, POLICY)
    assert rule(report, "CONTENT-001")["status"] == "WARN"
    assert report["decision"] == "APPROVE"


def test_multiple_violations_block():
    c = valid_campaign()
    c["invalid_consent_count"] = 2
    c["typology_active"] = False
    c["delivery_status"] = "pending"
    assert evaluate(c, POLICY)["decision"] == "BLOCK"
