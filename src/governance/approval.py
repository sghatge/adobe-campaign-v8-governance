"""Human review records with deterministic BLOCK enforcement."""

import json
from pathlib import Path
from datetime import datetime, timezone

from governance.audit import append_event


ALLOWED_ACTIONS = {"APPROVE", "REJECT", "REQUEST_CHANGES"}


def read_approvals(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Approval store is invalid JSON.") from exc
    if not isinstance(records, list):
        raise ValueError("Approval store must be a JSON array.")
    return records


def record_review(
    approval_path,
    audit_path,
    campaign_id,
    deterministic_decision,
    reviewer,
    action,
    comment,
):
    if deterministic_decision not in {"APPROVE", "BLOCK"}:
        raise ValueError("Invalid deterministic decision.")
    if deterministic_decision == "BLOCK" and action == "APPROVE":
        raise ValueError("A BLOCK campaign cannot be approved or released.")
    if action not in ALLOWED_ACTIONS:
        raise ValueError("Unsupported review action.")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Reviewer identity is required.")
    if not isinstance(comment, str) or not comment.strip():
        raise ValueError("A review reason is required.")

    records = read_approvals(approval_path)
    record = {
        "review_id": f"REV-{len(records) + 1:06d}",
        "campaign_id": campaign_id,
        "deterministic_decision": deterministic_decision,
        "action": action,
        "reviewer": reviewer.strip(),
        "comment": comment.strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "release_authorized": False,
    }
    records.append(record)

    approval_path = Path(approval_path)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = approval_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    temporary.replace(approval_path)

    append_event(
        audit_path,
        "HUMAN_REVIEW_RECORDED",
        campaign_id,
        reviewer.strip(),
        {
            "review_id": record["review_id"],
            "action": action,
            "deterministic_decision": deterministic_decision,
            "release_authorized": False,
            "comment": comment.strip(),
        },
    )
    return record
