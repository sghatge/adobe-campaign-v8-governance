import json
import pytest

from governance.audit import append_event, read_events, verify_chain
from governance.approval import record_review, read_approvals


def test_audit_event_creates_valid_chain(tmp_path):
    path = tmp_path / "audit.json"
    append_event(path, "ASSESSMENT", "CAMP-001", "system", {"decision": "BLOCK"})
    events = read_events(path)
    assert len(events) == 1
    assert verify_chain(events)


def test_audit_chain_links_events(tmp_path):
    path = tmp_path / "audit.json"
    append_event(path, "ASSESSMENT", "CAMP-001", "system", {})
    append_event(path, "REVIEW", "CAMP-001", "reviewer", {})
    events = read_events(path)
    assert events[1]["previous_hash"] == events[0]["event_hash"]
    assert verify_chain(events)


def test_tampered_audit_event_is_detected(tmp_path):
    path = tmp_path / "audit.json"
    append_event(path, "ASSESSMENT", "CAMP-001", "system", {"decision": "BLOCK"})
    events = read_events(path)
    events[0]["details"]["decision"] = "APPROVE"
    assert not verify_chain(events)


def test_append_refused_when_chain_is_tampered(tmp_path):
    path = tmp_path / "audit.json"
    append_event(path, "ASSESSMENT", "CAMP-001", "system", {})
    events = read_events(path)
    events[0]["actor"] = "changed"
    path.write_text(json.dumps(events))
    with pytest.raises(ValueError):
        append_event(path, "REVIEW", "CAMP-001", "reviewer", {})


def test_block_campaign_cannot_be_approved(tmp_path):
    with pytest.raises(ValueError):
        record_review(
            tmp_path / "approvals.json", tmp_path / "audit.json",
            "CAMP-001", "BLOCK", "Reviewer A", "APPROVE", "Try to release"
        )


def test_approved_decision_can_be_reviewed(tmp_path):
    record = record_review(
        tmp_path / "approvals.json", tmp_path / "audit.json",
        "CAMP-002", "APPROVE", "Reviewer A", "APPROVE", "Reviewed evidence"
    )
    assert record["action"] == "APPROVE"
    assert record["release_authorized"] is False
    assert len(read_approvals(tmp_path / "approvals.json")) == 1
    assert verify_chain(read_events(tmp_path / "audit.json"))


def test_review_requires_reviewer_and_reason(tmp_path):
    with pytest.raises(ValueError):
        record_review(
            tmp_path / "approvals.json", tmp_path / "audit.json",
            "CAMP-002", "APPROVE", "", "APPROVE", "Reason"
        )
    with pytest.raises(ValueError):
        record_review(
            tmp_path / "approvals.json", tmp_path / "audit.json",
            "CAMP-002", "APPROVE", "Reviewer A", "APPROVE", ""
        )
