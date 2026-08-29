---
title: Agentic SDLC Orchestration — Design Document v0.4
status: superseded
part_of: agentic-sdlc
doc_type: blueprint
layer: adapter-sdlc
version: "0.4"
superseded_by: plan/agentic-sdlc-design-v0.5.md
---

# Agentic SDLC Orchestration — Design Document v0.4

## Changelog from v0.3

v0.3 resolved all four open questions from v0.2, but in doing so grew heavy with implementation-level detail — exact schemas, exact thresholds, exact capture rules — sitting inside what should be an orchestration blueprint. v0.4 doesn't change any of that content; it **relocates** it into four modular reference files, so this document stays legible as "how the pipeline is shaped" rather than "every mechanism at every layer."

| Moved from v0.3 §... | To |
|---|---|
| §4.2 Pydantic intent models, §5 scope enum, `infra_triage_matrix.md`'s `FailureSignature`, new `GateResult` | `agent_interface_contracts.py` |
| Baseline capture mechanics, test double standards | `test_harness_architecture.md` |
| Context Gatherer search heuristics, token budgets | `context_retrieval_strategy.md` |
| §7 exact `max_retries` table, escalation ladder detail, cost ceilings | `budget_and_escalation_policy.md` |

Nothing here was demoted for being unimportant — it was extracted because a reader trying to understand *the shape of the pipeline* shouldn't have to wade through a Pydantic class definition to find it.

---

## Modular Reference Files

| File | Owns |
|---|---|
| `agent_interface_contracts.py` | Every schema in the system — additive intents, `InvariantScope`, `FailureSignature`, `GateResult` — single source of truth |
| `test_harness_architecture.md` | Baseline capture mechanics for `dom_state_diff_from_baseline`; Protocol-fake test double standards |
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
7. **Budget and circuit-breaking.** A standing Budget Accountant agent monitors spend across all agent activity and can trigger a ceiling halt; the same philosophy governs individual loop-back edges (exact thresholds: `budget_and_escalation_policy.md`).
8. **Merge conflicts are decomposition errors.** A merge conflict is evidence the Task Decomposer drew task boundaries incorrectly — never punted to the PR Reviewer. Repeated conflicts on the same seam escalate as a boundary failure, not an infinite retry loop.
9. **Shared state is governed, not merged.** Files that are legitimately shared across tasks are modified only through a closed vocabulary of typed, additive operations applied by a deterministic service (§4; schemas in `agent_interface_contracts.py`).
10. **Deterministic classification before LLM judgment.** Wherever a failure or event can be classified from structured signals alone, it is. An LLM is only invoked for the residue that doesn't cleanly match a deterministic rule. Governs both the Shared-File Intent Service (§4) and failure triage (§6, `infra_triage_matrix.md`).

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
| Budget Accountant | Utility | Monitors spend across all agents; ceiling-halt circuit breaker (`budget_and_escalation_policy.md`) |

Every Validator agent returns a `GateResult` (`agent_interface_contracts.py`) — a standardized pass/fail verdict with blocking vs. advisory findings and an evidence reference, so the Core Orchestrator can route on a consistent shape regardless of which Validator produced it.

---

## 3. Phase-by-Phase Architecture

### Phase 1 — Planning & Context (Gating)
Context Gatherer pulls targeted context into a separate context window (`context_retrieval_strategy.md`). Plan Writer produces a plan; Plan Reviewer adversarially reviews it (bounded loop, §7). Security Review runs a plan-time pass. The Invariant Curator injects relevant constraints into the approval step. A human gate approves the plan.

### Phase 2 & 3 — Decomposition & TDD (Verification Green)
The Task Decomposer produces disjoint tasks with interface maps and ownership assignments. A human Contract Freeze gate reviews the interface contracts — including any Protocol definitions for shared dependencies (`test_harness_architecture.md` §2.3) and any anticipated shared-file changes — and flags tasks that need the Structural Change SOP instead of the standard swarm flow. The Test Author then writes failing tests (`tests/**` only) ahead of any implementation.

### Phase 4 — Parallel Swarm & Shared-File Governance
Task Dev agents work disjoint `src/**` slices in parallel. Code Reviewer runs in shadow mode on each branch, escalating to a stronger model after repeated failed reviews (bounded, §7). Any change to a registered shared file is emitted as a typed intent (§4), applied synchronously before the agent continues. A task that turns out to need a structural, non-additive change exits the swarm via `structural_change_runbook.md`.

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

## 8. Open Questions for v0.5

- **Enterprise invariant arbitration.** If two repos' Context Gatherers generate opposing signals about whether an `enterprise_wide` invariant still holds, who arbitrates — a designated owner per enterprise invariant, or does every conflict go to the same human review queue as deprecation? *(Carried forward from v0.3 — still unresolved.)*
- **Decay tuning.** The §4.6 decay rule (−1 per clean integration phase, floored at 0) is a reasonable starting point but untested — worth revisiting once there's real promotion data on false-positive/false-negative rates.
- **Structural Change SOP cadence.** Repeated triggering of `structural_change_runbook.md` against the same file or subsystem may itself be a signal worth feeding back into governance — a file that keeps needing structural intervention might need a heavier redesign rather than another round of the SOP.
- **Modular file versioning.** Now that mechanics live in five companion files, do they carry independent version numbers, or do they always track the core document's version? Matters once one companion file needs to change without the others.

*(Resolved in v0.4: baseline snapshot mechanism — see `test_harness_architecture.md` §1.)*
