"""Synthetic multi-campaign portfolio analytics and local audit history."""

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from acc_v8_qa.engine import evaluate
from acc_v8_qa.investigation import investigate


def _read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JSON storage file: {path}") from exc


def _atomic_write(path, payload):
    """Write JSON atomically so an interrupted write cannot truncate history."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def load_portfolio(path):
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        raise ValueError("Portfolio must be a JSON object.")

    if payload.get("data_classification") != "SYNTHETIC":
        raise ValueError("Only explicitly synthetic portfolio data is accepted.")

    campaigns = payload.get("campaigns")
    if not isinstance(campaigns, list) or not campaigns:
        raise ValueError("Portfolio must contain at least one campaign.")

    identifiers = set()
    for campaign in campaigns:
        if not isinstance(campaign, dict):
            raise ValueError("Every campaign must be an object.")

        campaign_id = campaign.get("campaign_id")
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            raise ValueError("Every campaign needs a valid campaign_id.")

        if campaign_id in identifiers:
            raise ValueError(f"Duplicate campaign ID: {campaign_id}")

        identifiers.add(campaign_id)

    return campaigns


def assess_portfolio(campaigns, policy):
    """Run the existing V2 deterministic and advisory engines unchanged."""
    if not isinstance(campaigns, list) or not campaigns:
        raise ValueError("Campaigns must be a non-empty list.")

    batch_id = datetime.now(timezone.utc).isoformat()
    results = []

    for campaign in campaigns:
        qa_report = evaluate(campaign, policy)
        advisory = investigate(qa_report)

        findings = advisory["summary"]
        if findings["critical"]:
            risk = "CRITICAL"
        elif findings["high"]:
            risk = "HIGH"
        elif findings["low"] or qa_report["summary"]["warn"]:
            risk = "MODERATE"
        else:
            risk = "LOW"

        results.append({
            "batch_id": batch_id,
            "assessed_at": qa_report["evaluated_at"],
            "campaign_id": qa_report["campaign_id"],
            "campaign_type": campaign.get("campaign_type", "Unspecified"),
            "segment": campaign.get("segment", "Unspecified"),
            "decision": qa_report["decision"],
            "risk_level": risk,
            "policy_version": qa_report["policy_version"],
            "blocking_count": qa_report["blocking_count"],
            "qa_summary": qa_report["summary"],
            "qa_checks": qa_report["checks"],
            "investigation_summary": advisory["summary"],
            "investigation_findings": advisory["findings"],
        })

    return results


def summarize_portfolio(results):
    if not isinstance(results, list):
        raise ValueError("Results must be a list.")

    decisions = Counter(item["decision"] for item in results)
    risks = Counter(item["risk_level"] for item in results)
    controls = Counter()

    for item in results:
        for check in item["qa_checks"]:
            if check["status"] in {"FAIL", "UNKNOWN"}:
                controls[check["rule_id"]] += 1

    return {
        "campaign_count": len(results),
        "approved": decisions["APPROVE"],
        "blocked": decisions["BLOCK"],
        "critical_campaigns": risks["CRITICAL"],
        "high_risk_campaigns": risks["HIGH"],
        "moderate_risk_campaigns": risks["MODERATE"],
        "low_risk_campaigns": risks["LOW"],
        "total_findings": sum(
            item["investigation_summary"]["finding_count"]
            for item in results
        ),
        "control_failures": dict(controls.most_common()),
    }


def append_history(path, results):
    """Append assessment batches; existing records are never overwritten."""
    history = _read_json(path, [])
    if not isinstance(history, list):
        raise ValueError("Assessment history must be a JSON array.")

    history.extend(results)
    _atomic_write(path, history)
    return len(history)


def latest_batch(history):
    if not isinstance(history, list) or not history:
        return []

    latest_id = history[-1].get("batch_id")
    return [item for item in history if item.get("batch_id") == latest_id]
