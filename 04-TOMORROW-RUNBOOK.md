# 04 — Tomorrow's Runbook

Open this on a second screen and work down it. Do not improvise the order.

---

## Before you open the starter repo (5 min)

- [ ] `dashboard.html`, `logs/golden.jsonl`, fonts, and the prompt templates are on this machine
- [ ] Open `?replay=logs/golden.jsonl` — confirm the parachute renders **before** you write
      a line of code. If it's broken, fixing it is your first task, not your last.
      **Run the parachute at speed 1.** The golden log is paced to ~75s to sit underneath the
      3-minute script; at speed=4 the entire run is over before you finish Beat 1.
- [ ] Know the seek: `&from=<seq>` folds everything below that `seq` instantly and animates the
      rest. That is what makes "switch tabs and pick up at the same beat" possible.
- [ ] `node tests/fold.test.mjs` — 18 checks on the log and the fold. Green before you start.
- [ ] Phone tethering ready in case venue wifi dies
- [ ] Screen mirroring tested if you present from your own machine

---

## T+0 to T+15 · Reconnaissance and integration

Resist writing features. You're answering four questions.

1. **Where does the repo spawn parallel work?** Task tool, `asyncio.gather`, subprocess pool,
   whatever. That's your `agent.spawned` site.
2. **Where does a unit of work finish?** That's `agent.done` and `finding.written`.
3. **Are workers threads or processes?** Threads → in-process `EventLog`. Processes → outbox drain
   pattern (schema doc §Concurrency, option 1).
   **If the repo runs its agents sequentially, do not fix the repo.** Run your own dispatcher
   beside it and let the repo be the payload. `glassbox/simulate.py` already proves the shape.
   Deciding this at T+45 costs five minutes; converting someone else's orchestration to
   parallel costs the demo.
4. **What's the natural payload?** If the repo ships with sample data that fits the mission, use it.
   Fighting the repo's data model costs 20 minutes you don't have.

Then integrate:

- [ ] Drop `glassbox/events.py` in
- [ ] **Put something of theirs on the board** — the repo's own task names as strip labels, its
      run directory, its config in the mission line. Five minutes, and if the organisers wrote
      this repo it changes the read from "brought his own project" to "instrumented yours".
- [ ] Add `emit()` at the five sites: spawn, status change, finding, done, run start/finish
- [ ] Point `dashboard.html` at the repo's run directory
- [ ] Run it once. Even if it emits three events and crashes — **see events reach the board**

**Checkpoint T+15:** at least one real event from the starter repo rendered on the board. If not,
stop adding and debug this only. Nothing downstream works without it.

---

## T+15 to T+45 · The swarm

- [ ] Dispatcher slices the input into 6–8 parts
- [ ] Stagger the spawns 120–400ms
- [ ] Worker prompt filled in from the template
- [ ] Findings flow to the board
- [ ] Run end to end at least once

**Checkpoint T+45:** 8 strips bloom, work in visible parallel, findings stack up in the feed.

**If you're behind at T+45:** you have the core wow already. Skip to T+75 rehearsal and demo just
this. A swarm you can see is enough. Do not start the loop or the watcher if the swarm is shaky —
a polished two-beat demo beats a broken four-beat demo every single time.

---

## T+45 to T+60 · The loop

- [ ] Verifier runs over findings
- [ ] Seeded bad record produces a reliable `verify.failed`
- [ ] Dispatcher re-spawns as a child agent with `parent_id` set
- [ ] Retry strip renders nested beneath its parent with the bracket
- [ ] Budget cap enforced and visible

**Checkpoint T+60:** red strip → nested retry → green, at least twice in a row.

---

## T+60 to T+75 · Always-on

- [ ] Watcher polls the inbox, appends to the same log
- [ ] Idle state renders (scanline + LISTENING rail)
- [ ] Trigger file staged on the desktop, one drag from the inbox folder
- [ ] Rehearse the drop three times — it's the last thing they see

**Checkpoint T+75:** feature freeze. Whatever isn't working is now cut, not fixed.

---

## T+75 to T+90 · Rehearse and secure

- [ ] Full run end to end, saved to `logs/backup-live.jsonl` — **this, not the synthetic golden
      log, is the parachute you present.** The golden log shows the wrong payload's findings once
      the real run exists.
- [ ] Rehearse the 3-minute script out loud, on the clock, twice
- [ ] Second run saved — you now have two parachutes
- [ ] Browser: close every other tab, hide bookmarks, full screen, notifications off
- [ ] Terminal font bumped to presentation size
- [ ] Board open in **two** tabs: live in one, replay in the other, ready to switch without typing
- [ ] `?big=1` tested on the actual projector if you can get near it

An unrehearsed three-minute demo runs six minutes and gets cut off before the closing beat.
Rehearsal is not the optional part.

---

## Integration cheatsheet

The five call sites, in whatever language the repo is:

```python
log.emit("run.started", "dispatch", {"mission": M, "planned_agents": n})
log.emit("agent.spawned", wid, {"role": "worker", "label": t, "model": m}, parent_id=None)
log.emit("agent.status", wid, {"state": "working", "note": ""})
log.emit("finding.written", wid, {...})
log.emit("agent.done", wid, {"status": "ok", "duration_ms": d, "cost_usd": c})
```

**`agent_id` is always the agent being described — never `"dispatch"`.** The dispatcher is
*responsible* for emitting `agent.spawned`, but the event describes the worker, so it carries
the worker's id. Emit eight spawns as `"dispatch"` and the renderer, which keys agents on
`agent_id`, overwrites the same record eight times: you get **one strip instead of eight**, with
no error and nothing in the console. Use `log.spawned(wid, ...)` from `glassbox/events.py` and
this cannot happen.

If the repo is TypeScript, the emitter is nine lines — the contract is the file format, not the
library. Don't port anything else.

---

## Triage rules under pressure

| Symptom | Do this |
|---|---|
| Strips spin forever | An agent died without `agent.done`. Emit `failed` in the exception handler. |
| Board frozen | Almost always a restarted run appending to a live log — new `run_id`, `seq` back at 0. The board now resets when `run_id` changes; if it doesn't, you have two writers sharing one `run_id`. Switch to the outbox drain. |
| One strip instead of eight | You emitted `agent.spawned` with `agent_id="dispatch"`. Pass the worker's id. |
| Everything finishes instantly | Slices too small. Fewer, bigger slices — you want 20–60s per worker. |
| One strip grinds while seven idle | Uneven slices. Rebalance, don't optimise. |
| Rate limits | Drop to 6 workers, move workers to the faster model. |
| Findings are mush | Tighten `title` to 8 words and require `evidence_ref`. Almost always fixes it. |
| Live run dies at T+88 | Switch tabs. Present the replay. Say nothing about it. |

---

## The one rule

**At T+75, you stop building.** Every hackathon is lost in the last fifteen minutes by someone
adding one more thing. You have a parachute, a script, and a board. Use them.
