"""Offline, read-only investigation of deterministic QA evidence."""

from datetime import datetime, timezone

CATALOG = {
    "AUD-001": ("HIGH", "Audience variance",
        "Compare the submitted audience with the approved baseline and investigate segmentation or source-data changes.",
        ["Approved audience baseline", "Segment definition", "Extraction timestamp", "Change history"]),
    "CON-001": ("CRITICAL", "Consent integrity",
        "Reconcile consent evidence and resolve invalid-consent records before proceeding.",
        ["Consent source and timestamp", "Consent status evidence", "Reconciliation output"]),
    "SUP-001": ("CRITICAL", "Suppression integrity",
        "Reconcile suppression rules and prove suppressed records are excluded.",
        ["Suppression ruleset version", "Exclusion evidence", "Audience reconciliation"]),
    "WF-001": ("HIGH", "Workflow readiness",
        "Inspect unfinished or failed workflow activities and confirm successful completion.",
        ["Workflow execution log", "Failed activity details", "Completion timestamp"]),
    "TYP-001": ("HIGH", "Typology control",
        "Verify that the required typology is active and correctly assigned.",
        ["Typology identifier", "Activation state", "Assignment evidence"]),
    "APR-001": ("HIGH", "Human proof approval",
        "Obtain explicit approval from an authorized reviewer. Never infer approval.",
        ["Approved proof version", "Reviewer identity or role", "Approval timestamp"]),
    "ASYNC-001": ("HIGH", "Delivery state",
        "Investigate pending or already-started delivery states before pre-flight approval.",
        ["Delivery status history", "Workflow state", "Execution audit evidence"]),
    "CONTENT-001": ("LOW", "Content advisory",
        "Review the subject line against the applicable communication standard.",
        ["Final subject line", "Content review record"]),
}


def investigate(qa_report):
    """Explain QA findings without changing the deterministic decision."""
    if not isinstance(qa_report, dict):
        raise ValueError("QA report must be an object.")

    decision = qa_report.get("decision")
    if decision not in {"APPROVE", "BLOCK"}:
        raise ValueError("Decision must be APPROVE or BLOCK.")

    checks = qa_report.get("checks")
    if not isinstance(checks, list):
        raise ValueError("QA report checks must be a list.")

    findings = []

    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("Each QA check must be an object.")

        status = check.get("status")
        if status not in {"PASS", "FAIL", "UNKNOWN", "WARN"}:
            raise ValueError("Unsupported QA check status.")

        if status == "PASS":
            continue

        rule_id = check.get("rule_id")
        if not isinstance(rule_id, str):
            rule_id = "UNCLASSIFIED"

        catalog = CATALOG.get(rule_id)

        if catalog:
            risk, title, explanation, evidence = catalog
            confidence = "MEDIUM"
        else:
            risk = "LOW"
            title = "Unclassified rule"
            confidence = "LOW"
            explanation = (
                "No rule-specific diagnostic is available. "
                "Refer this evidence to a qualified human reviewer."
            )
            evidence = [
                "Rule definition",
                "Original evidence",
                "Reviewer assessment",
            ]

        findings.append({
            "rule_id": rule_id,
            "status": status,
            "risk": risk,
            "title": title,
            "evidence_fact": str(
                check.get("message", "No evidence message supplied")
            )[:1000],
            "confidence": confidence,
            "explanation": explanation,
            "recommended_evidence": evidence,
        })

    critical = sum(f["risk"] == "CRITICAL" for f in findings)
    high = sum(f["risk"] == "HIGH" for f in findings)
    low = sum(f["risk"] == "LOW" for f in findings)

    return {
        "investigation_version": "2.0.0",
        "mode": "OFFLINE_RULE_BASED_ADVISORY",
        "campaign_reference": qa_report.get(
            "campaign_id", "UNIDENTIFIED"
        ),
        "deterministic_decision": decision,
        "decision_source": "DETERMINISTIC_QA_ENGINE",
        "summary": {
            "finding_count": len(findings),
            "critical": critical,
            "high": high,
            "low": low,
            "human_review": (
                "PENDING" if findings
                else "NOT_REQUIRED_BY_THIS_REPORT"
            ),
        },
        "findings": findings,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "No LLM or external service is called.",
            "Recommendations are generic rule-based guidance, not root-cause proof.",
            "This layer cannot modify the deterministic decision, policy, approval, or campaign execution.",
        ],
    }
