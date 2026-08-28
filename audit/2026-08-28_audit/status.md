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
| 4 | C2 | not_started | — | — | — |
| 5 | C3 | not_started | — | — | — |
| 6 | C4 | not_started | — | — | — |
| 7 | H8 | not_started | — | — | — |
| 8 | H2 | not_started | — | — | — |
| 9 | H1 | not_started | — | — | — |
| 10 | H3+H4 | not_started | — | — | — |
| 11 | H5 | not_started | — | — | — |
| 12 | H7 | not_started | — | — | — |
| 13 | M1–M6 | not_started | — | — | Medium findings, internally parallelizable |

## Per-remediation detail

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
