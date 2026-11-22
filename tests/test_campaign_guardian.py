import copy
import json
from pathlib import Path
import pytest
from acc_v8_qa.engine import evaluate, load_json
from governance.audit import read_events, verify_chain
from governance.campaign_guardian import (INVARIANTS, MAX_ITERATIONS, assert_invariants, create_candidate_playbook, evaluate_candidate, read_playbooks, review_candidate_playbook, run_bounded_improvement_loop, write_recommendations, reviewer_evidence_improver)
ROOT = Path(__file__).resolve().parents[1]
POLICY = load_json(ROOT / "config" / "policy.json")
def campaign():
    return load_json(ROOT / "samples" / "campaign-pass.json")
def test_missing_consent_evidence_blocks():
    data = campaign(); del data["consent_evidence_ref"]
    report = evaluate(data, POLICY)
    assert report["decision"] == "BLOCK"
    assert next(c for c in report["checks"] if c["rule_id"] == "CON-001")["status"] == "UNKNOWN"
def test_missing_legal_basis_evidence_blocks():
    data = campaign(); del data["legal_basis_evidence_ref"]
    report = evaluate(data, POLICY)
    assert report["decision"] == "BLOCK"
    assert next(c for c in report["checks"] if c["rule_id"] == "CON-002")["status"] == "UNKNOWN"
def test_non_synthetic_evidence_fails_closed():
    data = campaign(); data["legal_basis_evidence_ref"] = "LEGAL-REF-123"
    assert evaluate(data, POLICY)["decision"] == "BLOCK"
def test_recommendations_are_traceable_and_not_applied():
    data = campaign(); del data["legal_basis_evidence_ref"]
    qa = evaluate(data, POLICY); result = write_recommendations(qa)
    rec = next(x for x in result["recommendations"] if x["rule_id"] == "CON-002")
    assert rec["source_status"] == "UNKNOWN" and rec["evidence_fact"]
    assert rec["auto_applied"] is False and rec["requires_human_review"] is True
def test_quality_never_overrides_compliance(monkeypatch):
    import governance.campaign_guardian as guardian
    monkeypatch.setattr(guardian, "quality_score", lambda _qa: 100)
    data = campaign(); del data["legal_basis_evidence_ref"]
    result = evaluate_candidate(data, POLICY)
    assert result["quality_score"] == 100 and result["decision"] == "BLOCK"
def test_improvement_loop_stops_at_five_iterations():
    data = campaign(); del data["consent_evidence_ref"]
    result = run_bounded_improvement_loop(data, POLICY, lambda c, _r: {**c, "subject": c["subject"] + "!"}, 5)
    assert MAX_ITERATIONS == 5 and result["iteration_count"] == 5
    assert result["decision"] == "BLOCK"
def test_improvement_loop_rejects_more_than_five():
    with pytest.raises(ValueError): run_bounded_improvement_loop(campaign(), POLICY, max_iterations=6)
def test_mandatory_invariants_cannot_be_weakened():
    candidate = copy.deepcopy(INVARIANTS); candidate["quality_cannot_override_compliance"] = False
    with pytest.raises(ValueError): assert_invariants(candidate)
    candidate = copy.deepcopy(INVARIANTS); candidate["mandatory_rules"].remove("CON-002")
    with pytest.raises(ValueError): assert_invariants(candidate)
def test_candidate_requires_explicit_human_approval_and_audits_activation(tmp_path):
    path = tmp_path / "playbooks.json"; audit = tmp_path / "audit.json"
    candidate = create_candidate_playbook(path, [{"rule_id": "CON-002"}])
    assert read_playbooks(path)["active_version"] == "1.0.0"
    with pytest.raises(ValueError): review_candidate_playbook(path, audit, candidate["version"], "Reviewer A", "APPROVE", "Reviewed")
    assert read_playbooks(path)["active_version"] == "1.0.0"
    review_candidate_playbook(path, audit, candidate["version"], "Reviewer A", "APPROVE", "Reviewed evidence", explicit_human_approval=True)
    assert read_playbooks(path)["active_version"] == candidate["version"]
    assert verify_chain(read_events(audit))
def test_ai_cannot_approve_own_recommendation(tmp_path):
    path = tmp_path / "playbooks.json"; candidate = create_candidate_playbook(path, [])
    with pytest.raises(ValueError): review_candidate_playbook(path, tmp_path / "audit.json", candidate["version"], "Codex assistant", "APPROVE", "Approve", explicit_human_approval=True)
    assert read_playbooks(path)["active_version"] == "1.0.0"
def test_rejected_candidate_keeps_active_version(tmp_path):
    path = tmp_path / "playbooks.json"; candidate = create_candidate_playbook(path, [])
    review_candidate_playbook(path, tmp_path / "audit.json", candidate["version"], "Reviewer A", "REJECT", "Needs revision")
    store = read_playbooks(path)
    assert store["active_version"] == "1.0.0"
    assert next(v for v in store["versions"] if v["version"] == candidate["version"])["status"] == "REJECTED"
def test_golden_regression_scenarios():
    cases = json.loads((ROOT / "tests/fixtures/campaign_guardian_golden.json").read_text())
    for case in cases:
        data = campaign()
        for field in case.get("remove", []): data.pop(field, None)
        data.update(case.get("set", {}))
        assert evaluate_candidate(data, POLICY)["decision"] == case["decision"], case["id"]



def test_loop_performs_at_most_five_evaluations(monkeypatch):
    import governance.campaign_guardian as guardian
    calls = 0
    original = guardian.evaluate_candidate
    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(guardian, "evaluate_candidate", counted)
    data = campaign(); del data["consent_evidence_ref"]
    guardian.run_bounded_improvement_loop(data, POLICY, lambda c, _r: {**c, "subject": c["subject"] + "!"}, 5)
    assert calls == 5


def test_invalid_audit_chain_prevents_playbook_activation(tmp_path):
    from governance.audit import append_event
    path = tmp_path / "playbooks.json"; audit = tmp_path / "audit.json"
    candidate = create_candidate_playbook(path, [])
    append_event(audit, "SEED", "CAMPAIGN-GUARDIAN", "system", {})
    events = read_events(audit); events[0]["actor"] = "tampered"
    audit.write_text(json.dumps(events))
    with pytest.raises(ValueError):
        review_candidate_playbook(path, audit, candidate["version"], "Reviewer A", "APPROVE", "Reviewed", explicit_human_approval=True)
    assert read_playbooks(path)["active_version"] == "1.0.0"
    assert next(v for v in read_playbooks(path)["versions"] if v["version"] == candidate["version"])["status"] == "PENDING_REVIEW"


def test_reviewer_evidence_drives_separate_bounded_revisions():
    data = campaign()
    data.pop("consent_evidence_ref")
    data.pop("legal_basis_evidence_ref")
    improver = reviewer_evidence_improver({
        "consent_evidence_ref": "SYNTHETIC-CONSENT-REVIEWED",
        "legal_basis_evidence_ref": "SYNTHETIC-LEGAL-REVIEWED",
    })
    result = run_bounded_improvement_loop(data, POLICY, improver, max_iterations=5)
    assert result["decision"] == "APPROVE"
    assert result["iteration_count"] == 3
    assert result["campaign"]["consent_evidence_ref"] == "SYNTHETIC-CONSENT-REVIEWED"
    assert result["campaign"]["legal_basis_evidence_ref"] == "SYNTHETIC-LEGAL-REVIEWED"

def test_reviewer_evidence_improver_rejects_non_synthetic_references():
    with pytest.raises(ValueError):
        reviewer_evidence_improver({"legal_basis_evidence_ref": "REAL-RECORD-1"})
