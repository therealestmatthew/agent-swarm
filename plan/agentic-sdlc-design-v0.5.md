---
title: Agentic SDLC Orchestration — Design Document v0.5
status: live
part_of: agentic-sdlc
doc_type: blueprint
version: "0.5"
---

# Agentic SDLC Orchestration — Design Document v0.5

## Changelog from v0.4

`plan/versions/REGRESSION.md` is the full analysis behind this version; this table is its
executive summary. Nine gaps were found between v0.1 and v0.4 — content that stopped appearing
between versions without ever being marked as cut, unlike every deliberate removal in this
document's own history. Five are reinstated here; the rest are recorded as held or as still-open
questions, not silently dropped a second time.

| Area | v0.4 | v0.5 |
|---|---|---|
| Validator asymmetry | Absent since v0.1 | **Reinstated:** Principle 11 — a validator sees the spec and the artifact, never the generator's rationale |
| Write-scope enforcement | Stated as an outcome | **Reinstated:** Principle 12 — enforced by permission/config, not by instructing an agent not to |
| Core Orchestrator state | Undefined | **Reinstated:** `RunManifest` schema (`agent_interface_contracts.py`); §3 names it as the orchestrator's entire context alongside the event log |
| Concurrent execution isolation | Absent since v0.1 | **Reinstated:** one git worktree per task — new companion, `execution_isolation.md` |
| Weakened-assertion detection | Absent since v0.1 | **Reinstated:** diff-scoped mutation testing — `test_harness_architecture.md` §3 |
| Consolidated gate tables | Never relocated from v0.1 | **Reinstated:** §9 — deterministic, agent, and human gates in one place |
| Reward-hacking framing | Absent since v0.1 | **Reinstated:** §10, restated against the current 22-agent roster |
| Shadow-mode calibration | No exit criterion anywhere in the set | **Reinstated:** verdict ledger and spec versioning — new companion, `calibration_and_measurement.md`; `GateResult` gains `reviewer_spec_version` (additive) |
| Five v0.1 open questions | Dropped without resolution at v0.2 | Re-listed in §12, marked carried-forward-and-unaddressed rather than silently absent |

Not reinstated: v0.1's build order (§9) — out of scope while the design is still being refined; see
`CLAUDE.md`'s own gating line. Naming drift between "Synchronous" and "Shared-File" Intent Service is
noted in `REGRESSION.md` and left as-is pending a deliberate naming pass.

## Modular Reference Files

| File | Owns |
|---|---|
| `agent_interface_contracts.py` | Every schema in the system — additive intents, `InvariantScope`, `FailureSignature`, `GateResult` — single source of truth |
| `core_adapter_boundary.md` | **New.** What the universal Core owns vs. what a target repo declares for itself — the `RepoDeclaration`/`GovernancePolicy` adapter contract, capability negotiation, hydration, and credential injection |
| `test_harness_architecture.md` | Baseline capture mechanics for `dom_state_diff_from_baseline`; Protocol-fake test double standards; diff-scoped mutation testing (§3) |
| `execution_isolation.md` | **New.** One git worktree per task — why disjoint write ownership alone doesn't isolate reads |
| `calibration_and_measurement.md` | **New.** Verdict ledger, Shadow Mode promotion thresholds, agent-spec versioning |
| `context_retrieval_strategy.md` | Context Gatherer search heuristics (git history vs. vector search) and token budget management |
| `budget_and_escalation_policy.md` | Exact loop ceilings, the escalation ladder rung-by-rung, and Budget Accountant cost ceilings |
| `infra_triage_matrix.md` | Deterministic failure-classification rules engine |
| `structural_change_runbook.md` | Human-gated SOP for non-additive shared-file changes |

---

## 1. Core Design Principles

1. **Maker/Checker pairing.** Every agent that generates an artifact is paired with an agent that validates it: Plan Writer / Plan Reviewer, Test Author / (implicitly) Test Runner, Task Dev / Code Reviewer, Test Runner / Test Investigator, PR author / PR Reviewer.
2. **Minimal-context orchestration.** The Core Orchestrator's sole job is coordination and routing. It does not hold large context itself; the Context Gatherer assembles targeted context per stage in a separate context window (mechanics: `context_retrieval_strategy.md`).
3. **TDD-first build.** All implementation work starts from a failing test, authored by a Test Author agent that is structurally separated from the agent that writes implementation code.
4. **Disjoint write ownership.** Within the parallel swarm, each Task Dev agent owns a mutually exclusive set of files (`src/**` scoped per task). Explicit carve-out for shared files (§4) and an explicit escape hatch for changes too large to be additive (`structural_change_runbook.md`).
5. **Human gates at irreversible or judgment-heavy points.** Plan Approval, Contract Freeze, QA→Prod promotion, shared-file registration/promotion, invariant deprecation, and structural architecture changes all require human sign-off.
6. **Model escalation on repeated failure.** Agents that fail review repeatedly are re-run on a stronger model rather than retried indefinitely (exact ladder: `budget_and_escalation_policy.md`).
7. **Budget and circuit-breaking.** Enforcement and forecasting are separated. A **deterministic Budget Enforcer** checks every phase transition against `GovernancePolicy.budget_ceilings` and refuses the transition on breach; a **Budget Accountant** agent forecasts spend trend advisorily and gates nothing. A circuit breaker that is itself an LLM can be slow, wrong, or unavailable at exactly the moment a runaway swarm is burning fastest — so nothing that must fire is left to judgment. The same philosophy governs individual loop-back edges (exact thresholds and the enforcement point: `budget_and_escalation_policy.md`).
8. **Merge conflicts are decomposition errors.** A merge conflict is evidence the Task Decomposer drew task boundaries incorrectly — never punted to the PR Reviewer. Repeated conflicts on the same seam escalate as a boundary failure, not an infinite retry loop.
9. **Shared state is governed, not merged.** Files that are legitimately shared across tasks are modified only through a closed vocabulary of typed, additive operations applied by a deterministic service (§4; schemas in `agent_interface_contracts.py`).
10. **Deterministic classification before LLM judgment.** Wherever a failure or event can be classified from structured signals alone, it is. An LLM is only invoked for the residue that doesn't cleanly match a deterministic rule. Governs both the Shared-File Intent Service (§4) and failure triage (§6, `infra_triage_matrix.md`).
11. **Validator asymmetry.** *(Reinstated from v0.1 — absent v0.2 through v0.4.)* A validator only adds signal if its inputs differ from the generator's. Concretely: information asymmetry (the reviewer sees the spec and the artifact, never the generator's own rationale — a validator that reads the builder's justification is grading the persuasion, not the artifact); tooling asymmetry (a validator can execute — run the tests, run the type checker, grep for callers — a review that only reads is a style pass); model asymmetry (a different tier from the builder, at minimum). Applies to every Maker/Checker pair in §2, most concretely Plan Writer/Plan Reviewer and Task Dev/Code Reviewer.
12. **Enforce with permissions, not prompts.** *(Reinstated from v0.1 — stated in v0.4 as an outcome, e.g. "Test Author... never touches implementation," without this as its stated mechanism.)* A write-scope boundary (Principle 4) or a role restriction (Test Author writes no implementation) is a permission or a filesystem/config-level constraint, never an instruction an agent is asked to reason its way past. An instruction can be argued with; a permission cannot.

---

## 2. Agent Roster

| Agent | Type | Role |
|---|---|---|
| Core Orchestrator | Deterministic | Coordination and routing only; minimal context |
| Context Gatherer | Generator | Assembles targeted context per stage — heuristics in `context_retrieval_strategy.md` |
| Plan Writer | Generator | Produces the implementation plan |
| Plan Reviewer | Validator | Adversarial review of the plan; bounded loop back to Plan Writer |
| Security Review (plan-time) | Validator | Reviews plan for security implications before approval |
| Invariant Curator | Utility | Maintains the manifest of architectural constraints, scoped `repo_local` / `enterprise_wide` (§5) |
| Task Decomposer | Generator | Breaks the approved plan into disjoint tasks with interface maps; owns the Structural Change SOP when triggered |
| Test Author | Generator | Writes failing tests only (`tests/**`); never touches implementation |
| Task Dev Swarm | Generator | Parallel agents, each owning a disjoint `src/**` slice; emits shared-file intents rather than editing shared files directly (§4) |
| Code Reviewer | Validator (shadow mode) | Reviews each Task Dev branch; bounded loop back; escalates model on repeated failure |
| Shared-File Intent Service | Deterministic + Validator | Applies typed additive intents to registered shared files in real time; rejects colliding intents with blocking context; tracks per-file conflict counters for promotion |
| Integrator | Deterministic | Merges branches; runs the No-Conflict Gate; increments conflict counters on ungoverned files |
| Test Runner | Utility | Executes the full suite |
| Baseline Guard | Validator | Checks `baseline_delta`, test counts, coverage — guards against silent test deletion |
| Test Investigator | Validator | Judgment fallback for failures the deterministic triage table can't classify (§6); bounded loop back to Task Dev |
| Flake Registry | Utility | Static registry of known flaky tests, supplemented by the deterministic triage matrix |
| CI Cleanup | Generator | Lint and formatting pass |
| PR Reviewer | Validator | Diff-time review of the draft PR |
| Security Reviewer (diff-time) | Validator | Diff-time security pass |
| Log Monitor | Utility | Always-on observation in production |
| Error Analyzer | Validator | Pattern-matches log findings; triggers rollback initialization on critical findings |
| Budget Enforcer | Deterministic | Middleware in the dispatch path; checks each transition against `GovernancePolicy.budget_ceilings` and refuses on breach. Never an LLM (`budget_and_escalation_policy.md` §4) |
| Budget Accountant | Utility (advisory) | Forecasts spend trend across all agents and raises advisory findings; **gates nothing** — separated from enforcement so a slow or wrong forecast cannot fail open |

Every Validator agent returns a `GateResult` (`agent_interface_contracts.py`) — a standardized pass/fail verdict with blocking vs. advisory findings and an evidence reference, so the Core Orchestrator can route on a consistent shape regardless of which Validator produced it.

---

## 3. Phase-by-Phase Architecture

The Core Orchestrator's entire state across all eight phases is a `RunManifest` (schema: `agent_interface_contracts.py`) plus a reference to the event log — never a plan body, never a diff. *(Reinstated from v0.1 §3.1, absent v0.2 through v0.4; the original resumability argument is preserved in `plan/versions/agentic-sdlc-design-v0.1.md` §3.1.)* The manifest persists after every phase transition, so a crashed run resumes from the last recorded phase rather than restarting. Because every model in this system is immutable (see `agent_interface_contracts.py`'s header), a transition produces a *new* `RunManifest` instance rather than mutating the old one — the same additive discipline Shared-File Governance (§4) applies to shared files applies here to orchestrator state.

### Phase 1 — Planning & Context (Gating)
Context Gatherer pulls targeted context into a separate context window (`context_retrieval_strategy.md`). Plan Writer produces a plan; Plan Reviewer adversarially reviews it (bounded loop, §7). Security Review runs a plan-time pass. The Invariant Curator injects relevant constraints into the approval step. A human gate approves the plan.

### Phase 2 & 3 — Decomposition & TDD (Verification Green)
The Task Decomposer produces disjoint tasks with interface maps and ownership assignments. A human Contract Freeze gate reviews the interface contracts — including any Protocol definitions for shared dependencies (`test_harness_architecture.md` §2.3) and any anticipated shared-file changes — and flags tasks that need the Structural Change SOP instead of the standard swarm flow. The Test Author then writes failing tests (`tests/**` only) ahead of any implementation.

### Phase 4 — Parallel Swarm & Shared-File Governance
Task Dev agents work disjoint `src/**` slices in parallel. Code Reviewer runs in shadow mode on each branch, escalating to a stronger model after repeated failed reviews (bounded, §7). Any change to a registered shared file is emitted as a typed intent (§4), applied by the Shared-File Intent Service and re-materialized into every live worktree before the agent continues (§4.7; mechanics in `execution_isolation.md` §7). A task that turns out to need a structural, non-additive change exits the swarm via `structural_change_runbook.md`.

### Phase 5 — Integration (Clean Merge)
The Integrator merges completed branches. Because shared-file changes were resolved in Phase 4, this phase only resolves genuine git-level conflicts on disjoint code. A conflict is treated per Principle 8: bounded retries, then escalation to the Decomposer as a boundary failure. The Integrator also increments the lifetime conflict counter for any ungoverned file involved (§4.6).

### Phase 6 — Verification & Cleanup
Test Runner executes the full suite. Baseline Guard checks for anti-deletion regressions. Failures are classified via the deterministic triage table (`infra_triage_matrix.md`) first; only signatures that don't cleanly match a rule reach the Test Investigator (§6). CI Cleanup runs lint/formatting, with a re-review pass.

### Phase 7 & 8 — Promotion & Observation
Draft PR is generated; PR Reviewer and a diff-time Security Reviewer evaluate it. Approved PRs merge automatically from Dev to QA; QA to Production requires a human approval gate. In production, the Log Monitor watches continuously; the Error Analyzer pattern-matches findings, initiating rollback authorization on critical ones.

---

## 4. Shared-File Governance (Synchronous Intent Service)

### 4.1 Problem
A small set of files — DI containers, routers, export barrels — are inherently shared across tasks that are otherwise disjoint. Treating them as ordinary merge targets recreates the failure mode the swarm's ownership model exists to avoid: two agents can produce textually non-overlapping, git-clean changes that are still semantically incompatible.

### 4.2 Typed, additive intents
Task Dev agents never edit a registered shared file directly. They emit typed intents (`AddExport`, `AddRoute`, `AddProviderBinding` — full schemas in `agent_interface_contracts.py`). The vocabulary is deliberately closed and additive-only; a genuine structural change (splitting a router, restructuring a DI graph) exits via `structural_change_runbook.md` instead.

### 4.3 Shared-File Registration
Before a file can accept intents, a one-time registration step maps its structural insertion points: an agent proposes the map, a human confirms it once, and it's cached for reuse.

### 4.4 Deterministic application, per language
Applying an intent is a mechanical AST transform wherever possible — `libcst` for Python, `ts-morph`/Babel for TypeScript/JS — with no LLM in the loop for the non-conflicting case.

### 4.5 Smart Mutex Rejection
A colliding intent is rejected back to the submitting agent with the blocking context (what the other agent already claimed), so it can resolve in one shot rather than restarting a planning cycle.

### 4.6 Self-expanding governance
Promotion is driven by a **cumulative, lifetime conflict counter per file** — not a per-phase count. Every git-level conflict the Integrator resolves on an ungoverned file increments that file's counter; three lifetime conflicts (`>2`) queue it for promotion. The counter decays by 1 per clean integration phase, floored at 0 — distinguishing chronic friction from an isolated heavy refactor that happened to touch the file three times in one phase. **Promotion still requires human confirmation**, identical to initial registration — the counter is evidence for a proposal, not an automatic action.

### 4.7 Materialization

A registered shared file is never tracked in a task's worktree. The Intent Service is the sole
writer of a canonical `shared/` branch; applied content is re-materialized into every live
worktree's working directory, where the interpreter sees it and git does not; the Integrator
fast-forwards that branch as the final commit. This is what "applied synchronously" in §4.2 means
concretely, and it is why §9.1's `merge.no_conflict` gate is honest rather than quietly exempted for
these files — task branches carry no shared-file changes to conflict over.

Because the shared-file content is then absent from every task's diff, Core synthesizes a
per-PR **shared-file delta view** from the intent log, attributing each hunk to the intent and the
task that produced it. Full mechanics, the restated read-view guarantee, and the constraints on
intent transport: `execution_isolation.md` §7.

---

## 5. Invariant Curator — Deprecation Flow

Every invariant is tagged `repo_local` or `enterprise_wide` (`InvariantScope`, `agent_interface_contracts.py`). Each tracks whether the Context Gatherer actually retrieves and uses it — but the zero-hit window is evaluated **within the invariant's own scope**: a `repo_local` invariant's disuse is measured against that one repo; an `enterprise_wide` invariant's disuse is measured across every repo the manifest serves, so a single repo's disinterest doesn't flag a constraint that's firing constantly elsewhere.

Zero-hit invariants are never auto-deleted. They route to a human review queue — the same standard of review their creation implicitly had.

---

## 6. Test Investigator & Failure Triage

Triage runs deterministic-first, LLM-fallback (Principle 10):

1. **Automatic isolated re-run** before any classification happens.
2. **Deterministic triage table.** Every failure is captured as a `FailureSignature` and run through the fixed rules engine in `infra_triage_matrix.md` — separating infra-class failures (timing, DOM state divergence, network) from logic failures, with no agent judgment in the loop.
3. **LLM fallback only on ambiguity.** A signature that doesn't cleanly match any rule falls through to the Test Investigator agent, which queries the Context Gatherer for related test context on demand rather than receiving a standing full-suite injection.
4. **Two-path classification for logic failures** — fails in isolation (timing/logic, routes to Task Dev) vs. passes in isolation but fails in the suite (state leakage).

Baseline capture mechanics for `dom_state_diff_from_baseline`: `test_harness_architecture.md` §1. Full rules engine: `infra_triage_matrix.md`.

---

## 7. Circuit Breakers on Adversarial Loops

Every loop-back edge has an explicit, bounded retry ceiling. A repeated loop signals a problem *upstream* of the current step — a bad plan, a bad decomposition, a bad heuristic — not the current agent's competence at it, so retrying indefinitely wastes budget without addressing the actual cause.

Exact ceilings, the rung-by-rung escalation ladder, and global cost ceilings: `budget_and_escalation_policy.md`.

---

## 8. Execution Isolation

*(Reinstated from v0.1 §6, absent v0.2 through v0.4.)* Disjoint write ownership (Principle 4)
isolates the *writes* within the parallel swarm. It does nothing for the *reads*: the moment one
Task Dev agent runs the suite, the interpreter imports the whole package, including a file another
agent is halfway through rewriting. Verification is repo-scoped even when editing is file-scoped.

Full mechanics — one worktree per task, lifecycle, and when to add containers — live in
`execution_isolation.md`.

---

## 9. Gates

*(Reinstated from v0.1 §4, never relocated into any v0.2–v0.4 companion — the only section from the
original design that simply stopped being carried forward rather than being superseded by
something.)* Every gate in this pipeline returns one of three shapes: a deterministic pass/fail, an
agent `GateResult`, or a human sign-off. Collected here so "what gates this phase" is answerable in
one place instead of reconstructed from scattered phase prose.

### 9.1 Deterministic gates

| Gate | Phase | Blocking | Notes |
|---|---|---|---|
| `ownership.disjoint` | Contract Freeze | Yes | Asserted before the swarm spawns |
| `intent.no_collision` | Parallel Swarm | Yes | Smart Mutex Rejection (§4.5); rejection returns blocking context, not a halt |
| `mutation.diff_scoped` | Verification | Yes | Surviving mutants on changed files only — see `test_harness_architecture.md` §3 |
| `merge.no_conflict` | Integration | Yes | The No-Conflict Gate (Agent Roster, Integrator row); a conflict here is a Boundary Failure (Principle 8), never resolved in place |
| `tests.baseline_delta` | Verification | Yes | Baseline Guard; the anti-deletion check (`agentic_sdlc_glossary.csv`, Baseline Delta) |
| `triage.deterministic` | Verification | Yes (routing only) | `infra_triage_matrix.md`'s rules engine; only non-matches reach the Test Investigator |
| `budget.within_ceiling` | Every transition | Yes | Budget **Enforcer** — deterministic middleware, not the Accountant agent; halts the run, never silently |

### 9.2 Agent gates

| Gate | Phase | Initially | Promotes when |
|---|---|---|---|
| `plan.review` | Planning | Gating | — |
| `security.plan` | Planning | Gating | — |
| `code.review` | Parallel Swarm | **Shadow** | Precision measured against human review over N runs — see `calibration_and_measurement.md` |
| `test.classification` | Verification | Gating | Deletion or skip proposals always require human sign-off regardless |
| `pr.review` | Pull Request | Gating | — |
| `security.diff` | Pull Request | Gating | — |

### 9.3 Human gates

| Gate | Phase | What the human is actually deciding |
|---|---|---|
| Plan approval | Planning | Is this the right change, and is the decomposition sane |
| Contract Freeze | Decomposition & TDD | Are the interface seams and the file ownership map correct |
| Shared-file registration / promotion | Parallel Swarm, Integration | Is this file's structural map correct; should this file join the registry |
| Test deletion sign-off | Verification | Fires only if an agent proposes removing or skipping a test |
| Invariant deprecation | Ongoing | Is a zero-hit invariant actually safe to retire |
| QA → Production promotion | Promotion | Is this safe to ship |
| Structural Change SOP resume | Any (on trigger) | Is the re-mapped architecture correct; are consumers migrated |
| Rollback authorization | Observation | Deterministic rule or human — never the Error Analyzer itself |

---

## 10. Anti-Reward-Hacking Guards

*(Reinstated from v0.1 §7, absent v0.2 through v0.4 as a named framing — most of the individual
guards survived piecemeal; the framing that ties them together as a deliberate threat model did
not.)* The pipeline's stated objective is "tests pass and reviews approve." Both are hackable, and
the cheapest path to green is not always the honest one.

| Attack | Guard |
|---|---|
| Delete or skip a failing test | `tests.baseline_delta` (§9.1) — any reduction in test count, skip count, or coverage is a blocking gate failure, not a review comment |
| Weaken an assertion (`>` quietly becomes `>=`) | `mutation.diff_scoped` (§9.1) — a test that still passes under mutation is theater |
| Write a test the implementation trivially satisfies | Test Author has a disjoint write scope from Task Dev (Principle 12) |
| Mock away the behavior under test | Protocol fakes checked by strict mypy (`test_harness_architecture.md` §2); an `Any`-shaped mock is invisible to the type checker |
| Silence a type error to reach green | CI Cleanup's diff-shape check forbids `cast(Any, ...)`, `# type: ignore`, and bare `except: pass` |
| Reviewer ratifies the builder rather than checking it | Validator asymmetry (Principle 11); Shadow Mode calibration (`calibration_and_measurement.md`) |

Mutation testing is the standout entry: a fast, hermetic unit suite makes `mutmut` affordable, and it
is the only deterministic answer to "did the agent write a real test, or a tautology?"

---

## 11. Measurement and Calibration

*(Reinstated from v0.1 §8, absent v0.2 through v0.4. Verified before reinstating: the only mention of
calibration anywhere in v0.2 through v0.4 is the Shadow Mode glossary entry itself — "until their
accuracy is calibrated against a baseline" — with no baseline, ledger, or threshold defined
anywhere.)* Without this, a Validator agent in Shadow Mode (Agent Roster; §9.2) has no way to leave
shadow, and no way to know whether it's producing signal or ceremony.

Verdict ledger schema, promotion thresholds, and agent-spec versioning: `calibration_and_measurement.md`.

---

## 12. Open Questions for v0.6

- **Enterprise invariant arbitration.** If two repos' Context Gatherers generate opposing signals about whether an `enterprise_wide` invariant still holds, who arbitrates — a designated owner per enterprise invariant, or does every conflict go to the same human review queue as deprecation? *(Carried forward from v0.3 — still unresolved.)*
- **Decay tuning.** The §4.6 decay rule (−1 per clean integration phase, floored at 0) is a reasonable starting point but untested — worth revisiting once there's real promotion data on false-positive/false-negative rates.
- **Structural Change SOP cadence.** Repeated triggering of `structural_change_runbook.md` against the same file or subsystem may itself be a signal worth feeding back into governance — a file that keeps needing structural intervention might need a heavier redesign rather than another round of the SOP.
- **Modular file versioning.** Now that mechanics live in 8 companion files, do they carry
  independent version numbers, or do they always track the core document's version? Matters once one
  companion file needs to change without the others. *(The question grows more pressing this version:
  two companions were just added.)*

**Re-listed, carried forward from v0.1 §10 and dropped without resolution at v0.2 — not previously
tracked in any subsequent Open Questions section:**

- **Task granularity.** What is one task — a file, a module, a vertical slice? Sets swarm width and
  conflict rate; v0.1 called this "the parameter most likely to be wrong on the first attempt."
- ~~**Concurrency ceiling.**~~ *Resolved — see `core_adapter_boundary.md` §3.6.* A repo declares
  its per-isolation-unit resource footprint (policy-bounded, since understating it buys concurrency
  at co-tenants' expense); Core clamps, divides, and takes the minimum against
  `GovernancePolicy.concurrency_cap`, API rate limits, and review throughput. Which constraint binds
  is now explicit per run rather than discovered at runtime, which is exactly what this question
  asked for.
- **Plan Writer dialogue depth.** How much user interaction before a plan counts as "drafted"? Too
  little and the review loop does work the human could have done in one sentence.
- **Run manifest location.** Repo-local (e.g. `.runs/`) or out of tree? In-tree gives free versioning
  and PR-visible provenance but puts run state in the diff. Now directly relevant: §3 and
  `agent_interface_contracts.py`'s `RunManifest` need somewhere to actually live.
- **Secrets posture.** Which agents get which credentials, and does anything in the build phase need
  more than read access to the repo?

*(Resolved in v0.5: validator asymmetry, permissions-not-prompts, execution isolation,
diff-scoped mutation testing, a consolidated gates table, reward-hacking framing, and shadow-mode
calibration — see the Changelog above and `plan/versions/REGRESSION.md`.)*

*(Resolved in v0.4: baseline snapshot mechanism — see `test_harness_architecture.md` §1.)*
