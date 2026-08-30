---
title: Agentic Architecture Manifest
status: live
part_of: repo-meta
doc_type: manifest
layer: repo-meta
---

# Agentic Architecture Manifest

A complete inventory of every file in this repository, as of `design/plans/agentic-sdlc-design-v0.5.md`.
115 tracked files: the live design (`design/plans/`), its agent cards (`design/plans/agents/`), the two
non-software adapters (`design/plans/optimization/`), the adversarial audit (`design/audits/`), and repo tooling.
The frozen hackathon project this grew out of is no longer in this tree — see the last section.
Repo history runs 2026-08-25 to present.

**Reading this table:** *Description* is what the file literally is (form/type). *Summary* is what's
actually in it. *Purpose* is the job it does in the larger system — why it exists at all.

This file is a snapshot, not a live view — it will drift the moment a new file is added. Regenerate
it (or at least re-diff `git ls-files` against it) whenever the file set changes materially, the
same discipline `design/plans/versions/REGRESSION.md` exists to enforce for the design content itself.

---

## Root

| File | Description | Summary | Purpose |
|---|---|---|---|
| `CLAUDE.md` | Instructions file for an AI agent working in this repo | States the project's goal, the seven design principles, working agreements (schemas live in one place, thresholds stay labelled illustrative), open questions, and a file-location table | Onboards a future agent (or person) cold — the one file that must never drift out of sync with what's actually true of the repo |
| `.gitignore` | Git ignore rules | Excludes `__pycache__/`, build artifacts, and `archive/glass-box/`'s regenerable run output and demo parachute | Keeps generated/derived files out of version control without needing per-directory rules |
| `AGENTIC_ARCHITECTURE_MANIFEST.md` | This file | Full file-by-file inventory of the repository | The single index a newcomer (or an agent with no session memory) reads to know what exists before reading anything else |
| `FRONTMATTER_MANIFEST.md` | Generated Markdown, front matter present | Every tracked doc's `title`/`status`/`part_of`/`doc_type`/`version` in one table, plus per-status/per-type summary counts | Machine-checkable proof every doc has valid front matter — regenerated on every commit, never hand-edited |

---

## `scripts/` and `.githooks/` — Repo Tooling

Keeps this manifest, `FRONTMATTER_MANIFEST.md`, and every count-bearing sentence in the live docs
honest without relying on anyone remembering to update them by hand.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `scripts/frontmatter.py` | Python module, stdlib only | Minimal front-matter parser/serializer for this repo's actual schema — not a general YAML library, the same "contract is the file format" tradeoff `archive/glass-box/glassbox/events.py` made | Shared by the other two scripts so front matter is read and written exactly one way |
| `scripts/check_frontmatter.py` | Python CLI | Backfills missing front matter (title from the H1, status/part_of/doc_type from a curated table plus path-based rules, `superseded_by` recomputed from the actual version chain every run), then writes `FRONTMATTER_MANIFEST.md` | Guarantees every doc is self-describing; fails loudly on a doc with no H1 rather than guessing a title |
| `scripts/sync_counts.py` | Python CLI | A registry of every live count assertion in `design/plans/` and root docs (glossary terms/categories, tracked file count, principle/section/agent-roster counts, companion file count) and how to recompute each one, with a regex per place it's asserted in prose | Deterministically rewrites a drifted number in place — this is what caught the manifest's own "48 tracked files" going stale the moment it was committed |
| `scripts/install-hooks.sh` | Bash script | Sets `core.hooksPath` to `.githooks` and makes the hook executable | One command to activate the hook after cloning, since `.git/hooks/` isn't tracked and can't ship with the repo directly |
| `.githooks/pre-commit` | Bash hook, tracked | Runs both Python scripts on every commit across the whole repo, re-stages whatever they fix, aborts the commit with a specific message if either hits something no rule can fix deterministically | The enforcement point — without it, both scripts are just tools someone has to remember to run |

---

## `design/plans/` — Live Design (v0.5)

The current source of truth. `CLAUDE.md`'s own rule governs everything here: mechanics (thresholds,
schemas, capture rules) belong in a companion file, never inline in the core blueprint.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `agentic-sdlc-design-v0.5.md` | Core orchestration blueprint, Markdown, 12 sections | 12 principles → 23-agent roster → 8 phases → Shared-File Governance (§4.7 now distinguishes proposing-agent synchronous materialization from lazy sibling reconciliation via pre-subprocess `WorktreeSyncRequest`) → Invariant deprecation → Failure triage → Circuit breakers → Execution Isolation → Gates → Anti-Reward-Hacking → Calibration → Open Questions | The one document that states *how the pipeline is shaped*; every companion file exists to keep this one legible by holding the mechanics elsewhere |
| `design/plans/contracts/__init__.py` | Python package init, Pydantic v2 | Defines `BaseContract` (frozen + extra=forbid config) and re-exports every public model, now including the adapter-surface schemas (`WorktreeSyncRequest`, `WorktreeSyncResult`) alongside orchestration, governance, and verification, so `from plan.contracts import GateResult` works | Single canonical import namespace across the plan docs and future consumers, without giving up per-module domain ownership |
| `design/plans/contracts/adapter_surface.py` | Pydantic v2 module, frozen models | Adapter-surface verbs Core invokes on (or receives from) the adapter runtime at the process boundary: `WorktreeSyncRequest` and `WorktreeSyncResult` (the unconditional pre-subprocess shared-file reconciliation call, `execution_isolation.md` §7.6). Module is opened as the future home for further adapter-surface schemas | Keeps Core-owned adapter-runtime verbs in one place rather than accreting into `orchestration.py` (which is Core-internal) or `governance.py` (which owns the adapter contract artifacts) — separates the runtime surface from the declaration/policy contract |
| `design/plans/contracts/orchestration.py` | Pydantic v2 module, frozen models | Core Orchestrator state: `RunManifest` (now including `rejection_graph_edges`, `diff_classification`, `last_sync_hash_by_task`), `Phase`, `HaltReason`; shared-file intent submission and outcome envelope: `IntentSubmission` (wraps a Tier-1 intent with `override_semantic_collisions` for the Two-Layer Collision Model), `IntentOutcome`, `IntentRejection` (with `deadlock_cycle` and `semantic_collision` reasons plus `semantic_feedback` / `override_key` fields), `RejectionEdge`; Crash Recovery types: `RecoveryStrategy`, `RecoveryManifest`. | Core is standalone for adapter-facing types — this module does not import from `governance` or `reference_adapter/` (see `core_adapter_boundary.md` §3); it imports `DiffClassification` from the leaf `verification` module so `RunManifest` can carry the Core-computed diff label the `gate_coverage.minimum` meta-gate reads |
| `design/plans/contracts/governance.py` | Pydantic v2 module, frozen models | Adapter contract: `RepoDeclaration` (now including `trivial_path_globs` for the `gate_coverage.minimum` triviality rule and `semantic_analyzers` for the Two-Layer Collision Model) + `GovernancePolicy` (now including `max_mutex_rejections` and `max_seconds_without_sync`, the materialization-window starvation bound consumed by `execution_isolation.md` §7.7) plus every sub-model they compose (`IsolationUnit`, `Capability`, `AbsentCapabilityPolicy`, `ResetResource`, `ResetStrategy`, `TestTier`, `IntentOpSpec` (with `semantic_analyzer_ids`), `SemanticAnalyzerSpec`, `SignalSpec`, `TriageRule`, `SecretSpec`, `SecretScrubberConfig`, `EgressPayload`, `ScrubbedEgressPayload`) | Adapter contract lives in one place; the declaration/policy split (`core_adapter_boundary.md` §3) is expressed as two top-level models with shared sub-models, and runtime scrubber schemas live alongside declaration-side schemas because they share the credential-lifecycle domain |
| `design/plans/contracts/verification.py` | Pydantic v2 module, frozen models | Validator return shapes (`GateResult`, `Finding`, `GateApplicability`), diff triviality label (`DiffClassification`, consumed by `gate_coverage.minimum` — design doc §9.1), failure-triage capture (`FailureSignature`), invariant scope enum (`InvariantScope`) | Every Validator agent returns a `GateResult`; the shape lives with the other verification-layer contracts, not scattered across the pipeline |
| `design/plans/contracts/reference_adapter/__init__.py` | Python package init | Reference adapter sub-package marker; docstring names the boundary rule (Core does not import from here) | Package boundary that keeps `core_adapter_boundary.md` §3 enforceable at import time as well as in prose |
| `design/plans/contracts/reference_adapter/web_intents.py` | Pydantic v2 module, frozen models | Web-adapter Tier 1 shared-file intent vocabulary: `AddExport`, `AddRoute`, `AddProviderBinding` (additive), plus `RenameExport`, `MoveRoute`, `DeprecateExport` (structural-but-safe), united as `SharedFileIntent` | D2 resolution — repo-specific intents live in a reference adapter rather than in the universal contracts file, so a non-web adapter can declare its own vocabulary without editing Core |
| `agentic_sdlc_glossary.md` | Markdown file | 64 defined terms spanning 12 categories, from `Additive Intents` to `Zero-hit Invariant` | Formal vocabulary for the whole design set — every term used in more than one document is defined exactly once here |
| `budget_and_escalation_policy.md` | Markdown companion | Loop ceilings (`max_retries=3` per loop-back edge), the 4-rung escalation ladder (with structural-intent deadlocks, `gate_coverage.minimum` coverage-family gaps, and sync starvation from `GovernancePolicy.max_seconds_without_sync` explicitly classified as boundary-type loops that skip model escalation), Budget Accountant cost ceilings | Owns the exact thresholds `agentic-sdlc-design-v0.5.md` §7 only names in principle |
| `context_retrieval_strategy.md` | Markdown companion | Context Gatherer search heuristics (`git log -S`/blame vs. vector search, broad-then-narrow default), per-consumer token budgets, overflow handling | Owns Context Gatherer mechanics referenced but not detailed in §3 |
| `crash_recovery.md` | Markdown companion, new | Startup Reconciliation Protocol, orphan cleanup, shared/ branch integrity via `git reset --hard`, resume decision tree, no-recompute posture, phase-boundary decay rule, sync-freshness-on-resume. | Describes how Core handles resuming interrupted runs and recovering state |
| `core_adapter_boundary.md` | Markdown companion | The Core/Adapter split, the three places a naive reading of it leaks (collision predicates via the Two-Layer Collision Model, telemetry schema, triage rules), the `RepoDeclaration`/`GovernancePolicy` contract split (a field is a declaration if a false value punishes the declarer, policy if it rewards them) and its governance, capability negotiation, hydration, credential injection and egress scrubbing, and how "universal" is made falsifiable. §2.1 is the Two-Layer Collision Model: Layer 1 deterministic key match in Core, Layer 2 adapter-declared semantic analyzer sandboxed in the isolation unit, verdict scrubbed as egress, override via `IntentSubmission.override_semantic_collisions`, override loops caught by `max_mutex_rejections`. | Turns "general-purpose orchestrator" from a claim into a checkable seam — the file that keeps one repo's specifics out of the Core |
| `execution_isolation.md` | Markdown companion, new in v0.5 | One git worktree per task; why disjoint write ownership alone doesn't isolate reads; lifecycle; when containers become necessary; and (§7) shared-file materialization — canonical branch, `skip-worktree` overlay, pull-based reconciliation into siblings via unconditional pre-subprocess `WorktreeSyncRequest`, synthesized delta view, and the constraints on intent transport; §7.6 states the language-agnostic subprocess-only invariant (Materialization Window Protocol), §7.7 bounds sync starvation | Reinstates v0.1 §6, which had no home in v0.2–v0.4: verification is repo-scoped even when editing is file-scoped |
| `calibration_and_measurement.md` | Markdown companion, new in v0.5 | Verdict ledger schema, Shadow Mode promotion criteria (illustrative), agent-spec versioning, cost-per-pair tracking | Reinstates v0.1 §8 — gives Shadow Mode (Agent Roster) an actual exit path; previously "calibrated against a baseline" named a baseline that didn't exist anywhere |
| `implementation_roadmap.md` | Markdown roadmap | Critique of the submitted implementation backlog, a defects table of contradictions found between live design files, the items the backlog omitted, and a six-stage build sequence keyed to the CPMI proving ground | Turns the design set into an ordered build plan — the first document here that describes work rather than architecture, and the one that states the release condition for `CLAUDE.md`'s design-not-build gate |
| `infra_triage_matrix.md` | Markdown companion | The deterministic `FailureSignature` rules engine — ordered rule table separating infra-class failures from logic failures before any LLM sees a failure | Owns the failure-classification mechanics `agentic-sdlc-design-v0.5.md` §6 only references |
| `structural_change_runbook.md` | Markdown runbook | Three-tier structural change governance: Tier 1 intents (RenameExport, MoveRoute, DeprecateExport) auto-resolve via the Intent Service; Tier 2 changes queue for async human review without halting the run; Tier 3 (high-blast-radius) triggers the full synchronous SOP — targeted pause, human architectural review, re-decomposition | The governance framework for changes that exceed the Tier 1 vocabulary, from lightweight async review to full synchronous architectural pause |
| `test_harness_architecture.md` | Markdown companion | Baseline capture rules (tiered: fresh-instance for Tier 1/2, warm-pool in-place cleaning for Tier 3 with triage-matrix protection), Protocol-fake test double standards, diff-scoped mutation testing (new in v0.5), and (§3.9) the diff-triviality classification rule the `gate_coverage.minimum` meta-gate reads | Owns the verification-layer mechanics that make a passing test mean something |
| `adapter_onboarding.md` | Markdown companion | Progressive onboarding Levels 0–3 (ad-hoc chat → execution → state & triage → full intent & pooling), browser pool lifecycle and cost attribution, Python Web App starter template illustrating the `RepoDeclaration`/`GovernancePolicy` split | Guides a target repo from zero adapter to full tiered execution without requiring a complete schema on day one |
| `llm_output_normalization.md` | Markdown companion | Normalization layer for LLM outputs: two-pass strategy (strip extra keys, then validate), model categories (strict vs agent-produced), integration, and escalation interaction | The structural answer to `extra="forbid"` parsing failures when evaluating LLM-generated models |
| `agent_taxonomy.md` | Markdown companion, draft | The 6 agent types (Orchestrator, Maker, Checker, Provider, Archivist, Executor), the full roster mapped to them, and the proposed Vault subsystem | Names the types the blueprint implied but never assigned; the summary layer above `design/plans/agents/` |
| `core_vs_adapter.md` | Markdown, classification | Per-file, per-section and per-module Core/adapter verdicts; the restated boundary criterion quantified over task domains; the 6 closed enums that block a non-software adapter | Turns "the Core is reusable" from a claim into a table someone can argue with |
| `work_packet_contract.md` | Markdown companion | The 15 fields of a dispatch envelope — scope, approved sources as an enumerated allowlist, freshness, permissions, output schema, evidence and reviewer requirements | Names something the design specified in pieces and never in one place; a Core gap found by an external review |

---

## `design/plans/versions/` — Superseded Design History

Every prior version, kept rather than discarded, plus the analysis that compares them. Nothing here
is live guidance — `CLAUDE.md` and the live `design/plans/` files are current; this is the record of how they
got here.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `REGRESSION.md` | Markdown analysis | v0.1-to-v0.4 diff: 9 load-bearing gaps found (validator asymmetry, worktree isolation, mutation testing, the Run Manifest, calibration, permissions-not-prompts, reward-hacking framing, 5 dropped open questions, build order), each with a verified quote and a keep/reinstate/hold call | The evidence behind v0.5's changelog — catches the exact failure mode it describes: v0.2's changelog documented six additions and zero removals |
| `agentic-sdlc-design-v0.1.md` | Markdown, original design proposal | 18 principles, 18-agent roster, full detail per agent (validator asymmetry, worktree isolation, `mutation.diff_scoped`, the Run Manifest, a verdict ledger) | The most detailed version ever written; roughly half its content didn't survive to v0.2 and is being selectively reinstated as of v0.5 |
| `agentic-sdlc-design-v0.2.md` | Markdown, versioned design doc | Adds the Shared-File Intent Service (typed additive intents replacing patch-based merges), Shared-File Registration, self-expanding governance, invariant deprecation, bounded loop ceilings | First version to introduce shared-state governance as a first-class mechanism; changelog documents only additions |
| `agentic-sdlc-design-v0.3.md` | Markdown, versioned design doc | Resolves all four v0.2 open questions: conflict-count promotion threshold, `InvariantScope` enum, infra-vs-logic triage split, the Structural Change SOP | Closes out v0.2's open questions cleanly — the one version whose changelog is fully honest about what it resolved |
| `agentic-sdlc-design-v0.4.md` | Markdown, versioned design doc | Pure reorganization: relocates schemas, thresholds, and capture rules out of the blueprint into `agent_interface_contracts.py` and four new companion files, changing no content | Established the "relocate mechanics, keep the blueprint legible" convention that `design/plans/`'s current structure — and this manifest's own organization — follows |

---
## `design/plans/agents/` — Agent Cards

One card per agent, filling `card_schema.md`. `design/plans/agent_taxonomy.md` stays the summary layer and
owns the 6-type vocabulary; the cards own everything else about an individual agent.

**Deviation from this manifest's one-row-per-file rule, stated rather than silent:** the 25 agent
cards are listed collectively below rather than individually. `design/plans/agents/README.md` is itself the
per-agent index table — agent, type, layer, pairing, link — so a row each here would be a second
copy of it, and a second copy that nothing keeps in sync is exactly the drift this repo's tooling
exists to prevent. `scripts/check_agent_cards.py` enforces card-set completeness on every commit.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `README.md` | Markdown, index | The 25-agent table (type, layer, pairing), type and layer distributions, and the 5 findings that writing the cards surfaced | The entry point to the card set, and the per-agent index this manifest deliberately does not duplicate |
| `card_schema.md` | Markdown, schema | The fields every card fills — type, pairing, purpose, typed inputs/outputs, write scope as a permission, layer, and the conditional loop/gate/calibration/budget sections | One home for the card format, for the same reason `design/plans/contracts/` is one home for the schemas |
| `types/*.md` | Markdown, 6 type exemplars | One per type (Orchestrator, Maker, Checker, Provider, Archivist, Executor); each states which fields its type requires, forbids or marks N/A, plus that type's standing constraint | Keeps per-type discipline in 6 files instead of repeated across 25 cards |
| `<agent>.md` | Markdown, 25 agent cards | One per roster row, plus the draft Vault Scribe and Vault Checker. Depth scales with the agent | The specification for each agent — nothing else in the set defines one individually |

---

## `design/plans/optimization/` — The Non-Software Adapters

The Personal and Team Optimization adapters: the second and third reference adapters under
`core_adapter_boundary.md` §6.1's widened dissimilarity standard, which now includes task domain.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `charter.md` | Markdown, companion | Scope, the two-adapter split, and the three substitutions that define the adapters — isolation unit, governed artifact, oracle — plus what is deliberately not adopted from the external review | The anchor document; states what is claimed and, in §6, what explicitly is not |
| `project_state_model.md` | Markdown, companion | The 8 governed registers, the additive intent vocabulary and collision keys, the non-additive ops that exit through the Structural Change SOP, source precedence, freshness | The Team adapter's governed shared artifact — what the Intent Service writes when the domain is project delivery |
| `routing_standard.md` | Markdown, companion | Four scoring axes and a 6-rule ordered routing table, with refusal as a first-class outcome | The one genuinely new mechanism from the external review: Core routes between phases, nothing routed at the entry point |
| `delivery_pulse_runbook.md` | Markdown, runbook | The 8-step recurring status workflow, the Omission Guard, the human-attention queue, and the calibration loop through the Verdict Ledger | The first end-to-end Optimization workflow — the domain equivalent of the roadmap's Stage 3 |
| `personal_adapter.md` | Markdown, companion | The single-writer adapter and how it differs from Team; two findings — most arbitration machinery has nothing to isolate, and evidence binding is weaker where the actor is the only witness | Exists to be dissimilar: "two similar adapters prove nothing that one proves" |
| `agents/*.md` | Markdown, 5 agent cards | Evidence Retriever, Project-State Validator, Status Synthesizer, Quality Reviewer, Continuity Assistant — same schema as the SDLC cards | The schema-neutrality check: a required field only an SDLC agent could fill would be a Core leak hiding in the card format |

---

## `design/audits/2026-08-28_audit/` — Adversarial Audit

The audit report, its feedback and question responses, and 13 remediation records keyed `C1`–`C5`,
`H1`–`H8`, `M1`–`M6`, plus session trackers and prompts. A second finding register, independent of
the roadmap's `D`/`R` IDs — the two have never been reconciled against each other, which is itself
worth noting.

Listed collectively, for the same reason as the agent cards above: the records are named by their
finding ID and `status.md` already indexes them, so a row each here would be a second index nothing
keeps in sync. **These are the only two places this manifest departs from one row per file**, and
both say so.

---

## `archive/glass-box/` — Removed

**Not in this tree.** The frozen hackathon project this repo grew out of was removed in `f2ba9fe`
and is gitignored; it survives on the `archive/glass-box` branch. This section is kept as a pointer
because three documents referenced the directory as though it were present after it was deleted —
`CLAUDE.md`, this manifest, and `implementation_roadmap.md` S5-4 — and a reader following those
references needs to land somewhere rather than nowhere.

Its reusable ideas are listed in that branch's `README.md`. The flagged design gap is still the
relevant one: the board has no concept of a phase or a human gate, both of which an ops dashboard
for this pipeline would need.
