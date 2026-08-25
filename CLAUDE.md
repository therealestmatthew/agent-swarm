# Glass Box

## What we're trying to accomplish

**A live mission-control board that makes an agent swarm visible while it runs.**

This was built for a 90-minute hackathon on three themes — *agent swarms, always-on, looping* —
with a 3-minute demo at the end. The demo is what's being optimized for, and that fact should
settle most arguments about priority.

The bet: every team builds a swarm; nobody *shows* one. Swarms live in terminal scrollback —
interleaved, scrolling faster than you can read, knowable only after they finish. So the
differentiator isn't the agents. It's that you can watch them.

All three themes land in one build:

| Theme | Mechanism | What the room sees |
|---|---|---|
| Swarm | dispatcher fans work to 6–8 workers | eight strips bloom and work at once |
| Looping | verifier re-dispatches failed findings as nested retry agents | a strip goes red, a child spawns beneath it, it goes green |
| Always-on | a folder watcher wakes the same board mid-demo | you drop a file in and the board reacts before you speak |

## The one architectural idea

Everything decouples through **one append-only JSONL event log**. Agents emit events; a
single-file HTML dashboard tails the log and renders it:

```js
state = events.reduce(apply, initialState())
```

That's the whole thing. Three properties fall out of it, and they're why the design is shaped
this way:

1. The visual can be built against a fake emitter, with no dependency on the agents.
2. Integration is `emit()` at ~5 call sites, in whatever language the agents are written in.
3. The board is a pure function of the log, so **replaying a saved log renders what happened** —
   which is the parachute if a live run dies on stage.

> Nothing renders from live agent state. Everything renders from the log. The moment the
> dashboard reads agent internals, we lose replay, repo-independence, and the parachute.

## Invariants — breaking these breaks the demo

1. **`apply()` stays pure.** No `Date.now()`, no fetch, no unseeded randomness. Anything needing
   wall-clock derives from `event.ts`. This is what makes replay work; guard it.
2. **`agent_id` is the agent the event is *about*, never whoever wrote it.** The dispatcher emits
   `agent.spawned`, but the event describes a worker, so it carries the *worker's* id. Emitting
   eight spawns as `"dispatch"` silently collapses the rack to one strip — no error, nothing in the
   console. This has been the single most expensive mistake in the project's history; see `09` KS-1.
3. **Every `agent.spawned` eventually gets an `agent.done`**, including from exception handlers, or
   strips spin forever and the board never goes idle.
4. **`seq` is monotonic and gap-free within a run.** A restart writes a new run — the renderer
   detects the backwards `seq` step and resets.
5. **Single file, no build step, no dependencies, no network.** Fonts are embedded as base64;
   the page makes zero external requests. Do not reintroduce the Google Fonts `<link>`.
6. **Don't assert what you haven't run.** Two review passes found claims in these docs that the
   code didn't support. If you write "verified", run it first.

## Working in this repo

No install step — `glassbox/events.py` falls back to a stdlib dataclass when pydantic isn't
importable, so this runs on any Python 3.10+ as it sits.

```bash
python3 -m glassbox.simulate --out runs/golden --fast   # regenerate the golden log
cp runs/golden/events.jsonl logs/golden.jsonl
node tests/fold.test.mjs                                # 18 assertions, must stay green
python3 -m http.server 8080                             # file:// is blocked by CORS
```

Then `dashboard.html?replay=logs/golden.jsonl` — at **speed 1**; the log is paced to play
underneath the script, and `&speed=4` is over before Beat 1 ends.

| Tool | For |
|---|---|
| `tools/beats.py` | prints the `&from=<seq>` seek URL for every demo beat in a log |
| `tools/save-parachute.sh` | saves a real run as `logs/backup-live.jsonl`, reprints the beats |
| `tools/build-mobile-preview.py` | standalone phone build with the log inlined |
| `tools/emit.ts`, `tools/emit.mjs` | paste-able emitters for a non-Python repo |

**Before committing a change to `dashboard.html`:** run the fold tests, then render
`logs/golden.jsonl` headlessly at **1280×720 and 1920×1080** and check strip count, the nested
retry, the rejected finding, zero console errors, and `scrollWidth === clientWidth`. The small
size is what catches new strip content overflowing. Rebuild the mobile preview too.

## Constraints that shape decisions

- **Read from six feet, on a bad projector, in a dark room.** Density is good; small text is not.
- **The log's `t=0` is script time 0:20**, because Beat 1 is narration over an empty board before
  you hit enter. Every beat comparison has to account for that offset.
- **`05`'s beat table is derived from the log**, by `tools/beats.py` — re-derive it after any
  pacing change rather than editing it by hand. It has been wrong in both directions before.
- **The parachute is `logs/backup-live.jsonl` from a real run**, not the synthetic golden log.
  It's gitignored on purpose: a committed synthetic copy would be a file that looks like the demo
  and isn't.
- **Rank by demo value ÷ implementation cost.** A 20-line change that lands beats a beautiful
  300-line one. The board already works; protecting that outranks improving it.

## Document map

| File | What it's for |
|---|---|
| `00` | Architecture, principles, risk register. Read first. |
| `01` | The event contract and emitter reference |
| `02` | Visual system: the ATC dispatch-rack direction, layout, states, motion |
| `03` | Dispatcher / worker / verifier / reducer prompts |
| `04` | Minute-by-minute runbook for the 90 minutes |
| `05` | The 3-minute beat sheet and on-stage fallbacks |
| `06`, `07` | Payload A (repo sweep) and Payload B (budget variance) |
| `08` | The adversarial review prompt |
| `09`, `10` | Two review passes: what was found, what was fixed, what was deferred and why |

## Open decisions

- **Payload A or B.** Must be settled *before* T+15: swapping on the day costs the parachute,
  because the golden log is Payload A end to end. See `07` §Cost of the swap.
- **`09` §4 — overlapping agent slices so two agents can disagree** and the verifier adjudicates.
  Still the strongest change available and still small. The convergence marks already on the board
  are the forward-compatible half; if the slices overlap, they upgrade themselves.

## Things we deliberately did not do

Recorded so they don't get re-proposed:

- **Don't fake the finding→brief lineage** by ranking on `severity × confidence`. It would look
  identical to the real thing and would be the board asserting a lineage it doesn't have, in a room
  that will ask. The real version needs a `cited_findings` payload field.
- **Don't skip, disable, or quarantine a test** to get to green.
- **Don't redesign the visual identity.** The CRT-amber-on-hangar-navy dispatch rack is deliberate
  and documented in `02`; work within it.
- **Don't add a dependency.** The no-install property is load-bearing at T+0 on an unknown machine.
