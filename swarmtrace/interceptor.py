from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from .storage import Event, TraceStore, state_hash, stable_json, utc_now

class Tracer:
    """Small explicit event hook that can wrap any agent loop."""
    def __init__(self, store: TraceStore, session_id: str | None = None, on_event: Callable[[Event], None] | None = None):
        self.store = store
        self.session_id = session_id or store.start_session()
        self.on_event = on_event

    def emit(self, sender_id: str, recipient_id: str | None, payload: Any, message_type: str = "message", state: Any = None, state_key: str | None = None) -> Event:
        encoded = stable_json(payload)
        event = Event(utc_now(), sender_id, recipient_id, message_type, payload, state_hash(state) if state is not None else None, len(encoded), state_key)
        self.store.add_event(self.session_id, event)
        if self.on_event:
            self.on_event(event)
        return event

    def message(self, sender_id: str, recipient_id: str, payload: Any, state: Any = None) -> Event:
        return self.emit(sender_id, recipient_id, payload, "message", state)

    def state_update(self, agent_id: str, key: str, value: Any, state: Any = None) -> Event:
        return self.emit(agent_id, None, {key: value}, "state_update", state, key)

    def close(self) -> None:
        self.store.end_session(self.session_id)
