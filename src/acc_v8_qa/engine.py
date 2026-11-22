import json
from datetime import datetime, timezone
from pathlib import Path


def evaluate(campaign, policy):
    checks = []

    def add(rule, status, message):
        checks.append({
            "rule_id": rule,
            "status": status,
            "message": message
        })

    def required(field):
        if field not in campaign or campaign[field] is None:
            return False
        return True

    # AUD-001: Audience variance
    if not required("audience_count") or not required("historical_average"):
        add("AUD-001", "UNKNOWN", "Audience baseline or count missing")
    else:
        current = campaign["audience_count"]
        baseline = campaign["historical_average"]

        if not isinstance(current, int) or not isinstance(baseline, int):
            add("AUD-001", "UNKNOWN", "Audience values must be integers")
        elif current < 0 or baseline <= 0:
            add("AUD-001", "UNKNOWN", "Invalid audience count or baseline")
        else:
            drift = abs(current - baseline) / baseline
            limit = policy["audience_drift_limit"]

            add(
                "AUD-001",
                "PASS" if drift <= limit else "FAIL",
                f"Audience drift {drift:.1%}; permitted {limit:.1%}"
            )

    # CON-001: Consent evidence and integrity
    consent_ref = campaign.get("consent_evidence_ref")
    consent_ref_valid = (
        isinstance(consent_ref, str)
        and consent_ref.startswith("SYNTHETIC-")
        and len(consent_ref) <= 160
    )
    if not required("invalid_consent_count"):
        add("CON-001", "UNKNOWN", "Consent evidence count missing")
    elif isinstance(campaign["invalid_consent_count"], bool) or not isinstance(campaign["invalid_consent_count"], int) or campaign["invalid_consent_count"] < 0:
        add("CON-001", "UNKNOWN", "Consent evidence count is invalid")
    elif campaign["invalid_consent_count"] > 0:
        add("CON-001", "FAIL", f"Invalid consent records: {campaign['invalid_consent_count']}")
    elif not consent_ref_valid:
        add("CON-001", "UNKNOWN", "Consent evidence reference missing or not synthetic")
    else:
        add("CON-001", "PASS", f"Consent evidence recorded; invalid records: {campaign['invalid_consent_count']}")

    # CON-002: Legal-basis evidence is a non-compensable compliance invariant.
    legal_basis_ref = campaign.get("legal_basis_evidence_ref")
    if not isinstance(legal_basis_ref, str) or not legal_basis_ref.startswith("SYNTHETIC-") or len(legal_basis_ref) > 160:
        add("CON-002", "UNKNOWN", "Legal-basis evidence reference missing or not synthetic")
    else:
        add("CON-002", "PASS", "Synthetic legal-basis evidence reference recorded")

    # SUP-001: Suppression integrity
    if not required("suppressed_recipient_count"):
        add("SUP-001", "UNKNOWN", "Suppression evidence missing")
    else:
        count = campaign["suppressed_recipient_count"]
        add(
            "SUP-001",
            "PASS" if count == 0 else "FAIL",
            f"Suppressed recipients in audience: {count}"
        )

    # WF-001: Workflow readiness
    if not required("workflow_status"):
        add("WF-001", "UNKNOWN", "Workflow status missing")
    else:
        status = campaign["workflow_status"]
        expected = policy["required_workflow_status"]
        add(
            "WF-001",
            "PASS" if status == expected else "FAIL",
            f"Workflow status: {status}; required: {expected}"
        )

    # TYP-001: Typology
    if not required("typology_active"):
        add("TYP-001", "UNKNOWN", "Typology evidence missing")
    else:
        active = campaign["typology_active"]
        add(
            "TYP-001",
            "PASS" if active is True else "FAIL",
            f"Mandatory typology active: {active}"
        )

    # APR-001: Human proof approval
    if not required("proof_approved"):
        add("APR-001", "UNKNOWN", "Approval evidence missing")
    else:
        approved = campaign["proof_approved"]
        add(
            "APR-001",
            "PASS" if approved is True else "FAIL",
            f"Proof approval recorded: {approved}"
        )

    # ASYNC-001: Delivery state
    if not required("delivery_status"):
        add("ASYNC-001", "UNKNOWN", "Delivery status missing")
    else:
        status = campaign["delivery_status"]

        if status in ("pending", "in-progress", "unknown"):
            result = "UNKNOWN"
        elif status == policy["required_delivery_status"]:
            result = "PASS"
        else:
            result = "FAIL"

        add(
            "ASYNC-001",
            result,
            f"Delivery state: {status}"
        )

    # CONTENT-001: Advisory subject check
    if not required("subject"):
        add("CONTENT-001", "UNKNOWN", "Subject content missing")
    elif len(campaign["subject"]) > policy["subject_max_length"]:
        add(
            "CONTENT-001",
            "WARN",
            "Subject exceeds configured advisory length"
        )
    else:
        add("CONTENT-001", "PASS", "Subject length within configured limit")

    blockers = [
        item for item in checks
        if item["status"] in ("FAIL", "UNKNOWN")
    ]

    return {
        "campaign_id": campaign.get("campaign_id", "UNIDENTIFIED"),
        "policy_version": policy["policy_version"],
        "decision": "BLOCK" if blockers else "APPROVE",
        "blocking_count": len(blockers),
        "summary": {
            "pass": sum(x["status"] == "PASS" for x in checks),
            "fail": sum(x["status"] == "FAIL" for x in checks),
            "unknown": sum(x["status"] == "UNKNOWN" for x in checks),
            "warn": sum(x["status"] == "WARN" for x in checks)
        },
        "checks": checks,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
