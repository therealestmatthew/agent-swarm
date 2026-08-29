---
title: Plan Reviewer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Plan Reviewer

## Type

Checker.

## Pairing

Reviews the **Plan Writer**'s plan. Bounded loop back.

## Purpose

Adversarial review of the plan before it reaches the human approval gate. Its value is caught-early
arithmetic: a decomposition flaw found here costs one loop iteration; the same flaw found at
integration costs the swarm's whole parallel phase and surfaces as a merge conflict nobody can
attribute.

## Inputs

- The plan artifact
- The stated criteria and the invariant manifest

**Never** the Plan Writer's rationale (Principle 11, information asymmetry).

## Outputs

- `GateResult` with a `Finding` list (`contracts/verification.py`)

## Write scope

None. A Checker that can edit what it reviews is reviewing its own output.

## Layer

**Core.** Adversarial review of a plan against stated criteria is domain-independent; only the
criteria are adapter data.

## Loop and escalation

Loops back to the Plan Writer, `max_retries=3`, **competence-type** — the tier rung applies.
On exhaustion: halt to the human plan-approval gate with findings attached, rather than passing a
plan neither agent could converge on.

## Gates

Produces `plan.review` (§9.2).

## Calibration posture

Gating. Precision measured against human overrides at the plan-approval gate — an unusually clean
signal, because a human verdict lands on every plan regardless of what this agent said.
`reviewer_spec_version` stamped on each verdict.

## Context budget

Plan artifact plus criteria plus invariants. Deliberately narrower than the Plan Writer's: this
agent needs the plan and the rules, not the breadth the plan was built from.

## Failure modes

- **False accept** — a flawed plan reaches the human gate carrying an implicit endorsement. The
  more expensive direction, since human reviewers anchor on a passing verdict.
- **False reject** — burns loop iterations on a sound plan, then halts. Visible and cheap.
- **Grading persuasion.** If rationale ever reaches this agent, it stops reviewing the artifact.
  Enforced by what the dispatch path passes, not by instructing the agent to ignore it — Principle
  12.
