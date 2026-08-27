---
title: 09 — Adversarial Review Findings
status: archived
part_of: glass-box
doc_type: review-findings
---

# 09 — Adversarial Review Findings

Response to `08-ADVERSARIAL-REVIEW-PROMPT.md`. Every claim below was checked against the
code in this repo, not inferred from the docs. Repro commands are included where it matters.

---

## 1. Kill shots

### KS-1 · The integration cheatsheet collapses the swarm to one strip, silently

`04-TOMORROW-RUNBOOK.md` §Integration cheatsheet — the five lines you paste at T+5 under
pressure — says:

```python
log.emit("agent.spawned", "dispatch", {"role": "worker", "label": t, "model": m}, parent_id=None)
```

The renderer keys agents on `ev.agent_id` (`dashboard.html:304`). Emit eight spawns with
`agent_id="dispatch"` and each overwrites the last. Verified: **one strip, labelled with
whatever lens spawned last.** No error, no warning, the board just shows a single agent.

`glassbox/events.py:163` gets this right (`spawned()` passes the worker's id). The cheatsheet
contradicts the library it's meant to summarise, and `01-EVENT-SCHEMA.md`'s event table
reinforces the error by listing `dispatch` in the Emitter column for `agent.spawned`.

This is the worst defect in the set: it is in the file you will be following, at the moment you
are least able to debug, and it destroys the one visual the entire project exists to produce.

**Fix tonight:** change the cheatsheet line to `log.emit("agent.spawned", wid, {...})` and add a
note to 01's table that Emitter means *who is responsible for emitting*, while `agent_id` is
always *the agent being described*.

### KS-2 · The parachute does not fit the script

`00` promises "the demo cannot fail" because replay renders the golden log. Measured:

| | |
|---|---|
| Golden log virtual span | **33.2s** |
| Replay at `speed=2` (QUICKSTART) | 16.6s |
| Replay at `speed=4` (`00` risk register, `04`) | **8.3s** |
| `05-DEMO-SCRIPT.md` narration budget | 2:30 |

At the documented speed the entire run — bloom, failure, retry, collapse, wake-up — is over
before you finish Beat 1. `00` and `01` both specify a ~60s run; the golden log is half that.

Worse, `05`'s failure-mode table says: *"Run dies mid-demo → Here's the run from ten minutes ago.
Switch tabs. Continue at the same beat."* **There is no seek.** `runReplay()` starts at
`events[0]` unconditionally; there is no `?from=`, no scrub, no pause. Switching tabs restarts
from the bloom. You cannot continue at the same beat, and the audience watches the first 90
seconds twice.

And `watch.triggered` fires **3.0 virtual seconds** after `reduce.finished` — 0.75s at speed=4.
Beat 5 asks you to walk to the laptop and drag a file. In replay the board wakes before you get
there.

**Fix tonight, in order of cost:** (a) regenerate the golden log with sleeps scaled to ~75s and a
15–20s gap before `watch.triggered`; (b) add `?from=<seq>` — about six lines in `runReplay`, fold
events below `from` instantly then animate the rest; (c) run the parachute at `speed=1`.

### KS-3 · A `seq` restart freezes the board with no symptom

The live poller dedupes on `seq` alone (`dashboard.html:571`). If anything appends to an existing
`events.jsonl` with `seq` restarting at 0 — a second run, a restarted dispatcher, a repo that
reuses its run directory — **every new event is silently discarded.** Verified: 0 of 92 events
accepted on a second run into the same file.

The board does not error. It does not clear. It sits there showing the previous run, looking
completely healthy, while your live run produces nothing.

`04`'s triage table lists "Board frozen → `seq` gap. Check for two writers." That is the wrong
diagnosis and will cost you ten minutes. The likely cause at 9am is a re-run, and `simulate.py`
hides it by deleting the file first (`simulate.py:281`) — so you will never hit this in dev, only
on stage.

**Fix tonight:** dedupe on `run_id + seq`, and reset state when `run_id` changes. Roughly four
lines. Also fix the triage row.

### KS-4 · Swapping to Payload B silently invalidates the parachute

`07` claims: *"Cost of the swap: one prompt file and a path... The event schema, dashboard,
dispatcher, verifier mechanics, runbook, and demo script are all untouched."*

The golden log is not in that list, and it is Payload A end to end — `simulate.py` hardcodes the
eight code-review lenses, `ARCHITECTURE.md:21` as the seeded failure, and "Two credentials and one
unvalidated path are live in main" as the headline. Swap at T+15 and your parachute shows a repo
sweep while you narrate a budget audit.

Regenerating means rewriting the `FINDINGS` dict, `RETRY_FINDING`, `LENSES`, and the reducer
headline: 20+ minutes at exactly the moment the swap is supposed to be saving you time.

**Fix tonight:** either build the Payload B golden log now (30 min, and `07`'s honeypot is the
better failure beat anyway — see below), or amend `07` to state plainly that the swap costs you
the parachute and must therefore be decided *before* T+15, not at it.

### KS-5 · The question you cannot currently answer

Not "is this just CSS" — you can answer that one. The dangerous question is:

> **"What did eight agents get you that one Opus call with the whole repo in context wouldn't?"**

Nothing in these nine files answers it. Worse, the board makes it *harder* to answer, because it
renders the redundancy legible: 17 findings from 8 agents, several overlapping, and the reducer's
job is explicitly to merge duplicates. A skeptic reads that as "you parallelised something that
didn't need parallelising, then paid a reducer to undo it."

The honest answers are real but unstated: independent contexts stop lens bleed (one agent that has
already found a secret stops looking for concurrency bugs); per-lens confidence is separately
calibratable; and the swarm degrades gracefully when one agent fails. Pick one, put it in the Q&A
sheet, keep it under fifteen seconds.

See §4 for the structural version of this answer, which is stronger.

---

## 2. Concrete defects

| File | Location | What's wrong | Should say |
|---|---|---|---|
| `04` | §Integration cheatsheet | `agent.spawned` emitted with `agent_id="dispatch"` → one strip | `log.emit("agent.spawned", wid, {...})` |
| `04` | §Triage, "Board frozen" | Misdiagnoses the likely cause | "`run_id` changed or `seq` restarted. Check you aren't appending to a previous run's file." |
| `01` | §Tonight's fixture | `--agents 8 --findings 20 --retries 2` — none of these flags exist | Actual flags are `--out`, `--fast`, `--seed`, `--no-second-cycle` |
| `01` | §Reference implementation | The inlined `EventLog` has no `drain_outbox`, so it cannot support option 1 — the concurrency path the same document recommends | Point at `glassbox/events.py` rather than inlining a reduced copy |
| `01` | §Test | `reduce_state`, `apply`, `State` don't exist in Python; there is no test suite at all | Either write them against the JS fold, or delete the section |
| `01` | §Invariants #6 | `test_prefix_is_stable` **fails** as written — `apply` mutates `st` in place and returns it, so a state you still hold is rewritten by later events. Verified. | Re-folding from `initialState()` is deterministic and *that* is what makes replay work. Say that instead — and note that a time-travel scrubber must re-fold, not memoise. |
| `01` | Event table, Emitter column | Invites KS-1 | Distinguish "who emits" from "what `agent_id` holds" |
| `01` | §Event types | `log.note` is sold as the escape hatch; the renderer has **no case for it**. Emitting one shows nothing. | Add a `log.note` case, or stop calling it an escape hatch |
| `01` / `03` | `task.claimed` | Renderer handles it; nothing emits it; no prompt template instructs it | Delete it from the schema |
| `02` | §The strip | Spec shows a ticking elapsed timer per strip; not implemented | Drop it, or implement — but see the clock defect below |
| `dashboard.html` | :615 | Comment claims "Keep the clock ticking between events so the board never looks frozen." No such timer exists. The clock only advances when an event arrives. | Implement or delete the comment |
| `dashboard.html` | `renderFindings` | `renderedFindings` is module-global; which findings get the `fresh` flare depends on how many times `render()` was called, which differs between live (250ms batches) and replay (rAF). Replay is *not* pixel-identical to live. | Track freshness in state, or soften the claim in `00`/`02` to "identical final state" |
| `simulate.py` | second cycle | `w1c2`/`w2c2`/`w3c2` spawn and never emit `agent.done` — violates `01` invariant #4. Verified. Board ends showing 3 strips spinning and "3 working" instead of the LISTENING rail. | Acceptable as a final frame, but say so deliberately rather than by accident |
| `simulate.py` | `run.finished` totals | Declares `findings: 15, cost_usd: 0.164`. Actual: **17 findings, $0.2026**. The counters on screen contradict the totals in the log. | Compute totals from what was emitted |
| `07` | §Slice map | "every agent gets 42 rows" — CC-4300 and CC-4400 have **43** (the planted dupe and the orphan) | Say 42–43 |
| `generate_budget.py` | :106 | `dupe["actual"] = index[...]["actual"]` is a no-op; `dupe` is already a copy of that row | Delete the line |
| `06` | §Guaranteeing the failure beat | "Be straight about this **if anyone asks**" — reactive | Say it in Beat 3 unprompted. Disclosed upfront it's method; extracted under questioning it's damage control. |

**Things I tried to break and could not:** `parseLines` handles a mid-line truncation cleanly (50
clean events out of a 60%-truncated file, no throw); the final event of a completed log *is*
rendered, because the writer always terminates with `\n`; re-folding the same log twice is
deterministic (`test_render_is_pure` passes); duplicate `seq` from two writers is dropped rather
than double-applied. The honeypot is excellent — CC-4310/5400 nets **+0.3%** across H1 against a
190% single-period spike, which is exactly the trap described.

---

## 3. Cut list — tonight

**Build nothing new.** The board is done. Tonight is KS-1 through KS-4 and nothing else; that is
roughly 90 minutes of work and it is all repair.

Cut from the plan:

1. **The cost ledger.** Already first on your own cut list, and it is currently wrong on screen.
   Deleting it removes a counter that contradicts the log.
2. **`task.claimed`** — dead event type, delete from schema and renderer.
3. **The `blocked` state.** A code path, a jitter animation, and a keyframe for something nobody
   will ask about and which lasts 3 seconds.
4. **Beat 2 down from 45s to 25s.** Ten seconds of silence is right and you should keep it. The
   other 35 seconds is one sentence of narration over a moving screen — that is dead air, and dead
   air is where the "it's a screensaver" read gets formed. Silence, then narrate continuously.
5. **`?big=1` testing on the projector** if it costs you more than five minutes to get near one.

**Do not cut the verifier loop.** It is currently last in build order and #2 on your cut list.
That is backwards. The loop is the only structural answer to "this is presentation polish" — it is
the one beat where the system does something a picture cannot fake. Move it ahead of the watcher.

---

## 4. The strongest alternative

Not a different project. The architecture is sound and the board is 80% built — changing course
now would be the actual mistake.

But there is a change worth making, and it is small: **show the agents disagreeing.**

Right now the slices are disjoint by construction — `06` and `07` both instruct workers to ignore
everything outside their lane, and `03` calls duplicate findings a bug. So the swarm is eight
independent jobs that happen to run at once, and the reducer's job is deduplication. That is
precisely the shape that invites KS-5.

Overlap two or three slices deliberately and let the verifier adjudicate when they conflict. On
Payload B this is nearly free: CC-4310's honeypot reads as a 190% overspend to an agent looking at
April and as a timing shift to one looking at the half-year. Give one agent the period slice and
another the account slice, let them file contradictory findings, and let the verifier reject the
narrow one on the evidence.

What that buys you:

- The board shows two strips reaching **opposite conclusions from the same rows**, then one going
  red. That is a picture of something a single call genuinely cannot produce — independent
  reasoning under separate contexts, adjudicated on evidence.
- KS-5 answers itself on screen. You stop having to argue that the fan-out was necessary.
- Beat 3 gets much stronger. "An agent made a claim its evidence doesn't support" becomes "two
  agents disagreed and the verifier settled it against the data."
- It costs one prompt change and overlapping slice boundaries. No renderer change at all.

`07`'s honeypot is already 90% of this. It is the best single asset in the plan and it is
currently sitting in the *fallback* file.

---

## 5. Timeline

**T+15 slips first**, and it is the only checkpoint gated entirely on an unknown. "Recon +
integration + a real event on the board in 15 minutes" assumes the starter repo installs and runs
first try. Budget 10 minutes for dependency install alone.

The cascade: T+15 → T+30 pushes the swarm to T+60, which means the loop never gets built, which
means you demo two beats. Survivable — `04` already says so.

**Where a competent person actually loses this** is not slipping. It is discovering at T+45 that
the starter repo's orchestration is *sequential*, and deciding to parallelise it. That is a
rewrite, it is invisible until you look, and no document here has a contingency for it.

Write one tonight, in one line: **if the repo runs its agents sequentially, do not fix the repo —
run your own dispatcher beside it and let the repo be the payload.** You already have
`simulate.py` proving the dispatcher shape works. That decision at T+45 costs 5 minutes; the
rewrite costs the demo.

The T+75 freeze is realistic, but only because it is self-enforcing — at T+75 you will be out of
time whether or not you respect the rule.

---

## 6. The risk not named anywhere

**The starter repo may be part of the judging criteria.**

`00` treats repo-independence as a pure strength: *"You never fight the framework, you decorate
it."* Technically correct, and it is why you can build tonight. But if the organisers hand every
team the same starter repo, they likely want to see it *used*, and Glass Box is architected to
treat it as an input source. A judge who wrote that repo may see a project that routed around
their work.

Cheap insurance, and you should do this at T+10: find one thing the starter repo already does and
put it on the board — its own task names as strip labels, its own run directory, its config values
in the mission line. Five minutes, and it changes the read from "brought his own project" to
"instrumented yours."

Second, smaller: there is **no test suite**, and `QUICKSTART.md` lists "State fold is pure" under
**Verified**. I ran it — the re-fold property holds, the prefix property in `01` does not. Assert
less, or run it.

---

## 7. Unstated dependencies on the starter repo

Answering `08` §3, which the first pass of this review skipped. Everything marked **verified** was
executed against the code in this repo; the one item marked *reasoned* could not be tested here.

### Tier 1 — costs more than fifteen minutes if wrong

**1. Pydantic v2. Verified, and it fails in the worst possible shape.**
Under pydantic 1.10.26, `glassbox/events.py` imports cleanly, `Event(...)` constructs cleanly
(`ConfigDict` and `frozen=True` are silently ignored by v1), and then the **first `emit()` dies**:

```
AttributeError: 'Event' object has no attribute 'model_dump'
```

So a starter repo pinned to pydantic 1.x gives you a green import at T+5 and an exception at T+12,
which is exactly when you are least able to read a traceback calmly. Two lines make it version-proof:

```python
def to_line(self) -> str:
    data = self.model_dump() if hasattr(self, "model_dump") else self.dict()   # v2 / v1
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
```

Cheaper still if the repo fights you: delete the model and keep a plain dict. The contract is the
file format, not the library — `01` already says so, so take it seriously when it costs you nothing.

**2. Python 3.10+.** *(Reasoned — no 3.9 available here to test.)* `parent_id: str | None`
(`events.py:40`, `:62`) is a string annotation under `from __future__ import annotations`, but
pydantic evaluates it at runtime, and `str | None` is a TypeError before 3.10. A repo pinned to 3.9
means rewriting the annotations to `Optional[str]` or switching interpreter.

**3. You can edit the code that spawns the work.** The entire integration is five `emit()` calls at
the repo's own call sites. If the parallelism lives somewhere you cannot reach — inside an SDK's
task runner, a vendored package, a hosted service — there is no call site to decorate. Fallback is
the same as for a sequential repo: run your own dispatcher beside it and let the repo be the payload.

**4. The repo's agents actually run in parallel.** See §5. This is the one that is invisible until
you look and expensive the moment you try to fix it.

**5. You can run a static HTTP server on the demo machine, and serve the run directory.**
**Verified:** `dashboard.html` opened over `file://` renders "Log not found" — the fetch is blocked
by CORS, exactly as QUICKSTART says. So a machine where you cannot run `python -m http.server` or
bind a port has no live board at all.

> **The parachute survives this one.** `build/glassbox-mobile.html` inlines the log and therefore
> needs no server: **verified rendering over `file://`** with the board playing. If the venue machine
> is locked down, that file on a USB stick is still a working demo.

**6. The run directory sits under the served root.** If the repo writes runs to an absolute path
outside where you serve from, the poll 404s silently (`runLive` returns on `!res.ok`) and the board
sits on the empty state looking fine. Symlink it or serve from a common parent.

**7. API quota for eight concurrent workers, at the venue, at T+40.** The risk register has "rate
limits → drop to 6 workers", which treats this as a tuning knob. It is a scheduling risk: thirty
teams on one event key, and your run is the one with the highest concurrency in the room. Know
before you start whether the key is yours or shared.

### Tier 2 — under fifteen minutes, but they will bite

**8. The inbox drop is a desktop GUI gesture.** If you develop in a devcontainer, Codespace, or a
remote VM, the watcher watches a filesystem your desktop cannot drag into, and Beat 5 — the closer,
the last thing the room sees — silently becomes impossible. Either run the whole thing locally, or
rehearse a visible `cp` in the terminal instead and accept that it lands softer.

**9. Threads versus processes.** Cheap only because both paths already exist (`EventLog` in-process,
or `drain_outbox`). Answer it during recon, not at T+40.

**10. Enough code to review** for Payload A. `06` handles it: under ~30 files, drop to six lenses.

**11. A browser from roughly 2022 or later.** Feature floor audited: no optional chaining, one `??`,
no `Array.at()`, plus `dvh` units in the mobile layer (Chrome 108 / Safari 15.4). Any current laptop
browser is fine; this is only a risk if you present from something you did not choose.

**12. Node, for `tests/fold.test.mjs`.** That dependency is mine, not the plan's. No node means no
test run; the board itself is unaffected.

**13. Filesystem write access and `os.fsync`.** Fine everywhere except a read-only container.

### Not dependencies, despite looking like them

Worth knowing so you do not spend recon time on them: the repo's **language** (the contract is the
file format; a TypeScript emitter is nine lines), its **framework or orchestrator** (you decorate,
never fight), and the **network** — the board now makes zero external requests, fonts included,
verified with every host blocked.

---

## Status — fixes applied

Everything in §1 and §2 is done, verified, and committed. `node tests/fold.test.mjs` is the check.
§7 is an enumeration, not a defect list — the one patch it recommends (pydantic v1 compatibility)
is **not applied**, because it adds a code path to the file most likely to be dropped into an
unknown repo and that should be your call.

| # | Fix | Where | Verified by |
|---|---|---|---|
| KS-1 | `agent.spawned` carries the worker's id, not `"dispatch"` | `04` cheatsheet, `01` event table, `03` dispatcher | Fold test: 8 spawns → 8 strips |
| KS-2 | Run paced to ~75s (+18s before the watcher fires); `?from=<seq>` seek added | `simulate.py`, `dashboard.html`, `05`, `04`, QUICKSTART | Log span 88.4s; `?from=70` renders 11 strips at seq 75 |
| KS-3 | Live board dedupes within a run and resets on `run_id` change | `dashboard.html` `runLive()` | Fold test: second run fully accepted, board rebuilds |
| KS-4 | The swap's real cost stated; decide before T+15 | `07` | — |
| KS-5 | The fan-out answer written into Beat 2 and the Q&A sheet | `05` | — |
| — | Keyed DOM: entry animations fire once instead of on every poll | `dashboard.html`, `02` | Headless: 1 element carrying `.enter` mid-replay, strip identity stable |
| — | `run.finished` totals computed from what was emitted | `simulate.py` | Fold test: totals reconcile |
| — | Every second-cycle agent emits `agent.done` (invariant #4) | `simulate.py` | Fold test: no orphans |
| — | `duration_ms` from the virtual clock, not wall clock | `simulate.py` | 61283ms, was 0 under `--fast` |
| — | `log.note` renders; `task.claimed` deleted from the schema | `dashboard.html`, `01`, `03` | — |
| — | Elapsed-timer spec dropped; the dead "ticking clock" comment removed | `02`, `dashboard.html` | — |
| — | Fonts embedded as base64 woff2 — no network at all | `dashboard.html`, `02`, QUICKSTART | Headless with every external host blocked |
| — | Sequential-repo contingency; T+10 "instrument their repo" step | `04` | — |
| — | Seeded failure disclosed in Beat 3 rather than on request | `06` | — |
| — | 42-row claim corrected; no-op line removed from the generator | `07`, `generate_budget.py` | CSVs byte-identical after the change |
| — | Test suite written, extracted from `dashboard.html` so it can't drift | `tests/fold.test.mjs`, `01` §Test | 18/18 |

**Not applied, and why.**

- **§3's cuts of working features** — the cost ledger and the `blocked` state. Both now behave
  correctly (the ledger reconciles with the log), so the stated reason for cutting them is gone.
  Deleting working visuals is your call about your own time, not a defect fix.
- **§4, overlapping slices so the agents disagree.** This is a design decision about what the demo
  argues, not a repair. It changes the slice maps in `06`/`07`, the worker prompts, and the golden
  log's narrative. It is still the highest-value change available and it is still small — but it
  should be your call, tonight, with the payload decision.
