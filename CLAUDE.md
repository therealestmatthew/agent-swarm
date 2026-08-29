---
title: Agentic SDLC Orchestration
status: live
part_of: repo-meta
doc_type: guide
layer: repo-meta
---

# Agentic SDLC Orchestration

## What we're trying to accomplish

**A specified, governed pipeline of AI agents that takes a change from plan to production, where
every generated artifact is checked by a different agent than produced it.**

The thesis is that agent pipelines fail in predictable ways — context rot, merge conflicts on
"disjoint" work, infinite adversarial loops, unbounded spend, silent truncation — and that each of
those has a structural answer rather than a prompt-engineering one. The design encodes those
answers.

**The first adapter is software delivery; it is not the only one.** The pipeline is a
general-purpose orchestrator with a universal Core and per-domain adapters
(`plan/core_adapter_boundary.md`). Two non-software adapters — **Personal** and **Team
Optimization** — are being designed alongside it (`plan/optimization/charter.md`), not because the
domain is the point but because `core_adapter_boundary.md` §6 is right that *"one adapter does not
demonstrate an abstraction."* A dissimilar adapter is the falsification test, and a non-software one
is the strongest available.

Before assuming any mechanism generalizes, read `plan/core_vs_adapter.md`. It classifies every
document, schema module and agent as Core, adapter, or shared — and records six closed enums in Core
that block a non-software adapter as currently written.

**We are in the structural design phase.** `plan/` is the source of truth and the current work is refining it.
- **Permitted:** Defining, refining, and modularizing Pydantic schemas, system contracts, glossary definitions, and interface boundaries. Schema relocation is design.
- **Forbidden:** Implementing agent logic, service execution code, internal pipeline routing logic, or API integrations. Do not build application logic until the design settles and this phase gate changes.

## Where things live

| Path | What it is |
|---|---|
| `plan/agentic-sdlc-design-v0.5.md` | The orchestration blueprint — principles, agent roster, the eight phases. **Read first.** |
| `plan/contracts/` | Every schema exchanged between agents, organized by domain (`orchestration.py`, `governance.py`, `verification.py`, `reference_adapter/`). Single source of truth. |
| `plan/implementation_roadmap.md` | Design → build sequence: backlog critique, cross-file defects found, and the six stages. **Read second.** |
| `plan/core_adapter_boundary.md` | The universal Core vs. the per-repo Adapter Layer — the `RepoDeclaration`/`GovernancePolicy` contract split and its governance, capability negotiation, hydration, credentials |
| `plan/infra_triage_matrix.md` | The deterministic failure-classification rules engine |
| `plan/test_harness_architecture.md` | Baseline capture, Protocol-fake test double standards, diff-scoped mutation testing |
| `plan/context_retrieval_strategy.md` | Context Gatherer search heuristics and token budgets |
| `plan/budget_and_escalation_policy.md` | Loop ceilings, the escalation ladder, cost ceilings |
| `plan/crash_recovery.md` | Startup Reconciliation Protocol, orphan cleanup, shared/ branch integrity, resume decision tree |
| `plan/structural_change_runbook.md` | Human-gated SOP for non-additive shared-file changes |
| `plan/execution_isolation.md` | Why disjoint write ownership alone doesn't isolate reads; one worktree per task; shared-file materialization (§7) |
| `plan/calibration_and_measurement.md` | Verdict ledger, Shadow Mode promotion criteria, agent-spec versioning |
| `plan/llm_output_normalization.md` | The two-pass strip-then-validate layer between LLM JSON and `extra="forbid"` models |
| `plan/adapter_onboarding.md` | Progressive Level 0–3 onboarding for a target repo, and the starter declaration template |
| `plan/work_packet_contract.md` | What exactly one agent receives when dispatched — scope, approved sources, permissions, evidence and reviewer requirements |
| `plan/agent_taxonomy.md` | The 6 agent types, the full roster mapped to them, and the proposed Vault subsystem. Summary layer above `plan/agents/` |
| `plan/agents/` | **One card per agent** — 25 of them, plus `card_schema.md` and a per-type exemplar in `types/`. Enforced by `scripts/check_agent_cards.py` |
| `plan/core_vs_adapter.md` | Which documents, schemas and agents are reusable Core vs. SDLC-only. **Read before assuming a mechanism generalizes.** |
| `plan/optimization/` | The Personal and Team Optimization adapters — the non-software domains, their governed registers, routing standard, and the Delivery Pulse runbook |
| `plan/agentic_sdlc_glossary.md` | Term definitions used across the set — 64 terms, with Category and Tags columns |
| `plan/versions/` | Superseded design versions (v0.1–v0.4) and `REGRESSION.md`, the analysis behind v0.5 |
| `audit/2026-08-28_audit/` | The adversarial audit and its 13 remediation records, keyed `C1`–`C5`, `H1`–`H8`, `M1`–`M6`. A second finding register, separate from the roadmap's `D`/`R` IDs |
| `AGENTIC_ARCHITECTURE_MANIFEST.md` | Every tracked file in the repo, one row each — description, summary, purpose. A snapshot: re-check it against `git ls-files` after any file is added or removed. |
| `FRONTMATTER_MANIFEST.md` | **Generated.** Every Markdown file's front matter in one table. Regenerated by `scripts/check_frontmatter.py` — don't hand-edit. |
| `scripts/` | `check_frontmatter.py` (front matter backfill + manifest), `sync_counts.py` (fixes drifted counts in place), `check_agent_cards.py` (roster ↔ taxonomy ↔ card agreement), `frontmatter.py` (shared parser), `install-hooks.sh` |
| `.githooks/pre-commit` | Runs all three scripts on every commit; re-stages anything they fix. Activate once with `scripts/install-hooks.sh`. |

The blueprint deliberately splits mechanics out into companion files. Keep that split: if a
threshold, schema, or capture rule is being written into the core document, it belongs in a
companion instead. v0.5 added two companions (`execution_isolation.md`,
`calibration_and_measurement.md`) for exactly this reason rather than growing §1's principle text.
The set now holds 13 SDLC companion files, not five.

## Principles that shape every decision

These are the design's own, condensed. When a proposal conflicts with one of these, the principle
wins unless the proposal argues explicitly for changing it.

1. **Maker/Checker.** Every agent that generates an artifact is paired with a different agent that
   validates it. No agent reviews its own output.
2. **Deterministic before LLM.** Anything classifiable from structured signals is classified by a
   fixed rules engine; an LLM sees only the ambiguous residue. Applies to failure triage and to
   shared-file intents alike.
3. **Shared state is governed, not merged.** Registered shared files change only through a closed
   vocabulary of typed additive intents, applied by a deterministic service. Anything non-additive
   exits through the Structural Change SOP.
4. **Merge conflicts are decomposition errors.** A conflict is evidence the Task Decomposer drew
   boundaries wrong — never something the PR Reviewer resolves, and never an infinite retry.
5. **Every loop is bounded.** Repeated failure signals a problem upstream of the current step, so
   retrying indefinitely spends budget without addressing the cause.
6. **Human gates at irreversible or judgment-heavy points**, and they are not delegable to an agent:
   plan approval, Contract Freeze, shared-file registration and promotion, invariant deprecation,
   structural changes, QA→Prod.
7. **Nothing fails silently.** Explicit `GateResult` verdicts, context overflow warnings rather than
   truncation, ceiling halts that never auto-resume, anti-deletion checks on the test suite.

## Working agreements

- **Docs before build.** The current phase is plan refinement. Changes land as design edits, not
  code.
- **Schemas live in `plan/contracts/`.** The package is the single home for a schema, organized by domain: `orchestration.py` for Core state, `governance.py` for the adapter contract, `verification.py` for validator outputs, `reference_adapter/` for concrete adapter vocabulary. Each module's docstring names its scope so a new schema has an obvious home. `plan/contracts/__init__.py` re-exports every public model, so consumers can import canonically from the top level (`from plan.contracts import GateResult`) even though the definition lives in `verification.py`. Two agents inventing two slightly different shapes for one thing is the drift the whole shared-file design exists to prevent — don't reintroduce it at the type level.
- **Pydantic v2, `extra="forbid"`, `frozen=True`** on every model. Agents produce new instances
  rather than mutating shared state. Agent-produced models (Validator outputs, additive intents) are routed through the normalization layer (`plan/llm_output_normalization.md`) which strips and logs hallucinated extra fields before strict validation. Core-internal models are instantiated directly. Each contract module's docstring declares its parsing discipline.
- **Say what's unresolved.** Several thresholds in the set are explicitly illustrative
  (cost ceilings, context budgets, the additive-intent threshold, decay tuning). Don't present them
  as decided, and don't quietly harden one without saying so.
- **Don't assert what you haven't run.** Carried over from the archived project, where two review
  passes found claims the code didn't support.
- **Every Markdown file carries YAML front matter** (`title`, `status`, `part_of`, `doc_type`,
  `layer`, and `version`/`superseded_by` where relevant). `scripts/check_frontmatter.py` backfills
  it and regenerates `FRONTMATTER_MANIFEST.md`; it runs on every commit, so a new doc with no front
  matter gets it added automatically rather than merged without it.
- **`layer` says which side of the Core/Adapter boundary a doc sits on** — `core`, `adapter-sdlc`,
  `adapter-personal`, `adapter-team`, `shared`, or `repo-meta`. It records the file's *dominant*
  classification; section-level detail lives in `plan/core_vs_adapter.md` §4, which is authoritative
  where the two disagree. Adding a value means adding it to `scripts/frontmatter.py:LAYERS`, not
  just writing it — an unrecognized value is reported, never silently dropped.
- **An agent is specified on its card, not in prose.** `plan/agents/<agent>.md`, filling
  `plan/agents/card_schema.md`. `plan/agent_taxonomy.md` stays authoritative for the 6-type
  vocabulary; the card owns everything else about that agent.
  `scripts/check_agent_cards.py` fails the commit if the roster, the taxonomy, and the cards
  disagree.
- **A count that can drift is written as a digit, never spelled out** ("7 companion files", not
  "seven") — that's the signal `scripts/sync_counts.py` uses to find and fix it. Adding a new
  count assertion means adding it to that script's `REGISTRY`, not just writing the number.

## Open questions

Tracked in `plan/agentic-sdlc-design-v0.5.md` §12, and live:

- **Enterprise invariant arbitration** — who arbitrates when two repos disagree about whether an
  `enterprise_wide` invariant still holds. Carried unresolved since v0.3.
- **Decay tuning** — the −1-per-clean-phase conflict counter decay is untested against real
  promotion data.
- **Structural Change SOP cadence** — repeated triggering against one file may itself be a
  governance signal.
- **Modular file versioning** — now 13 companion files, not five. Do they version independently
  of the blueprint?
- **Closed enums are the next declared leak** — six `Enum`/`Literal` constructs in Core cannot be
  extended by an adapter (`plan/core_vs_adapter.md` §6, roadmap D23/D24). The rule was learned for
  fields and never generalized to enums, so each schema growth reintroduces it.
- **Should `Phase` be adapter-declared?** `Phase.DECOMPOSITION_TDD` bakes one methodology into the
  universal enum — but a fully declared phase sequence moves flow control into repo-declared data,
  which is what Principle 2 keeps Core.
- **Does the conformance kit need a domain-neutrality case?** Without one it certifies portability
  across repositories only, which is the gap `core_adapter_boundary.md` §6.1 names.
- **Calibrating a Checker with no natural override event** — the Error Analyzer and Vault Checker
  will not reach the verdict volume `calibration_and_measurement.md` §2 assumes.
- **Four more, carried forward from v0.1 and dropped without resolution at v0.2** (task granularity,
  Plan Writer dialogue depth, run manifest location, secrets posture) — see §12 for the full
  restatement of each. The fifth, **concurrency ceiling**, is answered in
  `plan/core_adapter_boundary.md` §3.6: a repo declares its per-isolation-unit resource footprint,
  Core clamps it against policy and divides, then takes the minimum against the API rate limit and
  review throughput — so which constraint binds is a fact about a run rather than a discovery when
  the machine starts swapping.

`plan/implementation_roadmap.md` §3 carries the live register of findings against this set —
including the ones already resolved into it (the Core/Adapter split, the declaration/policy
contract, shared-file materialization, the intent-outcome schema, the budget enforcement split) and
the ones still open, with §8.3 naming which file each will change when it is decided. Read it before
opening a new question against the design, in case it is already recorded there.

Both items previously tracked here as drift were resolved in v0.5: the stale `v0.3.md` references in
`infra_triage_matrix.md` and `structural_change_runbook.md` now point at `v0.5.md`, and
`infra_triage_matrix.md`'s stale "not yet finalized" note on baseline capture now correctly points at
`test_harness_architecture.md` §1.

**v0.5 is a reinstatement pass, not new design.** `plan/versions/REGRESSION.md` found that v0.2's
changelog documented six additions and zero removals, though roughly half of v0.1's content didn't
survive. Five of the nine gaps it found are now reinstated (validator asymmetry, permissions over
prompts, the Run Manifest, execution isolation, calibration) — read that file before assuming
anything is missing from the live set by design rather than by accident.

## Deliberately out of scope, for now

- **Visualization.** The archived Glass Box board made a running swarm watchable and won the
  hackathon, but it is not part of this design. It may return as an **agent health and monitoring
  dashboard** once the pipeline is real. If it does, the reusable parts are listed in
  `README.md` on the `archive/glass-box` branch (the directory was removed from this tree in
  `f2ba9fe` and is gitignored) — and note that the board has no concept of a phase or a human
  gate, which an ops dashboard for this pipeline would need.
