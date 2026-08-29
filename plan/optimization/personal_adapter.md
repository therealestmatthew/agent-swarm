---
title: Personal Optimization Adapter
status: draft
part_of: optimization
doc_type: companion
layer: adapter-personal
---

# Personal Optimization Adapter

**Referenced by:** `charter.md` §2 · `core_adapter_boundary.md` §6

The third adapter. Its purpose in the set is as much methodological as functional: it is
deliberately unlike both others, so that three adapters test the Core rather than one testing it
twice.

## 1. Why it must be dissimilar

`core_adapter_boundary.md` §6: *"Two similar adapters prove nothing that one proves."* A Personal
adapter that was Team-with-fewer-users would add no evidence. The differences below are the point,
not incidental.

| | SDLC | Team | **Personal** |
|---|---|---|---|
| Concurrent writers | Many | Several | **One** |
| Approval chain | Reviewers + gates | Project lead | **None — the owner is the approver** |
| Audience | The team | Stakeholders | **Nobody** |
| Cadence | Per change | Weekly | **Continuous and irregular** |
| Oracle | Test suite | Evidence binding | **Evidence binding, weaker** |
| Isolation pressure | High | Moderate | **Near zero** |

## 2. What one writer does to the design

This is the interesting result: **most of the Core's machinery has nothing to isolate here.**

With a single writer there are no concurrent intents, so no collisions, so `intent.no_collision`
can never fire. Disjoint write ownership is trivially satisfied. Merge conflicts cannot occur, so
Principle 8 has nothing to detect. The Shared-File Intent Service still applies every change — the
mechanism is unchanged — but its arbitration half is dead weight.

Two readings, and the adapter does not pretend to know which is right:

1. **The governance is genuinely unnecessary here**, and Personal Optimization should run at
   onboarding Level 1–2 (`charter.md` §5) rather than Level 3. Cheaper, and honest about what the
   domain needs.
2. **The governance is doing something the concurrency framing obscures** — an additive-only
   vocabulary with a human gate on revision is a commitment device, not only a concurrency control.
   For goals and habits, being unable to quietly rewrite yesterday's commitment may be the single
   most valuable property.

Reading 2 is the more interesting claim and the less supported one. It is stated as a hypothesis
this adapter exists to test, not as a design rationale.

## 3. Registers

Deliberately fewer than Team's eight:

| Register | Holds |
|---|---|
| `goals` | Outcomes, with a horizon |
| `commitments` | Things promised, to self or others, with a due date |
| `habits` | Recurring intentions and their observance record |
| `notes` | Captured material, the candidate source for the above |
| `sources` | What may be cited |

No `stakeholders`, no `raid`, no `meetings`. An adapter that declared registers it never populates
would weaken the conformance evidence rather than strengthen it — the declaration is supposed to
describe the domain, not flatter the Core.

## 4. Isolation unit

A snapshot-pinned read view, and no write lease — with one writer there is nothing to lease
against.

This is a real test of `core_adapter_boundary.md` §3.6's concurrency derivation: the arithmetic
should yield 1 and the machinery should accept that without a special case. If Core requires a
lease to function, the lease is load-bearing in a way the design does not admit, and that is a
finding worth having.

## 5. Verification, and why it is weaker here

Evidence binding still applies: a claim about a commitment must resolve to a `commitments` record.

But the Team adapter's strongest check does not transfer. `claims.all_bound` is powerful there
because registers are maintained by *several* people, so citing them is citing something
independently maintained. Here the same person writes the records and the claims, so evidence
binding proves internal consistency rather than correspondence to anything outside.

**Stated plainly rather than glossed:** verification in the Personal adapter is materially weaker
than in either other adapter, and no mechanism in the current design closes that gap. A domain where
the actor is also the only witness may simply not support a strong oracle.

## 6. Cross-project memory

The constraint from `charter.md` §4 binds hardest here. A Personal adapter accumulating durable
knowledge about one individual is the most sensitive store in the whole design, and the one where
"scoped by accident" would be least visible.

Required: the Vault instance is scoped to the individual and never spans people. Per
`../agents/types/archivist.md`, the Archivist card must declare it.

## 7. Status

**Draft, and the least developed of the three adapters.** No agent roster, no workflow runbook, no
declared intent vocabulary. What exists is the dissimilarity argument in §1 and the two findings in
§2 and §5 — which is what this adapter is currently for.
