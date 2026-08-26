"""Find the demo beats in a run log and print the seek URLs for them.

    python3 tools/beats.py                        # logs/golden.jsonl
    python3 tools/beats.py logs/backup-live.jsonl
    python3 tools/beats.py --port 8080

05-DEMO-SCRIPT.md's entire on-stage failure plan is "switch to the replay tab and seek to
the beat you were on". Nothing computed those seq numbers, so they had to be found by hand
in a JSONL file — and after a real run they all change. This prints them.

The offset matters: the log's t=0 is script time 0:20, because Beat 1 is narration over an
empty board before you hit enter. Script times below already include it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Beat 1 is narration over an empty board; the run starts when you hit enter at its end.
SCRIPT_OFFSET_S = 20

# (beat, label, event type, which occurrence) — matched in log order.
BEATS = [
    ("2", "bloom", "run.started", "first"),
    ("2", "first finding", "finding.written", "first"),
    ("3", "rejection", "verify.failed", "first"),
    ("3", "retry spawned", "agent.retry", "first"),
    ("4", "collapse", "reduce.started", "first"),
    ("4", "brief", "reduce.finished", "first"),
    ("5", "listening", "watch.armed", "first"),
    ("5", "wake-up", "watch.triggered", "first"),
]


def clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Print demo-beat seek URLs for a run log.")
    ap.add_argument("log", nargs="?", default="logs/golden.jsonl", type=Path)
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    if not args.log.exists():
        sys.exit(f"no such log: {args.log}\nRun tools/save-parachute.sh after a live run.")

    events = []
    for raw in args.log.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    if not events:
        sys.exit(f"{args.log} has no readable events")

    def at(event: dict) -> float:
        stamp = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        return stamp(event["ts"]) - stamp(events[0]["ts"])

    base = f"http://localhost:{args.port}/dashboard.html?replay={args.log}"

    print(f"\n{args.log}  —  {len(events)} events, {clock(at(events[-1]))} long")
    print(f"script time = log time + 0:{SCRIPT_OFFSET_S}  (Beat 1 runs before you hit enter)\n")
    print(f"  {'beat':<5} {'moment':<14} {'seq':>4}  {'log':>5}  {'script':>6}   seek")
    print(f"  {'-'*5} {'-'*14} {'-'*4}  {'-'*5}  {'-'*6}   {'-'*4}")

    for beat, label, etype, _which in BEATS:
        found = next((e for e in events if e.get("type") == etype), None)
        if found is None:
            print(f"  {beat:<5} {label:<14} {'—':>4}  {'—':>5}  {'—':>6}   (no {etype} in this log)")
            continue
        seq = found["seq"]
        print(
            f"  {beat:<5} {label:<14} {seq:>4}  {clock(at(found)):>5}  "
            f"{clock(at(found) + SCRIPT_OFFSET_S):>6}   &from={seq}"
        )

    print("\nfull URLs, ready to paste:\n")
    for beat, label, etype, _which in BEATS:
        found = next((e for e in events if e.get("type") == etype), None)
        if found is not None:
            print(f"  beat {beat} · {label}\n    {base}&from={found['seq']}")
    print(
        "\nreminder: hold these in the address bar, do not pre-load them. "
        "Replay animates on load,\nso a tab left open at a beat will have played past it.\n"
    )


if __name__ == "__main__":
    main()
