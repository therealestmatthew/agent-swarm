---
title: Orchestrator (Agent Type)
status: live
part_of: agentic-sdlc
doc_type: agent-type
layer: core
---

# Orchestrator (Agent Type)

**Cards of this type:** `core-orchestrator.md` · `budget-enforcer.md`

## Definition

> Controls flow, dispatches agents, and enforces gates and spending ceilings. Produces routing
> decisions and phase transitions. Never produces domain artifacts. Minimal context by design.
> Predominantly or wholly deterministic — LLM is not in the critical path.
>
> — `agent_taxonomy.md` §1.1

## Why this type is Core by construction

An Orchestrator consumes structured state and emits a routing decision. It never reads an artifact's
*content* — that is what makes it domain-independent, and it is the mechanism behind Principle 2
(minimal-context orchestration). The Core Orchestrator's entire state across all eight phases is a
`RunManifest` plus a reference to the event log — never a plan body, never a diff.

The consequence worth stating: an Orchestrator that started reading artifacts to make better
routing decisions would become domain-coupled *and* accumulate the context rot the design exists to
avoid. Both failures arrive together, which is why the constraint is structural rather than stylistic.

## Field discipline

| Section | Required? | Notes |
|---|---|---|
| Type | **Required** | |
| Pairing | **Required** | Always `None — not a Maker/Checker pair`, with the reason |
| Purpose | **Required** | |
| Inputs | **Required** | Structured state only. An Orchestrator taking artifact *content* as input is mistyped |
| Outputs | **Required** | A routing decision, a phase transition, or a `HaltReason` |
| Write scope | **Required** | `RunManifest` and the event log only |
| Layer | **Required** | Expected `core`. An `adapter-*` Orchestrator means flow control leaked into a domain |
| Loop and escalation | **Forbidden** | An Orchestrator does not retry; it routes. Loop ceilings belong to the loops it dispatches |
| Gates | **Required** | Which gates it evaluates and where it refuses |
| Calibration posture | **N/A** | Nothing to calibrate without an LLM verdict |
| Context budget | **N/A** | Minimal context is the definition, not a budget |
| Failure modes | **Required** | |

## Boundary against Executor

An Orchestrator decides *what happens next*; an Executor *makes it happen*. The Core Orchestrator
reads `RunManifest` and emits the next phase; the Integrator performs the merge. Both are
deterministic — their outputs differ in kind, and that difference is the discriminator.

## Standing constraint

**No LLM in the critical path.** `budget_and_escalation_policy.md` §4.1 states the reason in its
strongest form: *"a circuit breaker that is itself an LLM can be slow, wrong, or unavailable — and
it fails hardest under exactly the runaway conditions it exists to catch. A breaker that fails open
under load is not a breaker."* Any proposal to add a judgment call to an Orchestrator has to answer
that sentence first.
