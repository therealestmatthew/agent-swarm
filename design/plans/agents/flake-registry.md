---
title: Flake Registry
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# Flake Registry

## Type

Archivist. Typed "Utility" in the roster, but its primary output is a durable knowledge record —
known-flaky test IDs — rather than an operational state change, which is the Archivist
discriminator (`types/archivist.md`).

## Pairing

None. A static registry maintained by a deterministic rules-supplement; no extraction judgment for a
Checker to review.

## Purpose

Holds known-flaky test IDs so that a failure with a history of non-determinism is not repeatedly
re-investigated as if it were novel.

## Inputs

- Human-registered flaky test IDs
- Isolated re-run outcomes from the Test Runner

## Outputs

- The registry, consumed by the deterministic triage matrix and the Test Investigator

## Write scope

The registry, as sole writer. **Deletions are human-gated**, consistent with every other Archivist.

## Layer

**Adapter-SDLC.** Its content is test IDs. The Core idea — a durable record of known-unreliable
signals, so triage does not relitigate them — generalizes, but nothing in this agent's current form
does.

## Retention and scope

Repo-local. A flaky test in one repo says nothing about another, and the registry must not span
repos.

## Failure modes

- **Becoming a suppression list.** The real risk. A test parked here stops being investigated, so an
  entry is an admission of an unfixed problem rather than a resolution. Entries should carry an
  expiry or a review trigger; that they currently do not is a gap this card records rather than
  fixes.
- **Stale entries.** A test fixed long ago still listed as flaky quietly weakens triage. No
  reconciliation pass exists for this registry — unlike the Vault, which has one.

## Planned convergence

If this registry is ever extended to actively reconcile against test history, its Archivist
character becomes more pronounced and it should adopt the `StalenessFlag` mechanism the Vault Scribe
already defines rather than inventing a second one.
