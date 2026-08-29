---
title: Integrator
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# Integrator

## Type

Executor.

## Pairing

None — not a Maker/Checker pair. A deterministic merge produces no judgment to review.

## Purpose

Merges task branches in the planned order, runs the No-Conflict Gate, and increments conflict
counters on ungoverned files. It is the agent that discovers whether the Task Decomposer was right.

## Inputs

- Task branches, in the merge order planned at decomposition (`execution_isolation.md` §6 — merge
  order is planned, not emergent)
- The registered shared-file list

## Outputs

- A merged branch, or a conflict
- Conflict counter increments, feeding shared-file registration decisions

## Write scope

The integration branch. **Not** the canonical `shared/` branch — that has exactly one writer, the
Shared-File Intent Service.

## Layer

**Adapter-SDLC.** Git merge mechanics, fast-forward semantics, and conflict markers are one
domain's answer. The Core idea it instantiates — combining parallel work and detecting collisions
under a planned order — is stated in Principle 8 and reused by the Optimization adapters with a
different mechanism entirely.

## Loop and escalation

**Boundary-type — the model-tier rung is skipped, and this is the canonical example.**
`budget_and_escalation_policy.md` §2.2: a merge conflict *"is evidence of a decomposition error, not
evidence the current model reasoned poorly — escalating model tier wouldn't address the actual
cause."*

On conflict, the run does not retry the merge with a better model. It routes back to decomposition.
Principle 8 states the rule flatly: a conflict is never something the PR Reviewer resolves, and
never an infinite retry.

## Gates

Produces `merge.no_conflict` (§9.1).

## Failure modes

- **Conflict on supposedly disjoint work.** The expected failure, and diagnostic rather than
  exceptional — it means the decomposition drew a boundary wrong, or that read coupling
  (`execution_isolation.md` §1) defeated write isolation.
- **Ungoverned file accumulating conflicts.** Handled by the cumulative counter, which is the signal
  for promoting a file into the registered shared set. Decay tuning on that counter is untested
  (§12).
- **Silent semantic conflict.** Two branches that merge cleanly and are jointly wrong. Text-level
  merging cannot see this; it is the verification phase's problem, not this agent's.
