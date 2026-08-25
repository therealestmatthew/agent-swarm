# 01 — Event Schema

The contract. Build this first; everything else is downstream of it.

**Format:** one JSON object per line, UTF-8, appended to `runs/<run_id>/events.jsonl`.
No rewrites, no deletes, no pretty-printing, no trailing commas. A line is immutable once written.

---

## Envelope

Every event has exactly these eight fields.

```json
{"v":1,"seq":42,"ts":"2026-08-25T17:14:02.113Z","run_id":"run_7fa3","type":"finding.written","agent_id":"w3","parent_id":"dispatch","payload":{}}
```

| Field | Type | Rule |
|---|---|---|
| `v` | int | Schema version. Always `1`. Lets the renderer refuse garbage. |
| `seq` | int | Monotonic per run, starting at 0. The renderer's dedupe and ordering key. |
| `ts` | str | ISO 8601 UTC with milliseconds and trailing `Z`. |
| `run_id` | str | `run_` + 4 hex. Stable for the whole run. |
| `type` | str | Dotted, from the table below. Never invent one at runtime. |
| `agent_id` | str | **The agent the event is about**, not necessarily the process that wrote it. `dispatch`, `verify`, `reduce`, `watch`, or `w1`…`wN`. Stable for the agent's life. |
| `parent_id` | str \| null | Who spawned this agent. Drives the retry-nesting visual. |
| `payload` | object | Type-specific. Never null — use `{}`. |

**Why `seq` and not just `ts`:** parallel writers produce out-of-order timestamps at millisecond
resolution. `seq` comes from a single allocator (the dispatcher, or a file lock) and gives the
renderer a total order it can trust. If allocating `seq` across processes is fussy in the starter
repo, fall back to per-agent sequence numbers and sort by `(ts, agent_id, seq)` — but try for global
first, it makes replay exact.

---

## Event types

### Lifecycle
| Type | Emitter | Payload |
|---|---|---|
| `run.started` | dispatch | `{mission, input_ref, planned_agents}` |
| `run.finished` | dispatch | `{status: ok\|partial\|failed, duration_ms, totals:{findings, retries, cost_usd}}` |

> **Emitter is not `agent_id`.** The Emitter column says which component is *responsible* for
> writing the event. `agent.spawned` is written by the dispatcher but *describes a worker*, so it
> carries **the worker's id**. The renderer keys agents on `agent_id`; emitting eight spawns as
> `"dispatch"` overwrites one record eight times and collapses the whole rack to a single strip,
> silently. Use `EventLog.spawned()` and this is handled for you.

### Swarm
| Type | Emitter | `agent_id` holds | Payload |
|---|---|---|---|
| `agent.spawned` | dispatch | **the new agent** | `{role: worker\|verifier\|reducer, label, model, task_summary}` |
| `agent.status` | any | the agent | `{state: thinking\|working\|waiting\|blocked, note}` |
| `agent.done` | any | the agent | `{status: ok\|failed, duration_ms, tokens_in, tokens_out, cost_usd}` |

### Findings
| Type | Emitter | Payload |
|---|---|---|
| `finding.written` | worker | `{finding_id, title, severity: high\|medium\|low, confidence: 0.0-1.0, summary, evidence_ref}` |

### Loop
| Type | Emitter | Payload |
|---|---|---|
| `verify.passed` | verify | `{finding_id, attempt}` |
| `verify.failed` | verify | `{finding_id, attempt, reason}` |
| `agent.retry` | dispatch | `{of_agent_id, attempt, reason, budget_remaining}` |

### Always-on
| Type | Emitter | Payload |
|---|---|---|
| `watch.armed` | watch | `{path, patterns}` |
| `watch.triggered` | watch | `{path, change: created\|modified, reason}` |

### Reduce
| Type | Emitter | Payload |
|---|---|---|
| `reduce.started` | reduce | `{finding_count}` |
| `reduce.progress` | reduce | `{stage, pct}` |
| `reduce.finished` | reduce | `{artifact_path, headline}` |

### Utility
| Type | Emitter | Payload |
|---|---|---|
| `log.note` | any | `{level: info\|warn\|error, message}` |

`log.note` is your escape hatch. If you need to surface something at 10pm tomorrow that has no
event type, emit a note rather than inventing a type the renderer doesn't know.

---

## Invariants

The renderer assumes all of these. Violating them is the only way to break the demo.

1. **Append-only.** Open with `"a"`, one `write()` per event, `flush()` immediately.
2. **One line, no embedded newlines.** `json.dumps(..., ensure_ascii=False)` with no `indent`.
3. **`seq` is monotonic and gap-free.** Gaps make the renderer wait for a line that never comes.
4. **Every `agent.spawned` eventually gets an `agent.done`.** Otherwise cards spin forever. Emit a
   `failed` done in your exception handler — *always*.
5. **`agent_id` is stable.** A retry is a *new* agent with a new id and `parent_id` set to the
   original. Never reuse an id.
6. **The renderer is a pure function of the event list.** `render(events[0..n])` is deterministic.
   This is what makes replay identical to live. Guard it.

---

## Reference implementation

Matches your usual stack: `uv`, Ruff, strict mypy, Pydantic v2 frozen models — **but requires none
of them.** `Event` is a frozen validating pydantic model when pydantic v2 is importable and a frozen
stdlib dataclass when it isn't, selected at import. Same fields, same frozen semantics, same
rejection of unknown keys, byte-identical output — verified across v2, v1, and a bare interpreter.
So the module drops into a repo pinned to pydantic 1.x, or one with no third-party deps at all,
without an install step or a PEP-668 argument on someone else's laptop.

**`glassbox/events.py` in this repo is the implementation.** The listing below is an abridged copy
for reading. It omits `drain_outbox()` — which *is* option 1 under §Concurrency, the path this
document recommends — along with `outbox_path()`, the injectable `time_source`, and `read_log()`.
Copy the file, never this block.

`glassbox/events.py` (abridged)

```python
"""Event contract for the Glass Box board. Import-light on purpose."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AgentRole = Literal["worker", "verifier", "reducer"]
Severity = Literal["high", "medium", "low"]


class Event(BaseModel):
    """One line in events.jsonl. Immutable once constructed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    v: Literal[1] = 1
    seq: int
    ts: str
    run_id: str
    type: str
    agent_id: str
    parent_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventLog:
    """Append-only writer. One instance per process; safe across threads."""

    def __init__(self, run_dir: Path, run_id: str | None = None) -> None:
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:4]}"
        self.path = run_dir / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq = 0

    def emit(
        self,
        type: str,
        agent_id: str,
        payload: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> Event:
        with self._lock:
            event = Event(
                seq=self._seq,
                ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                run_id=self.run_id,
                type=type,
                agent_id=agent_id,
                parent_id=parent_id,
                payload=payload or {},
            )
            self._seq += 1
            line = json.dumps(event.model_dump(), ensure_ascii=False, separators=(",", ":"))
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return event
```

### Concurrency

If workers run as **threads or async tasks** in one process: the lock above is sufficient. Done.

If workers run as **separate processes** (likely if the starter repo shells out to subagents), the
in-process counter breaks. Two options, in order of preference:

1. **Funnel through the parent.** Workers write findings to `outbox/<agent_id>.jsonl` and the
   dispatcher drains them into `events.jsonl` on a 100ms tick, assigning `seq` as it goes. Single
   writer, no locking, exact ordering. This is the safer choice under time pressure.
2. **POSIX append is atomic** for writes under `PIPE_BUF` (4096 bytes) on Linux/macOS with `O_APPEND`.
   Keep events small, let `seq` be per-agent, and sort by `(ts, agent_id, seq)` in the renderer.

Pick option 1 unless the repo makes it awkward.

---

## Tonight's fixture: `simulate.py`

Build this **before** the dashboard. It is your entire dev loop, and it produces the golden log.

```
python3 -m glassbox.simulate --out runs/golden --fast      # instant, for the parachute
python3 -m glassbox.simulate --out runs/current            # real-time, ~75s

# or, via uv:  uv run python -m glassbox.simulate ...
# flags: --out  --fast  --seed N  --pace F  --no-second-cycle
```

It should emit a realistic run with:
- staggered `agent.spawned` (120–400ms apart — the bloom is a visual, don't spawn all at once)
- overlapping work windows so parallelism is obvious
- findings arriving out of order across agents
- at least one `verify.failed` → `agent.retry` → `verify.passed` chain
- one agent that goes `blocked` for a few seconds before recovering
- a reducer that runs last and emits an artifact path
- total wall-clock ~75s at 1x for the main cycle, then an 18s pause before the watcher fires —
  long enough to play underneath a 2:30 script, and the pause is the window in which you walk
  over and drag the file

Then: `cp runs/golden/events.jsonl logs/golden.jsonl`. That file is your parachute. Back it up
somewhere that isn't the laptop you'll be demoing from.

---

## Test

```bash
node tests/fold.test.mjs
```

The state fold lives inside `dashboard.html`, so the tests extract it from that file at run time
rather than keeping a second copy that can drift. Eighteen checks, in five groups:

- **Log integrity** — every line parses, `seq` gap-free from 0, `ts` monotonic, `payload` never null
- **Schema invariants** — #4 (every `agent.spawned` gets an `agent.done`), #5 (ids never reused),
  and that `run.finished` totals reconcile with what the log actually contains
- **Invariant #6, purity** — re-folding the same log yields identical state, and so does every prefix
- **Transport** — mid-line truncation, a wrong `v`, and garbage lines are all survivable
- **Restart and seek** — a second run appended to the same file resets the board instead of being
  silently discarded, and folding below `?from=` reaches the state replay would have reached

One caveat the tests pin down deliberately: **`apply()` mutates and returns its accumulator.** A
state you are still holding gets rewritten by later events, so a past state is reached by re-folding
from `initialState()`, never by keeping a reference. That is what a time-travel scrubber has to do,
and it is cheap — the whole golden log folds in well under a millisecond.

If these pass, replay works, and your parachute is real.
