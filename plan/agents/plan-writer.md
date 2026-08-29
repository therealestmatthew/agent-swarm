---
title: Plan Writer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Plan Writer

## Type

Maker.

## Pairing

**Plan Reviewer** (adversarial review), and **Security Review (plan-time)** at the same gate. Two
Checkers on one Maker, because plan approval is a human gate and the cost of a bad plan reaching it
is a whole run.

## Purpose

Produces the implementation plan from assembled context. First Maker in the pipeline, and the one
whose output every later phase inherits — a decomposition error here becomes a merge conflict five
phases later, which is why Principle 8 treats those conflicts as evidence about this stage.

## Inputs

- Context window from the Context Gatherer
- The invariant manifest
- The request

Not its own retrieval — a Maker that gathers its own context is mistyped (`types/maker.md`).

## Outputs

- The implementation plan, an unschematized document artifact

## Write scope

Its own draft only. No repo write scope; nothing it produces is applied without the human plan
approval gate.

## Layer

**Core.** "Turn a request and its constraints into an ordered plan a decomposer can act on" is not
a software-specific operation. The Optimization adapters reuse this agent with different context
sources and a different plan shape.

Adapter-supplied nouns: what a plan *contains* and what counts as a well-formed one.

## Loop and escalation

Bounded loop back from the Plan Reviewer, `max_retries=3`. **Competence-type** — a rejected plan
usually reflects reasoning the current tier got wrong, so the escalation ladder's model-tier rung
applies here (unlike the boundary-type loops in `integrator.md`).

Ladder: re-gather context → retry same tier → escalate tier → halt to human.

## Gates

Gated by `plan.review` and `security.plan` (§9.2), then the **human plan-approval gate** (§9.3),
which is not delegable to an agent.

## Context budget

The largest per-consumer budget in the pipeline — this agent needs breadth where later agents need
precision. Invariants hard-included.

## Failure modes

- **Plans to the context it received rather than the problem.** The Context Gatherer's overflow
  warning is the signal; a plan built on a truncated window is confidently incomplete.
- **Rationale leaking to the reviewer.** Principle 11 forbids passing this agent's justification to
  the Plan Reviewer. *"A validator that reads the builder's justification is grading the persuasion,
  not the artifact."*
- **Dialogue depth undefined.** How much back-and-forth this agent should have with a human before
  producing a plan is an open question carried since v0.1 and still unresolved (§12). Stated, not
  answered.
