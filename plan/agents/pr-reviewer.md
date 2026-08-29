---
title: PR Reviewer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# PR Reviewer

## Type

Checker.

## Pairing

Reviews the merged diff — the synthesized product of every Task Dev agent's work, which no single
Maker authored.

## Purpose

Diff-time review of the draft PR, seeing the whole change as one artifact for the first time. Per-branch
review cannot catch a defect that only exists in the combination; this is where that class of
problem is visible.

## Inputs

- The full merged diff
- The **synthesized per-intent delta view** for governed shared files (`execution_isolation.md`
  §7.4) — without it, shared-file changes would appear as unattributable rewrites
- The original plan and the invariant manifest

## Outputs

- `GateResult` with `Finding` list

## Write scope

None. Explicitly, **this agent does not resolve merge conflicts** — Principle 8 makes a conflict a
decomposition error routed back to the Task Decomposer, never something patched here.

## Layer

**Adapter-SDLC.** It reviews a diff. The Core pattern — a final Checker over the assembled artifact,
distinct from the per-unit Checkers — is reusable, and Team Optimization's Quality Reviewer occupies
the same position.

## Loop and escalation

`max_retries=3`, competence-type.

## Gates

Produces `pr.review` (§9.2).

## Calibration posture

Gating. Its precision signal is weaker than the Code Reviewer's, because far fewer PRs than branches
flow through it — the ledger fills slowly, so promotion evidence accrues over more calendar time.

## Context budget

The full diff plus the plan. The largest single artifact any Checker handles, and the most likely to
hit overflow — where the Context Gatherer's summarize-never-drop rule matters most.

## Failure modes

- **Rubber-stamping the aggregate.** Every constituent branch passed review, which makes a clean
  verdict here the path of least resistance. The defects this agent uniquely can catch are exactly
  the ones no branch review saw.
- **Shared-file changes as noise.** Mitigated by the synthesized delta view; without it, governed
  changes read as a rewrite with no author.
