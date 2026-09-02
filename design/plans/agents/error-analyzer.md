---
title: Error Analyzer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Error Analyzer

## Type

Checker.

## Pairing

Reviews **Log Monitor** telemetry.

## Purpose

Pattern-matches production log findings and triggers rollback initialization on critical ones. It is
the last agent in the pipeline and the only one whose verdict can reach back into a shipped change.

## Inputs

- Structured telemetry from the Log Monitor
- The change's provenance — which run and which task produced what is now failing

## Outputs

- `GateResult` with `Finding` list
- A rollback initialization trigger on a critical finding

## Write scope

None. It **initializes** rollback; it does not perform one. **Rollback authorization is a human
gate** (§9.3), and this agent's trigger opens that gate rather than passing through it.

## Layer

**Core.** Observing a shipped artifact, classifying anomalies, and escalating to a reversal decision
is domain-independent. Only the signal vocabulary is adapter data.

## Loop and escalation

No loop back — there is no Maker to return to at this stage. A critical finding escalates to human
directly, which is the correct terminal behaviour for the last agent in the chain.

## Gates

Feeds the **rollback authorization** human gate (§9.3).

## Calibration posture

Gating, and the hardest agent in the roster to calibrate. Its ledger fills only when production
incidents occur, so the shadow window that works for the Code Reviewer would take far longer here —
and the events it must catch are, by design, rare. This is stated as an unresolved tension rather
than solved: the promotion criterion in `calibration_and_measurement.md` §2 assumes a verdict
volume this agent will not reach quickly.

## Failure modes

- **False critical.** Triggers an unnecessary rollback decision. Bounded by the human gate, which is
  exactly why the gate is there.
- **Missed critical.** The expensive direction — a defect keeps running in production. Argues for
  the same recall-over-precision bar as the security reviewers.
- **Attribution.** Connecting a production symptom to the run that caused it depends on provenance
  the pipeline must have retained. Where the trail is missing, this agent can classify the failure
  but not route it.
