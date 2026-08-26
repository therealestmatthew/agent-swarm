# Glass Box — archived

**Status: frozen. Built for a 90-minute hackathon, demoed in three minutes, and it won.**
Nothing here is a live plan. It is kept because parts of it are worth reusing, and because the
reasoning is worth not repeating.

Glass Box was a live mission-control board that made an agent swarm visible while it ran: agents
appended to one JSONL event log, and a single-file HTML dashboard folded that log into state and
rendered it. It was the visual half of what has since become the Agentic SDLC Orchestration design
in `plan/` — the pipeline the visuals were depicting is now the thing being designed for real.

## Why it's archived rather than carried forward

The design work moved from "show a swarm running" to "specify the pipeline properly." Those need
different artifacts. Most of what's here is shaped by constraints that no longer apply — a
90-minute build, a 3-minute script, a projector in a dark room — and reading it as current guidance
would be actively misleading.

Visualization may return later, most likely as an agent health and monitoring dashboard rather than
a demo piece. When it does, start from §Still worth reusing below, not from the demo docs.

## What's here

| Path | What it is |
|---|---|
| `00`–`10`, `QUICKSTART.md` | The full plan, two adversarial review passes, and the runbook/demo script |
| `dashboard.html` | The board. Single file, fonts embedded, no build step, no network |
| `glassbox/` | Event contract + append-only writer, and the simulator that produced the golden log |
| `tests/fold.test.mjs` | 18 assertions, extracted from `dashboard.html` at run time so they can't drift |
| `tools/` | Beat seeker, parachute saver, mobile preview builder, paste-able TS/JS emitters |
| `fallback/` | Deterministic budget dataset with planted anomalies |
| `logs/golden.jsonl` | The synthetic run the board replays |

It still runs, from this directory, with no install step:

```bash
python3 -m glassbox.simulate --out runs/golden --fast
cp runs/golden/events.jsonl logs/golden.jsonl
node tests/fold.test.mjs
python3 -m http.server 8080     # then dashboard.html?replay=logs/golden.jsonl
```

## Still worth reusing

Four things here earned their keep and would survive into a monitoring dashboard:

1. **The append-only event log as the only coupling.** Agents emit; the renderer folds. Nothing
   reads agent internals. That decoupling is why the board could be built before the agents
   existed, integrated with five `emit()` calls, and replayed exactly.
2. **The renderer as a pure fold** — `state = events.reduce(apply, initialState())`. No wall clock,
   no fetch, no unseeded randomness inside `apply()`. Replay works because of this and nothing else.
3. **`agent_id` is the agent an event is *about*, never whoever wrote it.** This was the single most
   expensive mistake in the project; see `09` KS-1. Any future emitter should make it a required
   first argument, as `tools/emit.ts` does.
4. **`10-SECOND-PASS.md` §6** — the deferred list, with reasons. Several of those findings are
   general (validation policies diverging across readers of one "contract", tests that enshrine the
   bug they should catch) and would recur in any similar system.

## What not to carry forward

The demo-shaped constraints: the 6–8 strip rack (`02` is explicit that it stops being readable
above eight, and the SDLC design has 22 agents), the 3-minute beat pacing, the projector-first
palette decisions, and the parachute discipline around `logs/backup-live.jsonl`. Those were right
for a stage and are wrong for an ops dashboard.

One design gap worth knowing about before rebuilding: the board has no concept of a **phase** or a
**human gate**. The SDLC pipeline has eight of the first and five of the second, and "the pipeline
stops and waits for a person" is among the most important things such a dashboard would need to
show. It was never renderable here.
