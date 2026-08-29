---
title: Provider (Agent Type)
status: live
part_of: agentic-sdlc
doc_type: agent-type
layer: core
---

# Provider (Agent Type)

**Cards of this type:** `context-gatherer.md` · and in Optimization, `evidence-retriever.md`

## Definition

> Assembles, retrieves, and delivers targeted context or data to other agents on demand. Does not
> produce domain artifacts and is not itself reviewed by a Checker. The supply chain for Makers and
> Checkers.
>
> — `agent_taxonomy.md` §1.4

## The ungated position, and what it costs

A Provider is the one agent type whose output reaches a Maker without passing a gate. That is a
deliberate trade — gating every context assembly would double the pipeline's cost for a artifact
nobody ships — but it concentrates risk. Everything downstream is only as good as what the Provider
handed over, and no `GateResult` will catch a quiet omission.

The design's answer is Principle 7 applied hard at this boundary. `context_retrieval_strategy.md`
§2.3–2.4: non-top-K material is compressed to one-line digests rather than dropped, and overflow
raises an explicit warning rather than truncating. The reasoning is that silent truncation creates
*"the illusion of complete coverage"* — a Maker cannot ask for what it does not know is missing.

**Every Provider card must state its overflow behaviour.** For this type it is the primary failure
mode, not a footnote.

## Field discipline

| Section | Required? | Notes |
|---|---|---|
| Type | **Required** | |
| Pairing | **Required** | Always `None — not gated`, with the trade stated |
| Purpose | **Required** | |
| Inputs | **Required** | The query and the scope it may search |
| Outputs | **Required** | Context bundles. Name the consumers |
| Write scope | **Required** | Almost always `None — read-only` |
| Layer | **Required** | Expected `core`; the *sources* it reads are adapter data |
| Loop and escalation | **Optional** | Only if it retries a failed retrieval |
| Gates | **Forbidden** | A Provider produces no `GateResult` |
| Calibration posture | **N/A** | No verdict to calibrate |
| Context budget | **Required** | This type *owns* the budget — per-consumer tiers and the ranking heuristic |
| Failure modes | **Required** | Must include overflow and silent-omission behaviour |

## Boundary against Archivist

A Provider assembles context for an immediate consumer in a single phase. An Archivist writes
knowledge durably across runs so it can be queried later. The Vault Scribe is an Archivist; the
Context Gatherer, which *queries* the Vault on the Archivist's read interface, is a Provider.

## Standing constraint — hard-include beats ranking

Invariants and correctness constraints are included regardless of relevance score. They are
*"correctness constraints, not optional context, and shouldn't be droppable by a ranking
algorithm."* A Provider card that subjects its constraint set to the same ranking as ordinary
material is specifying a bug.
