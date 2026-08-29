---
title: Agentic SDLC Orchestration — Design Document v0.2
status: superseded
part_of: agentic-sdlc
doc_type: blueprint
layer: adapter-sdlc
version: "0.2"
superseded_by: plan/versions/agentic-sdlc-design-v0.3.md
---

# Agentic SDLC Orchestration — Design Document v0.2

## Changelog from v0.1

| Area | v0.1 | v0.2 |
|---|---|---|
| Shared files (DI containers, routers, exports) | Integrator merges branches touching shared files via git patch | Task Dev agents emit typed, schema-constrained **intents**; a synchronous service applies them deterministically during the swarm |
| Shared-file insertion points | Undefined | One-time **Shared-File Registration** (agent-proposed, human-confirmed), cached per file |
| Ungoverned shared files | Not addressed | **Self-expanding governance** — repeated git conflicts on a file trigger promotion to the registry |
| Invariant Curator | Append-only | Adds a last-relevant / hit-count signal; zero-hit invariants route to human review, never auto-deleted |
| Test Investigator | Static flake registry, sees only failing test IDs | Automatic isolated re-run before classification; splits flakes into two paths; queries Context Gatherer for related passing-test docstrings on demand |
| Loop-back edges | Unbounded | Explicit `max_retries` ceiling on every loop; repeated failure escalates to a human/decomposition boundary instead of looping indefinitely |

---

## 1. Core Design Principles

1. **Maker/Checker pairing.** Every agent that generates an artifact is paired with an agent that validates it: Plan Writer / Plan Reviewer, Test Author / (implicitly) Test Runner, Task Dev / Code Reviewer, Test Runner / Test Investigator, PR author / PR Reviewer.
2. **Minimal-context orchestration.** The Core Orchestrator's sole job is coordination and routing. It does not hold large context itself; the Context Gatherer assembles targeted context per stage in a separate context window.
3. **TDD-first build.** All implementation work starts from a failing test, authored by a Test Author agent that is structurally separated from the agent that writes implementation code.
4. **Disjoint write ownership.** Within the parallel swarm, each Task Dev agent owns a mutually exclusive set of files (`src/**` scoped per task). This principle now has an explicit carve-out (§4) for the small set of files that are inherently shared.
5. **Human gates at irreversible or judgment-heavy points.** Plan Approval, Contract Freeze, QA→Prod promotion, and (new in v0.2) shared-file registration and invariant deprecation all require human sign-off — the system never silently commits to something that can't be cheaply undone.
6. **Model escalation on repeated failure.** Agents that fail review repeatedly are re-run on a stronger model (e.g., Sonnet → Opus) rather than retried indefinitely on the same model.
7. **Budget and circuit-breaking.** A standing Budget Accountant agent monitors spend across all agent activity and can trigger a "ceiling halt." v0.2 extends this philosophy to individual loop-back edges (§7): unbounded retries are a budget risk as much as a correctness risk.
8. **Merge conflicts are decomposition errors.** A merge conflict is not a routine event to patch around — it is evidence that the Task Decomposer drew task boundaries incorrectly. It is *never* punted to the PR Reviewer, which would corrupt the Verification phase. v0.2 codifies the bounded version of this: repeated conflicts on the same seam escalate as a **boundary failure**, not an infinite retry loop (§7).
9. **Shared state is governed, not merged.** *(New in v0.2.)* Where principle 4 doesn't apply — files that are legitimately shared across tasks — those files are not merged optimistically. They are modified only through a closed vocabulary of typed, additive operations applied by a deterministic service.

---

## 2. Agent Roster

| Agent | Type | Role |
|---|---|---|
| Core Orchestrator | Deterministic | Coordination and routing only; minimal context |
| Context Gatherer | Generator | Assembles targeted context per stage (codebase search/MCP, vector DB / agentic RAG) |
| Plan Writer | Generator | Produces the implementation plan |
| Plan Reviewer | Validator | Adversarial review of the plan; bounded loop back to Plan Writer |
| Security Review (plan-time) | Validator | Reviews plan for security implications before approval |
| Invariant Curator | Utility | Maintains the manifest of static architectural facts/constraints (see §5) |
| Task Decomposer | Generator | Breaks the approved plan into disjoint tasks with interface maps; owns task boundaries |
| Test Author | Generator | Writes failing tests only (`tests/**`); never touches implementation |
| Task Dev Swarm | Generator | Parallel agents, each owning a disjoint `src/**` slice; emits shared-file intents rather than editing shared files directly (see §4) |
| Code Reviewer | Validator (shadow mode) | Reviews each Task Dev branch; bounded loop back; escalates model on repeated failure |
| Shared-File Intent Service | Deterministic + Validator | *(New in v0.2.)* Applies typed additive intents to registered shared files in real time during the swarm; rejects colliding intents with blocking context |
| Integrator | Deterministic | Merges branches; runs the No-Conflict Gate; *(new)* flags ungoverned files with repeated git conflicts for registry promotion |
| Test Runner | Utility | Executes the full suite |
| Baseline Guard | Validator | Checks `baseline_delta`, test counts, coverage — guards against silent test deletion |
| Test Investigator | Validator | Classifies failures (see §6); bounded loop back to Task Dev |
| Flake Registry | Utility | Static registry of known flaky tests, now supplemented by dynamic re-run classification |
| CI Cleanup | Generator | Lint and formatting pass |
| PR Reviewer | Validator | Diff-time review of the draft PR |
| Security Reviewer (diff-time) | Validator | Diff-time security pass |
| Log Monitor | Utility | Always-on observation in production |
| Error Analyzer | Validator | Pattern-matches log findings; triggers rollback initialization on critical findings |
| Budget Accountant | Utility | Monitors spend across all agents; ceiling-halt circuit breaker |

---

## 3. Phase-by-Phase Architecture

### Phase 1 — Planning & Context (Gating)
Context Gatherer pulls targeted context from the codebase and vector DB into a separate context window. Plan Writer produces a plan; Plan Reviewer adversarially reviews it (bounded loop, §7). Security Review runs a plan-time pass. The Invariant Curator injects static architectural facts into the approval step. A human gate approves the plan.

### Phase 2 & 3 — Decomposition & TDD (Verification Green)
The Task Decomposer consumes the approved plan and produces disjoint tasks with interface maps and ownership assignments. A human Contract Freeze gate reviews the interface contracts — *this is also where anticipated shared-file changes should be pre-declared where possible*, reducing how often Phase 4's intent service has to arbitrate a genuinely novel collision. The Test Author then writes failing tests (`tests/**` only) ahead of any implementation.

### Phase 4 — Parallel Swarm & Shared-File Governance
Task Dev agents work disjoint `src/**` slices in parallel. Code Reviewer runs in shadow mode on each branch, escalating to a stronger model after repeated failed reviews (bounded, §7).

**This phase is substantially rewritten in v0.2** — see §4 for the full shared-file governance model. In short: any change a Task Dev agent needs to make to a registered shared file is emitted as a typed intent, not a file edit, and applied synchronously by the Shared-File Intent Service before the agent continues.

### Phase 5 — Integration (Clean Merge)
The Integrator merges completed branches. Because shared-file changes were already resolved in Phase 4, this phase now only has to resolve genuine git-level conflicts on disjoint code — the class of conflict the swarm's ownership model was originally designed to prevent. A conflict here is treated per Principle 8: bounded retries, then escalation to the Decomposer as a boundary failure (§7). The Integrator also runs the *(new)* self-expanding governance check (§4.5).

### Phase 6 — Verification & Cleanup
Test Runner executes the full suite. Baseline Guard checks for anti-deletion regressions. Test Investigator classifies any failures using the upgraded two-path flake model (§6), consulting the Flake Registry and querying the Context Gatherer for related test context on demand. CI Cleanup runs lint/formatting, with a re-review pass.

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

The vocabulary is deliberately **closed and additive-only**. If a task requires a genuine structural change to a shared file (splitting a router, restructuring the DI graph), it does not go through this service — it is decomposed as its own explicit, human-gated task. This keeps the intent vocabulary small enough to reason about and stops it from becoming a general-purpose "edit anything" escape hatch.

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

### 4.6 Self-expanding governance
The governed file set is not fixed at onboarding. During Phase 5, if the Integrator observes repeated git-level conflicts on a file that is *not* currently in the Shared-File Registry, it flags that file for promotion. This mirrors how the Invariant Curator accumulates constraints from intervention — the registry grows from observed friction rather than requiring someone to maintain it by hand.

*(Open question — see §8: what conflict frequency should trigger promotion, and does promotion require a human confirmation step like initial registration does?)*

---

## 5. Invariant Curator — Deprecation Flow

The v0.1 Invariant Curator was append-only: every human-intervention-derived constraint accumulated indefinitely, with no mechanism to retire stale ones. Left unchecked, this pollutes the Context Gatherer's search space with obsolete architecture rules.

**v0.2 adds a last-relevant signal, not an auto-delete mechanism.** Each invariant tracks whether the Context Gatherer actually retrieves and uses it when relevant work touches its domain. Invariants with zero hits over a defined window become *deprecation candidates* — but they are never silently removed. They drop into a human review queue, consistent with the Maker/Checker philosophy that governs every other risk point in the system: these constraints originated from human intervention, so their removal gets the same standard of review their creation implicitly had.

---

## 6. Test Investigator & Flake Handling

Three upgrades to how failures are triaged:

1. **Automatic isolated re-run before classification.** Any failing test is re-run in isolation before the Investigator classifies it. This is cheap and resolves a large fraction of ambiguous cases immediately.
2. **Two-path classification.**
   - *Fails in isolation* → timing or logic bug; routes back to Task Dev (bounded, §7).
   - *Passes in isolation, fails in the full suite* → state leakage / shared-state pollution, a distinct failure class from a code bug in the test's own logic. This distinction matters most as the pipeline extends to Selenium/Playwright-style UI and integration testing, where async rendering and shared browser state are a major source of infrastructure noise that looks like flakiness but isn't.
3. **On-demand context, not full-suite dumping.** Rather than always injecting every passing test's name and docstring, the Test Investigator queries the Context Gatherer for related test context on demand — reusing the retrieval mechanism already built for Phase 1, instead of duplicating a context-stuffing mechanism that would degrade as the suite grows.

---

## 7. Circuit Breakers on Adversarial Loops

Every loop-back edge in the pipeline now has an explicit, bounded retry ceiling rather than an implicit or unbounded one:

| Loop-back edge | Ceiling | On exhaustion |
|---|---|---|
| Plan Writer ↔ Plan Reviewer | `max_retries=3` | Escalate to human plan review |
| Task Dev ↔ Code Reviewer | `max_retries=3` | Escalate to stronger model (existing); if still failing after escalation, halt and route to human |
| Test Runner → Test Investigator → Task Dev | `max_retries=3` | Escalate to human triage |
| Integrator → Merge Conflict → Task Decomposer | `max_retries=3` | **Halt and escalate as a boundary failure** — this is treated as evidence the decomposition heuristic itself is wrong for this task, not that one more retry will fix it |

The underlying principle: a repeated loop is a signal about the *upstream* step (a bad plan, a bad decomposition, a bad heuristic), not about the agent's competence at the current step. Retrying the current step indefinitely wastes budget without addressing the actual cause — which is exactly what the Budget Accountant's ceiling-halt is meant to catch at the system level. These per-edge ceilings apply the same logic locally, before spend becomes the presenting symptom.

---

## 8. Open Questions for v0.3

- **Promotion threshold.** What conflict frequency on an ungoverned file should trigger registry promotion, and does promotion itself need a human confirmation step (matching initial registration) or can it be automatic given the Integrator's evidence is already deterministic?
- **Structural (non-additive) shared-file changes.** These are explicitly routed outside the intent service as their own decomposed, human-gated tasks (§4.2) — but the pipeline doesn't yet define what that task type looks like end to end.
- **Invariant Curator scope.** Is the manifest scoped per-repo, or intended to persist as reusable architecture memory across projects? This materially affects what "zero-hit" and deprecation should mean.
- **UI/integration flake routing.** For Selenium/Playwright-class work, is "route back to Task Dev" still the right destination for infrastructure-class flakes, or do they need a separate environment/infra-fix path distinct from a code-fix path?
