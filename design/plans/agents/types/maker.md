---
title: Maker (Agent Type)
status: live
part_of: agentic-sdlc
doc_type: agent-type
layer: core
---

# Maker (Agent Type)

**Cards of this type:** `plan-writer.md` · `task-decomposer.md` · `test-author.md` ·
`task-dev-swarm.md` · `ci-cleanup.md` · and in Optimization, `status-synthesizer.md` ·
`continuity-assistant.md`

## Definition

> Produces a first-draft domain artifact from context. Output is reviewed by a paired Checker.
> "Maker" is the explicit first half of the design's Maker/Checker principle (Principle 1).
>
> — `agent_taxonomy.md` §1.2

## The rule that has no exceptions

**Every Maker names at least one Checker.** Principle 1 is the design's first and most load-bearing
rule, and a Maker whose output nobody reviews is the single failure it prohibits. When a card cannot
name a Checker, the card says so as a finding rather than leaving the field blank — an unpaired
Maker discovered later is far more expensive than one written down now.

This is not hypothetical: the external review that prompted the Optimization adapters proposed a
Continuity Assistant with no reviewer. The card for it names the Quality Reviewer as its Checker
precisely because writing the card forced the question.

## Field discipline

| Section | Required? | Notes |
|---|---|---|
| Type | **Required** | |
| Pairing | **Required** | Must name a Checker. Blank is not an option |
| Purpose | **Required** | |
| Inputs | **Required** | Assembled by a Provider. A Maker that retrieves its own context is mistyped |
| Outputs | **Required** | A reviewable artifact |
| Write scope | **Required** | Usually its own worktree, or `None — emits intents` for shared state |
| Layer | **Required** | Varies. `plan-writer` is Core; `test-author` is adapter-SDLC |
| Loop and escalation | **Required** | With competence-type vs boundary-type stated explicitly |
| Gates | **Required** | Which gates its output must clear |
| Calibration posture | **N/A** | Makers are calibrated through their Checker's ledger, not their own |
| Context budget | **Required** | LLM in the critical path |
| Failure modes | **Required** | |

## Boundary against Provider

The Context Gatherer produces context *for* Makers, but its output is not itself reviewed by a
Checker — it is consumed directly, not gated. A Maker's output is always gated. The discriminator is
whether the output passes through a `GateResult`, not whether the agent is "creative."

## Standing constraint — validator asymmetry

Principle 11: a Maker's own rationale must not reach its Checker. *"A validator that reads the
builder's justification is grading the persuasion, not the artifact."* A Maker card that lists
"reasoning trace" among its outputs to a Checker is specifying a Principle 11 violation.
