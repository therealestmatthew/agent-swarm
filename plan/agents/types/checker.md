---
title: Checker (Agent Type)
status: live
part_of: agentic-sdlc
doc_type: agent-type
layer: core
---

# Checker (Agent Type)

**Cards of this type:** `plan-reviewer.md` · `security-review-plan.md` · `code-reviewer.md` ·
`baseline-guard.md` · `test-investigator.md` · `pr-reviewer.md` · `security-reviewer-diff.md` ·
`error-analyzer.md` · `vault-checker.md` · and in Optimization,
`project-state-validator.md` · `quality-reviewer.md`

## Definition

> Reviews a Maker's artifact against stated criteria. Produces a `GateResult` with a `Finding` list.
> May gate phase progression or operate in Shadow Mode during calibration.
>
> — `agent_taxonomy.md` §1.3

The largest type in the roster, which is the design working as intended rather than an imbalance.

## The three asymmetries

Principle 11 is the Checker type's operating discipline, and every card restates the one that binds
hardest for that agent:

- **Information** — the reviewer sees the spec and the artifact, never the generator's own
  rationale. *"A validator that reads the builder's justification is grading the persuasion, not the
  artifact."*
- **Tooling** — a validator can execute. Outside software this becomes: a validator can
  independently verify against source data. A Checker whose only instrument is re-reading the
  artifact is weaker than one that can go check.
- **Model** — a different tier from the builder, at minimum.

## Field discipline

| Section | Required? | Notes |
|---|---|---|
| Type | **Required** | |
| Pairing | **Required** | Names what it reviews |
| Purpose | **Required** | |
| Inputs | **Required** | The artifact and the criteria — **never the Maker's rationale** |
| Outputs | **Required** | Always `GateResult` (`contracts/verification.py`) |
| Write scope | **Required** | Almost always `None`. A Checker that can edit what it reviews is reviewing its own output |
| Layer | **Required** | |
| Loop and escalation | **Required** | The loop back to its Maker, with the ceiling |
| Gates | **Required** | The gate ID it produces, from §9.2 |
| Calibration posture | **Required** | `Shadow` or `Gating` + promotion criterion. Not optional for this type |
| Context budget | **Required** | Unless deterministic |
| Failure modes | **Required** | Both directions: false accept and false reject |

## Why `GateApplicability` matters more here than anywhere

A Checker's `GateResult` carries `applicability`: `APPLIED`, `NOT_APPLICABLE`, or `DEGRADED`. The
reason is stated in the schema itself — *a bare pass/fail cannot express "I did not run."* A Checker
that fails to run and returns nothing is indistinguishable, downstream, from one that ran and
passed. That is Principle 7's sharpest instance, and it is why `is_green` is true only for a gate
that actually ran and actually passed.

## Standing constraint — Shadow by default

A new or materially changed Checker gates nothing until its precision clears a human-set bar over N
runs (`calibration_and_measurement.md` §2). The argument for spending the shadow window rather than
promoting on faith: *"you are the oracle on your own repo in a way you are not on an unfamiliar one
— you can grade the graders here. That advantage is temporary."*

A prompt change bumps `reviewer_spec_version`. Without it the ledger keeps accumulating rows that no
longer describe the validator currently running.
