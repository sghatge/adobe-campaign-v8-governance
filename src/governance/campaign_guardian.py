"""Offline Campaign Guardian controls for evidence-led recommendations.
All recommendations are deterministic and advisory. The evaluator owns the
compliance gate; quality scores and proposed playbooks cannot override it.
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from acc_v8_qa.engine import evaluate
from governance.audit import append_event

MAX_ITERATIONS = 5
MANDATORY_RULES = frozenset({"CON-001", "CON-002", "SUP-001", "TYP-001", "APR-001"})
INVARIANTS = {
    "mandatory_rules": sorted(MANDATORY_RULES),
    "missing_evidence_blocks": True,
    "quality_cannot_override_compliance": True,
    "ai_cannot_approve": True,
    "active_requires_human_approval": True,
    "campaign_execution_enabled": False,
    "synthetic_data_only": True,
}

_GUIDANCE = {
    "AUD-001": ("Reconcile the audience count to the approved synthetic baseline before resubmitting.", ["SYNTHETIC audience extract reference", "SYNTHETIC approved baseline reference"]),
    "CON-001": ("Provide verifiable consent evidence and resolve every invalid-consent record.", ["SYNTHETIC consent evidence reference", "Consent reconciliation result"]),
    "CON-002": ("Provide evidence of the documented legal basis for this audience.", ["SYNTHETIC legal-basis evidence reference", "Reviewer verification of scope"]),
    "SUP-001": ("Reconcile suppression rules and prove excluded recipients are absent.", ["SYNTHETIC suppression evidence reference", "Audience reconciliation result"]),
    "WF-001": ("Complete the workflow and attach its synthetic completion evidence.", ["SYNTHETIC workflow run reference", "Completion status"]),
    "TYP-001": ("Verify the mandatory typology is active and assigned.", ["SYNTHETIC typology reference", "Activation evidence"]),
    "APR-001": ("Obtain explicit proof approval from an authorized human reviewer.", ["Approved proof version", "Human reviewer and timestamp"]),
    "ASYNC-001": ("Confirm delivery has not started and attach status evidence.", ["SYNTHETIC delivery status reference", "Pre-flight status"]),
    "CONTENT-001": ("Review the advisory content finding against the communication standard.", ["Final synthetic subject", "Review record"]),
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_recommendations(qa_report):
    """Write traceable recommendations only from non-PASS QA evidence."""
    if not isinstance(qa_report, dict) or not isinstance(qa_report.get("checks"), list):
        raise ValueError("A deterministic QA report is required.")
    recommendations = []
    for check in qa_report["checks"]:
        if not isinstance(check, dict) or check.get("status") == "PASS":
            continue
        rule_id = check.get("rule_id", "UNCLASSIFIED")
        instruction, evidence = _GUIDANCE.get(
            rule_id, ("Escalate this unclassified finding to a human reviewer.", ["Rule definition", "Original evidence", "Human assessment"])
        )
        recommendations.append({
            "recommendation_id": f"REC-{len(recommendations) + 1:03d}",
            "rule_id": str(rule_id),
            "source_status": check.get("status"),
            "evidence_fact": str(check.get("message", ""))[:1000],
            "recommendation": instruction,
            "evidence_to_collect": evidence,
            "auto_applied": False,
            "requires_human_review": True,
        })
    return {
        "writer_version": "1.0.0",
        "campaign_id": qa_report.get("campaign_id", "UNIDENTIFIED"),
        "source_decision": qa_report.get("decision"),
        "generated_at": _utc_now(),
        "recommendations": recommendations,
        "decision_authority": "DETERMINISTIC_EVALUATOR",
    }


def quality_score(qa_report):
    checks = qa_report.get("checks", [])
    if not checks:
        return 0
    return round(100 * sum(item.get("status") == "PASS" for item in checks) / len(checks))


def assert_invariants(invariants):
    """Reject a candidate that omits, relaxes, or replaces any invariant."""
    if not isinstance(invariants, dict):
        raise ValueError("Playbook invariants must be an object.")
    for key, expected in INVARIANTS.items():
        actual = invariants.get(key)
        if isinstance(expected, list):
            if not isinstance(actual, list) or not set(expected).issubset(actual):
                raise ValueError(f"Mandatory invariant {key} cannot be weakened.")
        elif actual is not expected:
            raise ValueError(f"Mandatory invariant {key} cannot be weakened.")


def evaluate_candidate(campaign, policy, playbook=None):
    """Evaluate deterministically; compliance remains a non-compensable gate."""
    qa = evaluate(campaign, policy)
    invariant_errors = []
    if playbook is not None:
        try:
            assert_invariants(playbook.get("invariants", {}))
        except (TypeError, ValueError) as exc:
            invariant_errors.append(str(exc))
    check_map = {check["rule_id"]: check["status"] for check in qa["checks"]}
    for rule_id in sorted(MANDATORY_RULES):
        if check_map.get(rule_id) != "PASS":
            invariant_errors.append(f"Mandatory invariant {rule_id} is not PASS.")
    decision = "BLOCK" if qa["decision"] == "BLOCK" or invariant_errors else "APPROVE"
    return {
        "campaign_id": qa["campaign_id"],
        "decision": decision,
        "deterministic_qa_decision": qa["decision"],
        "quality_score": quality_score(qa),
        "compliance_block": decision == "BLOCK",
        "invariant_errors": invariant_errors,
        "qa_report": qa,
        "recommendations": write_recommendations(qa),
    }


def reviewer_evidence_improver(references):
    """Return a local callback that applies only reviewer-entered synthetic refs.

    Each reference is applied as a separate candidate revision. Existing values
    are never overwritten and the QA evaluator must pass the reference before
    the loop can converge.
    """
    allowed = {"consent_evidence_ref", "legal_basis_evidence_ref"}
    if not isinstance(references, dict) or set(references) - allowed:
        raise ValueError("Only consent and legal-basis evidence references are accepted.")
    pending = []
    for field, reference in references.items():
        if not isinstance(reference, str) or not reference.startswith("SYNTHETIC-") or len(reference) > 160:
            raise ValueError("Evidence references must be synthetic and at most 160 characters.")
        if reference.strip():
            pending.append((field, reference.strip()))

    def apply_one(candidate, _evaluation):
        for item in pending:
            field, reference = item
            if not candidate.get(field):
                revised = copy.deepcopy(candidate)
                revised[field] = reference
                pending.remove(item)
                return revised
        return None

    return apply_one


def run_bounded_improvement_loop(campaign, policy, improver=None, max_iterations=MAX_ITERATIONS):
    """Run at most five review cycles; no model or network is called.

    The optional local callback receives a copy of the campaign and evaluator
    result, and returns a complete candidate mapping or None. The deterministic
    evaluator reruns after every proposal.
    """
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= MAX_ITERATIONS:
        raise ValueError(f"max_iterations must be between 1 and {MAX_ITERATIONS}.")
    current = copy.deepcopy(campaign)
    history = []
    for iteration in range(1, max_iterations + 1):
        result = evaluate_candidate(current, policy)
        history.append({"iteration": iteration, "decision": result["decision"], "quality_score": result["quality_score"], "recommendation_count": len(result["recommendations"]["recommendations"])})
        if result["decision"] == "APPROVE" or improver is None:
            break
        proposed = improver(copy.deepcopy(current), copy.deepcopy(result))
        if proposed is None or proposed == current:
            break
        if not isinstance(proposed, dict):
            raise ValueError("Improver must return a campaign object or None.")
        current = copy.deepcopy(proposed)
    final = result
    return {
        "campaign": current, "iterations": history,
        "iteration_count": len(history),
        "converged": final["decision"] == "APPROVE",
        "decision": final["decision"],
        "quality_score": final["quality_score"],
        "final_evaluation": final,
    }


def _default_store():
    return {
        "schema_version": 1, "active_version": "1.0.0",
        "versions": [{
            "version": "1.0.0", "status": "ACTIVE",
            "created_at": _utc_now(), "created_by": "SYSTEM_SEED",
            "reviewed_by": None, "rationale": "Immutable Phase 1 baseline.",
            "invariants": copy.deepcopy(INVARIANTS), "recommendations": [],
        }],
    }


def read_playbooks(path):
    path = Path(path)
    if not path.exists():
        return _default_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Playbook store is invalid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("versions"), list):
        raise ValueError("Playbook store has an invalid structure.")
    active = [v for v in data["versions"] if v.get("version") == data.get("active_version") and v.get("status") == "ACTIVE"]
    if len(active) != 1:
        raise ValueError("Playbook store must contain exactly one active version.")
    assert_invariants(active[0].get("invariants"))
    return data


def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def _next_version(versions):
    parsed = []
    for item in versions:
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", item.get("version", ""))
        if match:
            parsed.append(tuple(map(int, match.groups())))
    major, minor, patch = max(parsed, default=(1, 0, 0))
    return f"{major}.{minor}.{patch + 1}"


def create_candidate_playbook(path, recommendations, author="Campaign Guardian"):
    if not isinstance(recommendations, list) or not all(isinstance(x, dict) for x in recommendations):
        raise ValueError("Candidate recommendations must be a list of objects.")
    store = read_playbooks(path)
    if any(v.get("status") == "PENDING_REVIEW" for v in store["versions"]):
        raise ValueError("Review or reject the existing candidate before creating another.")
    candidate = {
        "version": _next_version(store["versions"]),
        "status": "PENDING_REVIEW",
        "created_at": _utc_now(), "created_by": str(author)[:120],
        "reviewed_by": None, "rationale": None,
        "invariants": copy.deepcopy(INVARIANTS),
        "recommendations": copy.deepcopy(recommendations),
    }
    store["versions"].append(candidate)
    _write_json_atomic(path, store)
    return candidate


def review_candidate_playbook(path, audit_path, version, reviewer, action, rationale, explicit_human_approval=False):
    if action not in {"APPROVE", "REJECT"}:
        raise ValueError("Review action must be APPROVE or REJECT.")
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("Human reviewer and rationale are required.")
    if re.search(r"\b(ai|assistant|codex|model|bot|system)\b", reviewer, re.I):
        raise ValueError("An AI or system actor cannot approve its own recommendation.")
    if action == "APPROVE" and explicit_human_approval is not True:
        raise ValueError("Explicit human approval is required to activate a playbook.")
    store = read_playbooks(path)
    candidate = next((v for v in store["versions"] if v.get("version") == version), None)
    if candidate is None or candidate.get("status") != "PENDING_REVIEW":
        raise ValueError("A pending candidate version is required.")
    assert_invariants(candidate.get("invariants"))
    candidate["reviewed_by"] = reviewer.strip()
    candidate["rationale"] = rationale.strip()[:1000]
    candidate["reviewed_at"] = _utc_now()
    if action == "APPROVE":
        old = next(v for v in store["versions"] if v["version"] == store["active_version"])
        old["status"] = "SUPERSEDED"
        candidate["status"] = "ACTIVE"
        store["active_version"] = candidate["version"]
        event = "PLAYBOOK_VERSION_ACTIVATED"
    else:
        candidate["status"] = "REJECTED"
        event = "PLAYBOOK_VERSION_REJECTED"
    append_event(audit_path, event, "CAMPAIGN-GUARDIAN", reviewer.strip(), {
        "version": candidate["version"], "action": action,
        "rationale": rationale.strip()[:1000], "explicit_human_approval": action == "APPROVE",
        "release_authorized": False,
    })
    _write_json_atomic(path, store)
    return copy.deepcopy(candidate)
