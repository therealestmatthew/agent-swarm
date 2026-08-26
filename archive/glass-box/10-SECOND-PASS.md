# 10 — Second-Pass Analysis

Two agents ran against this repo after `09`: one adversarial, explicitly barred from re-reporting
anything in `09-REVIEW-FINDINGS.md`; one on enhancements and visualization. Every claim below was
re-verified against the code and `logs/golden.jsonl` before being written down. Where the agents'
numbers were wrong, the corrected figure is here.

**Status key:** ✅ fixed in this pass · 📋 deferred, recorded only

---

## Part 1 — Ways to kill the board mid-demo

All eight are silent: no console error, no visible fault, just a board that is wrong or frozen
while looking healthy.

### ✅ 1.1 `apply()` hardcodes the agent ids `"verify"` and `"reduce"`

`dashboard.html:374,379,393,398,404`. Every other case in the fold uses `ev.agent_id`; these five
use string literals, and `touch()` returns silently on an unknown id.

A starter repo that names its verifier `verifier`, `v1`, or `verify-0` gets a **flat, dead strip** —
the one agent on the board that appears to be doing nothing, during Beats 3 and 4, which are the
beats where it is the focus. `04`'s cheatsheet lists five call sites and never mentions that the
verifier must be named `verify`, so an integrator has no way to discover this.

Measured: a verifier named `verifier-1` renders **1 trace bar** (its spawn) against **6** for one
named `verify`.

### ✅ 1.2 A non-numeric `cost_usd` or `confidence` freezes the board permanently

`st.cost += p.cost_usd || 0` (`:354`) — a JSON *string* is truthy, so `0 + "0.011"` gives
`"00.011"`. `renderCounters` then calls `st.cost.toFixed(3)` (`:476`) and throws. Same at `:562`
for `f.confidence.toFixed(2)`.

In replay the throw escapes `step()` **before** its trailing `requestAnimationFrame`, so the chain
dies and replay halts forever. In live it throws out of the `setInterval` callback every 250ms.
The end state is self-contradictory: the counter reads `findings=1` while the pane still says
"Waiting for findings."

Entirely plausible from a hand-written emitter — `04`'s cheatsheet passes `cost_usd` straight
through from whatever the repo hands you, and plenty of SDKs report cost as a decimal string.

### ✅ 1.3 `09` KS-3's fix has a hole: a pinned `run_id` grafts run 2 onto run 1

`dashboard.html:681`. The reset fires only on `run_id` **change**. But `EventLog.__init__` accepts
`run_id` as an argument, and `04`'s T+10 step encourages using the starter repo's own run
identity — so the most likely integration is a *deterministic, pinned* id. Restart the dispatcher
and `seq` restarts at 0 with the same `run_id`: no reset, and `seen` still holds `0..N`.

Verified in a live board across two runs in one file: run 2's `run.started`, both its
`agent.spawned`s and its first finding are discarded as already-seen, while its later events **are**
accepted and grafted onto run 1's state — attributed to an agent that has no strip. The mission
line still names run 1 and the seq counter climbs.

This is strictly worse than the freeze KS-3 described. A frozen board is at least self-consistent;
this is a plausible-looking blend of two runs.

### ✅ 1.4 `drain_outbox()` crash-loops and re-emits every prior line

`glassbox/events.py:182-191`. The loop guards `json.JSONDecodeError` but calls `self.emit()` — and
therefore `Event(...)` validation — with no guard, and `self._drained[agent_id] = already` is the
*last* statement, so when `emit()` raises the offset is never persisted.

One malformed line in one worker's outbox and every subsequent tick re-reads from the stale offset,
**re-emits every line before the bad one with fresh `seq`**, then throws again. At the 100ms tick
`01` prescribes that is ~10 duplicate batches per second, unbounded, and nothing after the bad line
is ever delivered. On the board, duplicate `agent.spawned` re-`set()`s the agent record, zeroing its
findings and bumping `order` — so the rack reshuffles ten times a second.

This is the path `01-EVENT-SCHEMA.md` calls *"the safer choice under time pressure"* and tells you
to pick by default. It had zero test coverage.

### ✅ 1.5 A missing `finding_id` collapses the whole pane into one card

`dashboard.html:553`/`:565`. `findingEls` is keyed on `f.id` with no fallback. Three findings
emitted without a `finding_id`: counter says **3**, pane shows **1**, no error. `st.verdicts` has
the same problem — a verdict keyed on `undefined` applies to every id-less finding at once.

Structurally identical to `09` KS-1, and `04`'s cheatsheet — which now carries a large correct
warning about `agent_id` — has no equivalent warning for the finding payload.

### ✅ 1.6 `?speed=<garbage>` gives a permanently blank board

`dashboard.html:275`, unvalidated `parseFloat`. `?speed=abc` → `NaN` → a completely blank Standby
board with a rAF loop burning a core, no error, and no indication the log loaded fine. `?speed=0`
applies event 0 and spins forever. A fat-fingered URL under demo pressure reads exactly like *"the
parachute is broken."*

### ✅ 1.7 `?seed=1` silently ignores `?from=`

The `SEED_MODE` early return (`:711`) sits *above* the seek loop (`:721`), so `from` never applies.
`?seed=1&from=70` renders identically to `?seed=1` — the final frame. Since `02` documents
`?seed=1` as the screenshot mode, the obvious use (a still of a specific beat) silently fails.

### ✅ 1.8 The mobile preview's Pause does not pause the clock

`tools/build-mobile-preview.py:197`. `rebase` is called on **resume**, not on pause, and
`virtualNow()` keeps running while paused — so resuming rebases to a virtual time that includes the
whole pause. Pause for 90 seconds and Play jumps to the end of the run. Pausing on a beat to talk
over it, the entire point of the control, destroys that beat. The speed buttons had the same bug.

---

## Part 2 — Where the board contradicted the demo script

### ✅ 2.1 Beat 3 was split, and then half of it deleted

At the final frame the rejected finding `w7-02` sat at feed index **5** and its amendment
`w7-02r1` at index **1** — four rows apart, with nothing linking them. Index ≥ 5 triggers
`.collapsed`, which hides `.sum` and `.ref`, so **the verifier's reason — "claim broader than cited
evidence" — was not on screen at all** during the 30 seconds built around it.

Beat 3 is the most important half-minute in the demo. The board split it across the pane and then
deleted the half that explains it.

### ✅ 2.2 The budget cap was not on screen

`05` Beat 3 instructs: *"Say the budget cap line out loud even though it's on screen."* It was not.
`agent.retry` carries `budget_remaining: 2` and `apply()` (`:382-384`) did `st.retries++` and
discarded the payload. A judge who looked for the cap you just claimed would not have found it.

### ✅ 2.3 `prefers-reduced-motion` silently deleted Beat 5

`*{animation:none!important}` (`:237`) kills `@keyframes flash`, so `#flash.on` never left
`opacity:0`. For any viewer with reduced motion enabled, the amber watch-trigger flash — the beat
that sells always-on — simply did not happen.

### ✅ 2.4 The pre-loaded replay tab could not work

`05:118` and `04:102` both assume a second tab *"already loaded with `&from=<seq>` at the beat you
were on."* `runReplay()` starts animating on load and there is no pause — a tab pre-loaded at
`&from=60` plays its remaining 44 virtual seconds immediately and sits on a finished board.
Background-tab rAF throttling does not save you: `step()` paces off `performance.now()` deltas, so
it catches up in one frame when focused.

`09` KS-2 fixed *"there is no seek."* The seek works. The pre-loaded tab did not, and `05`/`04`
were edited to assume it.

---

## Part 3 — The shape of the run

### ✅ 3.1 The golden log did not fit `05`'s own beat table

`09` fixed the log's *span* (33.2s → 88.4s) and verified exactly that. Nobody re-derived it against
`05-DEMO-SCRIPT.md`'s beat table, which was never updated. Measured at speed 1, before this pass:

| Beat | `05` target | Actual | |
|---|---|---|---|
| Bloom (first finding) | 0:20–0:45 | **0:15** | lands during Beat 1 |
| Failure | 0:45–1:15 | 0:45 | ✓ |
| Collapse | 1:15–1:45 | **1:01** | 14s early |
| Wake-up | 1:45–2:10 | **1:19** | 26s early |
| End | 3:00 | **1:28** | 92s of narration over a static frame |

### ✅ 3.2 An 11.71-second dead hole immediately after the bloom

The largest silent gap in the demo body sat at t=0:03 — right after the strips bloom, inside Beat 2.
Nothing moved: no findings, no status changes, not even a trace bar, since traces only advance on
events.

It came from `simulate.py`'s first queued finding offset, which `PACE = 2.25` multiplied along with
everything else — so the KS-2 pacing fix made the demo's worst dead-air stretch 2.25× longer.
`09` §3 is explicit that dead air is where the "it's a screensaver" read gets formed.

### ✅ 3.3 The "~75s" claim was wrong by 22%

`01`, `05` and `simulate.py` all stated a ~75-second main cycle. Measured `run.started` →
`run.finished`: **61.3s**. Not the total either, which is 88.4s.

---

## Part 4 — What the board did not show

Payload already on disk that never reached the screen: `agent.status.note`, `agent.spawned.model`,
`agent.done.{duration_ms,tokens_in,tokens_out}`, `agent.retry.budget_remaining`, `verify.*.attempt`,
`run.finished.status`.

### ✅ 4.1 Convergence — the on-screen answer to `09` KS-5

KS-5 named the question this project could not answer: *"what did eight agents get you that one big
call wouldn't?"* The answer was already in the data and not on the screen.

Independent agents, which cannot see each other, already land on the same file:

| Evidence | Agents |
|---|---|
| `src/ingest/loader.py` | w2 (VALIDATION) + w3 (ERROR PATHS) |
| `src/tools/convert.py` | w2 (VALIDATION) + w8 (DEAD WEIGHT) |

Eight isolated contexts reaching the same conclusion is something a single call structurally cannot
demonstrate. It also turns the reducer's dedup job from a liability into the evidence.

**The trap:** a naive `evidence_ref` group-by finds *three* collisions. The third is
`ARCHITECTURE.md` ← w7 + w7r1 — a parent and its own retry, not independent agents. Counting it
would draw a false convergence on the very finding that is already the rejection. Parent/child
pairs must be excluded via `a.parent`.

### ✅ 4.2 Calibration — the swarm's uncertainty predicted the verifier

Confidence was an 11px number in a corner, invisible from six feet and doing no work.

The rejected finding is **0.72** — the lowest-confidence `high` in the entire run, against a
next-lowest of **0.83**. Its amendment returns at **0.88**, downgraded to medium. Rendered as a
gauge that is not a number, it is a visibly short bar among long ones that gets *longer* after the
retry.

The Beat 3 line this earns: *"The one the verifier threw out is also the one the agent was least
sure about. The system's own calibration saw it coming — and the amended claim comes back narrower
and better calibrated."*

### ✅ 4.3 Eight strips that all said WORK

Every `agent.status` carries a `note` — "reading tree", "scanning", "rate limited, backing off",
"re-reading ARCHITECTURE.md against source" — and none of it rendered. Showing it makes the rack
eight things doing *specific different work*, which is the fan-out argument carried by the texture
rather than the narration. It also rescues the `blocked` state that `09` §3 proposed cutting:
`BLOCK · rate limited, backing off` explains itself.

---

## Part 5 — Files the docs named that did not exist

- `logs/backup-live.jsonl` — called *the* parachute in `00` and `04`. ✅ now produced by
  `tools/save-parachute.sh`.
- Nothing computed the `&from=<seq>` seek points that `05`'s entire on-stage failure plan depends
  on. ✅ now `tools/beats.py`.
- `tools/emit.ts` / `emit.mjs` — the nine-line emitter `00` and `04` both promise. ✅ now shipped,
  with `agent_id` as a required first argument so KS-1 cannot recur in a language that has no
  `log.spawned()` helper.
- `fallback/PLANTED.md` — `generate_budget.py`'s own docstring says it writes this. It never did.
  ✅ docstring corrected (it also claimed "~200 rows" for 338).

---

## Part 6 — Deferred

Recorded deliberately, not built. The hackathon is today; the board works, is tested, and has a
verified parachute. Each of these is either too large to re-verify under time pressure or needs a
decision that is not mine.

### 📋 6.1 `rackRows()` drops grandchildren, and `renderRack()` never removes stale nodes

`dashboard.html:484-492`, `:536`. An agent whose parent exists but is *itself* a child matches
neither branch and vanishes from the rack while remaining in `st.agents` — still counted by the
`agents` counter and by `activeCount()`, so if it never finishes the board never goes idle, with no
strip on screen to explain why. A parent cycle drops both agents.

Separately, `renderRack` inserts and moves but never removes, so an agent that leaves `rackRows`
leaves its DOM node behind forever. Reachable via orphan-then-reparent, and the consequence matters:
**the same log renders a different number of strips under `?seed=1` than under animated replay**,
which is a structural violation of the purity claim `00` and `02` sell.

Not fixed today because it only bites at retry depth ≥ 2, and `03` caps
`MAX_RETRIES_PER_FINDING = 1`. **Fix:** make the child walk recursive, and add a removal pass.
~8 lines.

### 📋 6.2 Three readers of the same "contract" disagree about what a valid line is

`read_log` (two policies, depending on whether pydantic is importable), `drain_outbox` (a third —
it ignores `v` entirely and rewrites a missing `type` to `log.note`), and `parseLines` (a fourth)
all accept different sets of malformed lines. `"seq":"7"` is accepted and silently rewritten to `7`
by pydantic `read_log`, kept as a string by the dataclass path, and rejected by the renderer.

So **the drop-in file's behaviour changes qualitatively based on whether pydantic happens to be
importable in the starter repo** — which is exactly what §1.4 above turns into a crash-loop.
`QUICKSTART`'s "the bytes written are identical either way" is true for well-formed events and
false for everything else.

Sub-case: `read_log` uses `.splitlines()`, which splits on U+2028/U+2029/U+0085 — characters
`json.dumps(..., ensure_ascii=False)` writes **raw**. A finding title quoted from a PDF containing
U+2028 is recovered by `parseLines` and silently lost by `read_log`. **Fix:** `.split("\n")`, and
pick one validation policy. ~10 lines, but it needs a decision about which policy wins.

### 📋 6.3 Cycle-2 `run.finished` mixes scopes, and the test enshrines it

`duration_ms` is cycle-scoped (9.1s, correct); `totals` is run-cumulative. One payload, two scopes.
And `tests/fold.test.mjs` asserts the *last* `run.finished` totals against the *whole file* — so the
test would now **fail** if someone made cycle-2 totals correctly cycle-scoped. That test is mine;
it locks in the behaviour it should catch. **Fix:** reset the tally per cycle and sum per
`run.started` segment. ~10 lines.

### 📋 6.4 `tests/fold.test.mjs` coverage gaps

- **Zero render coverage.** `rackRows`, `renderRack`, `renderFindings`, `renderFoot` are never
  imported — findings 1.1, 1.2, 1.5 and 6.1 all live there. 18/18 stayed green while the rack
  dropped an agent and the pane collapsed three findings into one.
- **`runLive` and `?from=` are re-implemented rather than extracted**, so the test asserts its own
  copy is correct. Finding 1.3 was invisible to it for exactly this reason.
- **`drain_outbox` has no test** — the riskiest function in the repo.
- **Nothing asserts against the beat table**, which is why §3.1 went unnoticed. Four assertions
  would have caught it.
- The extraction regex `/<script>\n([\s\S]*)<\/script>/` is greedy to the *last* `</script>`; a
  second script tag anywhere silently changes what gets tested.

A `tests/render.test.mjs` driving Playwright, guarded so it skips cleanly when Playwright is
absent, would close most of this. ~60 lines.

### 📋 6.5 The run lifeline

The strongest genuinely-new visualization proposed, and the only one that competes with an existing
signature element. The work trace is a scroll of the last 30 events with **no time axis**, so it
cannot answer "did these actually overlap, or did they take turns?" A shared axis across all strips
answers it as a measurement: eight bars starting within two seconds and overlapping for forty-five.

It also gives the run a silhouette in the final frame, and makes Beat 5 structural — the 18-second
gap before the wake-up becomes a drawn gap rather than a claim.

There is ~380px of dead horizontal space in every strip at 1920, so it costs no layout change.
~40 lines. Deferred because it needs a real monitor to tune and would compete with the trace at
1280×720. If it looks cluttered, cut the lifeline, not the trace — they do different jobs.

### 📋 6.6 Finding → brief lineage

Beat 4 claims *"every line of it traces back to a specific finding."* Nothing on screen shows that.
The real version: `reduce.finished` carries `cited_findings: [id,...]`, and on arrival every uncited
finding dims to 25% while the cited ones stay lit and connect to the headline. The room watches
seventeen become three.

Needs a **new payload field**, so it touches the reducer prompt, `simulate.py`, and the golden log —
and per `09` KS-4 the golden log is the parachute. **Do not fake it** by ranking on
`severity × confidence`: it would look identical and would be the board asserting a lineage it does
not have, in a room that will ask.

### 📋 6.7 The rest

- **The contested-pair adjudication card** — the full version of `09` §4. Two agents file conflicting
  claims on the same evidence, the verifier settles it, and the board renders them as one card with
  a verdict stamp. Depends on the overlapping-slice payload change, so it is two decisions deep.
  §4.1's convergence marks are the cheap forward-compatible half: build them now and this becomes an
  upgrade rather than a rewrite.
- **`simulate.py --payload b`** — move `MISSION`/`LENSES`/`FINDINGS`/`RETRY_FINDING` into two dicts
  and select with a flag, then generate both golden logs. Retires KS-4 properly, replacing a
  documentation warning with a working escape hatch. ~50 lines, mostly data.
- **Port the scrubber into `dashboard.html` behind `?scrub=1`** — it already exists and works in
  `build/glassbox-mobile.html`. Behind a flag specifically, because a control you can nudge on stage
  is a liability.
- **Model tier and the funnel arithmetic** — `agent.spawned.model` shows real cost-shaped routing
  (workers on Haiku, the retry escalating to Sonnet, the reducer on Opus) and is invisible;
  `17 RAISED · 1 REJECTED · 16 VERIFIED → 1 BRIEF` states Beat 4's collapse as arithmetic. Both
  cheap, both cut for time.

---

## What could not be broken

Useful signal, and worth knowing before someone asks:

- **XSS.** Every event-derived string reaches the DOM through `textContent` or `dataset`. The three
  `innerHTML` sites are static templates, a numeric counter list, and a numbers-only trace. No
  payload could inject markup.
- **Overlapping polls.** `seen` plus the seq sort make a slow fetch racing a fast one a no-op.
- **Empty, one-event, and truncated logs.** All handled; the `lines.length - 1` partial-write
  heuristic is correct on both the Python and JS sides.
- **`drain_outbox`'s offset arithmetic.** The `complete[already:]` slice with in-loop increment is
  right, including blank lines and decode failures. The bug was the missing guard, not the
  bookkeeping.
- **Scale.** 19,200 events / 4.2MB parse in 29.6ms — 12% of the 250ms poll budget.
- **The `blocked` beat.** Fires and recovers across all 200 seeds tested.
- **Fold purity, `?from=` correctness, the keyed DOM, `?big=1`.** All hold. The `09` fixes claimed
  as done are done.
