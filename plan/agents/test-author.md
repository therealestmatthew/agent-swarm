---
title: Test Author
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# Test Author

## Type

Maker.

## Pairing

**Baseline Guard**, which checks test counts, coverage, and `baseline_delta` against silent
deletion.

## Purpose

Writes failing tests only, before any implementation exists. Owns `tests/**` and never touches
implementation — the separation is what makes the tests an independent specification rather than a
description of whatever the implementation happened to do.

## Inputs

- The task specification and its interface map
- The Protocol definitions minted at Contract Freeze

## Outputs

- Test files under `tests/**`, expected to fail

## Write scope

`tests/**` only, **enforced by permission rather than instruction** (Principle 12). A Test Author
that could write implementation would be able to make its own tests pass, which is the reward-hacking
path the write-scope split exists to close.

## Layer

**Adapter-SDLC.** This agent is the concrete instantiation of Principle 3 (TDD-first), which
`core_vs_adapter.md` §4 classifies as the one adapter-specific principle.

Its Core generalization: *the acceptance criterion is fixed before the artifact is produced, and
authored by someone other than the producer.* In Team Optimization that becomes the quality
checklist and template requirements agreed before a status draft exists — same structure, no test
runner.

## Loop and escalation

`max_retries=3`, competence-type.

## Gates

Gated by `tests.diff_covered` (§9.1) and reviewed by `baseline_delta`.

## Context budget

Task spec, interface map, Protocol definitions. Deliberately excludes any implementation — there is
none yet, and after there is, this agent does not see it.

## Failure modes

- **Tautological tests.** A test that asserts what the code does rather than what it should do. The
  anti-reward-hacking guards (§10) and diff-scoped mutation testing exist because a passing suite
  is only evidence if the tests could have failed.
- **Tests that pass immediately.** A test written to fail that passes on first run is either
  testing nothing or testing something already built. Either way it is a signal, not a success.
