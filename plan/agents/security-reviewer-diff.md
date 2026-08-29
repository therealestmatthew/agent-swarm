---
title: Security Reviewer (diff-time)
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# Security Reviewer (diff-time)

## Type

Checker.

## Pairing

Reviews the merged PR diff, independently of the PR Reviewer and at the same gate.

## Purpose

Catches the security residue that plan-time review structurally cannot reach: consequences that only
exist once there is an implementation. The plan-time reviewer works on intent; this one works on
what was actually written.

## Inputs

- The full merged diff
- The invariant manifest, `enterprise_wide` constraints included
- Secret-scrubbing telemetry from the run

## Outputs

- `GateResult` with `Finding` list

## Write scope

None.

## Layer

**Adapter-SDLC.** Its findings are about code. The two-point structure — review intent early, review
the artifact late — is Core.

## Loop and escalation

A **blocking** security finding halts to human rather than looping. The design does not retry its
way past a security objection, and there is no model tier at which that would become appropriate.

## Gates

Produces `security.diff` (§9.2).

## Calibration posture

Gating, with the same recall-over-precision asymmetry as its plan-time counterpart. A false accept
ships a vulnerability; a false reject costs a human read.

## Failure modes

- **Credential in evidence.** A `Finding.evidence_ref` must never dereference to unscrubbed content.
  Scrubbing runs inside the isolation unit at the boundary, because a redaction filter must know the
  values it is redacting — which conflicts with Core never holding them
  (`core_adapter_boundary.md` §5). Audited as C1.
- **Evidence retention undefined.** How long an `evidence_ref` remains dereferenceable, and what
  happens when it does not, is roadmap finding D9 — still open. Named here because this agent's
  findings are the ones most likely to point at sensitive material.
