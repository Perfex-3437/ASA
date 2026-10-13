# SwarmTrace: Student Guide

## 1. What we built

SwarmTrace is a local-first Python tool for observing multi-agent programs. It records messages and state changes, saves them to SQLite, and checks the recorded events for suspicious patterns.

```text
Agent program -> Tracer -> SQLite database -> Analyzer -> CLI report
```

The project lives in these main modules:

| File | Responsibility |
|---|---|
| `swarmtrace/storage.py` | Event model and SQLite persistence |
| `swarmtrace/interceptor.py` | The `Tracer` API used by programs |
| `swarmtrace/analyzer.py` | Heuristic anomaly detection |
| `swarmtrace/cli.py` | `run`, `sessions`, and `inspect` commands |
| `tests/test_core.py` | Persistence and detection tests |

This is an example of **separation of concerns**: each module has one primary responsibility.

References:

- [Python modules](https://docs.python.org/3/tutorial/modules.html)
- [Separation of concerns](https://en.wikipedia.org/wiki/Separation_of_concerns)

## 2. Events and dataclasses

The central object is an immutable `Event`:

```python
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
```

An event is a record of one thing that happened, such as a message from `planner` to `worker`.

`@dataclass` asks Python to generate an initializer and useful representation methods. `frozen=True` makes the event effectively immutable after creation. Immutability is useful for historical records because later code should not silently change what happened.

References:

- [Dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Immutable objects](https://en.wikipedia.org/wiki/Immutable_object)

## 3. SQLite storage

`TraceStore` creates a local `.swarmtrace.db` file. It creates three tables:

- `sessions`: one record for each execution
- `events`: messages and state updates
- `anomalies`: warnings produced by the analyzer

An event has a UUID primary key. A primary key uniquely identifies a database row:

```python
str(uuid.uuid4())
```

After changing the database, the code calls `connection.commit()`. A commit permanently saves the current transaction.

SQLite is a good fit because it is built into Python, requires no server, and stores everything in one file.

References:

- [SQLite](https://sqlite.org/about.html)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [SQLite transactions](https://sqlite.org/lang_transaction.html)
- [UUIDs](https://docs.python.org/3/library/uuid.html)

## 4. Serialization and hashing

Agent payloads are usually Python dictionaries. The database stores them as JSON text:

```python
json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
```

`sort_keys=True` gives equivalent dictionaries a predictable representation. This is called stable serialization.

A state hash is a short fingerprint:

```python
hashlib.sha256(stable_json(state).encode()).hexdigest()[:16]
```

A hash helps identify whether state changed without copying the entire state into every event. A hash is not encryption and cannot reconstruct the original data.

References:

- [Python JSON](https://docs.python.org/3/library/json.html)
- [Python hashlib](https://docs.python.org/3/library/hashlib.html)
- [Cryptographic hash functions](https://en.wikipedia.org/wiki/Cryptographic_hash_function)

## 5. The `Tracer`

The tracer is the API that agent code uses:

```python
tracer.message("planner", "worker", {"task": "index files"})
tracer.state_update("worker", "status", "running")
```

Both convenience methods call the general `emit()` method. `emit()`:

1. Serializes the payload.
2. Measures its size.
3. Hashes the state if state was supplied.
4. Creates an `Event`.
5. Writes it to SQLite.
6. Optionally calls an event callback.
7. Returns the event.

The convenience methods are an abstraction. They provide a simple interface while hiding implementation details.

References:

- [Python type hints](https://docs.python.org/3/library/typing.html)
- [Abstraction](https://en.wikipedia.org/wiki/Abstraction_(computer_science))

## 6. Running a script

The CLI creates a tracer and runs a target Python script with `runpy.run_path()`:

```bash
python3 -m swarmtrace.cli run --script examples/agents.py
```

The CLI attaches the active tracer to the imported `swarmtrace` module. The target script can then use:

```python
from swarmtrace import tracer
```

The example sends the same message three times:

```python
from swarmtrace import tracer

for _ in range(3):
    tracer.message("a", "b", {"retry": True})
```

References:

- [`runpy`](https://docs.python.org/3/library/runpy.html)
- [Python import system](https://docs.python.org/3/reference/import.html)
- [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules)

## 7. The analyzer

The analyzer currently detects three patterns.

### Repeated messages

It creates a signature from sender, recipient, and serialized payload. If the same signature appears three times consecutively, it reports `infinite_loop`.

This is a heuristic, not proof. Three identical retry messages might be a bug, or they might be intentional.

### State collisions

The analyzer remembers the last agent to update each state key. If another agent updates the same key, it reports `state_collision`.

This is a conservative warning. It does not yet prove that two writes happened simultaneously or caused a race condition.

### Payload growth

If a payload is at least twice the size of the previous payload, it reports `token_bleed`.

The current implementation measures serialized JSON bytes, not actual language-model tokens. True token counts require a model-specific tokenizer such as `tiktoken` or a Hugging Face tokenizer.

References:

- [Heuristics](https://en.wikipedia.org/wiki/Heuristic)
- [Race conditions](https://en.wikipedia.org/wiki/Race_condition)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Hugging Face tokenizers](https://huggingface.co/docs/transformers/main_classes/tokenizer)

## 8. CLI commands

```bash
python3 -m swarmtrace.cli run --script examples/agents.py
python3 -m swarmtrace.cli sessions
python3 -m swarmtrace.cli inspect SESSION_ID
```

`run` executes a script and analyzes its session. `sessions` lists recorded executions. `inspect` prints all events and anomalies for one session.

The first version uses plain terminal output. The original plan mentioned Rich, which could later add colored tables, live updates, event trees, and filters.

References:

- [`argparse`](https://docs.python.org/3/library/argparse.html)
- [Rich](https://rich.readthedocs.io/)
- [Terminal user interfaces](https://en.wikipedia.org/wiki/Text-based_user_interface)

## 9. Tests

The tests use a temporary directory so they do not modify the real database:

```python
with tempfile.TemporaryDirectory() as directory:
```

They verify that events persist and that repeated messages and state collisions are detected.

An assertion states what must be true:

```python
assert len(store.events(session_id)) == 3
```

The tests were written, but `pytest` was not installed in the original environment. Python compilation and an end-to-end CLI smoke test passed.

References:

- [pytest](https://docs.pytest.org/)
- [Python assertions](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)

## 10. What is simplified

The foundation works, but several features remain future improvements:

- Replace plain output with a Rich dashboard.
- Add automatic adapters for frameworks such as LangGraph or CrewAI.
- Use real model tokenizers instead of byte length.
- Track concurrency and timestamps more precisely for state races.
- Add live streaming analysis.
- Add database migrations for schema changes.

## 11. The most important code path

Study this path first:

```text
lesson.py
  -> tracer.message()
  -> Tracer.emit()
  -> Event(...)
  -> TraceStore.add_event()
  -> SQLite events table
  -> analyzer.analyze()
  -> CLI output
```

If you understand that path, you understand the core application.

## 12. Recommended learning order

1. Python functions, classes, modules, dictionaries, and exceptions.
2. Object-oriented programming and composition.
3. Type hints and dataclasses.
4. SQL tables, rows, primary keys, indexes, and transactions.
5. JSON serialization and deserialization.
6. Hashing and fingerprints.
7. Testing with pytest.
8. Concurrency, events, queues, and race conditions.
9. Packaging with `pyproject.toml`.
10. Git branches, commits, remotes, and pull requests.

Useful starting points:

- [Official Python tutorial](https://docs.python.org/3/tutorial/)
- [Python packaging guide](https://packaging.python.org/)
- [The Git book](https://git-scm.com/book/en/v2)
- [GitHub Git basics](https://docs.github.com/en/get-started/using-git/about-git)
