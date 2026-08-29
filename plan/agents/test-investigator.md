---
title: Test Investigator
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# Test Investigator

## Type

Checker.

## Pairing

Reviews `FailureSignature`s that the deterministic triage table could not classify. Bounded loop
back to Task Dev.

## Purpose

The judgment fallback for ambiguous failures, and **only** for those. It is the residue-handler in
Principle 10's deterministic-before-LLM arrangement: fixed rules classify what they can, and the LLM
sees only what they could not.

Its classifications are logged as raw material for new deterministic rules — the LLM's job is
partly to work itself out of a job.

## Inputs

- The unclassified `FailureSignature`
- The ordered triage rules that failed to match
- The Flake Registry

## Outputs

- `GateResult` with a classification
- A logged classification record, feeding rule-set growth

## Write scope

None.

## Layer

**Adapter-SDLC.** Its inputs are test failure signatures. The Core pattern it sits in — deterministic
rules first, LLM on the residue, ambiguous cases logged to grow the rule set — is domain-neutral and
is arguably the most portable mechanism in the whole design.

## Loop and escalation

`max_retries=3` on its own loop, plus a bounded loop back to Task Dev when it classifies a failure
as a code defect. Competence-type.

## Gates

Produces `test.classification` (§9.2). Sits behind `triage.deterministic` (§9.1) — it runs only
where the deterministic gate returned no match.

## Calibration posture

Gating, but with a narrow remit: it classifies rather than approves, and a misclassification routes
work to the wrong queue rather than shipping a defect.

## Context budget

The signature, the rules that failed, the registry. Deliberately not the diff — this agent
classifies a failure, it does not review an implementation.

## Failure modes

- **"Flake" as a root cause.** It is not one. A failure classified as flake without an isolated
  re-run confirming it is an unexamined failure with a label.
- **Absorbing failures the rules should own.** If this agent is classifying the same pattern
  repeatedly, that pattern belongs in the deterministic table. Sustained volume here is a signal
  about the rule set, not a workload to accept.
- **Passes alone, fails in suite.** The known-ambiguous case, registered as roadmap finding D8 and
  still open — it will land as a reference rule in `infra_triage_matrix.md` §2 when decided.
