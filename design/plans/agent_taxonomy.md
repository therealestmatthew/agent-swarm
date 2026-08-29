---
title: Agent Taxonomy
status: draft
part_of: agentic-sdlc
doc_type: companion
layer: shared
---

# Agent Taxonomy

**Referenced by:** `agentic-sdlc-design-v0.5.md` §2 (Agent Roster) — intended addition once adopted.

**Status:** New companion. Formalizes the 6-type taxonomy implied but never named in the blueprint,
adds the Vault Scribe as the first dedicated Archivist agent, and proposes 3 follow-on companions
to fully specify the memory subsystem.

## Purpose

The blueprint's agent roster names roles and describes behaviors but never assigns a formal *type*.
Without a taxonomy, two problems emerge: new agents have no self-evident home, and the Maker/Checker
principle — the design's first and most load-bearing rule — is only half-named. The other half (the
types that are neither Maker nor Checker) have no vocabulary.

This companion assigns every agent exactly one type. The discriminating question is: **what is the
agent's primary output, and who or what consumes it?** That question produces 6 mutually exclusive
types. Adding a new agent to the roster means answering that question, not making a judgment call.

A secondary motivation: the 22-agent roster has no dedicated memory agent. Memory concerns are
currently distributed across 7 narrow, domain-specific structures (see §4.1). This companion names
that gap and defines the Vault Scribe to fill it.

---

## §1 — The Six Types

### 1.1 Orchestrator

> Controls flow, dispatches agents, and enforces gates and spending ceilings. Produces routing
> decisions and phase transitions. Never produces domain artifacts. Minimal context by design.
> Predominantly or wholly deterministic — LLM is not in the critical path.

**Hallmarks:**
- Output = next-phase routing decision or `HaltReason`
- Consumes structured state (`RunManifest`, event log ref) rather than artifact content
- No artifact review; no `GateResult`

**Boundary note — Orchestrator vs. Executor:** An Orchestrator decides *what happens next*; an
Executor *makes it happen*. The Core Orchestrator reads `RunManifest` and emits the next phase; the
Integrator performs the merge. Both are deterministic, but their outputs differ in kind.

### 1.2 Maker

> Produces a first-draft domain artifact from context. Output is reviewed by a paired Checker.
> "Maker" is the explicit first half of the design's Maker/Checker principle (Principle 1).

**Hallmarks:**
- Output = a reviewable artifact: plan document, task specification, test file, source diff,
  formatted diff
- Always paired with at least 1 Checker
- Works from context assembled by a Provider; does not retrieve its own context

**Boundary note — Maker vs. Provider:** The Context Gatherer produces context *for* Makers but
its output is not itself reviewed by a Checker — it is consumed directly, not gated. A Maker's
output is always gated.

### 1.3 Checker

> Reviews a Maker's artifact against stated criteria. Produces a `GateResult` with a `Finding`
> list. May gate phase progression or operate in Shadow Mode during calibration. The explicit second
> half of the Maker/Checker principle.

**Hallmarks:**
- Output = `GateResult` (`verification.py`)
- Never reviews its own output (Principle 1)
- May loop back to the paired Maker (bounded by loop ceilings; see `budget_and_escalation_policy.md`)
- Shadow Mode agents gate nothing until calibrated (see `calibration_and_measurement.md`)

**Boundary note — Checker vs. Executor:** Error Analyzer and Baseline Guard produce `GateResult`
instances reviewing a Maker's work; Log Monitor and Test Runner emit raw telemetry for others to
consume. The former are Checkers; the latter are Executors.

### 1.4 Provider

> Assembles, retrieves, and delivers targeted context or data to other agents on demand. Does not
> produce domain artifacts and is not itself reviewed by a Checker. The supply chain for Makers and
> Checkers.

**Hallmarks:**
- Output = context bundles, search results, assembled token windows
- Consumed by Makers and Checkers; not consumed directly by humans
- No `GateResult`; no artifact review

**Boundary note — Provider vs. Archivist:** A Provider assembles context for an immediate
consumer in a single phase. An Archivist writes knowledge durably across runs so it can be queried
later. The Vault Scribe is an Archivist; the Context Gatherer (which *queries* the Vault on the
Archivist's read interface) is a Provider.

### 1.5 Archivist

> Maintains persistent, cross-run knowledge. Reads unstructured or semi-structured inputs
> (transcripts, verdicts, registries), extracts structured knowledge, stores it durably, and keeps
> it synchronized with current reality. The institutional memory of the pipeline.

**Hallmarks:**
- Output = durable, queryable knowledge — not consumed immediately by one caller in one phase
- Operates across runs, not within a single phase
- Owns the integrity of what it stores: detects and flags staleness for human review
- Deletions are human-gated; the Archivist proposes but never unilaterally removes

**Boundary note — Archivist vs. Executor:** The Flake Registry is listed as a static registry
maintained by a deterministic rules-supplement. It is an Archivist rather than an Executor because
its *primary output* is a durable knowledge record (known-flaky test IDs), not a state change in
the pipeline's operational infrastructure. If the registry is ever extended to actively reconcile
against test history, that character becomes more pronounced.

### 1.6 Executor

> Performs deterministic, non-LLM operations on artifacts or infrastructure. Does not make judgment
> calls. Output is a state change — a merged branch, an applied intent, a test result, a structured
> telemetry event — rather than a finding or artifact.

**Hallmarks:**
- Output = operational state change or structured signal
- LLM not in the critical path; rule-based or algorithmic
- Does not produce `GateResult`; does not review Maker artifacts

**Boundary note — Budget Accountant:** Emits advisory `Finding`s but explicitly "gates nothing"
and is "advisory only." It observes spend telemetry rather than reviewing a Maker's artifact.
Executor is the correct type. If a future version adds a predictive LLM pass, reconsider.

---

## §2 — Full Roster Mapped to Types

23 existing agents + 2 proposed = **25 total**.

**Per-agent detail lives in `plan/agents/`**, one card per row of this table. This file stays
authoritative for the *type vocabulary* and the boundaries between types; the cards are
authoritative for everything else about an individual agent. `scripts/check_agent_cards.py` enforces
that every card's declared type matches this table.

> **Corrected.** This line previously read "23 existing agents + 1 proposed = **24 total**", which
> contradicted the type counts below (they sum to 25) and undercounted the proposals — the table
> proposes *two* agents, Vault Scribe and Vault Checker. Writing the 25 cards surfaced the
> discrepancy. The type counts were right; both summary figures were wrong.

| Agent | Type | Notes |
|---|---|---|
| Core Orchestrator | Orchestrator | |
| Budget Enforcer | Orchestrator | |
| Plan Writer | Maker | Paired with Plan Reviewer |
| Task Decomposer | Maker | Paired with implicit structural review; owns Structural Change SOP |
| Test Author | Maker | Paired with Baseline Guard |
| Task Dev Swarm | Maker | Paired with Code Reviewer; emits shared-file intents rather than direct edits |
| CI Cleanup | Maker | Lint/format pass; reviewed implicitly by Code Reviewer |
| Plan Reviewer | Checker | Paired with Plan Writer |
| Security Review (plan-time) | Checker | Paired with Plan Writer at plan-approval gate |
| Code Reviewer | Checker | Paired with Task Dev; Shadow Mode during calibration |
| Baseline Guard | Checker | Paired with Test Author; anti-deletion enforcement |
| Test Investigator | Checker | Judgment fallback for ambiguous `FailureSignature`; paired with Test Runner output |
| PR Reviewer | Checker | Paired with merged diff (synthesized Task Dev output) |
| Security Reviewer (diff-time) | Checker | Paired with PR diff |
| Error Analyzer | Checker | Paired with Log Monitor telemetry |
| Context Gatherer | Provider | Assembles context windows; sole consumer of Vault read interface |
| Invariant Curator | Archivist | Architectural invariants only; scoped `repo_local`/`enterprise_wide` |
| Flake Registry | Archivist | Known-flaky test IDs; supplemented by triage matrix |
| **Vault Scribe** | **Archivist** | **Proposed — see §3; sole Vault writer** |
| **Vault Checker** | **Checker** | **Proposed — Maker/Checker pair with Vault Scribe; validates extraction batches before Vault commit** |
| Integrator | Executor | Deterministic merge; No-Conflict Gate; conflict counter increment |
| Test Runner | Executor | Runs test suite; captures `FailureSignature`; does not classify |
| Shared-File Intent Service | Executor | Applies typed additive intents; sole writer of canonical `shared/` branch |
| Log Monitor | Executor | Always-on; emits structured telemetry; does not classify |
| Budget Accountant | Executor | Advisory `Finding`s only; gates nothing |

**Type counts:** 2 Orchestrators · 5 Makers · 9 Checkers (incl. Vault Checker) · 1 Provider · 3
Archivists (incl. Vault Scribe) · 5 Executors = 25 total

---

## §3 — Vault Scribe

### 3.1 The Vault

The **Vault** is the centralized, durable knowledge archive for the pipeline. It is a structured
store of decisions, requirements, architectural constraints, open questions, and resolved action
items — persistent across runs, repos, and agent generations. The Vault is the institutional memory
that allows a new run to start informed rather than cold.

The Vault is not the RunManifest (per-run operational state), not the Event Log (audit trail of
orchestration decisions), not the Verdict Ledger (validator accuracy data), and not the Intent Log
(shared-file governance history). Those stores remain separate. The Vault *reads from* them during
Vault Scribe processing passes; it does not absorb or replace them.

### 3.2 Purpose

The Vault Scribe:

1. **Processes** agent transcripts, `GateResult` records, human override notes, and resolved
   `Finding`s to extract structured knowledge
2. **Writes** extracted knowledge to the Vault in canonical, typed form
3. **Reconciles** Vault contents against current repo state (code, schemas, docs) to detect and
   flag entries that may no longer reflect reality
4. **Surfaces** stale or contradicted entries to humans for review — never auto-deletes

### 3.3 Entry Types

Each Vault entry is one of 5 types:

| Type | Meaning |
|---|---|
| `decision` | A resolved design or policy choice with rationale and the run/session that produced it |
| `requirement` | A stated functional or non-functional requirement, with source |
| `constraint` | A technical, organizational, or regulatory constraint that limits the solution space |
| `open_question` | An unresolved question with the context needed to answer it |
| `action_item` | A concrete next step assigned to a human or deferred to a future session |

### 3.4 Inputs and Outputs

**Inputs:**
- Agent transcripts (raw or summarized)
- `GateResult` records from the Verdict Ledger
- Human override notes from any human gate
- Resolved `Finding`s from any Checker
- Current repo state (code, schemas, companion files) — for reconciliation passes

**Outputs:**
- `VaultEntry` instances (typed, with source attribution and timestamp)
- `StalenessFlag` instances with evidence, routed to human review queue
- Read interface for Context Gatherer to query relevant prior decisions and constraints

### 3.5 Governance Boundaries

- **Sole writer:** Vault Scribe only. No other agent writes to the Vault directly.
- **Primary reader:** Context Gatherer, via the Vault's query interface. Human operators may also
  read directly.
- **Deletions:** Human-gated, never autonomous. Consistent with the Equivalent-Mutant Registry
  and Invariant Curator deprecation rules. The Vault Scribe may propose deletion via
  `StalenessFlag`; a human confirms.
- **Scope of the Invariant Curator:** The Invariant Curator remains a parallel Archivist scoped
  to architectural invariants. Its entries are a strict subset of what conceptually belongs in the
  Vault. Long-term convergence (Invariant Curator as a specialized Vault write client) is an open
  question tracked in §4.

### 3.6 Relationship to Existing Agents

**Context Gatherer → Vault:** When assembling context for Plan Writer or Task Decomposer, the
Context Gatherer queries the Vault for relevant prior decisions and constraints before falling back
to vector search and `git log -S`. This extends the existing retrieval priority order in
`context_retrieval_strategy.md` with a new first step: Vault query (exact, structured) → vector
search (semantic) → git history (provenance).

**Verdict Ledger → Vault Scribe:** The Vault Scribe reads calibration insights from the Verdict
Ledger as input to extraction passes. The Verdict Ledger's data store is owned by the calibration
subsystem (`calibration_and_measurement.md`); the Vault Scribe does not write to it.

### 3.7 Resolved Decisions

These were open questions; all 4 were resolved in the same session that produced this file.

1. **Extraction fidelity — Checker required.** The Vault Scribe's transcript → `VaultEntry`
   extraction step is a Maker operation and must be paired with a Checker (a separate Vault Checker
   agent) before entries land in the Vault. This creates a Maker/Checker pair within the Archivist
   subsystem. Exempting the Vault Scribe from Principle 1 would create a privileged carve-out from
   the design's most load-bearing rule and leave the Vault's integrity unguarded.
2. **Vault location — out-of-tree, ref-pinned.** The Vault lives in a dedicated store outside
   any single repo. Each `RunManifest` commits a `vault_ref` pointer (analogous to
   `event_log_ref`) so runs are traceable to the Vault state they read. Consistent with how the
   Event Log is handled. Repo-local storage was rejected because knowledge would fragment across
   repos and cross-repo decisions would require manual reconciliation.
3. **Staleness reconciliation cadence — event-triggered.** Reconciliation fires on specific
   signals: a `contracts/*.py` change, a companion file edit, or a run completion. This applies
   Principle 2 (Deterministic before LLM) to maintenance scheduling — a known event causes a
   known action. Per-run was rejected as too expensive at scale; nightly was rejected as arbitrary
   relative to actual change events.
4. **Invariant Curator convergence — merge in v0.6.** The Invariant Curator will become a
   specialized Vault write client in v0.6, writing invariants into the Vault through a
   `constraint`-typed `VaultEntry` with Curator-specific fields preserved (scope, zero-hit window,
   deprecation state). Two parallel Archivist stores risk the same schema drift the shared-file
   design was built to prevent. Context Gatherer will query 1 store, not 2.

---

## §4 — Proposed Companion Files for the Archivist Layer

The Vault Scribe definition in §3 is intentionally high-level. 3 follow-on files are needed to
fully specify the memory subsystem before any schema or implementation work begins. None of these
files exist yet.

### `plan/vault_architecture.md`

The structural specification of the Vault store itself. Should cover:

- **Entry types and schemas** — formal definition of the 5 `VaultEntry` types, their required
  fields, and what makes an entry well-formed
- **Storage format and location** — resolution of open question §3.7 #2; likely out-of-tree with
  a reference pointer committed to the repo (analogous to `RunManifest.event_log_ref`)
- **Query interface spec** — what the Context Gatherer can ask the Vault, in what form, and what
  the Vault returns; token-budget implications for context assembly
- **Staleness reconciliation** — what triggers a reconciliation pass, what "stale" means per entry
  type (a `decision` can be contradicted by a later schema change; a `constraint` can expire), and
  how `StalenessFlag` instances surface to the human review queue
- **Retention and deletion policy** — human-gated deletion workflow; whether entries are hard-deleted
  or soft-archived; relationship to the Equivalent-Mutant Registry's human-sign requirement
- **Relationship to existing stores** — explicit statement of what the Vault reads from (Verdict
  Ledger, Event Log, Intent Log) and what it does not absorb

### `plan/archivist_agents.md`

Agent-level specifications for the 2 Archivist agents that interact with the Vault. Should cover:

- **Vault Scribe agent spec** — extraction discipline (prompt posture, what counts as each entry
  type, how ambiguous or compound extractions are handled), trigger conditions (event-triggered per
  §3.7 decision #3)
- **Vault Checker agent spec** — the Checker paired with the Vault Scribe's extraction step
  (§3.7 decision #1); what it validates (type correctness, source attribution, no duplicate of
  existing entry), and its own loop ceiling
- **Invariant Curator agent spec** — current behavior formalized; v0.6 migration path to Vault
  write client (§3.7 decision #4), including the `constraint`-typed `VaultEntry` field requirements
  that must preserve Curator-specific fields
- **Reconciliation agent** — if staleness reconciliation is complex enough to warrant a separate
  agent rather than a Vault Scribe mode, that agent is defined here; otherwise the Vault Scribe's
  reconciliation mode is fully specified here
- **Cadence and trigger policy** — resolution of open question §3.7 #3

### `plan/contracts/memory.py`

Pydantic v2 schemas for the Vault subsystem. Should define:

- `VaultEntryType` — enum of the 5 entry types
- `VaultEntry` — the canonical unit of storage: type, body, source attribution (agent/session/run
  that produced it), timestamp, optional supersedes ref
- `VaultQuery` — what Context Gatherer sends to the Vault's read interface: query text, entry
  types filter, max-results, token budget
- `StalenessFlag` — what the Vault Scribe emits when an entry may no longer reflect reality:
  entry ref, evidence (repo artifact or schema version that contradicts it), proposed action
- `ExtractionResult` — what a single Vault Scribe extraction pass returns: list of `VaultEntry`
  candidates, list of `StalenessFlag` candidates, source attribution

Follows existing contract conventions: `extra="forbid"`, `frozen=True` on every model, module
docstring naming scope. Re-exported from `plan/contracts/__init__.py` so consumers import from
the top level (`from plan.contracts import VaultEntry`).
