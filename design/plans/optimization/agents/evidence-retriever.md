---
title: Evidence Retriever
status: draft
part_of: optimization
doc_type: agent-card
layer: adapter-team
---

# Evidence Retriever

## Type

Provider. Same type as the SDLC Context Gatherer, different corpus.

## Pairing

None — not gated. Its output reaches the Status Synthesizer without a `GateResult`, with the
consequences `../../agents/types/provider.md` sets out.

## Purpose

Assembles the evidence set a synthesis may draw on, scoped to what the work packet approved. It
exists so that `claims.all_bound` is checkable: a claim can only be bound to a record if something
enumerated the citable records first.

## Inputs

- The work packet's `approved_sources` — an enumerated allowlist, not a hint
- The pinned register snapshot
- `freshness_threshold`

## Outputs

- An evidence set: records with `source_id`, `last_confirmed_at`, and precedence tier
- An explicit **gap list** — what was asked for and not found

## Write scope

None — read-only.

## Layer

**Adapter-team.** The retrieval mechanism is Core; the corpus is this domain's registers.

## Context budget

Per-consumer, per `context_retrieval_strategy.md` §2.1. Records the Project-State Validator flagged
as exceptions are **hard-included** regardless of relevance score — same rule as invariants in SDLC,
same reason: they are correctness constraints, not optional context.

## Failure modes

- **Silent omission — the primary risk for this type.** A synthesis cannot cite what it was never
  shown, and no gate downstream will notice the absence. Hence the explicit gap list: an empty
  result and an unasked question must be distinguishable.
- **Precedence collapse.** Returning a chat message and a decision record as equally weighted
  evidence lets the least reviewed channel outrank the most reviewed. Every returned record carries
  its precedence tier (`../project_state_model.md` §3).
- **Stale passed through as current.** A record past `freshness_threshold` is returned marked
  stale, never dropped and never presented as live.
