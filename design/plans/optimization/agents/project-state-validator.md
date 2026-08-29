---
title: Project-State Validator
status: draft
part_of: optimization
doc_type: agent-card
layer: adapter-team
---

# Project-State Validator

## Type

Checker.

## Pairing

Reviews the **registers themselves** rather than a Maker's artifact — the humans who maintain them
are the makers here.

This is the one place the Optimization roster stretches the type definitions, and the card says so
rather than hiding it: `../../agents/types/checker.md` assumes a Checker reviews a Maker's output.
Here the "Maker" is a team updating records. The mechanism is unchanged — criteria in, `GateResult`
out — but the pairing is with a human process, and Principle 11's information asymmetry is
trivially satisfied because there is no generator rationale to leak.

## Purpose

Detects incomplete, stale, conflicting, or unowned records **before** anything synthesizes over
them. It gates synthesis for the reason `../delivery_pulse_runbook.md` §2 gives: a confident report
over known-incomplete registers is the most expensive failure this workflow has.

## Inputs

- The pinned register snapshot
- The deterministic data-quality rule set
- The last approved update, for change detection

## Outputs

- `GateResult` with a `Finding` per exception, each carrying an `evidence_ref` to the record
- The exception set, hard-included in the Evidence Retriever's context

## Write scope

None.

## Layer

**Adapter-team.** The rules are about project registers. The pattern — deterministic checks over
structured state, ordered, first match wins — is Core and identical to `infra_triage_matrix.md`'s
engine.

## Loop and escalation

**No agent loop.** Exceptions route to the human-attention queue, because every one of them is
resolved by a person updating a record. There is no Maker to retry.

**Boundary-type** in the sense that matters: a missing owner is not fixed by a better model.

## Gates

Produces a data-quality gate, gating synthesis.

## Calibration posture

**Gating from the start, not Shadow** — the rules are deterministic, so there is no precision to
calibrate. Any part of this agent requiring judgment belongs in a separate LLM pass over the
residue, per Principle 10, and *that* pass would start in Shadow.

## Failure modes

- **Exception fatigue.** A validator that flags 200 items every cycle gets ignored wholesale.
  Volume is a signal about register hygiene, not a result to be proud of.
- **Rules that encode one team's process.** These rules are adapter data and will not transfer
  between teams unchanged. Declared, never inferred.
- **Conflicts it cannot adjudicate.** Two sources disagreeing is detectable; which is right often is
  not. Precedence (`../project_state_model.md` §3) resolves what it can; the rest escalates rather
  than being guessed.
