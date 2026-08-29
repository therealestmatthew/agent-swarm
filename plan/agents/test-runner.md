---
title: Test Runner
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# Test Runner

## Type

Executor.

## Pairing

None — not a Maker/Checker pair. It reports what happened; it does not judge it.

## Purpose

Executes the declared test tiers and captures a `FailureSignature` at the moment of failure. The
separation that matters: this agent **does not classify**. Classification belongs to the
deterministic triage matrix, with the Test Investigator as the judgment fallback.

## Inputs

- `TestTier` declarations from `RepoDeclaration` — command, isolation unit, hermeticity,
  reset strategy
- The merged branch

## Outputs

- Pass/fail per tier
- `FailureSignature` (`contracts/verification.py`) — captured at failure time, **not reconstructed
  from logs afterward**
- Coverage and test counts, consumed by the Baseline Guard

## Write scope

None on the repo. Owns its execution environment.

## Layer

**Adapter-SDLC.** Test tiers, commands, and hermeticity are the defining nouns of software
verification. The Optimization adapters replace this agent entirely — their oracle is evidence
binding (`claims.all_bound`), not an executable suite.

## Gates

Feeds `tests.baseline_delta` and `triage.deterministic` (§9.1).

## Failure modes

- **Signature reconstructed rather than captured.** `infra_triage_matrix.md` §1 requires capture at
  the moment of failure. A signature rebuilt from logs afterward has already lost the state that
  distinguishes an infra failure from a code failure.
- **State leakage between tests.** Guarded by the declared `ResetStrategy` and its
  `clean_state_checks`. The governing rule is *construct fresh, never clean in place*, because
  clearing routines only reach what they explicitly enumerate.
- **Flake.** Not a root cause. Routed to the Flake Registry and the triage matrix, never accepted as
  an explanation on its own.

## Known Core leak

`TestTier.execution_tier` is a closed `Literal["tier1_unit","tier2_integration","tier3_browser"]`
in a Core model (`contracts/governance.py:142`), introduced by PR #5. An adapter cannot declare a
tier ladder of its own shape. Registered in `core_vs_adapter.md` §6.
