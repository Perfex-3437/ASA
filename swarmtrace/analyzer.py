from __future__ import annotations

from collections import defaultdict
from typing import Any

from .storage import TraceStore

DEFAULT_LOOP_THRESHOLD = 3

def analyze(store: TraceStore, session_id: str, loop_threshold: int = DEFAULT_LOOP_THRESHOLD) -> list[dict[str, Any]]:
    events = store.events(session_id)
    findings: list[dict[str, Any]] = []
    run: list[Any] = []
    for row in events:
        signature = (row["sender_id"], row["recipient_id"], row["payload_body"])
        if run and signature == run[-1][0]:
            run.append((signature, row))
        else:
            run = [(signature, row)]
        if len(run) == loop_threshold:
            finding = {"kind": "infinite_loop", "severity": "high", "message": f"Identical payload repeated {loop_threshold} times between {row['sender_id']} and {row['recipient_id']}", "event_id": row["event_id"]}
            findings.append(finding)
            store.add_anomaly(session_id, **finding)
    previous: dict[str, Any] = {}
    for row in events:
        if row["message_type"] != "state_update" or not row["state_key"]:
            continue
        key = row["state_key"]
        if key in previous and previous[key]["sender_id"] != row["sender_id"]:
            finding = {"kind": "state_collision", "severity": "medium", "message": f"Agents {previous[key]['sender_id']} and {row['sender_id']} both updated state key '{key}'", "event_id": row["event_id"]}
            findings.append(finding)
            store.add_anomaly(session_id, **finding)
        previous[key] = row
    for first, second in zip(events, events[1:]):
        if first["payload_size"] and second["payload_size"] >= first["payload_size"] * 2:
            finding = {"kind": "token_bleed", "severity": "medium", "message": f"Payload grew from {first['payload_size']} to {second['payload_size']} bytes", "event_id": second["event_id"]}
            findings.append(finding)
            store.add_anomaly(session_id, **finding)
    return findings
