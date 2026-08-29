---
title: Budget Enforcer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Budget Enforcer

## Type

Orchestrator.

## Pairing

None — not a Maker/Checker pair. Deterministic middleware; there is no judgment for a Checker to
review.

## Purpose

Sits in the dispatch path and refuses any transition that would breach a ceiling in
`GovernancePolicy`. It is separated from the Budget Accountant, which forecasts spend and gates
nothing, so that a slow or wrong forecast can never fail open.

## Inputs

- The proposed transition
- `GovernancePolicy` budget ceilings
- Accumulated spend for the run

## Outputs

- Pass, or a `HaltReason.CEILING_HALT`

## Write scope

None. It refuses transitions; it does not modify state.

## Layer

**Core.** Cost accrues identically in every domain, and a breaker that an orchestrator can route
around is not a breaker in any of them.

Adapter-supplied nouns: none. The ceilings are policy values, not adapter declarations — a repo
declaring its own budget ceiling would be grading itself.

## Gates

Produces `budget.within_ceiling` (§9.1).

## Failure modes

- **Fails open.** The one unacceptable outcome. `budget_and_escalation_policy.md` §4.1 is explicit:
  *"a circuit breaker that is itself an LLM can be slow, wrong, or unavailable — and it fails
  hardest under exactly the runaway conditions it exists to catch."* Hence deterministic middleware
  in the dispatch path rather than an agent the Orchestrator consults.
- **Halt semantics undefined.** `budget_and_escalation_policy.md` §3 says a run "pauses" without
  saying what that does to a live process — registered as roadmap finding D12 and still open. This
  card does not resolve it and should not be read as doing so.

## Schema

`GovernancePolicy.budget_ceilings: dict[str, LoopBudgetConfig]` (`contracts/governance.py:403`).
Keyed by loop edge, so a ceiling is per-loop rather than one global number — which is what makes
the on-exhaustion action in §1 of `budget_and_escalation_policy.md` expressible per edge.
