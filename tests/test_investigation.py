import pytest

from acc_v8_qa.investigation import investigate


def report(decision="BLOCK", checks=None):
    return {
        "campaign_id": "SYNTHETIC-001",
        "decision": decision,
        "checks": checks if checks is not None else [
            {
                "rule_id": "CON-001",
                "status": "FAIL",
                "message": "Invalid consent records: 2",
            }
        ],
    }


def test_consent_finding_is_critical_and_requires_review():
    result = investigate(report())
    assert result["deterministic_decision"] == "BLOCK"
    assert result["findings"][0]["risk"] == "CRITICAL"
    assert result["summary"]["human_review"] == "PENDING"


def test_unknown_delivery_remains_blocked():
    result = investigate(report(checks=[
        {
            "rule_id": "ASYNC-001",
            "status": "UNKNOWN",
            "message": "Delivery state pending",
        }
    ]))
    assert result["deterministic_decision"] == "BLOCK"


def test_warning_does_not_change_approval():
    result = investigate(report("APPROVE", [
        {
            "rule_id": "CONTENT-001",
            "status": "WARN",
            "message": "Subject is long",
        }
    ]))
    assert result["deterministic_decision"] == "APPROVE"
    assert result["findings"][0]["risk"] == "LOW"


def test_clean_report_has_no_findings():
    result = investigate(report("APPROVE", [
        {"rule_id": "AUD-001", "status": "PASS", "message": "Within limit"}
    ]))
    assert result["findings"] == []
    assert result["summary"]["human_review"] == "NOT_REQUIRED_BY_THIS_REPORT"


def test_unknown_rule_is_not_guessed():
    result = investigate(report(checks=[
        {"rule_id": "NEW-999", "status": "FAIL", "message": "Unexpected"}
    ]))
    assert result["findings"][0]["risk"] == "LOW"
    assert result["findings"][0]["confidence"] == "LOW"


@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_invalid_report_rejected(value):
    with pytest.raises(ValueError):
        investigate(value)


def test_invalid_check_rejected():
    with pytest.raises(ValueError):
        investigate(report(checks=["not-an-object"]))
