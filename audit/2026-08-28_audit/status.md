---
title: Audit v0.5 Remediation Execution Status
status: live
part_of: audit-2026-08-28
doc_type: tracker
---

# Audit v0.5 Remediation — Execution Status

Live status of the 13 remediations from the 2026-08-28 adversarial audit.
Updated as each remediation lands. See `adversarial_audit_report.md` for
the findings this remediates, `remediation_<ID>_*.md` for each fix plan,
and `followups.md` for items surfaced mid-execution.

**Branch:** `remediation/audit-v0.5-execution` (off `main`)
**Started:** 2026-08-28
**Execution model:** Orchestrator (Claude Opus 4.7) + Maker/Checker
sub-agent pairs per commit, following the design system's own principles.

## Dependency-ordered execution plan

Items at the same indent level with a `║` connector may parallelize if
they touch entirely different files.

```
1.  C5  — Phase gate clarity (CLAUDE.md, contracts decomposition)
2.  C1  — Secret scrubbing trust boundary (core_adapter_boundary.md §5)
3.  H6  — Schema validation two-pass (contracts, new validation module)
4.  C2  — Deadlock detection (design v0.5 §4.5, contracts)
5.  C3  — Gate bypass detector (design v0.5 §9, contracts)
6.  C4  — Materialization race fix (execution_isolation.md §7, design §4.7)
7.  H8  — Crash recovery (execution_isolation.md, design §3, new doc)
8.  H2  — Retry ceiling parameterization (budget_and_escalation_policy.md)
    ║
9.  H1  — Calibration metrics (calibration_and_measurement.md)
10. H3+H4 — Tiered execution & onboarding (core_adapter_boundary, harness)
11. H5  — Structural change tiers (structural_change_runbook, contracts)
12. H7  — Collision semantics (core_adapter_boundary §2.1, contracts)
13. M1–M6 — Medium findings (glossary, manifests, context, triage)
```

## Progress ledger

| # | ID | Status | Commits | Files modified | Notes |
|---|---|---|---|---|---|
| 1 | **C5** | completed | `cd34117`, `42c5ab4`, `cb53dda` | 16 (see below) | Decomposition + phase gate. Three surfaced items → `followups.md` |
| 2 | **C1** | completed | `6bacbce`, `22bad69` | 6 (see below) | Scrubber to Core, allow-list egress, credential-isolation floor. Three surfaced items → `followups.md` |
| 3 | **H6** | completed | `2c33e7d` (+ C5 scaffolding: `cd34117`, `42c5ab4`, `cb53dda`) | 4 (see below) | Normalization boundary, Core ownership, cross-refs, F5 closure. ~80% pre-seeded by C5. |
| 4 | **C2** | completed | `506ee85` | 7 (see below) | Cycle detection + threshold, task-scoped boundary failure. Two surfaced items → `followups.md` (F9, F10) |
| 5 | **C3** | completed | `fe66305` | 8 (see below) | Meta-gate `gate_coverage.minimum` for NOT_APPLICABLE bypass. Two surfaced items → `followups.md` (F9 broadened, F11 new) |
| 6 | **C4** | completed | `477a2da` | 7 (see below) | Pull-based materialization at subprocess boundaries. New `adapter_surface.py` module, subprocess-only invariant, sync-starvation timeout. One surfaced item → `followups.md` (F12) |
| 7 | H8 | not_started | — | — | — |
| 8 | H2 | not_started | — | — | — |
| 9 | H1 | not_started | — | — | — |
| 10 | H3+H4 | not_started | — | — | — |
| 11 | H5 | not_started | — | — | — |
| 12 | H7 | not_started | — | — | — |
| 13 | M1–M6 | not_started | — | — | Medium findings, internally parallelizable |

## Per-remediation detail

### C4 — Materialization race fix (completed 2026-08-28)

One commit with Maker/Checker sub-agent pair. Net: +219 / −17 across 7 files
(1 new module + 6 modifications).

- **`477a2da`** pull-based materialization: replaces the push-based
  re-materialization mechanism (`execution_isolation.md` §7.2) that raced
  against in-process module caches (`sys.modules`, `require.cache`,
  `$LOADED_FEATURES`) during test execution. Atomic POSIX rename provided
  filesystem-level atomicity but not runtime isolation. New Core-owned
  adapter-surface schema module `plan/contracts/adapter_surface.py` holds
  `WorktreeSyncRequest` and `WorktreeSyncResult` (fourth Core schema module
  alongside `orchestration.py`, `governance.py`, `verification.py`). Sync is
  idempotent by design (`was_noop=True` steady state) — event delivery is
  not a correctness dependency; no `SharedStateUpdatedEvent` introduced. New
  §7.6 in `execution_isolation.md` states the language-agnostic
  subprocess-only invariant (Python/Node/Ruby cache examples are
  parenthetical, not the rule). New §7.7 defines sync starvation semantics.
  New `GovernancePolicy.max_seconds_without_sync` field (illustrative,
  `None` means off). Boundary-type in `budget_and_escalation_policy.md`
  §2.2. `agentic-sdlc-design-v0.5.md` §4.7 revised to distinguish proposing
  agent (synchronous) from siblings (lazy pull at subprocess boundary).
  `GateApplicability`, `GateResult`, `HaltReason`, `RunManifest.*`,
  `DiffClassification`, and C1/C2/C3 fields all untouched — the pre-C5
  remediation draft would have written schemas to the deleted
  `plan/agent_interface_contracts.py`.

**Design decisions locked in during human gate:**
- **Sync trigger: unconditional pre-subprocess.** Agent's runtime calls
  `SyncWorktree()` unconditionally before every subprocess execution.
  Idempotent. Removes event-loss risk on agent crash/restart entirely; H8
  does not need to persist unseen events.
- **Schema home: new module `plan/contracts/adapter_surface.py`.** Fourth
  Core schema module for adapter-facing verbs. Deliberately opened as the
  future home for other adapter-surface schemas even though it holds one
  verb today. Must not import from `orchestration.py`, `governance.py`, or
  `reference_adapter/`.
- **Language generalization: subprocess-only, not Python-specific.** Rule
  is "target-system code MUST execute in a subprocess distinct from the
  agent's own runtime, so that materialization at the process boundary
  yields a fresh module/import cache." `sys.modules` becomes a parenthetical
  example alongside `require.cache` (Node) and `$LOADED_FEATURES` (Ruby).
- **Long-running executions: `max_seconds_without_sync` starvation
  timeout.** New `GovernancePolicy` field (illustrative, adapter-tunable,
  `None` means off). Task-scoped boundary failure via `active_task_ids`
  drop — no new `HaltReason` value. Interaction with retry ceilings: both
  may fire; whichever fires first wins.
- **§7.5 "Reads stay local" preserved.** `SyncWorktree()` is a
  Core-internal local reconciliation from the local `shared/` branch into
  the local worktree — never a wire read. A transport outage still doesn't
  break a running suite.

**Follow-ups surfaced:** F12 (sync freshness proof at other checkpoints —
`WorktreeSyncResult.source_commit_hash` docstring hints Core may use it to
prove sync freshness at other checkpoints, but no consumer is specified;
scoped to H8 since crash-recovery persistence is the natural home for
sync-freshness-at-resume).

**Downstream impact:** H8 (crash recovery) inherits an optional refinement
via F12 — whether to persist last-known `source_commit_hash` and prove sync
freshness on resume. H3+H4 (tiered execution & onboarding) may add more
verbs to `adapter_surface.py`; the module's import-discipline note
(no imports from `orchestration.py` or `governance.py`) may need revisiting
if a future verb requires capability-negotiation-style schemas. C1 §5.4's
container floor and C4 §7.6's subprocess-only rule are complementary — the
container gives Core the enforcement boundary for both egress scrubbing
and subprocess-only execution.

### C3 — NOT_APPLICABLE gate bypass detector (completed 2026-08-28)

One commit with Maker/Checker sub-agent pair. Net: +122 / −11 across 8 files.

- **`fe66305`** meta-gate `gate_coverage.minimum`: adds a Phase-6 aggregate
  check that fires when a `NON_TRIVIAL_CODE` diff produces no `APPLIED`-and-
  passed result from the coverage family (`tests.diff_covered` +
  `mutation.diff_scoped`, hard-coded). New `DiffClassification` enum in
  `plan/contracts/verification.py` (`TRIVIAL_DOCS`, `NON_TRIVIAL_CODE`);
  new `RunManifest.diff_classification` field on `plan/contracts/orchestration.py`
  (parallel to C2's `rejection_graph_edges` — task-scoped state persisted so
  H8 crash recovery cannot silently lose the classification). New
  `RepoDeclaration.trivial_path_globs` on `plan/contracts/governance.py`
  (adapter-extensible; Core defaults to `.md/.rst/.txt` allow-list). Extended
  `agentic-sdlc-design-v0.5.md` §9.1 with the meta-gate row, §10 with a new
  attack row cross-referencing the existing `mutation.diff_scoped` row
  (per-line, per-gate) vs. the new per-diff aggregate guard, Phase 6 with an
  ordering note, and §12 with a triviality-upgrade open question. New §3.9
  in `test_harness_architecture.md` defines the triviality rule and
  distinguishes from §3.6 (line-level) and §3.7 (repo-level absent
  capability), including the DEGRADE-branch interaction. Updated
  `budget_and_escalation_policy.md` §2.2 to classify coverage-family gaps
  as boundary-type, skipping escalation rung 3. Updated
  `AGENTIC_ARCHITECTURE_MANIFEST.md` row descriptions for the three
  contracts modules and the two prose docs. `GateApplicability` (3-value),
  `GateResult`, and `HaltReason` all untouched — the remediation was drafted
  pre-C5 and would have clobbered them.

**Design decisions locked in during human gate:**
- Triviality rule is illustrative extension allow-list (`.md/.rst/.txt`) +
  adapter-extensible `RepoDeclaration.trivial_path_globs`; no AST-aware
  analysis in the starting rule. §12 open question tracks the upgrade.
- `DiffClassification` enum in `verification.py`, but the field lives on
  `RunManifest` in `orchestration.py` — parallel to how C2 landed
  `rejection_graph_edges`. `GateResult` is a validator output; the
  classification is task/run metadata and does not belong there.
- `gate_coverage.minimum` FAIL is a task-scoped boundary failure via
  `active_task_ids` drop, exact mechanism from C2. No new `HaltReason`
  value.
- Coverage family is hard-coded to two gates. Expanding it requires an
  explicit edit to both the meta-gate constant AND the §9.1 row — no tag
  mechanism, no registry.
- `RunManifest.diff_classification` docstring locks in a **no-recompute**
  posture for H8: preserve on resume, do not re-derive from the diff. A
  diff mutated (or reverted) between crash and restart would silently
  reclassify the task and defeat the point of persistence.

**Follow-ups surfaced:** F9 broadened (H8 must preserve both
`rejection_graph_edges` and `diff_classification`, with C3's explicit
no-recompute posture on the latter); F11 new (design doc §2/Phase 6
should name the Core Orchestrator as the runner of `gate_coverage.minimum`
for future-reader clarity — housekeeping, not a new roster entry).

**Downstream impact:** H8 (crash recovery) picks up C3's no-recompute
requirement in addition to C2's persistence requirement, both tracked
under F9. No other remediations touched.

### C2 — Deadlock detection in Smart Mutex Rejection (completed 2026-08-28)

One commit with Maker/Checker sub-agent pair. Net: +105 / −12 across 7 files.

- **`506ee85`** deadlock detection: extended `IntentRejection.reason` with a 6th value
  `deadlock_cycle` (spec was pre-C5 and would have replaced the vocabulary — corrected at
  human gate). Added Core-only `RejectionEdge` model in `plan/contracts/orchestration.py`
  and persisted `RunManifest.rejection_graph_edges: list[RejectionEdge]` (additive,
  backward-compat, feeds H8 crash recovery). Added `GovernancePolicy.max_mutex_rejections:
  int = 3` (illustrative, adapter-tunable). Expanded `agentic-sdlc-design-v0.5.md` §4.5
  from 2 lines to cover cycle detection, per-tuple counter, task-scoped termination via
  `active_task_ids` drop, and explicit non-overlap with the SOP's slow-boil trigger.
  Updated `budget_and_escalation_policy.md` §2.2 to classify structural-intent deadlocks
  as boundary-type (skip model escalation). Sharpened `structural_change_runbook.md` §1
  trigger 5 to "non-cyclic" and added §5 "Deadlocked-intent escape hatch" for the manual
  review path over persisted rejection edges.

**Design decisions locked in during human gate:**
- Extend `IntentRejection.reason` (add `deadlock_cycle`), don't replace — spec was drafted
  before C5 and would have destroyed the post-C5 5-value vocabulary and `dict[str, str]`
  blocking_keys shape.
- Two parallel paths for repeated collisions: C2 detector handles graph cycles (fast,
  mechanical) and per-tuple counter breaches; the Structural Change SOP (`§1` trigger 5)
  handles non-cyclic slow-boil where blocking-context resolution isn't converging. Both
  paths cite each other for non-overlap.
- `max_mutex_rejections` on `GovernancePolicy` (adapter-tunable), illustrative default 3
  per CLAUDE.md convention.
- Persist `RejectionEdge`s in `RunManifest` so H8 crash recovery cannot silently lose
  detected deadlock state.
- Task-scoped boundary failure via `active_task_ids` drop; `HaltReason.BOUNDARY_FAILURE`
  reserved for cascade blockage. No new HaltReason value added.

**Follow-ups surfaced:** F9 (H8 must actually read persisted `rejection_graph_edges` on
resume), F10 (phase-boundary decay rule inferred by Maker but not locked at gate; H8 or
a design pass to confirm).

**Downstream impact:** H8 (crash recovery) inherits the requirement to integrate
`RunManifest.rejection_graph_edges` and settle the decay rule. No other remediations
touched by this change.

### H6 — Schema validation two-pass (completed 2026-08-28)

One commit for H6-specific changes; ~80% of deliverables were pre-seeded during
C5 (companion doc, schema, parsing annotations, design doc update, CLAUDE.md,
calibration metric, manifest entry). Net: +24 / −6 across 4 files.

- **`2c33e7d`** normalization boundary and cross-refs: added §2.4 to
  `core_adapter_boundary.md` (agent output normalization — inbound data-cleaning
  path, distinguished from §5 outbound credential-scrubbing). Clarified Core
  ownership of normalizer in `llm_output_normalization.md` §3. Added §6 Schema
  Defaulting Convention (F5 resolution). Fixed bidirectional cross-references
  between `core_adapter_boundary.md`, `calibration_and_measurement.md`, and
  `llm_output_normalization.md`.

**Design decisions locked in during human gate:**
- Core owns the normalizer (it's a mechanism: deterministic strip-and-log, no
  LLM calls). Adapter hands raw JSON strings to Core.
- New sub-section (§2.4) in `core_adapter_boundary.md` rather than inline reference
- F5 closed with both the existing inline comment (C5 `cd34117`) and a new §6
  schema-design convention note in `llm_output_normalization.md`

**Follow-ups resolved:** F5 (GovernancePolicy defaulting asymmetry)

**Downstream impact:** None significant — H6 was largely self-contained.
The normalization layer is referenced by later remediations only insofar as
they may produce agent-produced schemas that need parsing-discipline annotations.

### C1 — Secret scrubbing trust boundary (completed 2026-08-28)

Two commits, each with Maker/Checker sub-agent pair. Net: +142 / −15
across 6 files.

- **`6bacbce`** scaffold schemas: added `SecretScrubberConfig`,
  `EgressPayload`, `ScrubbedEgressPayload` to `plan/contracts/governance.py`
  (per user Q2 — governance already owns `SecretSpec`), re-exported from
  `plan/contracts/__init__.py`. All three inherit from `BaseContract`.
- **`22bad69`** prose: rewrote `core_adapter_boundary.md` §5 with new
  Core-side scrubbing design and a §5.3 "why the trust boundary moved"
  callout preserving the prior argument (per user Q1). Added
  `execution_isolation.md` §5.4 for credential-isolation floor (per user
  Q4). Extended manifest row. Fixed three roadmap contradictions the
  Maker surfaced (D9 L106, S0-10 L141, S4-5 L227 including stage title
  rename).

**Design decisions locked in during human gate:**
- Rewrite §5 with explicit design-change callout (not silent rewrite)
- Schemas in `plan/contracts/governance.py` (same domain as `SecretSpec`)
- Egress: **allow-list is the design**, DPI is a possible extension only
- Credential-isolation: new derivation rule alongside `ResetStrategy`,
  orthogonal source; `granted_secrets` non-empty → floors to `CONTAINER`
- Trust-boundary inversion accepted: Core-memory exposure of raw values
  for one task's duration < in-unit tamperability under adversarial agent

**Downstream impact:** H3+H4 (tiered execution + onboarding) will
touch `execution_isolation.md`; may need to consider the new §5.4 rule
in its derivation examples.

### C5 — Phase gate clarity + contracts decomposition (completed 2026-08-28)

Three commits, each with Maker/Checker sub-agent pair. Net: +730 / −603 across 16 files.

- **`cd34117`** scaffold: created `plan/contracts/` package with 4 modules by domain
  (`orchestration.py`, `governance.py`, `verification.py`,
  `reference_adapter/web_intents.py`) + `BaseContract` base class in `__init__.py`.
  Old file untouched.
- **`42c5ab4`** cross-references: 32 substitutions across 9 files, `CLAUDE.md`
  "Where things live" table row updated, "Schemas live in one place" working
  agreement rewritten per hybrid Q3 decision, 6 new rows added to
  `AGENTIC_ARCHITECTURE_MANIFEST.md`.
- **`cb53dda`** cleanup: deleted `plan/agent_interface_contracts.py`, removed its
  manifest row, rewrote `CLAUDE.md` phase-gate paragraph into a
  Permitted/Forbidden bulleted form per remediation §3.1.

**Design decisions locked in during human gate:**
- 4-module split (not the remediation's original 3-module proposal)
- Delete old file, but only after all cross-refs resolved (3-commit sequence)
- Hybrid ownership: module docstrings declare domain + `__init__.py` re-exports
- `BaseContract` base class centralizes `frozen=True, extra="forbid"`
- **Core/Adapter boundary fix:** `IntentOutcome.intent` typed as `BaseModel`
  rather than `AdditiveIntent` so `orchestration.py` doesn't import from
  `reference_adapter/`

**Downstream impact:** C2, C3, H5, H6, H7 all target contracts modules that now
exist as separate files rather than sections of a monolith.

## Session notes

- **Original driver:** Google Antigravity conversation
  `9003c0b9-9d48-4983-b68c-623522708d6b`. Hit RESOURCE_EXHAUSTED (429) right
  after user confirmed C5 dispatch. Claude Code picked up from there with full
  context reconstructed from the Antigravity DB.
- **Maker/Checker model:** Claude Code `general-purpose` sub-agents (fresh
  context each dispatch) rather than tiered Flash/Pro/Opus. Different mechanism,
  same governance principle (no agent reviews its own output).
- **Human gates so far:** 3 (C5, C1, H6 pre-dispatch design questions). Remaining
  remediations will each get their own gate.
- **H6 note:** C5's Maker sub-agents pre-seeded ~80% of H6 deliverables (companion
  doc, schema, annotations, design doc §3, CLAUDE.md, calibration §5, manifest).
  H6-specific Maker sub-agents encountered permission timeouts; remaining edits
  were applied directly by the Orchestrator and independently reviewed by a
  Checker sub-agent.
