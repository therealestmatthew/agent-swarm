---
title: Agent Card Schema
status: live
part_of: agentic-sdlc
doc_type: card-schema
layer: core
---

# Agent Card Schema

**Referenced by:** every file in `design/plans/agents/` and `design/plans/optimization/agents/` ·
`agent_taxonomy.md` §2 · enforced by `scripts/check_agent_cards.py`

## Purpose

`agent_taxonomy.md` assigns every agent a type and draws the boundaries between types. It does not
specify any individual agent — before these cards, no agent in the roster had a stated input
contract, write scope, loop ceiling, or failure behaviour anywhere. The roster table gave each agent
one line of role prose.

A card is the specification for one agent. This file is the schema every card fills in, held in one
place for the same reason `design/plans/contracts/` holds the schemas in one place: two cards inventing two
slightly different shapes for "what this agent may write" is the drift the whole design exists to
prevent, reintroduced at the documentation layer.

**Per-type specialization** — which fields are required, forbidden, or not applicable for a given
type — lives in `design/plans/agents/types/<type>.md`, not here and not repeated on 30 cards.

---

## 1. Front matter

```yaml
title:    <Agent Name>          # exactly as it appears in the roster
status:   live | draft
part_of:  agentic-sdlc | optimization
doc_type: agent-card
layer:    core | adapter-sdlc | adapter-personal | adapter-team | shared
```

`layer` is the per-agent Core-vs-adapter verdict, and it is the card's job to carry it —
`core_vs_adapter.md` classifies documents and contract modules, not agents. One home per fact.

---

## 2. Required sections

### `## Type`

One of the 6 types in `agent_taxonomy.md` §1. Exactly one — the types are mutually exclusive by
construction, and an agent that seems to need two is a decomposition error in the roster, not a
card that needs a second type.

### `## Pairing`

Which agent checks this one's output, or whose output this one checks (Principle 1). Every Maker
names at least one Checker; every Checker names what it reviews. **A Maker with no Checker is a
Principle 1 violation and the card must not paper over it** — say so plainly and register it as a
finding.

Orchestrators, Providers and Executors state `None — not a Maker/Checker pair` and say why, so the
absence reads as a decision rather than an omission.

### `## Purpose`

Two to four sentences. What this agent is for, and the failure it exists to prevent. Not a restated
role line.

### `## Inputs`

Typed where a type exists — cite the model and module (`GateResult`, `contracts/verification.py`).
Where an input has no schema yet, say `unschematized` rather than inventing one; inventing a shape
here is exactly how two agents end up with two shapes for one thing.

### `## Outputs`

Same discipline. State what consumes the output.

### `## Write scope`

What this agent may modify, **stated as a permission rather than an instruction** (Principle 12).
The test: if the only thing stopping the agent from writing outside this scope is that its prompt
asked it not to, the scope is not enforced and the card should say so.

Most agents' honest answer is `None — emits intents, writes nothing`. That is the design working:
agents propose typed changes and one deterministic service applies them.

### `## Layer`

`core`, `adapter-*`, or `shared`, with one paragraph of justification against the criterion in
`core_vs_adapter.md` §1: *would this be wrong in the same way for every task domain?*

For a `core` agent, also state **adapter-supplied nouns** — what an adapter must declare before this
agent can run at all. A Core agent with no adapter-supplied nouns is either genuinely universal or
insufficiently examined, and the card should say which.

---

## 3. Conditional sections

Required for some types, forbidden for others. The type exemplars in `types/` say which.

### `## Loop and escalation`

The retry ceiling on this agent's loop, the on-exhaustion action, and — load-bearing — whether the
loop is **competence-type** or **boundary-type** (`budget_and_escalation_policy.md` §2.2).

A competence-type failure may be answered by escalating model tier. A boundary-type failure may
not: a merge conflict is evidence of a decomposition error, not evidence the current model reasoned
poorly, so escalating the tier spends budget without addressing the cause. Getting this field wrong
produces exactly the runaway the ceilings exist to stop.

### `## Gates`

Gate IDs this agent produces or is gated by, from `agentic-sdlc-design-v0.5.md` §9. Checkers
produce `GateResult`s; Makers are gated by them.

### `## Calibration posture`

`Shadow` or `Gating`, and the promotion criterion (`calibration_and_measurement.md` §2). A Checker
that has never been calibrated gates nothing, by default and on purpose.

### `## Context budget`

The per-consumer token budget and what gets hard-included regardless of ranking
(`context_retrieval_strategy.md` §2.1–2.2). Required for any agent with an LLM in its critical
path; meaningless for a deterministic one.

### `## Failure modes`

What goes wrong specifically with this agent, and what the system does about it. Not generic risk
prose — a failure mode nobody can act on does not belong on a card.

---

## 4. Rules the cards are checked against

Enforced by `scripts/check_agent_cards.py` on every commit:

1. Every roster row in `agentic-sdlc-design-v0.5.md` §2 has exactly one card.
2. Every card maps to a roster row. A card for an agent nobody dispatches is dead documentation.
3. Every card's `## Type` matches its type in `agent_taxonomy.md` §2. Three files disagreeing about
   one agent's type is the drift this check exists to catch.
4. Every card declares `layer` in front matter, from `frontmatter.LAYERS`.
5. Every card has all sections §2 marks required.

Rule 3 is why the taxonomy stays authoritative for types even though the cards are authoritative
for everything else. Types are a closed vocabulary; per-agent detail is not.

---

## 5. Deliberately not on a card

- **Prompt text.** A card specifies an agent's contract, not its wording. Prompts version
  independently and are calibration data (`reviewer_spec_version` in `GateResult`); binding them
  into a design doc would make every prompt tweak a design change.
- **Model tier.** Set by policy (`GovernancePolicy.model_tier_allowlist`) and moved by the
  escalation ladder at runtime. A tier written on a card would be stale on contact.
- **Cost estimates.** They belong in the verdict ledger where they are measured, not in prose where
  they are guessed.
