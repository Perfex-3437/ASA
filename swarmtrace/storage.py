from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def state_hash(state: Any) -> str:
    return hashlib.sha256(stable_json(state).encode()).hexdigest()[:16]

@dataclass(frozen=True)
class Event:
    timestamp: str
    sender_id: str
    recipient_id: str | None
    message_type: str
    payload_body: Any
    current_state_hash: str | None
    payload_size: int
    state_key: str | None = None
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            object.__setattr__(self, "event_id", str(uuid.uuid4()))

class TraceStore:
    """SQLite-backed append-only trace store."""
    def __init__(self, path: str | Path = ".swarmtrace.db") -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT, script TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT NOT NULL,
            sender_id TEXT NOT NULL, recipient_id TEXT, message_type TEXT NOT NULL,
            payload_body TEXT NOT NULL, current_state_hash TEXT, payload_size INTEGER NOT NULL,
            state_key TEXT, FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, kind TEXT NOT NULL,
            severity TEXT NOT NULL, message TEXT NOT NULL, event_id TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, timestamp);
        """)
        self.connection.commit()

    def start_session(self, script: str | None = None) -> str:
        session_id = str(uuid.uuid4())
        self.connection.execute("INSERT INTO sessions VALUES (?, ?, NULL, ?)", (session_id, utc_now(), script))
        self.connection.commit()
        return session_id

    def end_session(self, session_id: str) -> None:
        self.connection.execute("UPDATE sessions SET ended_at=? WHERE id=?", (utc_now(), session_id))
        self.connection.commit()

    def add_event(self, session_id: str, event: Event) -> None:
        self.connection.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event.event_id, session_id, event.timestamp, event.sender_id, event.recipient_id,
             event.message_type, stable_json(event.payload_body), event.current_state_hash,
             event.payload_size, event.state_key))
        self.connection.commit()

    def events(self, session_id: str) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM events WHERE session_id=? ORDER BY timestamp", (session_id,)))

    def add_anomaly(self, session_id: str, kind: str, severity: str, message: str, event_id: str | None = None) -> None:
        self.connection.execute("INSERT INTO anomalies(session_id,kind,severity,message,event_id,created_at) VALUES (?,?,?,?,?,?)",
            (session_id, kind, severity, message, event_id, utc_now()))
        self.connection.commit()

    def anomalies(self, session_id: str) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM anomalies WHERE session_id=? ORDER BY id", (session_id,)))

    def sessions(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM sessions ORDER BY started_at DESC"))

    def close(self) -> None:
        self.connection.close()
