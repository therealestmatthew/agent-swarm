---
title: Agent Cards
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: shared
---

# Agent Cards

One card per agent. `agent_taxonomy.md` remains the summary and generalization layer — it owns the
6-type vocabulary and the boundaries between types; these cards own everything per-agent.

- **Schema:** `card_schema.md` — the fields every card fills in
- **Per-type specialization:** `types/` — which fields each type requires, forbids, or marks N/A
- **Enforced by:** `scripts/check_agent_cards.py`, on every commit

## The roster

25 agents: 23 in `agentic-sdlc-design-v0.5.md` §2, plus Vault Scribe and Vault Checker, both
`draft` and proposed in `agent_taxonomy.md` §3.

| Agent | Type | Layer | Pairing |
|---|---|---|---|
| [Core Orchestrator](core-orchestrator.md) | Orchestrator | `core` | — |
| [Budget Enforcer](budget-enforcer.md) | Orchestrator | `core` | — |
| [Plan Writer](plan-writer.md) | Maker | `core` | Plan Reviewer + Security Review (plan-time) |
| [Task Decomposer](task-decomposer.md) | Maker | `core` | **Contract Freeze gate only — weakest pairing in the roster** |
| [Task Dev Swarm](task-dev-swarm.md) | Maker | `shared` | Code Reviewer |
| [Test Author](test-author.md) | Maker | `adapter-sdlc` | Baseline Guard |
| [CI Cleanup](ci-cleanup.md) | Maker | `adapter-sdlc` | Code Reviewer, implicitly |
| [Plan Reviewer](plan-reviewer.md) | Checker | `core` | reviews Plan Writer |
| [Security Review (plan-time)](security-review-plan.md) | Checker | `shared` | reviews Plan Writer |
| [Code Reviewer](code-reviewer.md) | Checker | `shared` | reviews Task Dev Swarm |
| [Baseline Guard](baseline-guard.md) | Checker | `shared` | reviews Test Author |
| [Test Investigator](test-investigator.md) | Checker | `adapter-sdlc` | reviews unclassified failures |
| [PR Reviewer](pr-reviewer.md) | Checker | `adapter-sdlc` | reviews merged diff |
| [Security Reviewer (diff-time)](security-reviewer-diff.md) | Checker | `adapter-sdlc` | reviews merged diff |
| [Error Analyzer](error-analyzer.md) | Checker | `core` | reviews Log Monitor telemetry |
| [Vault Checker](vault-checker.md) | Checker | `core` | reviews Vault Scribe · *draft* |
| [Context Gatherer](context-gatherer.md) | Provider | `core` | — not gated |
| [Invariant Curator](invariant-curator.md) | Archivist | `core` | — human gate on deprecation |
| [Flake Registry](flake-registry.md) | Archivist | `adapter-sdlc` | — |
| [Vault Scribe](vault-scribe.md) | Archivist | `core` | Vault Checker · *draft* |
| [Shared-File Intent Service](shared-file-intent-service.md) | Executor | `core` | — |
| [Integrator](integrator.md) | Executor | `adapter-sdlc` | — |
| [Test Runner](test-runner.md) | Executor | `adapter-sdlc` | — |
| [Log Monitor](log-monitor.md) | Executor | `core` | — |
| [Budget Accountant](budget-accountant.md) | Executor | `core` | — gates nothing |

**By type:** 2 Orchestrators · 5 Makers · 9 Checkers · 1 Provider · 3 Archivists · 5 Executors = 25.

This matches `agent_taxonomy.md` §2's type counts and contradicts its summary line, which read "23
existing agents + 1 proposed = 24 total". The table proposes *two* agents, so 23 + 2 = 25. The type
counts were right; both summary sentences were wrong. Corrected in the taxonomy.

**By layer:** 13 `core` · 4 `shared` · 8 `adapter-sdlc`.

Slightly over half the roster is Core, which is the most direct evidence available for the
reusability claim in `core_vs_adapter.md` — and also the sharpest bound on it. The 8 adapter-SDLC
agents are not incidental: they are the entire verification spine (Test Author, Test Runner, Test
Investigator, Baseline Guard's mechanism, Flake Registry) plus integration and diff review. Any new
domain must supply its own answer to *what counts as verified* before the Core roster is of any use
to it. `optimization/charter.md` §3 gives that answer for Optimization.

## Cross-domain

The Optimization adapters' specialists use this same schema, in
[`../optimization/agents/`](../optimization/agents/). That they fit it without new fields is the
schema-neutrality check in `optimization/charter.md` — a field only SDLC agents can fill would be a
Core leak.

## Findings surfaced by writing the cards

Writing a card per agent forced questions the one-line roster never had to answer:

1. **The Task Decomposer has no independent Checker.** `ownership.disjoint` verifies slices do not
   overlap; nothing reviews whether the boundaries were drawn *well*. Since Principle 8 makes every
   downstream merge conflict a verdict on this agent, its output is the least-reviewed
   highest-leverage artifact in the pipeline.
2. **CI Cleanup's pairing is implicit**, resting on its output happening to appear in a diff someone
   else reviews.
3. **The Vault Checker has no gate ID** in §9.2, because the agent is proposed and the gate list was
   not updated with it.
4. **Two agents are hard to calibrate by the standard criterion.** The Error Analyzer's ledger fills
   only on production incidents; the Vault Checker has no natural human-override event. The
   promotion criterion in `calibration_and_measurement.md` §2 assumes a verdict volume neither will
   reach.
5. **`TestTier.execution_tier` and `ResetStrategy.strategy_type`** are closed `Literal`s in Core
   models — recorded in `core_vs_adapter.md` §6.
