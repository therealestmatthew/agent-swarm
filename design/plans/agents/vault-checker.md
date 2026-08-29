---
title: Vault Checker
status: draft
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Vault Checker

**Status: draft — proposed agent, not in the blueprint §2 roster.** Defined in
`agent_taxonomy.md` §3.7 decision 1.

## Type

Checker.

## Pairing

Reviews the **Vault Scribe**'s extraction batches before they commit to the Vault.

## Purpose

Validates extracted entries so that Principle 1 holds inside the Archivist subsystem too. Its
existence is an argument as much as a function: the alternative — trusting the Scribe's extraction
because it is "just" memory — would carve an exception into the design's most load-bearing rule at
precisely the point where errors are least visible, since a bad Vault entry surfaces as a confident
wrong answer several runs later.

## Inputs

- An `ExtractionResult` — candidate `VaultEntry` list and `StalenessFlag` list
- Existing Vault entries, for duplicate detection

**Never** the Scribe's extraction rationale (Principle 11).

## Outputs

- `GateResult` with `Finding` list, gating the batch's commit

## Write scope

None. It approves batches; the Scribe remains the Vault's sole writer.

## Layer

**Core.** Validating that extracted knowledge is well-typed, attributed, and non-duplicative is
domain-independent.

## Loop and escalation

Loops back to the Vault Scribe, `max_retries=3`, competence-type. On exhaustion the batch is held
rather than committed — an unvalidated batch does not enter the Vault by default, because the
default has to be the safe one for a store nothing downstream re-checks.

## Gates

Produces a Vault-commit gate. **Not yet assigned a gate ID in §9.2** — noted as a gap, since this
agent is proposed rather than adopted.

## Calibration posture

Shadow initially, like every new Checker. But the promotion signal is weak: there is no natural
human-override event on a Vault commit the way there is at the plan-approval gate, so precision must
be measured by sampling rather than by overrides. Unresolved, and stated as such.

## What it validates

1. **Type correctness** — the entry is genuinely one of the 5 types, not a compound forced into one.
2. **Source attribution** — every entry traces to the run, session, or agent that produced it. An
   unattributed entry cannot be re-examined when it is later contradicted.
3. **Non-duplication** — the entry does not restate an existing one. Duplicate decisions with
   different wording are how a knowledge store becomes self-contradicting.

## Failure modes

- **Approving a plausible misextraction.** The hardest case: an entry that is well-typed, properly
  attributed, and wrong. Type-checking cannot catch it, and nothing downstream will.
- **Duplicate detection at scale.** Comparing each candidate against the whole Vault gets expensive
  as it grows. No approach is specified; `vault_architecture.md` owns it.
