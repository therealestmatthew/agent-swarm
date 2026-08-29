---
title: Shared-File Intent Service
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Shared-File Intent Service

## Type

Executor. The roster types it "Deterministic + Validator" because it rejects colliding intents, but
rejection here is a computed predicate over declared collision keys, not a judgment about an
artifact — so Executor is correct (`types/executor.md`).

## Pairing

None — not a Maker/Checker pair. It applies typed operations deterministically; there is no
judgment for a Checker to review.

## Purpose

Applies typed additive intents to registered shared files in real time, as the **sole writer** of
the canonical shared branch. It is the mechanism behind Principle 9 — *shared state is governed, not
merged* — and it exists because concurrent edits to shared files are the single most reliable way to
turn a parallel swarm into a merge-conflict generator.

## Inputs

- Typed additive intents from Task Dev agents, normalized before they arrive
  (`llm_output_normalization.md` §3)
- The registered shared-file list (a `GovernancePolicy` field — a repo registering its own shared
  files would be grading itself)
- The declared intent vocabulary, `IntentOpSpec` with `collision_keys`
  (`contracts/adapter_surface.py`)

## Outputs

- `IntentOutcome` — applied, with anchor and content digest
- `IntentRejection` — with `reason`, `blocking_task_id`, `blocking_op`, and structured
  `blocking_keys`
- Per-file cumulative conflict counters, feeding promotion decisions

## Write scope

**The canonical `shared/` branch, exclusively.** No other agent writes to it — not the Integrator,
not any Task Dev agent. This sole-writer property is the guarantee the shared-file design rests on;
`execution_isolation.md` §7.5 makes it explicit that transport must be one shared service and not
one instance per agent, because N writers and no mutex is the failure being designed out.

## Layer

**Core.** The lock, the serialization, and the rejection protocol are universal. Any domain with
concurrent writers against governed shared state needs exactly this.

Adapter-supplied nouns: the intent vocabulary and its collision keys. `core_adapter_boundary.md`
§2.1 is explicit that *whether two intents collide* is not universal — it is a semantic question
about a vocabulary Core has never seen. Resolved by `IntentOpSpec.collision_keys`, exact match only,
deliberately under-powered. **Core does not accept an adapter-supplied predicate function**, because
that would move arbitration logic into untrusted repo-declared code.

In Team Optimization the same service applies `AddAction` / `AddDecision` / `AddRisk` against
project registers, keyed on `(register, record_id, field)`.

## Gates

Produces `intent.no_collision` (§9.1).

## Failure modes

- **Prose in a rejection.** The rejection payload is typed — `blocking_keys` is a
  `dict[str, str]`, not a message. Free-form text on this path would be an injection channel between
  agents, since one agent's output becomes another's input with no human in between.
- **Non-additive change arriving as additive.** The vocabulary deliberately has no `RemoveExport` or
  `RenameRoute`. Anything non-additive exits through the Structural Change SOP. The residual risk is
  N additive operations amounting to a structural change one intent at a time — the threshold that
  should catch this is explicitly illustrative, not decided.
- **Materialization races.** Registered shared files are re-materialized into live worktrees via
  `skip-worktree` plus atomic rename. Audited as C4 in the 2026-08-28 audit.
- **Counter decay is untuned.** The −1-per-clean-phase decay on conflict counters, which drives
  promotion, has never been tested against real data (§12).
