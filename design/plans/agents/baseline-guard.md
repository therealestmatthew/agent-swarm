---
title: Baseline Guard
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: shared
---

# Baseline Guard

## Type

Checker.

## Pairing

Reviews the **Test Author**'s output, and guards the suite against every agent downstream of it.

## Purpose

Checks `baseline_delta`, test counts, and coverage to catch silent test deletion. It exists because
the cheapest way for any agent to turn a failing suite green is to remove the failing test, and
nothing else in the pipeline would notice.

## Inputs

- Current test counts, coverage, and `baseline_delta`
- The baseline snapshot, captured against the **declared post-hydration state** — never against
  empty, and never against the previous test's end state (`core_adapter_boundary.md` §4)

## Outputs

- `GateResult` with `Finding` list

## Write scope

None.

## Layer

**Shared, and the most interesting generalization in the roster.** The mechanism — compare against a
captured baseline and block silent removal — is Core. The nouns are SDLC.

Its Optimization analogue is **anti-omission**: a status update that silently drops a risk carried
in the prior approved update is the exact structural equivalent of deleting a failing test. Same
guard, same asymmetry, different artifact. The Team adapter reuses this agent as an Omission Guard
(`optimization/delivery_pulse_runbook.md`).

## Gates

Produces `tests.baseline_delta` (§9.1). Test deletion sign-off is a **human gate** (§9.3) — this
agent blocks; a human authorizes.

## Calibration posture

Gating from the start, not Shadow. The check is deterministic — counts against a baseline — so there
is no precision to calibrate, and the failure it catches is severe enough that an advisory period
would be a hole rather than a measurement.

## Failure modes

- **Legitimate deletion blocked.** A genuinely obsolete test trips the guard. Resolved through the
  human sign-off gate rather than by loosening the threshold — the governance asymmetry from
  `test_harness_architecture.md` §1.5 applies: tightening is automatic, loosening is a human gate,
  because loosening *"is self-rewarding for whoever proposes it."*
- **Count preserved, meaning removed.** Replacing a real test with a tautological one keeps the
  count stable. Diff-scoped mutation testing exists for this residue; the Baseline Guard alone
  cannot see it.
- **Baseline compared against the wrong thing.** Comparing against empty rather than the declared
  post-hydration state produces false alarms in any repo whose tests need seeding — which is why
  the boundary file redefined what baseline means.
