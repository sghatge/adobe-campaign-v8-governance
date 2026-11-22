import importlib
import json

import pytest

from governance.audit import append_event, export_ledger, read_events, verify_chain_report
from governance.campaign_guardian import (
    INVARIANTS,
    build_review_packet,
    create_candidate_playbook,
    playbook_diff,
    read_playbooks,
    review_candidate_playbook,
)


def test_audit_report_verifies_sequence_and_exports_metadata(tmp_path):
    ledger = tmp_path / "audit.json"
    append_event(ledger, "ASSESS", "SYNTHETIC-1", "DETERMINISTIC_QA", {"decision": "BLOCK"})
    append_event(ledger, "REVIEW", "SYNTHETIC-1", "Reviewer A", {"action": "REJECT"})

    report = verify_chain_report(read_events(ledger))
    exported = export_ledger(ledger)

    assert report["valid"] is True
    assert report["verified_count"] == report["event_count"] == 2
    assert exported["integrity"] == report
    assert exported["events"] == read_events(ledger)
    assert json.loads(json.dumps(exported))["export_version"] == 1


def test_audit_report_locates_first_tampered_event_and_exports_failure(tmp_path):
    ledger = tmp_path / "audit.json"
    append_event(ledger, "ASSESS", "SYNTHETIC-1", "ENGINE", {})
    append_event(ledger, "REVIEW", "SYNTHETIC-1", "Reviewer A", {})
    events = read_events(ledger)
    events[1]["actor"] = "Changed reviewer"
    ledger.write_text(json.dumps(events), encoding="utf-8")

    report = verify_chain_report(read_events(ledger))
    exported = export_ledger(ledger)

    assert report["valid"] is False
    assert report["verified_count"] == 1
    assert report["first_invalid_sequence"] == 2
    assert "hash" in report["reason"].lower()
    assert exported["integrity"]["valid"] is False


def test_audit_report_detects_removed_or_reordered_events(tmp_path):
    ledger = tmp_path / "audit.json"
    for number in range(3):
        append_event(ledger, "ASSESS", f"SYNTHETIC-{number}", "ENGINE", {})
    events = read_events(ledger)
    removed = events[:1] + events[2:]

    report = verify_chain_report(removed)

    assert report["valid"] is False
    assert report["first_invalid_sequence"] == 2


def test_playbook_diff_shows_candidate_changes_without_changing_invariants(tmp_path):
    store_path = tmp_path / "playbooks.json"
    candidate = create_candidate_playbook(
        store_path,
        [{"rule_id": "CON-002", "recommendation": "Collect synthetic legal basis evidence."}],
    )
    store = read_playbooks(store_path)
    active = next(v for v in store["versions"] if v["version"] == store["active_version"])

    diff = playbook_diff(active, candidate)

    assert diff["from_version"] == "1.0.0"
    assert diff["to_version"] == candidate["version"]
    assert diff["added"] == candidate["recommendations"]
    assert diff["removed"] == []
    assert diff["unchanged_count"] == 0
    assert diff["invariants_unchanged"] is True


def test_playbook_diff_fails_closed_if_candidate_weakens_invariants(tmp_path):
    store_path = tmp_path / "playbooks.json"
    candidate = create_candidate_playbook(store_path, [])
    store = read_playbooks(store_path)
    active = next(v for v in store["versions"] if v["version"] == store["active_version"])
    candidate["invariants"] = dict(INVARIANTS, quality_cannot_override_compliance=False)

    with pytest.raises(ValueError, match="cannot be weakened"):
        playbook_diff(active, candidate)


def test_rejected_candidate_is_retained_and_never_becomes_active(tmp_path):
    store_path = tmp_path / "playbooks.json"
    audit_path = tmp_path / "audit.json"
    candidate = create_candidate_playbook(store_path, [{"rule_id": "CON-002"}])

    review_candidate_playbook(
        store_path, audit_path, candidate["version"],
        "Reviewer A", "REJECT", "Evidence needs more detail.",
    )
    store = read_playbooks(store_path)
    rejected = next(v for v in store["versions"] if v["version"] == candidate["version"])

    assert store["active_version"] == "1.0.0"
    assert rejected["status"] == "REJECTED"
    assert verify_chain_report(read_events(audit_path))["valid"] is True


def test_audit_report_detects_reordered_events(tmp_path):
    ledger = tmp_path / "audit.json"
    for number in range(3):
        append_event(ledger, "ASSESS", f"SYNTHETIC-{number}", "ENGINE", {})
    reordered = list(reversed(read_events(ledger)))

    report = verify_chain_report(reordered)

    assert report["valid"] is False
    assert report["first_invalid_sequence"] == 1


def test_audit_module_reload_restores_phase2_exports():
    import governance.audit as audit_module

    try:
        del audit_module.export_ledger
        importlib.reload(audit_module)
        assert callable(audit_module.export_ledger)
        assert callable(audit_module.verify_chain_report)
    finally:
        importlib.reload(audit_module)


def test_review_packet_bundles_decision_evidence_without_release_authority():
    loop_result = {
        "decision": "BLOCK",
        "iterations": [{"iteration": 1, "decision": "BLOCK", "quality_score": 80}],
        "final_evaluation": {
            "campaign_id": "SYNTHETIC-CAMPAIGN-1",
            "decision": "BLOCK",
            "quality_score": 80,
            "compliance_block": True,
            "qa_report": {"checks": [{"rule_id": "CON-001", "status": "FAIL"}]},
            "recommendations": {"recommendations": [{"rule_id": "CON-001", "auto_applied": False}]},
        },
    }
    packet = build_review_packet(
        loop_result,
        "1.0.0",
        {"valid": True, "event_count": 1, "verified_count": 1, "head_hash": "abc"},
    )

    assert packet["decision"] == "BLOCK"
    assert packet["compliance_block"] is True
    assert packet["decision_authority"] == "DETERMINISTIC_EVALUATOR"
    assert packet["release_authorized"] is False
    assert packet["checks"] == loop_result["final_evaluation"]["qa_report"]["checks"]
    assert packet["audit_integrity"]["valid"] is True
    assert "campaign" not in packet
