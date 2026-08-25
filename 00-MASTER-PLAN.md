# GLASS BOX — Master Plan

**One line:** A live mission-control board that makes an agent swarm visible while it runs.

**Why it wins:** Every team will build a swarm. Nobody will *show* one. Swarms today live in
terminal scrollback — invisible, sequentially scrolled, impossible to feel. Glass Box puts the
parallelism on screen: agents spawn as cards, work in visible parallel, fail and retry in front of
the audience, and a reducer assembles the answer while everyone watches. Same underlying work as
the rest of the room, categorically different reaction.

---

## Document map

| File | What it's for | When you need it |
|---|---|---|
| `00-MASTER-PLAN.md` | This file. Architecture, principles, risk. | Read first |
| `01-EVENT-SCHEMA.md` | The event contract + emitter reference impl | Build first, tonight |
| `02-DASHBOARD-DESIGN.md` | Visual direction, layout, states, motion | Build second, tonight |
| `03-AGENT-CONTRACTS.md` | Dispatcher / worker / verifier / reducer prompts | Tonight if time |
| `04-TOMORROW-RUNBOOK.md` | Minute-by-minute for the 90 minutes | Tomorrow, open on second screen |
| `05-DEMO-SCRIPT.md` | The 3-minute beat sheet + fallbacks | Tomorrow, memorize |

---

## The architecture, and why it's shaped this way

Everything decouples through **one append-only JSONL event log**.

```
                      ┌──────────────┐
   watcher ──────────▶│              │
   (always-on)        │  dispatcher  │
                      │              │
                      └──────┬───────┘
                             │ fan-out
        ┌──────────┬─────────┼─────────┬──────────┐
        ▼          ▼         ▼         ▼          ▼
     worker 1   worker 2  worker 3  worker 4   worker N
        │          │         │         │          │
        └──────────┴────┬────┴─────────┴──────────┘
                        │  every agent appends events
                        ▼
                 ┌─────────────┐
                 │ events.jsonl│ ◀── single source of truth
                 └──────┬──────┘
                        │ tailed by
              ┌─────────┴─────────┐
              ▼                   ▼
        verifier (loop)      dashboard.html
              │              (pure renderer)
              └─▶ re-dispatch      │
                                   ▼
                              reducer ──▶ artifact.md
```

### The three properties this buys you

**1. You can build the whole visual tonight without the starter repo.**
The dashboard consumes events, not code. Write a fake emitter, generate a plausible log, build the
entire UI against it. Tomorrow's repo changes nothing about the renderer.

**2. Integration tomorrow is one function call.**
Whatever the starter repo's agents do, you add `emit(...)` at four or five points. Repo-agnostic by
construction. If they hand you TypeScript instead of Python, the emitter is nine lines in any
language — the contract is the file format, not the library.

**3. The demo cannot fail.**
The dashboard is a **pure function of the event list**. That means replay is free: point it at last
night's golden log at 4x speed and it renders identically. If the live run dies at minute 88, you
present the replay and the audience cannot tell. Build the golden log tonight; it is your parachute
and your dev fixture at the same time.

> **Hold this line all day:** nothing renders from live agent state. Everything renders from the
> log. The moment you let the dashboard call into agent internals, you lose replay, you lose
> repo-independence, and you lose your parachute.

---

## How the three hackathon themes land in one build

| Theme | Mechanism | What the audience actually sees |
|---|---|---|
| **Agent swarm** (P1) | Dispatcher fans work into a task queue; N workers claim and execute in parallel; reducer synthesizes | 8 cards bloom at once and work simultaneously — the parallelism is the spectacle |
| **Always-on** (P2) | A watcher on an input folder; on change, it triggers a new dispatch cycle into the same board | You drop a file in mid-demo and the board wakes up unprompted |
| **Looping** (P3) | Verifier re-checks findings; failures re-dispatch as child tasks with an attempt counter and a hard budget cap | A card flips red, a retry card spawns beneath it, and it turns green — the loop is *watched*, not explained |

You are not building three things. You are building one thing that reads as three.

---

## Scope discipline

**The wow is the board.** Protect it. Everything else is negotiable.

Build order, strictly:

1. **Event schema + emitter** — 20 min. Nothing works without the contract.
2. **Dashboard against fake events** — the bulk of tonight. This is the deliverable.
3. **Golden log** — record one good synthetic run to `logs/golden.jsonl`. Parachute secured.
4. **Agent prompts** — repo-agnostic templates, ready to paste.
5. **Watcher** — 15 min, and it's the closing beat, so don't skip it.
6. **Verifier loop** — last. If it's cut, the demo still lands.

### Cut list, in the order you cut them
1. Cost ledger (nice, not load-bearing)
2. Verifier loop → if cut, remove the retry beat from the demo script
3. Live execution entirely → present the replay, say nothing about it
4. Watcher → if cut, the demo ends on the reducer artifact instead

### What "done" means at minute 75
A run you have executed end to end at least twice, with the log saved. Feature work stops at 75.
The last 15 minutes are rehearsal, and rehearsal is not optional — an unrehearsed 3-minute demo
becomes a 6-minute demo and gets cut off before the closing beat.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Starter repo is a framework you don't know | Emitter is a side-effect call. You never fight the framework, you decorate it. |
| Parallel agents are slower than expected | Cap at 6–8 workers on tiny task slices. Runtime should be ~45–90s, which is also the right demo length. |
| Live run fails on stage | Replay mode. `?replay=logs/golden.jsonl&speed=4` |
| Log write contention across parallel processes | Line-buffered append mode + one `write()` per event. See schema doc, §Concurrency. |
| Dashboard looks janky on the venue projector | Design for a dark room and a low-gamma projector: high contrast, big type, no thin light-grey text. Test at 50% browser zoom. |
| You run out of time on the payload | The payload is the *least* important decision. Swap in a trivially seeded dataset and spend the time on the board. |

---

## Open decision: what the swarm is actually solving

Deliberately deferred. The architecture above is payload-agnostic — the workers can be hunting
budget variances, auditing a codebase, triaging tickets, or checking a document set for
contradictions, and not one line of the dashboard changes.

Criteria for choosing it (next conversation):

- **Naturally parallel.** The work must genuinely split into 6–8 independent slices. If a human
  would do it sequentially, the swarm looks like theatre.
- **Recognizable stakes.** The audience should understand the problem in one sentence, without
  domain background.
- **Findings have severity.** The board is much more alive when some cards come back urgent.
- **Verifiable.** There must be a cheap check that can fail, or the loop beat has nothing to show.
- **Seedable in 5 minutes.** You must be able to produce believable input data instantly.
