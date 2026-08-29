---
title: Archivist (Agent Type)
status: live
part_of: agentic-sdlc
doc_type: agent-type
layer: core
---

# Archivist (Agent Type)

**Cards of this type:** `invariant-curator.md` · `flake-registry.md` · `vault-scribe.md`

## Definition

> Maintains persistent, cross-run knowledge. Reads unstructured or semi-structured inputs,
> extracts structured knowledge, stores it durably, and keeps it synchronized with current reality.
> The institutional memory of the pipeline.
>
> — `agent_taxonomy.md` §1.5

## The type that governs memory

This is the type where "agent memory" — the thing most multi-agent systems leave implicit and
unbounded — is made explicit and governed. Two constraints define it, and both are on every card:

**Deletions are human-gated.** An Archivist proposes removal via a `StalenessFlag`; a human
confirms. Never autonomous. An archive that can quietly forget is worse than no archive, because
downstream consumers cannot tell the difference between "this was never recorded" and "this was
dropped."

**The Archivist owns the integrity of what it stores.** It is responsible for detecting when an
entry no longer reflects reality and surfacing it, not merely for writing it once. An unmaintained
store degrades into confidently-stated stale facts, which is worse than an empty one.

## Field discipline

| Section | Required? | Notes |
|---|---|---|
| Type | **Required** | |
| Pairing | **Conditional** | Required where extraction is a judgment call. The Vault Scribe is paired with the Vault Checker for exactly this reason |
| Purpose | **Required** | |
| Inputs | **Required** | Including what it reads for reconciliation |
| Outputs | **Required** | Durable entries + `StalenessFlag`s + a read interface |
| Write scope | **Required** | **Sole-writer status must be stated explicitly** where it holds |
| Layer | **Required** | |
| Loop and escalation | **Optional** | |
| Gates | **Conditional** | Only where paired with a Checker |
| Calibration posture | **N/A** | Unless the paired Checker gates |
| Context budget | **Required** | Where extraction uses an LLM |
| Failure modes | **Required** | Must cover staleness and extraction error |
| Retention and scope | **Required, this type only** | What persists, for how long, and **what it must never span** |

## Why `Retention and scope` is a required section here

The external review that prompted the Optimization adapters raised one constraint the design did not
already hold: **no cross-project memory**. It is a real gap. `InvariantScope` already has the right
shape (`REPO_LOCAL` / `ENTERPRISE_WIDE`), but nothing obliged an Archivist to declare its scope.

Now every Archivist card states what its store must never span — across clients, projects, or
people. An archive whose scope is undeclared will be scoped by accident, and the accident is only
discovered when something leaks.

## Boundary against Executor

The Flake Registry is a static registry maintained by a deterministic rules-supplement, yet it is an
Archivist rather than an Executor because its *primary output* is a durable knowledge record — known
flaky test IDs — not a state change in operational infrastructure. If it were ever extended to
actively reconcile against test history, that character would become more pronounced, not less.
