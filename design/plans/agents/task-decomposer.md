---
title: Task Decomposer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Task Decomposer

## Type

Maker.

## Pairing

Reviewed structurally at the Contract Freeze human gate rather than by a dedicated Checker agent.
**This is the roster's weakest Maker/Checker pairing** and the card says so rather than implying
otherwise: `ownership.disjoint` (§9.1) checks that the slices do not overlap, but nothing
independently reviews whether the boundaries were drawn *well*. A non-overlapping decomposition can
still be a bad one, and the design's own Principle 8 says the evidence arrives late — as a merge
conflict, phases later.

## Purpose

Breaks the approved plan into disjoint tasks with interface maps, and owns the Structural Change SOP
when a change turns out to be non-additive. This is the highest-leverage agent in the pipeline:
Principle 8 holds that *merge conflicts are decomposition errors*, which makes every conflict
downstream a verdict on this agent's output.

## Inputs

- The approved plan
- The current structural map of the target
- The registered shared-file list
- The invariant manifest

## Outputs

- A task set with disjoint write ownership
- An interface map per task
- A planned merge order (`execution_isolation.md` §6 — merge order is planned, not emergent)
- A Structural Change SOP trigger, where the change cannot be expressed additively

## Write scope

None on the target. Emits a task set; the Orchestrator dispatches it.

## Layer

**Core.** "Split work into non-overlapping units whose boundaries hold under parallel execution" is
the general problem, and every domain that parallelises knowledge work has it.

Adapter-supplied nouns: what a unit of ownership *is*. In SDLC it is a path glob over `src/**`. In
Team Optimization it is an enumerated set of record IDs leased for the task
(`optimization/project_state_model.md`). The derivation is Core; the noun is not.

## Loop and escalation

Loops back on a failed `ownership.disjoint` check, `max_retries=3`.

**Boundary-type — the model-tier rung is skipped.** This is the type case for
`budget_and_escalation_policy.md` §2.2: overlapping slices are evidence the task was scoped wrong,
not evidence the current model reasoned poorly. Escalating tier spends budget without touching the
cause. Getting this field wrong here would produce exactly the runaway the ceilings exist to stop.

On exhaustion: halt to human. Repeated failure means the plan is not decomposable as written, which
is a fact about the plan and not about the decomposer.

## Gates

Gated by `ownership.disjoint` (§9.1) and the **Contract Freeze** human gate (§9.3). Triggers the
Structural Change SOP, whose resume is itself a human gate.

## Context budget

Plan, structural map, shared-file registry, invariants. Structural information is hard-included —
a decomposition made without the current structural map is a guess.

## Failure modes

- **Disjoint on paper, coupled in practice.** The design's sharpest known limit:
  `execution_isolation.md` §1 — *"verification is repo-scoped even when editing is file-scoped."*
  Two tasks can own non-overlapping slices and still break each other's verification. Disjoint write
  ownership does not imply independence, and `ownership.disjoint` cannot see the difference.
- **Additive-looking structural change.** N additive operations against one artifact may be a
  structural change happening one intent at a time. The threshold that should trigger the SOP is
  explicitly illustrative, not decided (`structural_change_runbook.md` §4).
- **Granularity undefined.** How large a task should be is an open question carried since v0.1, and
  it interacts with the additive-intent threshold — roadmap D13 notes the two will be resolved
  "together or not at all."
