---
title: Budget Accountant
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Budget Accountant

## Type

Executor. It emits advisory `Finding`s, which looks Checker-shaped, but it observes spend telemetry
rather than reviewing any Maker's artifact — so Executor is correct (`types/executor.md`).

## Pairing

None — not a Maker/Checker pair.

## Purpose

Forecasts spend trend across all agents and raises advisory findings. **Gates nothing.**

The split from the Budget Enforcer is the design's clearest statement about which functions may be
probabilistic: *"A missed forecast costs a warning that would have been nice to have; a missed
enforcement costs the budget."* Forecasting may be wrong. Enforcement may not.

## Inputs

- Per-agent spend telemetry
- Run history

## Outputs

- Advisory `Finding`s only, `severity="advisory"`

## Write scope

None.

## Layer

**Core.** Spend accrues identically in every domain, and the enforce/forecast separation is a
general principle about where probabilistic reasoning is admissible.

## Gates

**None, deliberately.** This is the field that matters most on this card. An advisory agent that
acquired gating authority would reintroduce exactly the failure the split was made to prevent — a
forecast standing between the run and its next step.

## Failure modes

- **Findings ignored.** Advisory findings that never change behaviour are cost without benefit. The
  honest test is whether a human has ever acted on one; if not, the agent is telemetry with a
  higher price.
- **Drift toward enforcement.** The failure mode to watch across versions. If a future change lets a
  forecast block a transition, the type assignment and the §4.2 argument both have to be revisited
  rather than quietly stretched.
- **Cost model uncalibrated.** The forecast rests on a cost model that roadmap item #4 defers to
  Stage 6, "unblocked by data." Until then its outputs are structurally sound and numerically
  unvalidated, which is stated here rather than implied.
