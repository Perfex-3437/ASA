import tempfile
from pathlib import Path

from swarmtrace.analyzer import analyze
from swarmtrace.interceptor import Tracer
from swarmtrace.storage import TraceStore


def test_trace_persists_and_detects_loop():
    with tempfile.TemporaryDirectory() as directory:
        store = TraceStore(Path(directory) / "trace.db")
        tracer = Tracer(store)
        for _ in range(3):
            tracer.message("a", "b", {"retry": True})
        tracer.close()
        findings = analyze(store, tracer.session_id)
        assert len(store.events(tracer.session_id)) == 3
        assert findings[0]["kind"] == "infinite_loop"
        store.close()


def test_state_collision():
    with tempfile.TemporaryDirectory() as directory:
        store = TraceStore(Path(directory) / "trace.db")
        tracer = Tracer(store)
        tracer.state_update("a", "shared", 1)
        tracer.state_update("b", "shared", 2)
        tracer.close()
        assert any(item["kind"] == "state_collision" for item in analyze(store, tracer.session_id))
        store.close()
