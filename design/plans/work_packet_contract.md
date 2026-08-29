---
title: Work Packet Contract
status: draft
part_of: agentic-sdlc
doc_type: companion
layer: core
---

# Work Packet Contract

**Referenced by:** `core_vs_adapter.md` · `agents/card_schema.md` ·
`optimization/routing_standard.md`

## Purpose

What exactly one agent receives when it is dispatched.

The design specifies this in pieces and never in one place: `context_retrieval_strategy.md` §2.1
owns the token budget, `RepoDeclaration` owns execution facts, `SecretSpec.scope` owns credential
scope, `GovernancePolicy` owns what is permitted. No artifact says "here is the dispatch envelope,
these are its fields." That gap was found by an external review of this design, and it is a real
one: an agent's card can state its inputs, but nothing states the *shape* every dispatch shares.

This is Core, not Optimization. The gap exists for the SDLC pipeline too — it simply went unnoticed
because there is only one adapter, and with one adapter the envelope and its contents are
indistinguishable.

## The fields

| Field | Purpose | Source |
|---|---|---|
| `packet_id` | Identity, for the event log and the ledger | Core |
| `run_id`, `task_id` | Provenance back to the `RunManifest` | Core |
| `agent` | Which agent this is for | Core |
| `purpose` | What this dispatch is to accomplish | Orchestrator |
| `scope` | The isolation unit: worktree ref, or snapshot + record-ID lease | Adapter |
| `approved_sources` | What may be read. **An enumerated allowlist, not a starting point** | Adapter + policy |
| `freshness_threshold` | Beyond which a source is stale and cannot be cited | Policy |
| `read_permissions` | Enforced by the dispatch path, not by instruction | Policy |
| `write_scope` | Almost always empty — agents emit intents | Policy |
| `output_schema` | The contract model the output validates against | Core |
| `evidence_requirement` | Whether claims must carry an `evidence_ref` | Policy |
| `reviewer` | Which Checker gates this output, or explicitly none | Core |
| `escalation_rule` | On missing or conflicting information | Policy |
| `context_budget` | Token ceiling and hard-include set | Core |
| `spec_version` | The agent spec that produced it, for the ledger | Core |

## Why the fields split by owner

The same discriminating test that separates `RepoDeclaration` from `GovernancePolicy`
(`core_adapter_boundary.md` §3.1) applies here:

> A field is a declaration if a false value punishes the declarer. It is policy if a false value
> rewards them.

`scope` is a declaration — an adapter that declares too small a scope breaks its own agent.
`read_permissions` and `write_scope` are policy: an agent granted broader access than it needs is
rewarded by it, so the grant cannot come from the thing being granted access.

`approved_sources` is the field most likely to be got wrong. It must be an **enumerated allowlist**,
not a hint. "These are relevant sources" and "these are the only readable sources" differ by exactly
the property that makes Principle 12 work.

## Relationship to existing schemas

Not a new schema so much as a name for an existing envelope. `packet_id` / `run_id` / `task_id` /
`spec_version` are Core fields already tracked; `context_budget` restates
`context_retrieval_strategy.md` §2.1; `output_schema` names what the normalization layer
(`llm_output_normalization.md` §1) validates against.

When it becomes a Pydantic model it belongs in `contracts/orchestration.py`, `frozen=True`,
`extra="forbid"`, like everything else.

## Deliberately not fields

- **The prompt.** Same reason it is not on an agent card: prompts version independently and are
  calibration data.
- **Credential values.** Names and scopes only. Values never appear in a manifest, never on a
  worktree filesystem, and never pass through an agent's context (`core_adapter_boundary.md` §5).
- **Other agents' in-flight work.** `execution_isolation.md` §7.3: isolated from in-progress work,
  deliberately not isolated from governed shared state.

## Open

- **Whether `evidence_requirement` is a boolean or a policy object.** In SDLC it is nearly always
  on. In Optimization it is the whole verification story (`optimization/charter.md` §3.3), and may
  need per-claim-type granularity. Unresolved.
- **Where the packet is persisted.** The run manifest location question (§12) has been open since
  v0.1 and this inherits it rather than answering it.
