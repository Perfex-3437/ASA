from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

from .analyzer import analyze
from .interceptor import Tracer
from .storage import TraceStore


def show_session(store: TraceStore, session_id: str) -> None:
    events = store.events(session_id)
    anomalies = store.anomalies(session_id)
    print(f"Session {session_id}\nEvents: {len(events)}  Anomalies: {len(anomalies)}")
    for event in events:
        target = event["recipient_id"] or "state"
        print(f"  {event['timestamp']} {event['sender_id']} -> {target} [{event['message_type']}] {event['payload_body']}")
    for item in anomalies:
        print(f"  ! {item['severity'].upper()} {item['kind']}: {item['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="swarmtrace", description="Trace and diagnose local multi-agent programs")
    parser.add_argument("--db", default=".swarmtrace.db", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run a Python script under SwarmTrace")
    run.add_argument("--script", required=True)
    inspect = sub.add_parser("inspect", help="Inspect a recorded session")
    inspect.add_argument("session_id")
    sub.add_parser("sessions", help="List recorded sessions")
    args = parser.parse_args(argv)
    store = TraceStore(args.db)
    try:
        if args.command == "run":
            tracer = Tracer(store)
            sys.modules["swarmtrace"].tracer = tracer
            try:
                runpy.run_path(str(Path(args.script).resolve()), run_name="__main__")
            finally:
                tracer.close()
            findings = analyze(store, tracer.session_id)
            print(f"Session: {tracer.session_id}\nCaptured {len(store.events(tracer.session_id))} events, found {len(findings)} anomalies")
            return 0
        if args.command == "inspect":
            show_session(store, args.session_id)
            return 0
        for session in store.sessions():
            print(f"{session['id']}  {session['started_at']}  {session['script'] or ''}")
        return 0
    finally:
        store.close()

if __name__ == "__main__":
    raise SystemExit(main())
