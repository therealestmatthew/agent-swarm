---
title: Status Synthesizer
status: draft
part_of: optimization
doc_type: agent-card
layer: adapter-team
---

# Status Synthesizer

## Type

Maker.

## Pairing

**Quality Reviewer**, and the **Omission Guard** at step 6 of `../delivery_pulse_runbook.md`.

## Purpose

Drafts the periodic update from validated records and approved evidence. The only agent in the Team
adapter that generates prose an audience will read, which makes it the one whose failures are least
visible: a wrong number in a status report looks exactly like a right one.

## Inputs

- Validated registers, post-gate
- The evidence set, with precedence tiers and freshness stamps
- The previous approved update
- The output template

## Outputs

- A draft update in which **every claim carries an `evidence_ref`**

## Write scope

**None.** It drafts; it does not touch registers. Anything it proposes changing is emitted as a
typed intent and applied by the Shared-File Intent Service, or — for a non-additive change like
closing an action — refused outright, since the vocabulary has no operation for it
(`../project_state_model.md` §2.2).

## Layer

**Adapter-team.** The artifact is a project status update.

## Loop and escalation

Loops back from the Quality Reviewer, `max_retries=3`, **competence-type** — a rejected draft is
usually a reasoning failure, so the model-tier rung applies.

On exhaustion: escalate to the human-attention queue with the draft and findings attached, rather
than releasing something two agents could not converge on.

## Gates

Gated by `claims.all_bound`, the quality review, and the omission check. Then the **human approval
gate**, which is not delegable.

## Context budget

Validated registers, evidence set, previous update, template. Deliberately **not** the raw source
corpus — this agent synthesizes from what the Evidence Retriever approved, and letting it reach past
that would make `approved_sources` advisory rather than enforced.

## Failure modes

- **Fluent and unfounded.** The characteristic LLM failure and the reason for evidence binding. An
  unbound claim fails `claims.all_bound` deterministically — no reviewer judgment required.
- **Bound and still wrong.** The residue no gate closes: `claims.all_bound` proves a claim cites a
  live record, never that the claim follows from it. This is what the Quality Reviewer and the human
  approver are for, and it should not be described as covered.
- **Optimistic drift.** Systematically softening bad news across cycles is invisible in any single
  update and obvious across ten. The Omission Guard catches disappearance; nothing currently catches
  gradual softening, and that gap is named rather than solved.
- **Template compliance mistaken for quality.** A structurally complete update can be substantively
  empty.
