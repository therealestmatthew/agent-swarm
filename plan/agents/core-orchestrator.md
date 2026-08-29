---
title: Core Orchestrator
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Core Orchestrator

## Type

Orchestrator.

## Pairing

None — not a Maker/Checker pair. The Core Orchestrator produces no reviewable artifact. Its
decisions are constrained by deterministic gates and the Budget Enforcer sitting in its own dispatch
path, not by a Checker reviewing its judgment.

## Purpose

Routes work between phases and dispatches agents. It exists to hold the pipeline's flow control in
one deterministic place, so that no agent decides what happens after itself. The failure it prevents
is the one every unbounded multi-agent system hits: agents negotiating their own next steps until
nobody can say why the run is still going.

## Inputs

- `RunManifest` (`contracts/orchestration.py`) — the entire per-run state
- `event_log_ref` — a reference, not the log's contents
- `GateResult` verdicts from Checkers (`contracts/verification.py`)
- `RepoDeclaration` and `GovernancePolicy`, digest-pinned at run start

**Never** a plan body, a diff, a transcript, or any artifact's content.

## Outputs

- The next `Phase`, or a `HaltReason`
- Dispatch instructions to agents
- `RunManifest` updates, including `policy_adjustments` when Core clamps a declared value

## Write scope

`RunManifest` and the event log. Nothing else — no worktree, no shared branch, no artifact.

## Layer

**Core.** It would be wrong in the same way for every task domain: a router that reads artifact
content accumulates context rot and couples itself to one domain's nouns simultaneously.

Adapter-supplied nouns: the phase *sequence* is currently Core, and this is the type's weakest
point. `Phase.DECOMPOSITION_TDD` bakes one methodology into the universal enum
(`core_vs_adapter.md` §6). A domain without a TDD step has no correct value to route through.

## Gates

Evaluates every deterministic gate in §9.1 as a routing precondition, and consumes agent gate
verdicts from §9.2. Refuses to start on `ADAPTER_INVALID`, `ADAPTER_DIGEST_MISMATCH`, or
`ADAPTER_POLICY_CONFLICT`.

## Failure modes

- **Digest mismatch mid-run.** Both declaration and policy are digest-pinned into the `RunManifest`
  at run start; Core halts on a mismatch rather than adopting the new value. A declaration that
  changes under a live run is either a race or an attack, and neither should be resolved by
  proceeding.
- **Resume after crash.** Governed by `crash_recovery.md`. The binding rule is the no-recompute
  posture: `RunManifest.diff_classification` is preserved on resume and never re-derived, because
  the diff may have been mutated between crash and restart.
- **Ceiling halt.** Never auto-resumes. A halt that resumes itself is not a ceiling.
