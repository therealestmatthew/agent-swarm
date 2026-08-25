# Quickstart

**No install step.** There are no required dependencies — `glassbox/events.py` falls back to a
stdlib dataclass when pydantic isn't importable, so this runs on any Python 3.10+ as it sits. Run
it from the repo root (`python3 -m glassbox.simulate` imports the `glassbox` package by path).

```bash
# 1. Generate the golden log (instant, but paced like a real 110-second run)
python3 -m glassbox.simulate --out runs/golden --fast
cp runs/golden/events.jsonl logs/golden.jsonl

# 2. Check it — 18 assertions on the log and the state fold
node tests/fold.test.mjs

# 3. Serve — the dashboard fetches the log, so file:// will not work
python3 -m http.server 8080

# 4. Open
#    replay (the parachute):  http://localhost:8080/dashboard.html?replay=logs/golden.jsonl
#    seek to a beat:          ...&from=60
#    projector:               ...&big=1
#    static, no animation:    ...&seed=1
#    live:                    http://localhost:8080/dashboard.html
```

**Replay at speed 1.** The log is paced to play underneath the 3-minute script; `&speed=4` puts the
entire run on screen in 22 seconds, before you finish Beat 1.

### If you'd rather use uv

`pyproject.toml` declares the project with no dependencies, so both of these work on a clean
machine:

```bash
uv run python -m glassbox.simulate --out runs/golden --fast              # stdlib fallback
uv run --extra validate python -m glassbox.simulate --out runs/golden --fast   # + pydantic v2
```

`--extra validate` turns the event envelope back into a frozen, validating pydantic model. The
bytes written are identical either way — verified across pydantic v2, pydantic v1, and no pydantic
at all. Use it while building; you don't need it to demo.

### If the board is empty

| What you see | Cause |
|---|---|
| `ModuleNotFoundError: No module named 'glassbox'` | Run from the repo root, not from `glassbox/`. |
| `error: externally-managed-environment` from pip | You don't need pip. Skip the install; see above. |
| Board stuck on **NO RUN LOADED** | `dashboard.html` fetches over HTTP — `file://` is blocked by CORS. Serve the directory. |
| Log-not-found in replay | The path is relative to the server root. Serve from the repo root so `logs/golden.jsonl` resolves. |

For a live run, in a second terminal:

```bash
python3 -m glassbox.simulate --out runs/current      # real-time, ~110s
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
| `dashboard.html` | The board. Single file, no build step, no dependencies, fonts embedded. |
| `tests/fold.test.mjs` | 18 assertions, extracted from `dashboard.html` so they can't drift. |
| `tools/beats.py` | Prints the `&from=<seq>` seek URL for every demo beat in a log. |
| `tools/save-parachute.sh` | Saves a real run as `logs/backup-live.jsonl` and reprints the beats. |
| `tools/emit.ts`, `emit.mjs` | The emitter, paste-able, for a repo that isn't Python. |
| `09`, `10` | The two review passes, and what each one fixed. |
| `fallback/` | Budget dataset + deterministic generator |
| `logs/golden.jsonl` | The parachute. Back this up somewhere that isn't the demo laptop. |

## Verified

Run `node tests/fold.test.mjs` — these are assertions, not claims:

- 96 events, `seq` gap-free, timestamps monotonic, `payload` never null
- Every beat in `05-DEMO-SCRIPT.md` lands inside its window — verified with `tools/beats.py`
- State fold is pure — re-folding the same log yields identical state, and so does every prefix
- Every `agent.spawned` gets an `agent.done`; `run.finished` totals reconcile with the log
- 14 agents (8 lenses + verifier + reducer + 1 retry child + 3 second-cycle), 17 findings,
  1 rejection, 1 nested retry, 1 watch trigger
- `parseLines` survives half-written lines, truncation, garbage, and a wrong `v`
- A restarted run appended to the same log resets the board instead of being silently discarded
- `?from=<seq>` reaches the same state replay would have reached

Rendering checked headlessly at 1920×1080 with every external host blocked: 14 strips, the retry
nested under `w7`, 17 findings with one struck through, no horizontal scroll, fonts resolved.

## Before bed

1. ~~Download the three fonts locally~~ — **done.** All seven faces are embedded in
   `dashboard.html` as base64 woff2. Zero network requests; verified with every external host
   blocked. Don't reintroduce the `<link>`.
2. **Open the replay URL and watch it end to end**, at speed 1, with the script in your hand. If
   the parachute doesn't render tonight, it won't render tomorrow.
3. **Copy `logs/golden.jsonl` off this machine.**
4. **Decide the payload tonight** (`07`, §Cost of the swap). Swapping at T+15 costs you the
   parachute, which is the one thing that can't be rebuilt on the day.
5. Read `09-REVIEW-FINDINGS.md` §4 — the one design change still open is overlapping two slices so
   the agents can disagree. It is small, and it is the answer to the hardest question in the room.

## Tomorrow, at T+0

Copy `glassbox/events.py` and `dashboard.html` into the starter repo. Add `emit()` at five sites
(see `04-TOMORROW-RUNBOOK.md` §Integration cheatsheet). Point the dashboard at the repo's run
directory. Everything else is already done.
