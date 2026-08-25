"""Event contract for the Glass Box board.

Import-light on purpose: this module gets dropped into an unknown starter repo at T+0 and
must not drag dependencies with it. **It has no required dependencies.** If pydantic v2 is
importable the event is a frozen validating model; otherwise it degrades to a stdlib frozen
dataclass with the same surface. Either way the bytes on disk are identical, because the
contract is the file format, not the library.

That matters at T+0 in three ways: `python3 -m glassbox.simulate` runs on a bare interpreter
with nothing installed, a starter repo pinned to pydantic v1 cannot break it, and you never
have to argue with a PEP-668 "externally-managed-environment" on someone else's laptop.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Any, Literal

try:                                     # pydantic v2 gives validation; nothing else needs it
    from pydantic import BaseModel, ConfigDict, Field

    HAVE_PYDANTIC_V2 = hasattr(BaseModel, "model_dump")
except ImportError:                      # bare interpreter, or pydantic v1
    HAVE_PYDANTIC_V2 = False

AgentRole = Literal["worker", "verifier", "reducer"]
AgentState = Literal["thinking", "working", "waiting", "blocked"]
Severity = Literal["high", "medium", "low"]

SCHEMA_VERSION = 1


# The envelope, in the order 01-EVENT-SCHEMA.md specifies. to_line() reads these off the
# instance by name, so both implementations below serialise byte-identically.
FIELDS = ("v", "seq", "ts", "run_id", "type", "agent_id", "parent_id", "payload")


def _to_line(event: Any) -> str:
    data = {name: getattr(event, name) for name in FIELDS}
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


if HAVE_PYDANTIC_V2:

    class Event(BaseModel):  # type: ignore[no-redef]
        """One line in events.jsonl. Immutable once constructed."""

        model_config = ConfigDict(extra="forbid", frozen=True)

        v: Literal[1] = SCHEMA_VERSION
        seq: int
        ts: str
        run_id: str
        type: str
        agent_id: str
        parent_id: str | None = None
        payload: dict[str, Any] = Field(default_factory=dict)

        def to_line(self) -> str:
            return _to_line(self)

else:

    @dataclass(frozen=True)
    class Event:  # type: ignore[no-redef]
        """One line in events.jsonl. Immutable once constructed.

        Stdlib fallback. Same fields, same output; unknown keys raise TypeError, which is
        what ``extra="forbid"`` does on the pydantic path, so ``read_log`` behaves the same.
        """

        seq: int
        ts: str
        run_id: str
        type: str
        agent_id: str
        parent_id: str | None = None
        payload: dict[str, Any] = field(default_factory=dict)
        v: int = SCHEMA_VERSION

        def to_line(self) -> str:
            return _to_line(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class EventLog:
    """Append-only writer. One instance per process; safe across threads.

    For multi-PROCESS workers, do not instantiate this in the worker. Have workers write to
    ``outbox/<agent_id>.jsonl`` and drain them from the dispatcher with ``drain_outbox``.
    Single writer, no locking, exact ordering.
    """

    def __init__(
        self,
        run_dir: Path | str,
        run_id: str | None = None,
        time_source: Callable[[], str] | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:4]}"
        # Overridable so the simulator can generate a log instantly while still writing
        # realistic inter-event gaps — replay pacing reads ts, not wall clock.
        self._time_source = time_source or _now
        self.path = self.run_dir / "events.jsonl"
        self.outbox_dir = self.run_dir / "outbox"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq = 0
        self._drained: dict[str, int] = {}

    # -- core -----------------------------------------------------------------

    def emit(
        self,
        type: str,
        agent_id: str,
        payload: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> Event:
        """Append one event. Flushes and fsyncs so the dashboard sees it within a poll."""
        with self._lock:
            event = Event(
                seq=self._seq,
                ts=self._time_source(),
                run_id=self.run_id,
                type=type,
                agent_id=agent_id,
                parent_id=parent_id,
                payload=payload or {},
            )
            self._seq += 1
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(event.to_line() + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return event

    # -- multi-process support ------------------------------------------------

    def outbox_path(self, agent_id: str) -> Path:
        return self.outbox_dir / f"{agent_id}.jsonl"

    def drain_outbox(self) -> list[Event]:
        """Pull new lines from every worker outbox into the main log, assigning seq.

        Call this on a ~100ms tick from the dispatcher. Tracks how many lines it has already
        consumed per file, so it is safe to call repeatedly while workers are still writing.
        Partially-written trailing lines are left for the next tick.

        A worker can write anything, so every line is skipped rather than raised on, and the
        consumed count is persisted in a ``finally``. Both matter: with an unguarded ``emit()``
        and the count as the last statement, a single malformed line would re-emit every line
        before it with fresh ``seq`` on every tick, forever, and never deliver anything after it.
        """
        drained: list[Event] = []
        for path in sorted(self.outbox_dir.glob("*.jsonl")):
            agent_id = path.stem
            already = self._drained.get(agent_id, 0)
            try:
                lines = path.read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                continue
            # A trailing element that isn't followed by "\n" is a partial write. Only take
            # complete lines: everything before the final split element.
            complete = lines[:-1]
            try:
                for raw in complete[already:]:
                    already += 1
                    if not raw.strip():
                        continue
                    try:
                        record = json.loads(raw)
                        drained.append(
                            self.emit(
                                type=record.get("type", "log.note"),
                                agent_id=record.get("agent_id", agent_id),
                                payload=record.get("payload", {}),
                                parent_id=record.get("parent_id"),
                            )
                        )
                    except Exception:
                        # Malformed JSON, or a record the Event contract rejects. Drop the
                        # line and keep draining — one bad worker must not stall the run.
                        continue
            finally:
                self._drained[agent_id] = already
        return drained

    # -- convenience ----------------------------------------------------------

    def run_started(self, mission: str, planned_agents: int, input_ref: str = "") -> Event:
        return self.emit(
            "run.started",
            "dispatch",
            {"mission": mission, "planned_agents": planned_agents, "input_ref": input_ref},
        )

    def run_finished(self, status: str, duration_ms: int, totals: dict[str, Any]) -> Event:
        return self.emit(
            "run.finished", "dispatch", {"status": status, "duration_ms": duration_ms, "totals": totals}
        )

    def spawned(
        self,
        agent_id: str,
        role: AgentRole,
        label: str,
        model: str = "",
        task_summary: str = "",
        parent_id: str | None = None,
    ) -> Event:
        return self.emit(
            "agent.spawned",
            agent_id,
            {"role": role, "label": label, "model": model, "task_summary": task_summary},
            parent_id=parent_id,
        )

    def status(self, agent_id: str, state: AgentState, note: str = "") -> Event:
        return self.emit("agent.status", agent_id, {"state": state, "note": note})

    def finding(
        self,
        agent_id: str,
        finding_id: str,
        title: str,
        severity: Severity,
        confidence: float,
        summary: str,
        evidence_ref: str,
    ) -> Event:
        return self.emit(
            "finding.written",
            agent_id,
            {
                "finding_id": finding_id,
                "title": title,
                "severity": severity,
                "confidence": round(confidence, 2),
                "summary": summary,
                "evidence_ref": evidence_ref,
            },
        )

    def done(
        self,
        agent_id: str,
        status: str = "ok",
        duration_ms: int = 0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
    ) -> Event:
        return self.emit(
            "agent.done",
            agent_id,
            {
                "status": status,
                "duration_ms": duration_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost_usd, 4),
            },
        )


def read_log(path: Path | str) -> list[Event]:
    """Read a log back. Skips malformed and wrong-version lines rather than raising."""
    events: list[Event] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if record.get("v") != SCHEMA_VERSION:
            continue
        try:
            events.append(Event(**record))
        except Exception:
            continue
    return events
