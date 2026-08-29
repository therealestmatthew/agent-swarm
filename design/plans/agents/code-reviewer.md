---
title: Code Reviewer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: shared
---

# Code Reviewer

## Type

Checker.

## Pairing

Reviews each **Task Dev Swarm** branch. Bounded loop back.

## Purpose

Reviews each parallel branch before it reaches integration. It is the roster's calibration
showcase — the agent the Shadow Mode machinery was designed around, and the first scheduled for
promotion from advisory to gating.

## Inputs

- The branch diff
- The task specification and interface map
- The invariant manifest

**Never** the Task Dev agent's rationale (Principle 11).

## Outputs

- `GateResult` with `Finding` list, each carrying an `evidence_ref`

## Write scope

None.

## Layer

**Shared.** "An independent reviewer checks a Maker's artifact against a spec, with tooling the
Maker did not have" is Core. What it reviews, and the tooling asymmetry's concrete form — this
reviewer can *execute* — is adapter-SDLC. Outside software the same asymmetry becomes: the reviewer
can independently verify against source data.

## Loop and escalation

`max_retries=3`, **competence-type** — the model-tier rung applies and is the point. This is the
loop `budget_and_escalation_policy.md` §2.1 uses as its standard ladder: re-gather context → retry
same tier → escalate tier → halt to human.

## Gates

Produces `code.review` (§9.2).

## Calibration posture

**Shadow initially — gates nothing until promoted.** The roster explicitly types this agent
"Validator (shadow mode)", and it is the design's worked example of earning gating authority.

Promotion requires precision over N runs clearing a human-set bar, measured in the verdict ledger
against human overrides and downstream outcomes. The argument for spending the window rather than
promoting on faith: *"you are the oracle on your own repo in a way you are not on an unfamiliar one
— you can grade the graders here. That advantage is temporary; spend it during the shadow window."*

Every verdict carries `reviewer_spec_version`. A prompt change bumps it — without that the ledger
accumulates rows that no longer describe the validator currently running, and precision computed
across the boundary is meaningless.

Promotion is scheduled for roadmap Stage 6, "unblocked by data," because the criterion cannot be met
before the data exists.

## Context budget

Diff, spec, interface map, invariants hard-included. Notably *not* the whole repo — a reviewer given
everything reviews nothing carefully.

## Failure modes

- **False accept.** Passes a defect to integration, where it costs a full merge cycle. The reason
  Shadow Mode precedes gating.
- **False reject.** Burns loop iterations and, once gating, blocks correct work. Cheaper, and
  visible in the ledger as override rate.
- **Reward hacking on findings.** A reviewer measured on findings-per-review will produce findings.
  Cost per genuinely-caught defect — precision crossed with spend
  (`calibration_and_measurement.md` §4) — is the metric that resists this; raw finding count does
  not.
- **Spec-version blending.** Handled by `reviewer_spec_version`, and worth stating as a failure mode
  because it is silent: nothing looks wrong, the numbers are just no longer about this agent.
