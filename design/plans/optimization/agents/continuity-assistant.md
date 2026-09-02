---
title: Continuity Assistant
status: draft
part_of: optimization
doc_type: agent-card
layer: adapter-team
---

# Continuity Assistant

## Type

Maker.

## Pairing

**Quality Reviewer.**

**This pairing did not exist in the proposal this agent came from.** The external review specified
five specialists, gave four of them a coherent place in a review chain, and left this one producing
a transition brief that nobody checked — a straightforward Principle 1 violation, and an easy one to
miss because the agent is read-only and looks harmless.

Read-only is not the relevant property. The artifact is what someone inheriting a project will rely
on, so an unreviewed brief is a confidently-wrong handover. Writing the card is what surfaced this;
the schema requires a Maker to name a Checker and offers no blank to leave (`../../agents/types/maker.md`).

## Purpose

Produces an onboarding or handover brief: current state, key documents, open commitments, recent
decisions and their rationale. It exists for the moment institutional knowledge is most likely to be
lost, which is also the moment nobody has time to check it carefully.

## Inputs

- Validated registers, post-gate
- Recent approved updates
- The `sources` manifest
- Decisions with their recorded rationale

## Outputs

- A structured transition brief, every claim evidence-bound

## Write scope

**None.** Emits nothing back into the registers — a handover brief that silently created or closed
records would be exactly the automatic task creation the external review rightly excluded.

## Layer

**Adapter-team.** The brief's structure is domain-specific; the Maker/Checker shape is Core.

## Loop and escalation

`max_retries=3`, competence-type. On exhaustion, to the human-attention queue.

## Gates

Gated by `claims.all_bound` and the quality review, then the human approval gate. A brief is
released to a person, so it clears the same human gate as a status update.

## Context budget

Broader than the Status Synthesizer's — a handover is a wider question than a reporting period —
which makes it the Team adapter's most likely overflow case. The Evidence Retriever's gap list
matters most here: the brief must be able to say what it could not establish.

## Failure modes

- **Confident gaps.** The worst outcome for this artifact. A brief that omits an open commitment
  reads exactly like one where no commitment exists, and the reader has no way to tell. Explicit
  "not established" sections are required, not optional.
- **Rationale loss.** A decision without its rationale is a fact the successor cannot reason about
  or safely revisit. Where `decisions` records lack rationale, the brief must surface the absence
  rather than restating the bare decision.
- **Timing.** This agent is most needed exactly when registers are least likely to be current —
  someone leaving has usually stopped updating them. The Project-State Validator's exceptions are
  therefore more load-bearing here than anywhere else in the workflow.
