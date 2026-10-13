# SwarmTrace

SwarmTrace is a local-first Python CLI for recording and diagnosing multi-agent execution traces. It uses only the Python standard library at runtime and stores data in SQLite.

## Quick start

```bash
python3 -m swarmtrace.cli run --script examples/agents.py
python3 -m swarmtrace.cli sessions
python3 -m swarmtrace.cli inspect SESSION_ID
```

A traced script can use the injected `tracer` object:

```python
from swarmtrace import tracer

tracer.message("planner", "worker", {"task": "index files"})
tracer.state_update("worker", "status", "running")
```

The `Tracer` API can also be embedded directly:

```python
from swarmtrace import Tracer, TraceStore

store = TraceStore(".swarmtrace.db")
tracer = Tracer(store)
tracer.message("a", "b", {"hello": "world"})
tracer.close()
```

The analyzer detects repeated identical messages, competing state-key updates, and sudden payload growth. The database contains sessions, immutable events, and anomaly records.
