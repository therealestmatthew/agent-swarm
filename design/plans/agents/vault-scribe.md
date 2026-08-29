---
title: Vault Scribe
status: draft
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Vault Scribe

**Status: draft — proposed agent, not in the blueprint §2 roster.** Defined in
`agent_taxonomy.md` §3; full specification deferred to the proposed `plan/vault_architecture.md`.

## Type

Archivist. The first dedicated one, and the reason the Archivist type was named at all.

## Pairing

**Vault Checker.** Extraction from transcripts into typed entries is a Maker operation and must be
paired, per `agent_taxonomy.md` §3.7 decision 1. Exempting the Scribe from Principle 1 would create
a privileged carve-out from the design's most load-bearing rule and leave the Vault's integrity
unguarded — the store every later run reads from would be the one thing nobody checks.

## Purpose

The pipeline's institutional memory. Processes transcripts, `GateResult` records, human override
notes and resolved `Finding`s into structured knowledge; keeps that knowledge synchronized with
current reality; surfaces contradicted entries for human review.

It exists so a new run starts informed rather than cold. Without it, memory concerns are distributed
across 7 narrow, domain-specific structures and no agent owns knowledge as such.

## Inputs

- Agent transcripts, raw or summarized
- `GateResult` records from the Verdict Ledger
- Human override notes from any human gate
- Resolved `Finding`s from any Checker
- Current repo state, for reconciliation passes

## Outputs

- `VaultEntry` instances — one of 5 types: `decision`, `requirement`, `constraint`,
  `open_question`, `action_item` — with source attribution and timestamp
- `StalenessFlag` instances with evidence, routed to human review
- The read interface the Context Gatherer queries

## Write scope

**The Vault, as sole writer.** No other agent writes to it. **Deletions are human-gated** — the
Scribe proposes via `StalenessFlag`; a human confirms.

## Layer

**Core.** Extracting durable knowledge from run history, and keeping it honest against current
reality, is domain-independent. The Optimization adapters need it at least as much as SDLC does —
the external review's "Project State Store" is this mechanism under another name, and its governed
registers are what the Vault would hold for that domain.

Adapter-supplied nouns: what the transcripts are about, and what "contradicted by current reality"
means per entry type.

## Retention and scope

Out-of-tree and ref-pinned: each `RunManifest` commits a `vault_ref` so runs are traceable to the
Vault state they read (§3.7 decision 2). Repo-local storage was rejected because knowledge would
fragment across repos.

**Scope constraint, from the external review:** the Vault must not span clients, engagements, or
people. `InvariantScope` has the right shape and the Vault should adopt it. This is the one memory
constraint the design did not already hold, and it is load-bearing for the Optimization adapters in
a way it is not for SDLC.

## Reconciliation cadence

Event-triggered, not periodic: a `contracts/*.py` change, a companion file edit, or a run
completion. This applies Principle 10 to maintenance scheduling — a known event causes a known
action. Per-run was rejected as too expensive at scale; nightly as arbitrary relative to actual
change events.

## Context budget

Extraction passes are the largest LLM workload outside the swarm. Budget unset — it depends on
transcript volume, which nothing has measured.

## Failure modes

- **Confidently stale entries.** The worst outcome for any archive: a superseded decision retrieved
  as current is worse than no entry, because the Context Gatherer hard-includes constraints and a
  Maker will build on it. Reconciliation and `StalenessFlag` exist for this and are the least
  specified part of the design.
- **Extraction error.** A misextracted decision propagates silently into every later run. Why the
  Vault Checker is mandatory rather than advisory.
- **Unbounded growth.** Retention policy is deferred to `vault_architecture.md` and is genuinely
  unresolved. An archive with no retention rule becomes a corpus nobody can search.
