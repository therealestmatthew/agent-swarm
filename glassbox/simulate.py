"""Fake swarm. Your entire dev loop tonight, and the source of the golden log.

    python3 -m glassbox.simulate --out runs/current            # live, ~75s
    python3 -m glassbox.simulate --out runs/golden --fast      # instant, for the parachute

No dependencies required; run it from the repo root. `uv run python -m ...` works too.

Emits a run that exercises every visual on the board: staggered spawns, overlapping work,
out-of-order findings, one blocked agent, one verification failure that retries and passes,
a reducer, and an always-on second cycle.
"""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from glassbox.events import EventLog

MISSION = "Eight specialists review the same codebase simultaneously, each through one lens."

# Every sleep is multiplied by this. The demo script narrates for 2:30; a run that is over
# in 33 seconds cannot be replayed underneath it. 2.25 puts the run at ~75s, inside the
# 45-90s window 00-MASTER-PLAN specifies, with room to replay at speed=1.
PACE = 2.25

# Virtual seconds between the brief landing and the watcher firing. Beat 5 needs long
# enough for you to stop talking, walk to the laptop and drag the file — in replay this
# gap is the only thing standing between the reducer and the wake-up.
WATCH_GAP_S = 8.0

LENSES: list[tuple[str, str]] = [
    ("w1", "SECRETS"),
    ("w2", "VALIDATION"),
    ("w3", "ERROR PATHS"),
    ("w4", "DEPENDENCIES"),
    ("w5", "TEST COVERAGE"),
    ("w6", "CONCURRENCY"),
    ("w7", "DOCS DRIFT"),
    ("w8", "DEAD WEIGHT"),
]

FINDINGS: dict[str, list[tuple[str, str, str, float, str]]] = {
    "w1": [
        ("Hardcoded API key in test fixture", "high", "tests/fixtures/config.json:12", 0.94,
         "Live-format credential committed in a fixture, not a placeholder."),
        ("Token logged at info level", "medium", "src/auth/session.py:88", 0.81,
         "Session token written to application logs on every refresh."),
    ],
    "w2": [
        ("Unvalidated path reaches file open", "high", "src/ingest/loader.py:41", 0.89,
         "User-supplied filename passed to open() without normalization or allowlist."),
        ("Subprocess call builds shell string", "high", "src/tools/convert.py:57", 0.86,
         "Command assembled by concatenation with shell=True."),
    ],
    "w3": [
        ("Bare except swallows all failures", "medium", "src/pipeline/run.py:132", 0.92,
         "Except block catches everything and continues with partial state."),
        ("Temp files leak on error path", "low", "src/ingest/loader.py:73", 0.68,
         "Cleanup only runs on the success branch."),
    ],
    "w4": [
        ("Four imports absent from manifest", "medium", "pyproject.toml:18", 0.87,
         "Modules imported at runtime are not declared as dependencies."),
        ("Deprecated datetime.utcnow in use", "low", "src/util/clock.py:9", 0.79,
         "Removed in newer runtimes; naive datetimes propagate downstream."),
    ],
    "w5": [
        ("Retry logic has no test coverage", "high", "src/pipeline/retry.py:24", 0.83,
         "The branch that decides whether to retry is never exercised."),
        ("Assertion cannot fail as written", "medium", "tests/test_loader.py:56", 0.9,
         "Compares a value to itself after transformation."),
    ],
    "w6": [
        ("Shared dict mutated across tasks", "high", "src/pipeline/state.py:30", 0.85,
         "Concurrent workers write the same dict with no lock."),
        ("HTTP calls have no timeout", "medium", "src/client/api.py:17", 0.88,
         "A hung upstream blocks the worker indefinitely."),
    ],
    "w7": [
        ("README documents a flag that is gone", "medium", "README.md:44", 0.91,
         "Documented --strict flag has no corresponding argument in the parser."),
        # This is the seeded overreach: it will fail verification on attempt 1.
        ("Retry backoff contradicts architecture doc", "high", "ARCHITECTURE.md:21", 0.72,
         "Doc specifies exponential backoff; code appears to retry immediately."),
    ],
    "w8": [
        ("Unreachable branch after early return", "low", "src/tools/convert.py:96", 0.74,
         "Condition cannot be true given the guard above it."),
    ],
}

RETRY_FINDING = (
    "Architecture doc overstates retry policy",
    "medium",
    "ARCHITECTURE.md:21",
    0.88,
    "Doc claims exponential backoff; code has none. The doc is wrong, not the code.",
)


@dataclass
class Clock:
    """Wall-clock, or instant when --fast.

    Either way it advances a virtual timeline that becomes the events' ``ts``. That is what
    lets ``--fast`` generate the golden log in a second while replay still paces it like a
    real 60-second run.
    """

    fast: bool = False
    pace: float = 1.0
    virtual: float = field(default_factory=time.time)

    def sleep(self, seconds: float) -> None:
        scaled = seconds * self.pace
        self.virtual += scaled
        if not self.fast:
            time.sleep(scaled)

    def stamp(self) -> str:
        # Every event nudges the clock 1ms so seq order and ts order never disagree.
        self.virtual += 0.001
        return (
            datetime.fromtimestamp(self.virtual, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


def simulate(out: Path, fast: bool, seed: int, second_cycle: bool, pace: float = PACE) -> Path:
    rng = random.Random(seed)
    clock = Clock(fast=fast, pace=pace)
    log = EventLog(out, time_source=clock.stamp)
    started_virtual = clock.virtual

    # run.finished totals must reconcile with what was actually emitted. Hardcoding them
    # puts the counters on screen in contradiction with the log they are folded from.
    tally = {"findings": 0, "retries": 0, "cost_usd": 0.0}

    def done(agent_id: str, **kw: object) -> None:
        tally["cost_usd"] += float(kw.get("cost_usd", 0.0))
        log.done(agent_id, **kw)  # type: ignore[arg-type]

    def finding(agent_id: str, *args: object) -> None:
        tally["findings"] += 1
        log.finding(agent_id, *args)  # type: ignore[arg-type]

    log.run_started(MISSION, planned_agents=len(LENSES), input_ref="./")

    # --- spawn, staggered. The bloom is a visual; do not spawn all at once. ---
    for agent_id, lens in LENSES:
        log.spawned(agent_id, "worker", lens, model="claude-haiku-4-5", task_summary=f"{lens} lens")
        log.status(agent_id, "thinking", "reading tree")
        clock.sleep(rng.uniform(0.12, 0.40))

    # --- overlapping work. Findings arrive interleaved across agents. ---
    queue: list[tuple[float, str, tuple[str, str, str, float, str]]] = []
    for agent_id, _lens in LENSES:
        offset = rng.uniform(1.5, 4.0)
        for planted in FINDINGS.get(agent_id, []):
            offset += rng.uniform(2.5, 6.5)
            queue.append((offset, agent_id, planted))
    queue.sort(key=lambda item: item[0])

    for agent_id, _lens in LENSES:
        log.status(agent_id, "working", "scanning")

    blocked_at = rng.uniform(4.0, 7.0)
    blocked_done = blocked_at + 3.2
    blocked_agent = "w4"
    blocked_fired = False
    recovered = False

    elapsed = 0.0
    counters = {agent_id: 0 for agent_id, _ in LENSES}

    for offset, agent_id, (title, severity, ref, confidence, summary) in queue:
        step = max(0.0, offset - elapsed)
        clock.sleep(step)
        elapsed = offset

        if not blocked_fired and elapsed >= blocked_at:
            log.status(blocked_agent, "blocked", "rate limited, backing off")
            blocked_fired = True
        if blocked_fired and not recovered and elapsed >= blocked_done:
            log.status(blocked_agent, "working", "resumed")
            recovered = True

        counters[agent_id] += 1
        finding(
            agent_id,
            f"{agent_id}-{counters[agent_id]:02d}",
            title,
            severity,
            confidence,
            summary,
            ref,
        )

    # --- workers finish, staggered ---
    for agent_id, _lens in LENSES:
        clock.sleep(rng.uniform(0.15, 0.5))
        done(
            agent_id,
            status="ok",
            duration_ms=int(rng.uniform(18_000, 52_000)),
            tokens_in=rng.randint(9_000, 24_000),
            tokens_out=rng.randint(400, 1_400),
            cost_usd=rng.uniform(0.004, 0.019),
        )

    # --- the loop: verify, fail one, retry as a nested child, pass ---
    log.spawned("verify", "verifier", "VERIFY", model="claude-haiku-4-5")
    log.status("verify", "working", "checking evidence refs")
    clock.sleep(1.4)

    all_ids = [f"{a}-{i + 1:02d}" for a, _ in LENSES for i in range(len(FINDINGS.get(a, [])))]
    bad_id = "w7-02"
    for finding_id in all_ids:
        clock.sleep(0.12)
        if finding_id == bad_id:
            log.emit(
                "verify.failed",
                "verify",
                {"finding_id": finding_id, "attempt": 1, "reason": "claim broader than cited evidence"},
            )
        else:
            log.emit("verify.passed", "verify", {"finding_id": finding_id, "attempt": 1})

    clock.sleep(0.6)
    tally["retries"] += 1
    log.emit(
        "agent.retry",
        "dispatch",
        {"of_agent_id": "w7", "attempt": 1, "reason": "claim broader than cited evidence", "budget_remaining": 2},
    )
    log.spawned("w7r1", "worker", "DOCS DRIFT · amended", model="claude-sonnet-5", parent_id="w7")
    log.status("w7r1", "working", "re-reading ARCHITECTURE.md against source")
    clock.sleep(2.6)

    title, severity, ref, confidence, summary = RETRY_FINDING
    finding("w7r1", f"{bad_id}r1", title, severity, confidence, summary, ref)
    log.emit("verify.passed", "verify", {"finding_id": f"{bad_id}r1", "attempt": 2})
    done("w7r1", status="ok", duration_ms=2_600, tokens_in=6_100, tokens_out=310, cost_usd=0.011)
    done("verify", status="ok", duration_ms=9_400, tokens_in=14_000, tokens_out=900, cost_usd=0.008)

    # --- reduce ---
    verified = len(all_ids)
    log.spawned("reduce", "reducer", "REDUCE", model="claude-opus-5")
    log.emit("reduce.started", "reduce", {"finding_count": verified})
    for stage, pct in (("clustering", 30), ("ranking", 60), ("drafting", 85)):
        clock.sleep(0.9)
        log.emit("reduce.progress", "reduce", {"stage": stage, "pct": pct})
    clock.sleep(1.1)
    log.emit(
        "reduce.finished",
        "reduce",
        {
            "artifact_path": "runs/current/brief.md",
            "headline": "Two credentials and one unvalidated path are live in main; fix before the next deploy.",
        },
    )
    done("reduce", status="ok", duration_ms=4_800, tokens_in=31_000, tokens_out=2_100, cost_usd=0.086)

    log.run_finished(
        "ok",
        # Virtual, not wall-clock: with --fast the real elapsed time is ~0, which would
        # put a 0ms duration in a log whose timestamps span 75 seconds.
        duration_ms=int((clock.virtual - started_virtual) * 1000),
        totals={
            "findings": tally["findings"],
            "retries": tally["retries"],
            "cost_usd": round(tally["cost_usd"], 4),
        },
    )

    # --- always-on: the board goes idle, then wakes ---
    log.emit("watch.armed", "watch", {"path": "runs/inbox", "patterns": ["*.py", "*.md", "*.csv"]})
    if second_cycle:
        # Long enough to stop talking, walk over, and drag the file. See WATCH_GAP_S.
        clock.sleep(WATCH_GAP_S)
        log.emit("watch.triggered", "watch", {"path": "hotfix_auth.py", "change": "created"})
        cycle2_started = clock.virtual
        log.run_started("Re-sweep triggered by inbox change", planned_agents=3, input_ref="hotfix_auth.py")
        for agent_id, lens in LENSES[:3]:
            log.spawned(f"{agent_id}c2", "worker", lens, model="claude-haiku-4-5")
            log.status(f"{agent_id}c2", "working", "scanning hotfix_auth.py")
            clock.sleep(rng.uniform(0.15, 0.35))
        clock.sleep(2.0)
        finding(
            "w1c2",
            "w1c2-01",
            "New file reintroduces the hardcoded key",
            "high",
            0.96,
            "Same credential as tests/fixtures/config.json:12, copied into the hotfix.",
            "hotfix_auth.py:7",
        )
        # Close the cycle. Every agent.spawned gets an agent.done (schema invariant 4) —
        # without these the board ends on three strips spinning forever and the LISTENING
        # rail never comes back, which is both a broken invariant and a weaker last frame.
        for agent_id, _lens in LENSES[:3]:
            clock.sleep(rng.uniform(0.2, 0.5))
            done(
                f"{agent_id}c2",
                status="ok",
                duration_ms=int(rng.uniform(6_000, 11_000)),
                tokens_in=rng.randint(3_000, 7_000),
                tokens_out=rng.randint(150, 500),
                cost_usd=rng.uniform(0.002, 0.007),
            )
        log.run_finished(
            "ok",
            duration_ms=int((clock.virtual - cycle2_started) * 1000),
            totals={
                "findings": tally["findings"],
                "retries": tally["retries"],
                "cost_usd": round(tally["cost_usd"], 4),
            },
        )

    return log.path


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a Glass Box run.")
    parser.add_argument("--out", type=Path, default=Path("runs/current"))
    parser.add_argument("--fast", action="store_true", help="No real sleeps — generate instantly.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--pace", type=float, default=PACE,
                        help=f"Multiplier on every sleep. Default {PACE} targets a ~75s run.")
    parser.add_argument("--no-second-cycle", action="store_true")
    args = parser.parse_args()

    if args.out.exists():
        for stale in args.out.glob("events.jsonl"):
            stale.unlink()

    path = simulate(
        args.out, fast=args.fast, seed=args.seed,
        second_cycle=not args.no_second_cycle, pace=args.pace,
    )
    count = sum(1 for _ in path.open(encoding="utf-8"))
    print(f"wrote {count} events to {path}")


if __name__ == "__main__":
    main()
