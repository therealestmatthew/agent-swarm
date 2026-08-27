---
title: Implementation Roadmap — Design to Execution
status: live
part_of: agentic-sdlc
doc_type: roadmap
version: "1.0"
---

# Implementation Roadmap — Design to Execution

**Referenced by:** `CLAUDE.md` (phase gate) · `agentic-sdlc-design-v0.5.md` §12 (Open Questions)

**Proving ground:** Connected Planning Model Intelligence (CPMI) — a Python + Selenium tool whose
core value is custom DOM extraction logic. Every sequencing decision in this file is made against
that target, not against a generic repo. Where the design set assumes a different shape of codebase
than CPMI actually is, that gap is recorded in §3 as a defect rather than scheduled as a task.

---

## 1. Verdict on the backlog as submitted

The submitted backlog is a good inventory and a bad plan. Four structural problems:

1. **It is a flat priority list for deeply ordered work.** There are no dependency edges. At least
   four of the five P0s cannot start until a decision that is nowhere in the list has been made
   (§3, D1 and D2). Priority answers "how much do we care"; it does not answer "what can start
   Monday." This file replaces priority with sequence.
2. **It schedules the governed parts and omits the governor.** The Core Orchestrator, the event log,
   `RunManifest` persistence, and the agent dispatcher appear nowhere. Item 8 asks *where* the run
   manifest lives without asking *who writes it*. Every other item is a component that plugs into a
   runtime that has not been scoped. Nothing in the list, executed perfectly, produces a pipeline
   that runs once end to end.
3. **It re-opens closed questions and drops open ones.** Item 5 (Baseline Snapshot Mechanics) was
   resolved in v0.4 and lives in `test_harness_architecture.md` §1 — the real gap there is
   Selenium-specific and different (D4). Meanwhile 2 of the 5 open questions v0.5 §12 carries
   forward — **concurrency ceiling** and **Plan Writer dialogue depth** — are absent from the
   backlog entirely. That is the exact silent-drop pattern `plan/versions/REGRESSION.md` exists to
   document, recurring one document later.
4. **Its P2 tier is miscategorised.** Items 10–13 are tuning questions (decay rate, cost
   calibration, SOP cadence). They are not low-priority work that could be pulled forward with more
   people; they are **impossible** until first-run telemetry exists. Labelling them P2 implies a
   choice that is not available. They belong in a separate *blocked-by-data* tier (§6).

The one item whose stated priority I would raise on its own merits is **Secrets Posture (item 6,
P1)**. CPMI drives a browser against a live Connected Planning tenant. From the first real run, an
LLM-driven process holds credentials to a production-adjacent SaaS system, and a Selenium failure
artifact — screenshot of an authenticated session, DOM dump, HAR — is the highest-leakage evidence
class in the entire design. It is a P0 and it blocks item 5.

---

## 2. What is missing, in one place

New items introduced by this roadmap, with the item they attach to:

| ID | Item | Why it is missing-critical | Attaches to |
|---|---|---|---|
| R1 | CPMI shared-file inventory + intent vocabulary derivation | The existing vocabulary is web-framework-shaped; CPMI has no router (D2) | Blocks backlog #1 |
| R2 | Shared-file materialization model across worktrees | §4 and `execution_isolation.md` describe incompatible mechanics (D1) | Blocks backlog #1 |
| R3 | Core Orchestrator skeleton: state machine, event log, manifest persistence, dispatcher | The governor, absent from the backlog entirely | Subsumes backlog #8 |
| R4 | Agent Spec format and registry | Supersedes "prompts" — prompt is 1 of 6 fields (§4, S0-4) | Supersedes backlog #3 |
| R5 | Two-tier test strategy + `mutation.diff_scoped` scope predicate | The blocking mutation gate is unsatisfiable on browser tests (D5) | Blocks backlog #5 |
| R6 | Container isolation for the browser tier | `execution_isolation.md` §5's own escape condition is true on day one (D6) | Blocks backlog #5 |
| R7 | Cost metering substrate + hard kill switch | Replaces the un-runnable half of backlog #4 | Reframes backlog #4 |
| R8 | Human gate control plane (sign-off with identity, written to the event log) | 8 human gates exist; nothing lets a human see or clear one | Distinct from backlog #7 |
| R9 | Evidence artifact redaction and retention policy | `Finding.evidence_ref` may point at authenticated screenshots (D9) | Pairs with backlog #6 |
| R10 | Deterministic-core conformance suite | The "deterministic before LLM" thesis is currently untested | Follows R2 |
| R11 | Run abort and halt semantics | "Pause" is undefined for an agent holding a live driver (D12) | Follows R3 |
| R12 | `FailureSignature` extension for in-process state leakage | Python leaks through module globals, not just the DOM (D7) | Amends contracts |
| R13 | Concurrency ceiling | v0.5 §12 open question dropped from the backlog | Standalone |
| R14 | Plan Writer dialogue depth | v0.5 §12 open question dropped from the backlog | Standalone |

---

## 3. Design defects found

These need a **decision**, not a schedule. Several are cheap; two are load-bearing. None are
patched here — the roadmap records them; the design set is where they get fixed.

| ID | Where | Defect | Severity |
|---|---|---|---|
| D1 | `v0.5` §4.2 vs. `execution_isolation.md` §6 | §4 says an intent is "applied synchronously before the agent continues." `execution_isolation.md` gives every Task Dev its own worktree with its own `HEAD`, and says "the Integrator's shared-file commit last." Both cannot be true. Either the service writes into every live worktree — destroying the stable read view §3 of that file promises — or the agent never sees its own applied intent and "synchronous" is a fiction whose collisions resurface at merge, which is precisely what §4 exists to prevent. **No materialization path is specified anywhere in the set.** | **Load-bearing** |
| D2 | `agent_interface_contracts.py` §4.2 intents | `AddExport` / `AddRoute` / `AddProviderBinding` is an Express/Nest/FastAPI vocabulary. CPMI is a Selenium extraction tool: no router, no DI container. Its real shared surfaces are a selector/constant map, an extractor or page-object registry, `conftest.py` fixtures, a CLI subcommand table, and `__init__.py` barrels. Prototyping an AST transform for `AddRoute` validates a transform that will never fire on the proving ground. | **Load-bearing** |
| D3 | `v0.5` Agent Roster vs. §9.1 | Budget Accountant is typed *Utility* (an agent) in the roster, but `budget.within_ceiling` is listed as a **deterministic** gate on every transition. A circuit breaker that is itself an LLM can fail to fire, and it fails hardest under exactly the runaway conditions it exists to catch. Recommend: the ceiling check is deterministic middleware in the dispatcher; keep an agent only for advisory forecasting. | High |
| D4 | `test_harness_architecture.md` §1.2 | The mandate is `browser.new_context()` / `context.close()`. **Selenium has no `new_context()`.** Its equivalent is a fresh driver process with a fresh `--user-data-dir` — order-of-seconds process spawn, not milliseconds. §1.2's explicitly-accepted cost tradeoff was priced for Playwright contexts and is materially wrong for the stated proving ground. | High |
| D5 | `v0.5` §9.1 vs. `test_harness_architecture.md` §3.2 | `mutation.diff_scoped` is **blocking**, and §3.2 justifies its affordability with "a pure, hermetic unit suite (this project's stated target environment)." CPMI's load-bearing tests are browser tests, which are neither pure nor hermetic. As specified the gate either blocks forever or gets waived — and a routinely-waived blocking gate is worse than no gate, because the ledger records it as enforced. | High |
| D6 | `execution_isolation.md` §5 | "Containers are not required — yet ... revisit the moment any task's tests start binding a port or hitting a real service." A Selenium driver binds a port and drives a real service. The escape condition is satisfied before the first task runs; containers are Stage 0 scope for the browser tier, not a later concern. | High |
| D7 | `FailureSignature` | `dom_state_diff_from_baseline` is the only leakage signal. In Python the dominant leak channels are module-level globals, an un-torn-down driver singleton, an unreverted monkeypatch, and import-order effects — all of which leave the DOM pristine. Triage rule 4 will confidently misroute every one of them to Task Dev as **Logic**, and Task Dev will "fix" a test that has no bug. | High |
| D8 | `infra_triage_matrix.md` §2 | No rule covers `isolated_rerun_outcome == "passed"` with no timeout proximity, no network excess, and no DOM diff — i.e. *passes alone, fails in suite*. `v0.5` §6 step 4 names this case ("state leakage") but the rules engine does not implement it. Every instance falls through to the LLM Investigator, and this is the single most common flake shape in a suite of this kind, so it will dominate LLM triage spend. | Medium |
| D9 | `Finding.evidence_ref` | Nothing constrains what an evidence reference may point at, how long it is retained, or who may dereference it. For a browser suite that means authenticated screenshots, DOM dumps containing tokens, and HAR files with bearer headers flowing into an event log that LLM agents read. | Medium |
| D10 | `v0.5` §12 vs. backlog | Concurrency ceiling and Plan Writer dialogue depth were carried forward as open in v0.5 and dropped from the backlog without resolution — the v0.2 regression pattern, repeating. | Medium |
| D11 | Glossary + `v0.5` §4 heading | "Shared-File Intent Service" and "Synchronous Intent Service" both exist as glossary terms cross-referencing each other as aliases, and §4's heading still uses the old name. Backlog item 14 is correct that this is cosmetic — but it is cosmetic **now** and stops being cheap once code, schemas, and log field names are written against either spelling. | Low, urgent |
| D12 | `budget_and_escalation_policy.md` §3 | A ceiling halt "pauses the pipeline" and snapshots state. Undefined: what a pause does to an agent mid-`WebDriverWait`, to a held driver process, to an intent submitted but not yet applied, and to N live worktrees. There is no general run-abort anywhere in the set — only the SOP's targeted pause and production rollback. | Medium |
| D13 | `structural_change_runbook.md` §4 vs. `v0.5` §12 | The runbook's open "additive-intent-count threshold" and §12's open "task granularity" are the same knob measured from opposite ends: a task large enough to need many intents against one file *is* a task drawn too coarsely. Resolving them independently will produce two numbers that contradict each other. | Medium |

---

## 4. The sequence

Six stages. A stage may start when its predecessor's **exit criterion** is met, not when its
predecessor's tasks are "mostly done." Original backlog numbers are given as `#n`.

### Stage 0 — Decide and record (documents only; no runtime)

Nothing here needs code, and everything downstream is blocked on it. This is the stage the backlog
skipped.

| Task | Notes |
|---|---|
| **S0-1** Resolve D1: shared-file materialization | The one decision that determines what the intent service *is*. Recommended shape: the service is the sole writer of a canonical shared-file branch; worktrees materialize its output read-only and never commit it; the Integrator's shared-file commit is a fast-forward of that branch, not a merge. Write it into `execution_isolation.md` and `v0.5` §4 as one mechanism described once. |
| **S0-2** CPMI shared-file inventory (**R1**, resolves D2) | Read the actual CPMI tree. Enumerate every file two tasks would both need to touch. Derive the intent vocabulary from that list. Expect roughly: `AddSelector`, `RegisterExtractor`, `AddFixture`, `AddCliCommand`, `AddExport`. Retire `AddRoute` and `AddProviderBinding` unless CPMI genuinely has them. |
| **S0-3** Two-tier test strategy (**R5**, resolves D4, D5, D6) | Tier 1 hermetic unit (worktree-isolated, mutation-gated, fast). Tier 2 browser integration (container-isolated, driver-per-test, **not** mutation-gated, flake-registry-governed). Give `mutation.diff_scoped` an explicit scope predicate so a waiver is never needed. Re-price §1.2's cost tradeoff against Selenium's real teardown cost. |
| **S0-4** Agent Spec format (**R4**, supersedes #3) | An agent is not a prompt. It is `{system_prompt, input_schema, output_schema, tool_allowlist, write_scope, model_tier, spec_version}`. `GateResult.reviewer_spec_version` already expects this record to exist; nothing currently defines it. Prompts are drafted **inside** this format, not instead of it. |
| **S0-5** Provisional task granularity + intent threshold (**#2**, resolves D13) | Set both knobs together, explicitly as provisional. Starting rule: one task owns exactly one `src/` module directory plus its mirrored `tests/` path; a task requiring more than 3 additive intents against a single shared file is a decomposition error and exits via the SOP. Both numbers are measured and revised in Stage 5 — do not present them as settled. |
| **S0-6** Concurrency ceiling (**R13**) | For CPMI the binding constraint is not API rate limits — it is RAM. Each Chrome instance is hundreds of MB, and the ceiling is `floor(available_RAM / per-container footprint)` long before token throughput binds. Say so, and state which resource binds first rather than discovering it at runtime. |
| **S0-7** Naming pass (**#14**, resolves D11) | Mechanical. One spelling: **Shared-File Intent Service**. Collapse the duplicate glossary term into an alias note, fix §4's heading. Do it before any code names a field. |

**Exit criterion:** D1, D2, D5, D6 have written answers in the design set, and the intent vocabulary
is CPMI-derived. Until then, backlog #1 is prototyping against a guess.

### Stage 1 — Walking skeleton (first thing that runs)

The correction to the backlog's biggest structural flaw: build the governor, end to end, before any
component is good.

| Task | Notes |
|---|---|
| **S1-1** Core Orchestrator state machine (**R3**, subsumes #8) | Reads a `RunManifest`, dispatches, persists a new one. Phases 2→6 only. |
| **S1-2** Event log + manifest persistence (**#8**) | Resolves the run-manifest-location question by building it. Recommendation: **out of tree**, content-addressed, with an in-tree pointer committed to the PR — auditability without putting run state in every diff. |
| **S1-3** Cost metering + hard kill switch (**R7**, reframes #4, resolves D3) | Every invocation emits `{tokens_in, tokens_out, model, cost, task_id, phase}` to the event log. The **kill switch is deterministic middleware in the dispatch path** and ships now; the accurate cost model is derived from Stage 3–5 telemetry, not calculated up front from invented priors. |
| **S1-4** Worktree lifecycle manager | `execution_isolation.md` §4's lifecycle, as code: create, hand off, tear down, reap orphans. |
| **S1-5** Run abort / halt semantics (**R11**, resolves D12) | Define what pause does to a live driver, a held lock, and a submitted-but-unapplied intent. Then implement it, because Stage 4 will need it. |
| **S1-6** Human gate control plane (**R8**) | Authenticated approve/reject that writes an identity into the event log. Most phases cannot complete without it. Note this is **control plane, not visualization** — it is not the dashboard `CLAUDE.md` scopes out. |

**Exit criterion:** a stub task with hard-coded agents traverses Phases 2→6 unattended, halts at a
human gate, resumes after sign-off, and **resumes correctly from `kill -9`**. If the manifest cannot
survive a kill, resumability is a claim rather than a property.

### Stage 2 — The deterministic core (TDD'd conventionally, by humans)

This is the layer the whole thesis rests on. It is also the only layer that can be tested to a
conventional standard, so it should be held to the highest one in the repo.

| Task | Notes |
|---|---|
| **S2-1** AST transform prototype (**#1**) | Now correctly scoped: the CPMI-derived vocabulary from S0-2, against real CPMI files. **The success criterion is not "libcst inserted a node."** It is: (a) round-trips through the repo formatter with zero unrelated diff lines, (b) is idempotent under replay, (c) fails loudly rather than partially on an unmapped structure. |
| **S2-2** Collision detection (§4.5) | The actual novelty, and absent from the backlog. Same-key collisions are trivial; the hard cases are semantic — a shadowing binding, two selectors for the same element under different names. Decide what the service detects and what it provably does not. |
| **S2-3** Triage rules engine (**#5** partial, resolves D8) | Implement `infra_triage_matrix.md` §2, plus the missing passes-alone/fails-in-suite rule. |
| **S2-4** `FailureSignature` in-process leakage field (**R12**, resolves D7) | Additive schema change: a process-state diff alongside the DOM-state diff. |
| **S2-5** Deterministic-core conformance suite (**R10**) | Golden cases for every rule, every intent transform, every gate evaluation. |

**Exit criterion:** the conformance suite is green, and every ambiguous-fallthrough path is covered
by a case that asserts it falls through *deliberately* rather than by omission.

### Stage 3 — First Maker/Checker pair, under a real oracle

The backlog starts with Plan Writer / Task Decomposer. That is the **worst** first pair: plan quality
is subjective, and the verdict ledger that would grade them does not exist yet. Start where the
oracle is deterministic.

| Task | Notes |
|---|---|
| **S3-1** Test Author agent spec + Baseline Guard + mutation gate | Ground truth is a test suite, not an opinion. Falsifiable on day one. |
| **S3-2** Task Dev / Code Reviewer in Shadow Mode | Per `calibration_and_measurement.md` §2 — shadow is the default onboarding path. |
| **S3-3** Verdict ledger | Stands up the measurement substrate the P2 tuning items are all blocked on. |
| **S3-4** Plan Writer / Task Decomposer specs (**#3**) | Last, not first — by now there is a ledger to grade them against. |
| **S3-5** Plan Writer dialogue depth (**R14**) | Answerable once S3-4 runs and the review-loop cost is observable. |

**Exit criterion:** one real CPMI change goes plan → decomposition → tests → implementation → merge
with agents in the loop and humans at the gates, single task, no parallelism.

### Stage 4 — The browser tier (where CPMI actually lives)

| Task | Notes |
|---|---|
| **S4-1** Container isolation for browser tasks (**R6**) | Per S0-3's Tier 2. |
| **S4-2** Selenium baseline snapshot mechanics (**#5**, resolves D4) | Driver-per-test with a fresh profile dir; the §1.4 comparison table adapted to what a Selenium driver can actually report. |
| **S4-3** Secrets posture (**#6**) | Promoted to hard blocker. Credentials injected into the container environment at task start, never a file inside a worktree the agent can read and echo. Per Principle 12 this is a permission boundary, not an instruction. |
| **S4-4** Evidence redaction and retention (**R9**, resolves D9) | What an `evidence_ref` may point at, how long it lives, who may dereference it. Ships **with** S4-3, not after. |
| **S4-5** Flake Registry | Only meaningful once there is a real browser suite generating real flakes. |

**Exit criterion:** the browser tier runs green twice consecutively from cold, and a deliberately
injected state leak is caught by triage as *Infra — state leakage*, not misrouted to Task Dev.

### Stage 5 — Swarm at width

| Task | Notes |
|---|---|
| **S5-1** Parallel dispatch to the S0-6 ceiling | |
| **S5-2** Integrator + No-Conflict Gate + cumulative conflict counter | |
| **S5-3** Structural Change SOP, first live trigger | |
| **S5-4** Swarm observability (**#7**) | Correctly placed here: there is nothing to observe until there is parallelism. Reuse candidates are listed in `archive/glass-box/README.md` — but note that board has no concept of a phase or a human gate, which this needs. |
| **S5-5** Task granularity, measured (**#2** revisited) | The empirical answer that replaces S0-5's provisional one. v0.1 called this "the parameter most likely to be wrong on the first attempt"; deciding it in a document rather than from conflict-rate data repeats that mistake. |

**Exit criterion:** a multi-task CPMI change merges clean, with at least one intent collision
correctly rejected and resolved in one shot per §4.5.

### Stage 6 — Unblocked by data

Everything here needs telemetry that does not exist until Stage 5 has run several times.

- **#11** Conflict decay-rate tuning — needs promotion data.
- **#4** Cost model, calibrated — needs S1-3's metering across real runs.
- Shadow → Gating promotion for `code.review` — needs the S3-3 ledger at volume.
- **#12** Structural Change SOP cadence — needs repeat triggers to exist.
- **#9** Vocabulary extension process — needs the first genuine "we need a new intent op" event, which is the only thing that shows what the process must handle. Formalising it before that is speculative design of a workflow with no users.

---

## 5. Revised priority, against the original

| # | Item | Was | Now | Why it moved |
|---|---|---|---|---|
| 1 | AST Transform Prototype | P0 | **Stage 2** | Not blocked by importance — blocked by D1 and D2. Cannot start until the vocabulary is CPMI-derived and materialization is decided. |
| 2 | Task Granularity Heuristic | P0 | **Stage 0 (provisional) + Stage 5 (measured)** | Cannot be settled a priori; needs conflict-rate data. |
| 3 | Core Agent Prompts | P0 | **Stage 0 (format) + Stage 3 (content)** | Prompt is 1 of 6 fields in an agent spec; and Plan Writer is the wrong first pair. |
| 4 | Baseline Cost Model | P0 | **Stage 1 (metering + kill switch) + Stage 6 (model)** | The kill switch is the safety property and ships now; the model is unfalsifiable without measurement. |
| 5 | Baseline Snapshot Mechanics | P0 | **Stage 4** | Largely already resolved in v0.4; the live gap is Selenium-specific and needs containers first. |
| 6 | Secrets Posture | P1 | **Stage 4, hard blocker** | Live tenant credentials in an LLM-driven process. Raised. |
| 7 | Swarm Observability | P1 | **Stage 5** | Nothing to observe before parallelism — but see R8: gate sign-off is Stage 1 and is a different thing. |
| 8 | Run-Manifest Location | P1 | **Stage 1** | Raised: it is not a filing question, it is the orchestrator's persistence layer. |
| 9 | Vocabulary Extension Process | P1 | **Stage 6** | Lowered: speculative until a real extension is needed. |
| 10 | Enterprise Invariant Arbitration | P2 | **Deferred, no stage** | Single-repo (CPMI) proving ground. The question does not arise until repo two. Say that, rather than carrying it as perpetually-P2. |
| 11 | Conflict Decay-Rate Tuning | P2 | **Stage 6** | Blocked by data, not deprioritised. |
| 12 | Structural Change Cadence | P2 | **Stage 6** | Blocked by data. |
| 13 | Modular File Versioning | P2 | **Stage 0, do it in an hour** | Raised: the answer is "companions version independently, and each names the blueprint version it was last reconciled against." Cheap now; expensive after Stage 2 writes code against these files. |
| 14 | Naming Inconsistency | P2 | **Stage 0** | Raised on sequence, not on impact. Costs an hour now and more every week. |

---

## 6. What this changes in `CLAUDE.md`

`CLAUDE.md` currently states: *"We are in design, not build. Do not start implementing agents,
services, or schemas until the design settles and this line changes."*

That gate is still correct and should **not** be flipped by this document. What it lacks is a
release condition. Proposed: the gate releases when **Stage 0's exit criterion is met** — D1, D2,
D5, and D6 answered in the design set, and the intent vocabulary derived from the real CPMI tree.
Stage 0 is entirely documents, so it is executable under the current gate as written.

---

## 7. Decisions needed from the human

1. **D1 — materialization.** The recommendation in S0-1 is one of at least three viable shapes. This
   is an architecture decision, not a scheduling one, and it changes what gets built in Stage 2.
2. **CPMI repo access.** S0-2 cannot be done from this repo. The shared-file inventory requires
   reading the actual CPMI tree.
3. **Scope of the first end-to-end run.** Stage 3's exit criterion names "one real CPMI change" —
   which change, and who signs the gates.
4. **D3 — Budget Accountant.** Confirm the ceiling check moves to deterministic middleware, or state
   why it should remain an agent.

---

## 8. Deliberately not in this roadmap

- **Enterprise invariant arbitration** (#10) — see §5. Not deferred to a later stage; genuinely out
  of scope for a single-repo proving ground, and better answered by the second repo's real
  disagreement than by anticipating it.
- **The dashboard as a product.** R8 builds a gate control plane because the pipeline cannot run
  without one. Visualization stays scoped out per `CLAUDE.md` until the pipeline is real.
