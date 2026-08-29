---
title: Invariant Curator
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Invariant Curator

## Type

Archivist.

## Pairing

None currently. Deprecation proposals go to a human gate rather than to a Checker — which is the
stronger control, since invariant removal is irreversible in practice.

## Purpose

Maintains the manifest of architectural constraints that every Maker must respect, scoped
`repo_local` or `enterprise_wide`. It exists so that constraints outlive the run that discovered
them; an invariant nobody records is re-litigated every time it is encountered.

## Inputs

- Human-registered constraints
- Zero-hit telemetry — invariants no rule has matched within a defined window
- Current structural state, for reconciliation

## Outputs

- The invariant manifest, consumed by the Context Gatherer and hard-included in every window
- Deprecation proposals for zero-hit invariants

## Write scope

The invariant manifest, as sole writer. **Deletions are human-gated** — the Curator proposes,
a human confirms. Never autonomous.

## Layer

**Core.** Every domain has constraints that must survive the session that produced them, and the
asymmetry — cheap to add, human-gated to remove — is domain-independent.

Adapter-supplied nouns: what an invariant constrains, and what "zero-hit" is measured over.

## Retention and scope

Scoped by `InvariantScope`: `REPO_LOCAL` or `ENTERPRISE_WIDE`. Nothing else. In the Optimization
adapters this scope field is load-bearing in a way it is not here — it is the mechanism preventing
cross-project memory (`types/archivist.md`), which the external review correctly identified as the
one memory constraint the design did not already hold.

## Failure modes

- **Zero-hit does not mean obsolete.** An invariant may go unhit because the constraint is being
  respected — the success case looks identical to the dead case. This is why deprecation is a
  proposal to a human rather than an automatic sweep, and why the window is a tuning parameter
  nobody has calibrated.
- **Enterprise invariant arbitration — unresolved.** When two repos disagree about whether an
  `enterprise_wide` invariant still holds, the design does not say who decides. Carried since v0.3
  (§12).

## Planned convergence

`agent_taxonomy.md` §3.7 decision 4 has this agent becoming a specialized Vault write client in
v0.6, writing invariants as `constraint`-typed `VaultEntry` records with Curator-specific fields
preserved. The reasoning is the design's own: two parallel Archivist stores risk exactly the schema
drift the shared-file design was built to prevent, and the Context Gatherer should query one store
rather than two.
