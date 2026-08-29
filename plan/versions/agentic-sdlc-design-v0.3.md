---
title: Agentic SDLC Orchestration — Design Document v0.3
status: superseded
part_of: agentic-sdlc
doc_type: blueprint
layer: adapter-sdlc
version: "0.3"
superseded_by: plan/versions/agentic-sdlc-design-v0.4.md
---

# Agentic SDLC Orchestration — Design Document v0.3

## Changelog from v0.2

| Area | v0.2 | v0.3 |
|---|---|---|
| Governance promotion threshold | Open question | **Resolved:** cumulative `git_conflict_count` per file (lifetime, not per-phase), decay on clean phases, human confirmation gate retained |
| Invariant scope | Open question | **Resolved:** two-value enum (`repo_local` / `enterprise_wide`); zero-hit computed within the invariant's own scope |
| Infrastructure flake routing | Open question | **Resolved:** deterministic triage table lives in `infra_triage_matrix.md`; only ambiguous signatures reach the Test Investigator |
| Structural (non-additive) shared-file changes | Open question | **Resolved:** dedicated SOP in `structural_change_runbook.md` |

All four v0.2 open questions are resolved as of v0.3. New open questions raised by these resolutions are tracked in §8.

---

## 1. Core Design Principles

1. **Maker/Checker pairing.** Every agent that generates an artifact is paired with an agent that validates it: Plan Writer / Plan Reviewer, Test Author / (implicitly) Test Runner, Task Dev / Code Reviewer, Test Runner / Test Investigator, PR author / PR Reviewer.
2. **Minimal-context orchestration.** The Core Orchestrator's sole job is coordination and routing. It does not hold large context itself; the Context Gatherer assembles targeted context per stage in a separate context window.
3. **TDD-first build.** All implementation work starts from a failing test, authored by a Test Author agent that is structurally separated from the agent that writes implementation code.
4. **Disjoint write ownership.** Within the parallel swarm, each Task Dev agent owns a mutually exclusive set of files (`src/**` scoped per task). This principle has an explicit carve-out (§4) for the small set of files that are inherently shared, and an explicit escape hatch (see `structural_change_runbook.md`) for changes too large to be additive.
5. **Human gates at irreversible or judgment-heavy points.** Plan Approval, Contract Freeze, QA→Prod promotion, shared-file registration/promotion, invariant deprecation, and structural architecture changes all require human sign-off — the system never silently commits to something that can't be cheaply undone.
6. **Model escalation on repeated failure.** Agents that fail review repeatedly are re-run on a stronger model (e.g., Sonnet → Opus) rather than retried indefinitely on the same model.
7. **Budget and circuit-breaking.** A standing Budget Accountant agent monitors spend across all agent activity and can trigger a "ceiling halt." This philosophy extends to individual loop-back edges (§7): unbounded retries are a budget risk as much as a correctness risk.
8. **Merge conflicts are decomposition errors.** A merge conflict is not a routine event to patch around — it is evidence that the Task Decomposer drew task boundaries incorrectly. It is *never* punted to the PR Reviewer, which would corrupt the Verification phase. Repeated conflicts on the same seam escalate as a **boundary failure**, not an infinite retry loop (§7).
9. **Shared state is governed, not merged.** Where principle 4 doesn't apply — files that are legitimately shared across tasks — those files are not merged optimistically. They are modified only through a closed vocabulary of typed, additive operations applied by a deterministic service (§4).
10. **Deterministic classification before LLM judgment.** *(New in v0.3.)* Wherever a failure or event can be classified from structured signals alone — a flake signature, a conflict count — it is. An LLM is only invoked for the residue that doesn't cleanly match a deterministic rule. This principle now governs both the Shared-File Intent Service (§4) and flake triage (§6).

---

## 2. Agent Roster

| Agent | Type | Role |
|---|---|---|
| Core Orchestrator | Deterministic | Coordination and routing only; minimal context |
| Context Gatherer | Generator | Assembles targeted context per stage (codebase search/MCP, vector DB / agentic RAG) |
| Plan Writer | Generator | Produces the implementation plan |
| Plan Reviewer | Validator | Adversarial review of the plan; bounded loop back to Plan Writer |
| Security Review (plan-time) | Validator | Reviews plan for security implications before approval |
| Invariant Curator | Utility | Maintains the manifest of static architectural facts/constraints, scoped `repo_local` or `enterprise_wide` (see §5) |
| Task Decomposer | Generator | Breaks the approved plan into disjoint tasks with interface maps; owns task boundaries; owns the Structural Change SOP when triggered |
| Test Author | Generator | Writes failing tests only (`tests/**`); never touches implementation |
| Task Dev Swarm | Generator | Parallel agents, each owning a disjoint `src/**` slice; emits shared-file intents rather than editing shared files directly (see §4) |
| Code Reviewer | Validator (shadow mode) | Reviews each Task Dev branch; bounded loop back; escalates model on repeated failure |
| Shared-File Intent Service | Deterministic + Validator | Applies typed additive intents to registered shared files in real time during the swarm; rejects colliding intents with blocking context; tracks per-file `git_conflict_count` for promotion |
| Integrator | Deterministic | Merges branches; runs the No-Conflict Gate; increments conflict counters on ungoverned files and flags promotion candidates |
| Test Runner | Utility | Executes the full suite |
| Baseline Guard | Validator | Checks `baseline_delta`, test counts, coverage — guards against silent test deletion |
| Test Investigator | Validator | Judgment fallback for failures the deterministic triage table can't classify (see §6); bounded loop back to Task Dev |
| Flake Registry | Utility | Static registry of known flaky tests, supplemented by dynamic re-run classification and the deterministic triage matrix |
| CI Cleanup | Generator | Lint and formatting pass |
| PR Reviewer | Validator | Diff-time review of the draft PR |
| Security Reviewer (diff-time) | Validator | Diff-time security pass |
| Log Monitor | Utility | Always-on observation in production |
| Error Analyzer | Validator | Pattern-matches log findings; triggers rollback initialization on critical findings |
| Budget Accountant | Utility | Monitors spend across all agents; ceiling-halt circuit breaker |

---

## 3. Phase-by-Phase Architecture

### Phase 1 — Planning & Context (Gating)
Context Gatherer pulls targeted context from the codebase and vector DB into a separate context window. Plan Writer produces a plan; Plan Reviewer adversarially reviews it (bounded loop, §7). Security Review runs a plan-time pass. The Invariant Curator injects relevant `repo_local` and `enterprise_wide` architectural facts into the approval step. A human gate approves the plan.

### Phase 2 & 3 — Decomposition & TDD (Verification Green)
The Task Decomposer consumes the approved plan and produces disjoint tasks with interface maps and ownership assignments. A human Contract Freeze gate reviews the interface contracts — this is also where anticipated shared-file changes should be pre-declared where possible, and where a task is flagged for the Structural Change SOP (`structural_change_runbook.md`) if it's non-additive by nature. The Test Author then writes failing tests (`tests/**` only) ahead of any implementation.

### Phase 4 — Parallel Swarm & Shared-File Governance
Task Dev agents work disjoint `src/**` slices in parallel. Code Reviewer runs in shadow mode on each branch, escalating to a stronger model after repeated failed reviews (bounded, §7). Any change a Task Dev agent needs to make to a registered shared file is emitted as a typed intent, not a file edit, and applied synchronously by the Shared-File Intent Service before the agent continues (§4). If a task turns out to require a structural, non-additive shared-file change, it exits the swarm via the Structural Change SOP rather than attempting an intent it can't express.

### Phase 5 — Integration (Clean Merge)
The Integrator merges completed branches. Because shared-file changes were already resolved in Phase 4, this phase only has to resolve genuine git-level conflicts on disjoint code. A conflict here is treated per Principle 8: bounded retries, then escalation to the Decomposer as a boundary failure (§7). The Integrator also increments the lifetime `git_conflict_count` for any ungoverned file involved and runs the promotion check (§4.6).

### Phase 6 — Verification & Cleanup
Test Runner executes the full suite. Baseline Guard checks for anti-deletion regressions. Failures are classified via the deterministic triage table (`infra_triage_matrix.md`) first; only signatures that don't cleanly match a rule reach the Test Investigator for judgment (§6). CI Cleanup runs lint/formatting, with a re-review pass.

### Phase 7 & 8 — Promotion & Observation
Draft PR is generated; PR Reviewer and a diff-time Security Reviewer evaluate it. Approved PRs merge automatically from Dev to QA; QA to Production requires a human approval gate. In production, the Log Monitor watches continuously; the Error Analyzer pattern-matches performance regressions and error spikes, initiating rollback authorization on critical findings.

---

## 4. The Synchronous Intent Service (Shared-File Governance)

### 4.1 Problem
A small set of files — DI containers, routers, export barrels — are inherently shared across tasks that are otherwise disjoint. Treating them as ordinary merge targets recreates exactly the failure mode the swarm's ownership model exists to avoid: two agents can produce textually non-overlapping, git-clean changes that are still semantically incompatible (e.g., conflicting middleware ordering, duplicate export names).

### 4.2 Typed, additive intents
Task Dev agents never edit a registered shared file directly. Instead they emit one or more typed intents, modeled the same way as the rest of the system's spec models — Pydantic v2, `extra="forbid"`, `frozen=True`:

```python
class AddExport(BaseModel, frozen=True):
    model_config = ConfigDict(extra="forbid")
    name: str
    source_module: str

class AddRoute(BaseModel, frozen=True):
    model_config = ConfigDict(extra="forbid")
    path: str
    handler: str
    middleware: list[str] = []

class AddProviderBinding(BaseModel, frozen=True):
    model_config = ConfigDict(extra="forbid")
    interface: str
    implementation: str
    scope: Literal["singleton", "transient", "scoped"]
```

The vocabulary is deliberately **closed and additive-only**. If a task requires a genuine structural change to a shared file (splitting a router, restructuring the DI graph), it does not go through this service — it exits via the Structural Change SOP (`structural_change_runbook.md`). This keeps the intent vocabulary small enough to reason about and stops it from becoming a general-purpose "edit anything" escape hatch.

### 4.3 Shared-File Registration
Before a file can accept intents, it goes through a one-time registration step, following the same Maker/Checker pattern used elsewhere:

1. An agent proposes the file's structural map — where the relevant array/dict lives, the shape of each entry, and the anchor node for insertion.
2. A human confirms the proposal once.
3. The confirmed map is cached and reused for all future intents against that file.

This is intentionally *not* the Task Decomposer's job at plan time (it's a file-structure concern, not a planning concern) and *not* left for agents to re-derive dynamically on every task (that reintroduces the exact ambiguity the typed vocabulary is meant to remove).

### 4.4 Deterministic application, per language
Applying an intent to a registered file is a mechanical AST transform wherever possible — no LLM in the loop for the non-conflicting case:

- **Python** targets: `libcst`, which preserves comments and formatting while safely inserting into the mapped structure.
- **TypeScript/JS** targets: `ts-morph` or Babel, performing the equivalent structural insertion (import + array/object entry) without destabilizing the surrounding file.

The intent vocabulary stays language-agnostic at the agent level; the service routes each intent to the correct transformer based on the target file's extension and its registered structural map.

### 4.5 Smart Mutex Rejection
When an intent is submitted, the service applies a mutex on the semantic path it touches (e.g., the route path, the export name, the binding interface):

- **No collision:** applied deterministically, immediately, synchronously — the submitting agent gets confirmation before it builds further downstream logic on top of the change.
- **Collision:** rejected back to the submitting agent *with the blocking context* — what the other agent already claimed (path, signature, scope) — so it can resolve in one shot rather than restarting a planning cycle.

Running this synchronously during Phase 4, rather than deferred to Phase 5 integration, catches incompatibilities at the cheapest possible point: before agents build more code assuming their version of the shared file won.

### 4.6 Self-expanding governance *(resolved in v0.3)*
The governed file set is not fixed at onboarding. Promotion is driven by a **cumulative, lifetime conflict counter per file**, not a per-phase count:

- Every git-level conflict the Integrator resolves on an ungoverned file increments that file's `git_conflict_count` by 1. The counter persists across integration runs — it is a property of the file, not of any single Phase 5 pass.
- **Promotion trigger:** `git_conflict_count > 2` (i.e., on the third lifetime conflict) queues the file for registry promotion.
- **Decay:** the counter decrements by 1 for every integration phase the file goes through with zero conflicts, floored at 0. This distinguishes chronic friction (repeated conflicts spread across time) from an isolated rough patch (e.g., one unusually large refactor that happens to touch the file three times in a single phase) — a heavy single-phase refactor decays back down over subsequent clean phases rather than permanently flagging the file, while a file with recurring conflicts every few phases never fully decays and eventually crosses the threshold.
- **Promotion still requires human confirmation**, identical to initial registration (§4.3) — the counter is evidence for a proposal, not an automatic action. This keeps promotion inside the Maker/Checker philosophy (Principle 1) even though the *evidence-gathering* is fully deterministic.

---

## 5. Invariant Curator — Deprecation Flow

The original Invariant Curator was append-only: every human-intervention-derived constraint accumulated indefinitely, with no mechanism to retire stale ones. Left unchecked, this pollutes the Context Gatherer's search space with obsolete architecture rules.

**Scope enum *(new in v0.3)*.** Every invariant is tagged with a scope:

```python
class InvariantScope(str, Enum):
    REPO_LOCAL = "repo_local"        # e.g., "this service's routing must go through middleware X"
    ENTERPRISE_WIDE = "enterprise_wide"  # e.g., overarching data governance / compliance rules
```

**Last-relevant signal, scoped correctly.** Each invariant tracks whether the Context Gatherer actually retrieves and uses it when relevant work touches its domain. Critically, the hit-count is evaluated **within the invariant's own scope**:

- A `repo_local` invariant's zero-hit window is measured against usage in that one repo — as before.
- An `enterprise_wide` invariant's zero-hit window is measured against usage **across every repo the manifest serves**, not any single one. A repo that hasn't touched a particular enterprise constraint recently does not, by itself, make that constraint a deprecation candidate — it may be firing constantly in three other repos.

This is the fix for the failure mode Gemini flagged: without scope-aware hit tracking, cross-project architectural memory could be erroneously flagged as stale simply because one repository's Context Gatherer hadn't needed it lately.

**Deprecation still routes to human review, never auto-deletes**, consistent with the Maker/Checker philosophy that governs every other risk point in the system: these constraints originated from human intervention, so their removal gets the same standard of review their creation implicitly had.

---

## 6. Test Investigator & Flake Handling

Failure triage now runs deterministic-first, LLM-fallback *(new in v0.3)*:

1. **Automatic isolated re-run before classification.** Any failing test is re-run in isolation before any classification happens. This is cheap and resolves a large fraction of ambiguous cases immediately.
2. **Deterministic triage table.** Every failure is captured as a structured `FailureSignature` (schema and full rules engine defined in `infra_triage_matrix.md`) and run through a fixed decision table *before* any LLM sees it. The table separates infra-class failures (timing proximity to a configured timeout, DOM state divergence at test start, elevated network calls) from genuine logic failures, and routes each to the appropriate queue without agent judgment in the loop.
3. **LLM fallback only on ambiguity.** A signature that doesn't cleanly match any rule in the table — e.g., an assertion failure co-occurring with elevated network latency — is *not* forced into the nearest bucket. It falls through to the Test Investigator agent for judgment. This mirrors the same "deterministic first, escalate only on genuine ambiguity" shape used by the Shared-File Intent Service (§4.4) and is now stated as a general system principle (Principle 10).
4. **Two-path classification for logic failures.**
   - *Fails in isolation* → timing or logic bug; routes back to Task Dev (bounded, §7).
   - *Passes in isolation, fails in the full suite* → state leakage / shared-state pollution; this remains distinct even after the infra-matrix split, since state leakage can be a genuine code bug (a test not cleaning up after itself) rather than infrastructure noise.
5. **On-demand context, not full-suite dumping.** When the Test Investigator is invoked, it queries the Context Gatherer for related test context on demand — reusing the retrieval mechanism already built for Phase 1, instead of duplicating a context-stuffing mechanism that would degrade as the suite grows.

Full schema and rules engine: see `infra_triage_matrix.md`.

---

## 7. Circuit Breakers on Adversarial Loops

Every loop-back edge in the pipeline has an explicit, bounded retry ceiling rather than an implicit or unbounded one:

| Loop-back edge | Ceiling | On exhaustion |
|---|---|---|
| Plan Writer ↔ Plan Reviewer | `max_retries=3` | Escalate to human plan review |
| Task Dev ↔ Code Reviewer | `max_retries=3` | Escalate to stronger model (existing); if still failing after escalation, halt and route to human |
| Test Runner → Test Investigator → Task Dev | `max_retries=3` | Escalate to human triage |
| Integrator → Merge Conflict → Task Decomposer | `max_retries=3` | **Halt and escalate as a boundary failure** — evidence the decomposition heuristic itself is wrong for this task, not that one more retry will fix it |

The underlying principle: a repeated loop is a signal about the *upstream* step (a bad plan, a bad decomposition, a bad heuristic), not about the agent's competence at the current step. Retrying the current step indefinitely wastes budget without addressing the actual cause — which is exactly what the Budget Accountant's ceiling-halt is meant to catch at the system level. These per-edge ceilings apply the same logic locally, before spend becomes the presenting symptom.

---

## 8. Open Questions for v0.4

- **Baseline snapshot mechanism.** `infra_triage_matrix.md`'s `dom_state_diff_from_baseline` field needs a defined capture point and comparison method (what counts as "baseline" — clean browser profile at suite start? per-test setup state?).
- **Decay tuning.** The §4.6 decay rule (−1 per clean integration phase, floored at 0) is a reasonable starting point but untested — worth revisiting once there's real promotion data on false-positive/false-negative rates.
- **Enterprise invariant conflicts.** If two repos' Context Gatherers produce conflicting signals about whether an `enterprise_wide` invariant still holds, who arbitrates — is there a designated owner per enterprise invariant, or does every conflict go to the same human review queue as deprecation?
- **Structural Change SOP cadence.** Now that non-additive changes have a defined exit path (`structural_change_runbook.md`), does repeated triggering of that SOP for the same file/subsystem feed back into anything (e.g., a signal that the file needs architectural rework, not just repeated one-off SOP runs)?
