"""Local append-only, hash-chained audit event prototype."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _canonical(payload):
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(payload):
    return hashlib.sha256(_canonical(payload)).hexdigest()


def read_events(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Audit ledger is not valid JSON.") from exc
    if not isinstance(events, list):
        raise ValueError("Audit ledger must be a JSON array.")
    return events


def verify_chain(events):
    previous = GENESIS
    for event in events:
        if not isinstance(event, dict):
            return False
        supplied_hash = event.get("event_hash")
        payload = {k: v for k, v in event.items() if k != "event_hash"}
        if payload.get("previous_hash") != previous:
            return False
        if supplied_hash != _digest(payload):
            return False
        previous = supplied_hash
    return True


def _atomic_write(path, events):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(events, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def append_event(path, event_type, campaign_id, actor, details):
    if not all(isinstance(x, str) and x.strip() for x in
               (event_type, campaign_id, actor)):
        raise ValueError("Event type, campaign ID and actor are required.")
    if not isinstance(details, dict):
        raise ValueError("Event details must be an object.")

    events = read_events(path)
    if not verify_chain(events):
        raise ValueError("Audit chain integrity check failed; append refused.")

    previous = events[-1]["event_hash"] if events else GENESIS
    payload = {
        "sequence": len(events) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "campaign_id": campaign_id,
        "actor": actor.strip(),
        "details": details,
        "previous_hash": previous,
    }
    payload["event_hash"] = _digest(payload)
    events.append(payload)
    _atomic_write(path, events)
    return payload
