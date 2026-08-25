# Quickstart

```bash
pip install pydantic          # or: uv add pydantic

# 1. Generate the golden log (instant, but paced like a real 33-second run)
python3 -m glassbox.simulate --out runs/golden --fast
cp runs/golden/events.jsonl logs/golden.jsonl

# 2. Serve — the dashboard fetches the log, so file:// will not work
python3 -m http.server 8080

# 3. Open
#    replay (the parachute):  http://localhost:8080/dashboard.html?replay=logs/golden.jsonl&speed=2
#    projector:               ...&big=1
#    static, no animation:    ...&seed=1
#    live:                    http://localhost:8080/dashboard.html
```

For a live run, in a second terminal:

```bash
python3 -m glassbox.simulate --out runs/current      # real-time, ~33s
```

Then open `dashboard.html` with no query string — it polls `runs/current/events.jsonl` every 250ms.

---

## What's here

| Path | What it is |
|---|---|
| `00`–`05` | The plan: architecture, schema, design, agent contracts, runbook, demo script |
| `06`, `07` | Payload A (repo sweep) and Payload B (budget fallback) |
| `08` | The adversarial review prompt to paste into Claude Code |
| `glassbox/events.py` | Event contract + append-only writer. **This is the file you drop into the starter repo.** |
| `glassbox/simulate.py` | Fake swarm. Your dev loop, and the golden log's source. |
| `dashboard.html` | The board. Single file, no build step, no dependencies. |
| `fallback/` | Budget dataset + deterministic generator |
| `logs/golden.jsonl` | The parachute. Back this up somewhere that isn't the demo laptop. |

## Verified

- 92 events, `seq` gap-free, timestamps monotonic
- State fold is pure — replaying the same log twice yields identical state
- 14 agents (8 lenses + verifier + reducer + 1 retry child + 3 second-cycle), 17 findings,
  1 rejection, 1 nested retry, 1 watch trigger
- `parseLines` drops half-written trailing lines rather than throwing

## Before bed

1. **Download the three fonts locally** and swap the Google Fonts `<link>` for `@font-face`.
   Venue wifi will not be your friend, and a fallback font visibly wrecks the strip layout.
2. **Open the replay URL and watch it end to end.** If the parachute doesn't render tonight, it
   won't render tomorrow.
3. **Copy `logs/golden.jsonl` off this machine.**
4. Run the `08` prompt through Claude Code and act on the kill shots before you build anything else.

## Tomorrow, at T+0

Copy `glassbox/events.py` and `dashboard.html` into the starter repo. Add `emit()` at five sites
(see `04-TOMORROW-RUNBOOK.md` §Integration cheatsheet). Point the dashboard at the repo's run
directory. Everything else is already done.
