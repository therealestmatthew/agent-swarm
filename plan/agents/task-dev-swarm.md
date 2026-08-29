---
title: Task Dev Swarm
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: shared
---

# Task Dev Swarm

## Type

Maker. The only agent in the roster that runs as N parallel instances.

## Pairing

**Code Reviewer**, per branch, in Shadow Mode during calibration.

## Purpose

Parallel agents, each owning one disjoint slice, implementing against tests that already fail. This
is where the pipeline's throughput comes from, and where every isolation guarantee is actually
tested.

## Inputs

- One task specification and its interface map
- The failing tests for that slice
- A context window scoped to the slice
- A read-only materialized view of governed shared files

## Outputs

- An implementation on the task's own branch
- **Typed additive intents** for any registered shared file — never a direct edit

## Write scope

Its own worktree and its own declared slice. **Registered shared files are not writable**; the agent
emits intents that the Shared-File Intent Service applies.

This is Principle 12's clearest instance in the roster. The swarm agent is not asked to avoid
editing shared files — it cannot. That distinction is the whole design: the external review's demand
that specialists hold "zero write authority" is satisfied here structurally rather than by policy.

## Layer

**Shared.** The pattern — N isolated Makers, disjoint ownership, shared state reached only through
typed intents — is Core and is what the Optimization adapters reuse. The nouns (`src/**` slices, a
git worktree, a language-specific transformer) are adapter-SDLC.

## Loop and escalation

Loops back from the Code Reviewer, `max_retries=3`, **competence-type** — the tier rung applies,
Sonnet → Opus. A failing implementation is usually a reasoning failure, unlike the boundary failures
in `task-decomposer.md` and `integrator.md`.

## Gates

Gated by `code.review` (§9.2, initially Shadow), `tests.diff_covered` and `mutation.diff_scoped`
(§9.1). Its intents are gated by `intent.no_collision`.

## Context budget

Slice-scoped. This agent sees its own task, its tests, its interface map, and the materialized view
of shared files — not other tasks' work in progress. `execution_isolation.md` §7.3: isolated from
*in-progress work*, deliberately **not** isolated from *governed shared state*.

## Failure modes

- **Read coupling despite write isolation.** The known structural limit. Verification is
  repo-scoped even when editing is file-scoped, so a slice can be broken by a peer it never touched.
  One worktree per task addresses the write side; the read side is why merge order is planned.
- **Intent rejection loops.** A rejected intent returns structured `blocking_keys`, never prose.
  `IntentRejection` carries typed fields specifically because free-form text on that path is an
  injection channel between agents.
- **Concurrency ceiling.** How many instances may run is derived, not chosen — declared footprint
  clamped against policy, divided, then minimised against API rate limits and review throughput
  (`core_adapter_boundary.md` §3.6). Which constraint binds is a fact about a run rather than a
  discovery when the machine starts swapping.
