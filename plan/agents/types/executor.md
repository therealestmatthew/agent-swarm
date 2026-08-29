---
title: Executor (Agent Type)
status: live
part_of: agentic-sdlc
doc_type: agent-type
layer: core
---

# Executor (Agent Type)

**Cards of this type:** `integrator.md` · `test-runner.md` · `shared-file-intent-service.md` ·
`log-monitor.md` · `budget-accountant.md`

## Definition

> Performs deterministic, non-LLM operations on artifacts or infrastructure. Does not make judgment
> calls. Output is a state change — a merged branch, an applied intent, a test result, a structured
> telemetry event — rather than a finding or artifact.
>
> — `agent_taxonomy.md` §1.6

## Where the system's actual authority lives

Executors are the only agents that change anything real. Every Maker in the roster proposes; an
Executor applies. That inversion is Principle 12 made concrete — *enforce with permissions, not
prompts* — and it is why "the agents cannot write to source of truth" is a structural fact here
rather than a policy someone has to remember.

The consequence for cards: an Executor's **write scope is the tightest and most load-bearing field
on the card**, because it is the real boundary. The Shared-File Intent Service is the sole writer of
the canonical shared branch; that sentence is the guarantee the whole shared-file design rests on.

## Field discipline

| Section | Required? | Notes |
|---|---|---|
| Type | **Required** | |
| Pairing | **Required** | Always `None — not a Maker/Checker pair`, with the reason |
| Purpose | **Required** | |
| Inputs | **Required** | |
| Outputs | **Required** | A state change or a structured signal — **never a judgment** |
| Write scope | **Required** | The card's most important field. State sole-writer status where it holds |
| Layer | **Required** | Varies widely: the Intent Service is Core; the Integrator is git |
| Loop and escalation | **Conditional** | Only where the operation retries |
| Gates | **Conditional** | An Executor may *evaluate* a deterministic gate (§9.1) without being a Checker |
| Calibration posture | **N/A** | Nothing probabilistic to calibrate |
| Context budget | **N/A** | No LLM in the critical path |
| Failure modes | **Required** | |

## Deterministic gates are not Checker gates

An Executor may evaluate a gate from §9.1 — `merge.no_conflict`, `intent.no_collision`,
`budget.within_ceiling`. These are deterministic predicates over structured state, not reviews of a
Maker's artifact, so evaluating one does not make the agent a Checker. The discriminator holds:
a Checker forms a judgment about an artifact; an Executor computes a predicate.

## Boundary note — the Budget Accountant

The Budget Accountant emits advisory `Finding`s but *"gates nothing"* and is explicitly advisory. It
observes spend telemetry rather than reviewing any Maker's artifact, so Executor is the correct
type. The split from the Budget Enforcer is deliberate and worth restating: *"A missed forecast
costs a warning that would have been nice to have; a missed enforcement costs the budget."*
Forecasting may be probabilistic; enforcement may not.

## Standing constraint — no LLM in the critical path

Same rule as Orchestrator, same reason. If a future version adds a predictive LLM pass to an
Executor, the type assignment has to be revisited rather than quietly stretched.
