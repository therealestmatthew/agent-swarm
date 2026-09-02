---
title: Context Gatherer
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Context Gatherer

## Type

Provider. The only one in the SDLC roster.

## Pairing

None — not gated. Its output reaches Makers without passing a `GateResult`, which is a deliberate
cost trade and the reason its overflow behaviour is specified so tightly below.

## Purpose

Assembles the targeted context window each agent receives, per stage. It exists because
minimal-context orchestration (Principle 2) only works if something is responsible for deciding what
"minimal" contains — otherwise every agent defensively requests everything and context rot returns
through the back door.

## Inputs

- The consuming agent's identity and stage
- A retrieval query
- The invariant manifest (always, regardless of query)
- The Vault read interface, once the Vault Scribe exists (`agent_taxonomy.md` §3.6)

## Outputs

- An assembled context window, within the consumer's token budget
- An explicit overflow warning when the budget cannot hold what was judged relevant

## Write scope

None — read-only.

## Layer

**Core.** `context_retrieval_strategy.md` §1.1 distinguishes retrieval modes by *question type* —
exact-target provenance versus conceptual similarity — and that distinction holds for a wiki, a CRM,
or an email archive as readily as for a repo.

Adapter-supplied nouns: the corpora and the provenance mechanism. `git log -S` and `git blame` are
one domain's answer to "what happened to this specific thing"; a records system answers it with a
revision history. The retrieval *order* is Core; the commands are adapter data.

## Context budget

This agent owns the budget rather than merely respecting one. Per-consumer tiers, ranked by symbol
overlap, recency, and invariant relevance.

**Invariants are hard-included regardless of score.** They are *"correctness constraints, not
optional context, and shouldn't be droppable by a ranking algorithm."* Subjecting them to the same
ranking as ordinary material would be a bug, not a tuning choice.

## Retrieval order

Once the Vault exists: Vault query (exact, structured) → vector search (semantic) → git history
(provenance). The Vault goes first because a resolved prior decision is cheaper and more reliable
than re-deriving it from source.

## Failure modes

- **Silent truncation — the primary risk.** Non-top-K material is compressed to one-line digests
  rather than dropped, and overflow raises an explicit warning. Dropping silently creates *"the
  illusion of complete coverage"*: a Maker cannot ask for what it does not know is missing, and
  nothing downstream will catch the omission because no gate sees this output.
- **Over-retrieval.** The opposite failure, and the cheaper one — it costs tokens and dilutes
  attention rather than producing a confidently wrong artifact.
- **Stale Vault entries.** Mitigated by the Vault Scribe's reconciliation passes, not by this agent.
  The Gatherer trusts the read interface; guarding it is the Archivist's job.
