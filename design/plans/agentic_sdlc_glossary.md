---
title: Agentic SDLC Glossary
status: live
part_of: agentic-sdlc
doc_type: reference
layer: shared
---

# Agentic SDLC Glossary

## Additive Intents

**Category:** Shared-File Governance | **Tags:** `shared-file; intent; deterministic; principle-9`

A closed, schema-constrained vocabulary of operations (e.g., AddRoute, AddExport) used by agents to modify shared files deterministically, bypassing the need for git merges on shared configurations.

## Advisory Finding

**Category:** Schema & Contract | **Tags:** `gateresult; finding; severity; loop-control`

A non-blocking `Finding` (`severity="advisory"`). Surfaced to whoever consumes the `GateResult` but never reopens the loop it was raised in and never flips `GateResult.passed` to False — it becomes a backlog item instead.

## Agent Gate

**Category:** Process (Phase & Gate) | **Tags:** `gate; gateresult; shadow-mode; phase-9`

One of the three gate shapes catalogued in design doc §9.2: a Validator agent's `GateResult`, initially Shadow and promoting to Gating per `calibration_and_measurement.md`. Distinct from a Deterministic Gate (no judgment involved) and a Human Gate (no agent involved).

## Agentic SDLC

**Category:** Core Principle | **Tags:** `pipeline; scope`

The overall system this glossary describes: a specified, governed multi-agent pipeline that carries a software change from plan to production, with a maker paired to a checker at every artifact-producing step.

## Anti-Reward-Hacking Guards

**Category:** Test Harness | **Tags:** `reward-hacking; mutation-testing; baseline-delta; validator-asymmetry; principle-11; principle-12`

The design's threat model for its own objective function: "tests pass and reviews approve" is hackable, and the cheapest path to green is not always the honest one. Design doc §10 catalogues each attack (deleting a test, weakening an assertion, mocking away behavior, silencing a type error, a reviewer ratifying the builder) against its specific guard. Reinstated from v0.1 §7, absent v0.2 through v0.4 as a named framing.

## Baseline Delta

**Category:** Test Harness | **Tags:** `baseline; anti-deletion; test-harness; baseline-guard`

The computed difference between a run's test-suite shape (test count, skip count, coverage) and its pre-run `Baseline Snapshot`. What `Baseline Guard` actually checks — distinct from the snapshot itself, which is the reference point, not the comparison.

## Baseline Guard

**Category:** Agent Role | **Tags:** `agent; validator; anti-deletion; test-harness`

The Validator agent that checks `Baseline Delta` — test counts, skip counts, coverage — against the pre-run snapshot, guarding against an agent silently deleting or skipping a test to reach green.

## Baseline Snapshot

**Category:** Test Harness | **Tags:** `baseline; test-harness; state-leakage`

The known-good state of the execution environment (e.g., a completely fresh browser context, cleared local storage, closed DOM modals) captured at t=0 of a test. Used to detect state leakage.

## Blocking Context

**Category:** Shared-File Governance | **Tags:** `shared-file; intent; rejection; smart-mutex`

The specific claim an agent already holds on a shared-file path (its route, export name, or binding interface), returned to a colliding submitter by Smart Mutex Rejection so the collision can be resolved in one shot rather than restarting a planning cycle. Not to be confused with a Blocking Finding — this is rejection metadata, not a review verdict.

## Blocking Finding

**Category:** Schema & Contract | **Tags:** `gateresult; finding; severity; loop-control`

A `Finding` (`severity="blocking"`) that flips `GateResult.passed` to False and reopens the generator/validator loop it was raised in. The only kind of finding that gates anything.

## Boundary Failure

**Category:** Loop & Escalation | **Tags:** `merge-conflict; task-decomposer; escalation; principle-4`

A failure mode indicating that task boundaries were drawn incorrectly. A standard git merge conflict on purportedly disjoint files is treated as a boundary failure, escalating back to the Task Decomposer.

## Budget Accountant

**Category:** Agent Role | **Tags:** `agent; utility; advisory; budget; forecasting`

The standing advisory agent that forecasts token, dollar, and wall-clock spend trend across a run and raises Advisory Findings only. It holds no halt authority: enforcement belongs to the deterministic `Budget Enforcer`, because a circuit breaker that is itself an LLM fails hardest under the runaway conditions it exists to catch.

## Budget Enforcer

**Category:** Budget & Cost | **Tags:** `budget; deterministic; circuit-breaker; principle-10; enforcement`

Deterministic middleware in the Core Orchestrator's dispatch path that checks every phase transition against `GovernancePolicy.budget_ceilings` and refuses the transition on breach, emitting a `Ceiling Halt`. Split from the `Budget Accountant` so that the check which must fire is never left to LLM judgment.

## Ceiling Halt

**Category:** Budget & Cost | **Tags:** `budget; circuit-breaker; principle-7; never-silent`

A hard stop issued by the deterministic `Budget Enforcer` when a run exceeds a `GovernancePolicy` threshold for token usage, dollar cost, or wall-clock time. Never silent, and never auto-resuming.

## Context Isolation

**Category:** Context & Retrieval | **Tags:** `context; orchestrator; principle-2`

The architectural principle of separating the Context Gatherer's retrieval window from the Core Orchestrator and Plan Writer windows to prevent token bloat and context rot.

## Context Rot

**Category:** Context & Retrieval | **Tags:** `context; failure-mode; retrieval`

The degradation of a model's reasoning quality as its context window fills with stale, irrelevant, or merely voluminous material — the failure `Context Isolation` exists to prevent by keeping retrieval in its own window rather than the orchestrator's.

## Contract Freeze

**Category:** Process (Phase & Gate) | **Tags:** `human-gate; interface-map; phase-2; phase-3`

A human-gated review step following task decomposition where interface contracts, and any anticipated shared-file changes, are locked before implementation begins, preventing tasks from diverging from their agreed boundaries mid-build.

## Cumulative Conflict Counter

**Category:** Shared-File Governance | **Tags:** `shared-file; integrator; self-expanding-governance; phase-5`

The lifetime, not per-integration-phase, tally of git-level conflicts recorded against an ungoverned shared file. Crossing a fixed threshold queues the file for human-confirmed promotion into the Shared-File Registry, with the count decaying on clean phases to distinguish chronic friction from an isolated heavy refactor.

## Deterministic Gate

**Category:** Process (Phase & Gate) | **Tags:** `gate; deterministic; phase-9`

One of the three gate shapes catalogued in design doc §9.1: a pass/fail check with no agent judgment in the loop — ownership disjointness, mutation coverage, merge conflicts, baseline delta, budget ceilings. Always blocking; never shadow.

## Deterministic Triage

**Category:** Failure Triage | **Tags:** `failure-triage; deterministic; principle-10`

The practice of classifying execution failures using a fixed rules engine based on structured telemetry (e.g., FailureSignature) before invoking an LLM for judgment.

## Deterministic-First Principle

**Category:** Core Principle | **Tags:** `deterministic; principle-10; failure-triage; shared-file`

The system-wide rule that any event classifiable from structured signals alone, such as a flake signature or a conflict count, is classified by a fixed rules engine; an LLM is invoked only for the ambiguous residue that doesn't cleanly match a rule.

## Diff-Scoped Mutation Testing

**Category:** Test Harness | **Tags:** `test-harness; mutation-testing; tautological-test; gate; phase-9`

Running `mutmut` per task branch, scoped to files the task actually changed, as the `mutation.diff_scoped` deterministic gate. The only guard against a test that calls the real code with the real shape and still passes under a weakened assertion — a different attack from mocking away behavior, which Protocol Fakes guard instead. Reinstated from v0.1 §7 (`mutation.diff_scoped` gate) and §4.1, absent v0.2 through v0.4.

## Disjoint Write Ownership

**Category:** Core Principle | **Tags:** `ownership; task-dev; principle-4; swarm`

A rule enforcing that each parallel Task Dev agent operates within a mutually exclusive set of files (src/**), preventing standard git conflicts by design.

## Environment/Infra Queue

**Category:** Failure Triage | **Tags:** `failure-triage; infra; task-dev; routing`

The remediation path for failures the deterministic triage matrix classifies as infrastructure-related, such as timing, DOM state leakage, or network, rather than code bugs. Kept separate from the standard Task Dev code-fix loop so infra issues aren't fixed with spurious code changes.

## Equivalent Mutant

**Category:** Test Harness | **Tags:** `mutation-testing; human-gate; anti-reward-hacking; loop-control`

A code mutation semantically identical to the original, which no test can kill. Blocking on one is unfixable, so an agent would burn its whole `Loop Ceiling` against a target that does not exist. Recorded in a human-signed registry structured like the `Flake Registry`: an agent may propose an equivalence, never record one.

## Escalation Ladder

**Category:** Loop & Escalation | **Tags:** `escalation; loop-control; model-tier; human-gate`

The defined sequence of responses to repeated agent failure (e.g., 1. Re-gather context, 2. Re-spec task, 3. Escalate model tier, 4. Halt to human).

## Evidence Reference

**Category:** Schema & Contract | **Tags:** `gateresult; finding; schema`

The `evidence_ref` field on a `Finding` — a pointer to where the issue lives (e.g., `"diff:src/foo.py#L42"`, `"log:run_id/line_88"`), so a finding is checkable rather than asserted.

## Execution Isolation

**Category:** Core Principle | **Tags:** `worktree; disjoint-write-ownership; principle-4; task-dev`

One git worktree per task, restoring the property Disjoint Write Ownership alone doesn't provide: isolating what a task's test run *reads*, not just what it writes. Without it, one Task Dev agent's test run imports the whole package, including a file another agent is mid-rewrite on — verification is repo-scoped even when editing is file-scoped. Reinstated from v0.1 §6, absent v0.2 through v0.4; mechanics in `execution_isolation.md`.

## FailureSignature

**Category:** Schema & Contract | **Tags:** `schema; failure-triage; test-harness; isolated-rerun`

The frozen schema capturing a test failure at the moment it happens — error class, elapsed time, configured timeout, isolated-rerun outcome, DOM-state diff from baseline, and network calls over threshold. The input the deterministic triage rules engine runs on; never reconstructed later from logs.

## Finding

**Category:** Schema & Contract | **Tags:** `schema; gateresult; validator`

A single issue raised by a Validator agent: a severity (`blocking` or `advisory`), a message, and an `Evidence Reference`. The atomic unit a `GateResult` is a list of.

## Gate

**Category:** Process (Phase & Gate) | **Tags:** `phase; gateresult; human-gate; deterministic`

A checkpoint a pipeline phase must pass before advancing — deterministic (e.g., `typecheck.strict`), agent-driven (e.g., Plan Reviewer), or human (e.g., Contract Freeze). Every gate that involves judgment returns a `GateResult`.

## Gate Applicability

**Category:** Schema & Contract | **Tags:** `gateresult; scoping; never-silent; principle-7`

The third thing a `GateResult` can say, alongside pass and fail: `applied`, `not_applicable`, or `degraded`. A scoped gate with nothing in scope would otherwise have to report a green check for a check that never ran, or block work it never examined. A non-applied result is never rendered as passing - see `GateResult.is_green`.

## GateResult

**Category:** Schema & Contract | **Tags:** `schema; validator; finding; principle-1`

The standardized return schema for every Validator agent: a pass/fail verdict, a list of findings tagged blocking or advisory, and a reference to the supporting evidence for each.

## Human Gate

**Category:** Process (Phase & Gate) | **Tags:** `human-gate; principle-6; phase`

A checkpoint that requires explicit human sign-off and cannot be delegated to an agent — plan approval, Contract Freeze, shared-file registration/promotion, invariant deprecation, structural changes, and QA→Prod. Reserved for irreversible or judgment-heavy decisions.

## Interface Map

**Category:** Process (Phase & Gate) | **Tags:** `task-decomposer; contract-freeze; ownership; phase-2`

The set of contracts, function signatures, shared types, and ownership boundaries the Task Decomposer produces when splitting a plan into disjoint tasks, forming the basis of the Contract Freeze review.

## Invariant Manifest

**Category:** Invariant Management | **Tags:** `invariant; invariant-curator; context-gatherer`

The living document the Invariant Curator maintains: every stored architectural constraint, each tagged `repo_local` or `enterprise_wide`, that the Context Gatherer consults on every run so agents don't have to re-derive documented architecture from scratch.

## Invariant Scope

**Category:** Invariant Management | **Tags:** `invariant; schema; deprecation`

The repo_local or enterprise_wide classification attached to every stored architectural constraint, used to compute its zero-hit deprecation window correctly across single-repo versus cross-repo usage.

## Isolated Re-run

**Category:** Failure Triage | **Tags:** `failure-triage; failuresignature; test-harness`

The automatic re-execution of a failing test by itself, before any classification happens. Cheap, resolves a large share of ambiguous failures immediately, and produces the `isolated_rerun_outcome` field the deterministic triage table keys on.

## Isolation Unit Derivation

**Category:** Test Harness | **Tags:** `isolation; container; worktree; derived; adapter-invalid`

Core's rule for computing the minimum isolation unit from a repo's declared `Reset Strategy` resource needs: binding a port, needing an unshared path, or reaching an external service each force a container. Derived is a floor - a repo may declare a stronger unit, never a weaker one, and doing so is an invalid contract. Replaces the earlier escape condition that had to be noticed at runtime.

## Loop Ceiling

**Category:** Loop & Escalation | **Tags:** `loop-control; budget; escalation-ladder`

The strict maximum iteration limit (max_retries) placed on adversarial loops (e.g., Plan Writer vs. Plan Reviewer) to prevent infinite, pedantic cycles.

## Maker/Checker Pairing

**Category:** Core Principle | **Tags:** `principle-1; validator; generator`

The foundational pipeline principle where every agent that generates an artifact (Maker) is paired with a distinct agent that validates it (Checker).

## Model Tier

**Category:** Loop & Escalation | **Tags:** `escalation-ladder; model; cost`

The model a given agent step runs on (e.g., Sonnet vs. Opus). Rung 3 of the Escalation Ladder raises the tier for a task that has failed review at the current one — used only after re-gathering context and re-specifying the task have both been tried, so a specification problem isn't mistaken for a capability problem.

## No-Conflict Gate

**Category:** Process (Phase & Gate) | **Tags:** `integrator; boundary-failure; deterministic; phase-5`

The deterministic check the Integrator runs during merge: because shared-file changes were already resolved via Additive Intents in the swarm phase, anything that reaches this gate as a conflict is a genuine git-level collision on disjoint code — a Boundary Failure, not routine merge noise.

## Permissions, Not Prompts

**Category:** Core Principle | **Tags:** `principle-12; disjoint-write-ownership; tdd-first-build; enforcement`

The enforcement doctrine that a write-scope boundary (e.g., Test Author never touching `src/**`) is a permission or config-level constraint, never an instruction an agent is asked to reason its way past — an instruction can be argued with, a permission cannot. Reinstated from v0.1 principle 4's consequence column, absent v0.2 through v0.4 (v0.4 states the outcome without this as its stated mechanism).

## Phase

**Category:** Process (Phase & Gate) | **Tags:** `phase; pipeline-structure`

One of the pipeline's eight top-level stages — Planning & Context, Decomposition & TDD, Parallel Swarm, Integration, Verification & Cleanup, Promotion, and Observation — each with its own gates and agent handoffs.

## Protocol Fake

**Category:** Test Harness | **Tags:** `test-harness; tdd; tautological-test; test-author`

A typed test double implemented against a defined Protocol, or equivalent structural interface, rather than an open, Any-shaped mock, so that a drift between a fake and the real dependency's interface is caught by strict type-checking instead of passing a tautological test.

## Reset Strategy

**Category:** Test Harness | **Tags:** `reset; baseline; adapter; cost; declared`

The adapter-declared mechanism that produces a clean slate for one test, plus what host resources it needs and what it costs. The rule that a fresh instance is constructed rather than an old one cleaned is universal; the mechanism is not - `browser.new_context()` is Playwright's, and Selenium's honest equivalent costs seconds rather than milliseconds. `typical_cost_ms` feeds the wall-clock ceiling and the concurrency derivation.

## Rules Engine

**Category:** Failure Triage | **Tags:** `deterministic; failure-triage; principle-10`

The fixed, ordered decision table a deterministic gate evaluates before any LLM sees the input — the concrete mechanism behind `Deterministic Triage` and the `Deterministic-First Principle`. `infra_triage_matrix.md` is the canonical example: first-matching-rule wins, and only genuine non-matches fall through to agent judgment.

## Run Manifest

**Category:** Schema & Contract | **Tags:** `schema; core-orchestrator; phase; principle-2; resumability`

The Core Orchestrator's entire context across every phase — a `RunManifest` (schema: `design/plans/contracts/orchestration.py`) plus a reference to the event log, never a plan body or a diff. Persisted as a new, immutable instance after every phase transition, so a crashed run resumes from the last recorded phase rather than restarting. Reinstated from v0.1 §3.1, absent v0.2 through v0.4 with no replacement — the Core Orchestrator's state representation was previously unspecified entirely.

## Scope Predicate

**Category:** Test Harness | **Tags:** `mutation-testing; hermetic; diff-scope; gate`

The rule deciding whether `Diff-Scoped Mutation Testing` applies to a given changed line: in scope if covered by a hermetic tier, `not_applicable` if covered only non-hermetically, and caught earlier by `tests.diff_covered` if uncovered entirely. Scoped per line rather than per file, so a task is never blocked by untested code it did not touch.

## Self-Expanding Governance

**Category:** Shared-File Governance | **Tags:** `shared-file; cumulative-conflict-counter; integrator`

The mechanism by which the Shared-File Registry grows over time, as files accumulating repeated git conflicts are flagged for promotion, so the governed file set is driven by observed friction rather than manual maintenance.

## Shadow Mode

**Category:** Agent Role | **Tags:** `validator; calibration; code-reviewer; verdict-ledger`

A deployment state for new Validator agents where they execute against real data and record their verdicts, but cannot gate or block progression until their accuracy is calibrated against a baseline.

## Shared-File Intent Service

**Category:** Agent Role | **Tags:** `agent; shared-file; deterministic; alias`

The deterministic-plus-validator agent that applies typed Additive Intents to registered shared files in real time, rejects colliding intents with `Blocking Context`, and tracks each file's `Cumulative Conflict Counter`. Named `Synchronous Intent Service` in earlier design versions and in the core roster table — see that entry.

## Shared-File Registration

**Category:** Shared-File Governance | **Tags:** `shared-file; human-gate; structural-map`

A one-time, human-gated onboarding step that maps the structural insertion points (AST nodes) of a file so it can safely process Additive Intents.

## Smart Mutex Rejection

**Category:** Shared-File Governance | **Tags:** `shared-file; intent; blocking-context; mutex`

A real-time lock mechanism where an intent collision on a shared file is rejected and routed back to the submitting agent alongside the blocking context (what the opposing agent claimed), allowing for a one-shot fix.

## State Leakage

**Category:** Test Harness | **Tags:** `test-harness; failure-triage; baseline-snapshot`

An infrastructure-class failure where a test fails due to polluted artifacts (e.g., leftover cookies, hung browser sessions from prior custom DOM extractions) rather than flawed test logic.

## Structural Change

**Category:** Shared-File Governance | **Tags:** `shared-file; human-gate; escape-hatch`

A non-additive architectural modification (e.g., splitting a router, breaking a DI graph) that falls outside the intent vocabulary and requires the human-gated Structural Change SOP.

## Structural Map

**Category:** Shared-File Governance | **Tags:** `shared-file; ast; registration; deterministic`

The cached record, produced at Shared-File Registration, of a shared file's insertion points — where the relevant array or object lives, the shape of each entry, the anchor node for a new one. What lets an Additive Intent be applied as a mechanical AST transform with no LLM in the loop.

## Synchronous Intent Service

**Category:** Shared-File Governance | **Tags:** `shared-file; intent; deterministic; alias`

The real-time service that applies typed Additive Intents to registered shared files during the parallel swarm phase, replacing post-hoc merge resolution with immediate, deterministic application or rejection.

## Tautological Test

**Category:** Test Harness | **Tags:** `test-harness; protocol-fake; tdd; mocking`

A test that passes regardless of whether the implementation is correct — most often because an untyped, Any-shaped mock silently accepts calls to methods that don't exist yet or with the wrong signature. What a `Protocol Fake` under strict mypy is built to make impossible.

## TDD-First Build

**Category:** Core Principle | **Tags:** `principle-3; test-author; tdd`

The mandate that all implementation follows a failing test, strictly enforced by utilizing a dedicated Test Author agent that lacks implementation write permissions.

## Validator Asymmetry

**Category:** Core Principle | **Tags:** `principle-1; principle-11; maker-checker-pairing; shadow-mode`

The requirement that a validator's inputs differ from the generator's, in at least one of three ways: information (spec and artifact only, never the generator's own rationale — seeing it turns review into grading a persuasion attempt), tooling (a validator can execute — run tests, run the type checker, grep for callers — not just read), or model (a different tier, at minimum). Without this, Maker/Checker Pairing risks becoming two agents agreeing rather than one checking the other. Reinstated from v0.1 principle 2, absent v0.2 through v0.4.

## Verdict Ledger

**Category:** Calibration & Measurement | **Tags:** `shadow-mode; gateresult; calibration; code-reviewer`

The record, appended to for every `GateResult`, of what happened after a validator's verdict: whether a human overturned it, whether the artifact it passed later failed downstream, and the `reviewer_spec_version` that produced it. This *is* the baseline Shadow Mode's promotion criterion is measured against — without it, "calibrated against a baseline" names a baseline that doesn't exist anywhere in the design. Reinstated from v0.1 §8, absent v0.2 through v0.4; schema and promotion mechanics in `calibration_and_measurement.md`.

## Zero-hit Invariant

**Category:** Invariant Management | **Tags:** `invariant; invariant-curator; deprecation; human-gate`

An architectural constraint stored by the Invariant Curator that has not been retrieved or utilized over a defined window. Flagged as a candidate for human-reviewed deprecation.

