---
title: Quality Reviewer
status: draft
part_of: optimization
doc_type: agent-card
layer: adapter-team
---

# Quality Reviewer

## Type

Checker.

## Pairing

Reviews the **Status Synthesizer**'s draft, and the **Continuity Assistant**'s transition brief.

Two Makers, one Checker. This is the Optimization roster's answer to the Principle 1 gap the
external review shipped with: it proposed a Continuity Assistant with no reviewer at all. Sharing
this Checker is cheaper than a second one and better than none — the check discipline is the same
in both cases, since both artifacts are prose asserting things about project state.

## Purpose

Checks a draft against the approved checklist and against its evidence. The last agent before a
human sees the work.

## Inputs

- The draft artifact
- The template and checklist requirements
- The evidence set the draft cites

**Never** the Synthesizer's rationale (Principle 11, information asymmetry).

## Outputs

- `GateResult` with a `Finding` list

## Write scope

None.

## Layer

**Adapter-team.** The checklist is domain-specific. Its position — a final Checker over the
assembled artifact, distinct from per-unit checks — is Core, and structurally the same as the SDLC
PR Reviewer's.

## Loop and escalation

Loops back to the Synthesizer, `max_retries=3`, competence-type.

## Gates

Produces the quality-review gate, feeding the human approval gate.

## Calibration posture

**Shadow initially**, like every new Checker.

Its promotion signal is the best-conditioned in the whole design. A human disposition —
accepted, edited, rejected — lands on *every* pulse, at the reporting cadence, whether or not this
agent flagged anything. That is a denser and less biased signal than the SDLC Code Reviewer gets,
and it is why `../delivery_pulse_runbook.md` §8 expects this agent to reach a promotion decision
sooner.

`reviewer_spec_version` on every verdict. A checklist change bumps it — otherwise the ledger keeps
accumulating rows that no longer describe the reviewer currently running.

## Context budget

Draft, checklist, cited evidence. Not the full register set — this agent verifies the draft against
what it cited, and widening it to re-derive the whole picture would duplicate the Synthesizer's job
rather than check it.

## Failure modes

- **Checking form, not substance.** A checklist is easy to satisfy structurally. The failure mode
  is a green verdict on a complete-looking, substantively empty update.
- **False accept.** Passes a wrong claim to a human who now has an agent's endorsement to anchor on.
  The reason for Shadow Mode first.
- **Sharing a Checker across two Makers.** Recorded as a compromise: a reviewer tuned for status
  updates may be a weaker reviewer for transition briefs. Revisit if the ledger shows materially
  different precision on the two artifact types.
