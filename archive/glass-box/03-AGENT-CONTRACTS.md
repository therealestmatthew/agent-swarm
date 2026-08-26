# 03 — Agent Contracts

Four roles. Each one's job is defined by the events it emits, not by its internals — which is what
makes these portable onto whatever the starter repo hands you.

| Role | Count | Emits | Cut if short on time? |
|---|---|---|---|
| Dispatcher | 1 | `run.*`, `agent.spawned`, `agent.retry` | No — it's the spine |
| Worker | 6–8 | `agent.status`, `finding.written`, `agent.done` | No — it's the swarm |
| Verifier | 1 | `verify.*` | Yes — cut the loop beat with it |
| Reducer | 1 | `reduce.*` | No — it's the payoff |
| Watcher | 1 | `watch.*` | Yes — cut the closing beat with it |

---

## Sizing the swarm

**6–8 workers.** Not 3, not 20.

- Below 6, the board looks sparse and the parallelism isn't visually obvious.
- Above 8, strips shrink below readable size on a projector and rate limits start biting.
- Each worker's task should complete in **20–60 seconds**. Longer and the demo drags; shorter and
  the strips finish before anyone has looked at them.

Slice the work so every worker gets roughly equal load. Uneven slices produce a board where one
strip is still grinding while seven sit finished — which reads as a bug even though it isn't.

**Model assignment:** workers on the fastest model that does the job (Haiku or Sonnet), reducer on
the strongest (Opus). This is real engineering, not a demo trick — and it gives you a legitimate
line for the Q&A about cost-shaped routing if the ledger is on screen.

---

## Dispatcher

Owns the run. Single writer to the log if you took option 1 in the schema doc.

```
1. emit run.started {mission, input_ref, planned_agents}
2. read input → split into N slices
3. for each slice: emit agent.spawned (agent_id = the WORKER, not "dispatch"), launch worker
                                                            ← stagger 120–400ms
4. drain worker outboxes → append to events.jsonl, assigning seq
5. on verify.failed with budget remaining:
     emit agent.retry {of_agent_id, attempt, reason, budget_remaining}
     emit agent.spawned {parent_id: <original>}  ← new agent id, e.g. w2r1
6. when all workers done: launch reducer
7. emit run.finished {status, duration_ms, totals}
```

**Stagger the spawns.** A 120–400ms gap between `agent.spawned` events is the difference between
strips appearing all at once (looks like a page load) and blooming into the rack one after another
(looks alive). This is the cheapest wow in the entire build.

**Budget guard.** Hard cap: `MAX_RETRIES_PER_FINDING = 1`, `MAX_TOTAL_RETRIES = 3`. Emit
`budget_remaining` on every retry so the board can show it. An unbounded loop on stage is a
demo that never ends, and the cap is also the honest answer to "how would you run this in prod?"

---

## Worker prompt template

Repo-agnostic. Fill the braces at build time.

```
You are worker {agent_id}, one of {n} agents working the same mission in parallel.

MISSION
{mission_statement}

YOUR SLICE
{slice_description}

You own this slice only. Other agents have the others. Do not investigate outside it —
duplicate work across agents wastes the run.

WHAT TO PRODUCE
Zero or more findings. A finding is something a decision-maker would act on. If your slice
is clean, produce none and say so — a false finding is worse than no finding.

For each finding emit exactly one line to your outbox at {outbox_path}:

{"type":"finding.written","payload":{"finding_id":"<slug>","title":"<8 words max>",
"severity":"high|medium|low","confidence":0.0-1.0,"summary":"<25 words max>",
"evidence_ref":"<file:line or record id>"}}

RULES
- evidence_ref must point at something real in your slice. No finding without evidence.
- confidence is your honest calibration, not a sales number.
- title is scanned on a wall display from six feet away. Front-load the noun.
- Emit an agent.status line when you change phase: thinking → working → waiting.

Finish within {time_budget} seconds. If you're not done, emit what you have.
```

The `evidence_ref` requirement is doing real work here: it's what the verifier checks, and it's what
keeps the findings from being plausible-sounding mush when someone in the audience asks.

---

## Verifier prompt template

The loop. Keep it cheap and mechanical — the failure needs to be *legible*, not clever.

```
You are the verifier. For each finding below, check exactly one thing:
does evidence_ref point at something that actually supports the claim in summary?

Do not evaluate whether the finding is interesting or well-written. Only whether the
evidence is real and supports it.

FINDINGS
{findings_json}

For each, emit one line:
{"type":"verify.passed","payload":{"finding_id":"...","attempt":1}}
or
{"type":"verify.failed","payload":{"finding_id":"...","attempt":1,"reason":"<12 words max>"}}

reason must state the specific defect: missing evidence, evidence contradicts claim,
reference not found, claim broader than evidence.
```

**Seed a guaranteed failure.** Plant one record in your input data that will reliably produce an
unverifiable finding. You need the red-strip-to-green-strip beat to fire on stage, and hoping the
model spontaneously makes a checkable mistake in a 90-second run is not a plan. This is stagecraft,
and it's honest stagecraft — the mechanism is real, you're just guaranteeing it gets exercised.

---

## Reducer prompt template

The payoff. Everything on the board collapses into one artifact.

```
You are the reducer. {n} agents worked {n} slices of the same mission in parallel and
produced the findings below, all verified.

MISSION
{mission_statement}

VERIFIED FINDINGS
{findings_json}

Produce a brief with exactly this structure:

# {mission_title}
**Headline:** one sentence a decision-maker acts on.

## What we found
3-5 bullets, most consequential first. Each cites its finding_id.

## What we'd need to confirm
2-3 bullets on the weakest links. Name them plainly.

## Coverage
One line: slices examined, findings raised, findings rejected by verification.

Write for someone with 30 seconds. No preamble, no restating the mission, no hedging
language. Where findings conflict, say so rather than averaging them.
```

Write to `runs/current/brief.md` and emit `reduce.finished {artifact_path, headline}`. The board
renders the headline in the bottom rail at 22px — that's the last thing on screen before you take
questions, so it needs to be a real sentence, not a label.

---

## Watcher

Fifteen minutes of work, and it's your closing beat.

```python
# Poll, don't inotify. Cross-platform, no deps, impossible to debug wrong at 9am.
seen: set[str] = set()
log.emit("watch.armed", "watch", {"path": str(inbox), "patterns": ["*.csv", "*.json"]})
while True:
    for path in sorted(inbox.iterdir()):
        if path.name not in seen:
            seen.add(path.name)
            log.emit("watch.triggered", "watch", {"path": path.name, "change": "created"})
            dispatch(path)          # new cycle, same board, same log
    time.sleep(0.5)
```

Two things that matter:
- **Same log, same board.** The second cycle appends to the same `events.jsonl`. Don't start a new
  run file — you want the audience watching one continuous board come back to life.
- **Prime it before you present.** Have the trigger file already sitting on your desktop, one drag
  away. Fumbling for a file in Finder kills the moment.
