---
title: Audit v0.5 Remediation Follow-ups
status: live
part_of: audit-2026-08-28
doc_type: tracker
---

# Audit v0.5 Remediation — Follow-up Items

Items surfaced while executing the 13 remediations that were out of the
current remediation's scope but need resolution later. Each item is
tracked from **pending** → **in-scope** (when the remediation that will
resolve it is being executed) → **resolved** (with the commit hash).

Add a new row for each item discovered. Don't retire an item until its
resolution has landed.

## Status legend

- **pending** — surfaced, awaiting the remediation that will address it
- **in-scope** — the remediation currently executing is expected to close it
- **resolved** — closed by a commit, with hash and commit message reference
- **deferred** — knowingly kicked past the 13-remediation series (needs a
  new tracking home)

## Items

| ID | Surfaced in | Scope for resolution | Status | Description |
|---|---|---|---|---|
| F1 | C5 commit 2 | H2 or a dedicated prose reconciliation pass | pending | `plan/budget_and_escalation_policy.md:74` and `plan/agentic-sdlc-design-v0.5.md` (near Principle 7 area) cite `GovernancePolicy.budget_ceilings`, but no such field exists on `GovernancePolicy` in `plan/contracts/governance.py`. Actual budget-adjacent fields: `max_resource_footprint_mb`, `concurrency_cap`, `model_tier_allowlist`, `non_hermetic_coverage_posture`, `max_baseline_diff_rate`, `max_mutants_per_task`. Either the prose is drifted (rename/replace references) or the schema needs the field added. H2 (retry ceilings) touches `budget_and_escalation_policy.md` and is a natural home; alternatively spin a dedicated micro-pass. |
| F2 | C5 commit 2 | Housekeeping (independent of any remediation) | pending | `plan/implementation_roadmap.md:96` still marks D2 as `**Load-bearing**`. C5 is exactly the "Stage 0 relocation" that D2's Resolution text called for; D2 is effectively resolved by this remediation. Update the Status column to `Resolved` and note the resolving commit. |
| F3 | C5 commit 1 (Maker observation during scaffold) | Structural Change SOP (invokes `structural_change_runbook.md`) | pending | `FailureSignature` (in `plan/contracts/verification.py`) still hard-codes `dom_state_diff_from_baseline: bool` and `network_calls_over_threshold: int` — adapter-specific signals sitting in the universal envelope. The current comment already notes these should be relocated into the `signals` dict via the SOP. Relocation is a non-additive schema change and requires the runbook. Not blocking any specific remediation, but worth queueing once the C-series is done. |
| F4 | C5 commit 1 (Maker observation during scaffold) | Deferred to build phase (needs a `model_validator`) | pending | `RepoDeclaration.image_ref` "required when `isolation_unit` is `CONTAINER`" is documented in a comment but not enforced by a `model_validator`. Cross-field invariant is prose-only. Belongs with build-phase validation hardening, not design work. |
| F5 | C5 commit 1 (Maker observation during scaffold) | H6 (schema validation two-pass) or a documentation pass | resolved | `GovernancePolicy.absent_capability_policy` has no default while `non_hermetic_coverage_posture` defaults to `DEGRADE`. Asymmetry is defensible (top-level vs. scoped posture) but not called out in prose. Either add a docstring explanation or standardize the defaulting behavior. H6 touches the model layer and can carry this. Resolved: inline comment at governance.py L309 (C5 commit `cd34117`) documents the rationale. Schema defaulting convention note added to `llm_output_normalization.md` §6. |
| F6 | C1 commit 2 (Maker observation during prose rewrite) | Housekeeping / stylistic sweep | pending | Two references to "boundary scrubbing" survive C1 and now read ambiguously under the new design (does "boundary" mean the isolation-unit boundary or the trust boundary?): `plan/core_adapter_boundary.md:37` in the §1.1 Core-owns table and `AGENTIC_ARCHITECTURE_MANIFEST.md:66` in the row for `core_adapter_boundary.md` itself. Defensible as-is but a sweep to "egress scrubbing" would align both with the new §5 header ("Credential injection and egress scrubbing"). |
| F7 | C1 remediation §5 open questions | Deferred to build phase (needs binary-format investigation) | pending | Binary artifact redaction strategy is unresolved: how do we safely scrub binary files (images, PDFs, HAR attachments) without corrupting them? Either strictly forbid binary exfiltration while credentials are active, or rely on filename/metadata scrubbing only. Design docs currently note this via `EgressPayload.content` field comment (base64/hex for binary), but the actual scrubbing pass strategy is unwritten. Belongs with concrete scrubber implementation in build phase. |
| F8 | C1 remediation §5 open questions | Deferred to build phase (needs OS-level memory-wipe primitives) | pending | Core memory lifecycle for `SecretScrubberConfig` is unwritten. Holding raw credential values in Python string memory means values survive garbage collection until the memory is reused; a Core memory dump could expose them even after the task ends. Options: explicit `mlock`/wipe via `ctypes`, use of a keyring/vault process that returns opaque handles, or acceptance of the risk under container process boundaries. Depends on the deployment posture, not on any specific remediation. |
| F9 | C2 Checker cross-cutting note; broadened by C3 Checker | H8 (crash recovery) | pending | Persisted `RunManifest` state added by C2 and C3 must actually be **read** on resume, not just written. C2 added `RunManifest.rejection_graph_edges` (deadlock cycle evidence — cite `agentic-sdlc-design-v0.5.md` §4.5 and `plan/contracts/orchestration.py` `RejectionEdge` docstring). C3 added `RunManifest.diff_classification` with an explicit **no-recompute** posture — H8 must preserve this value across resume and MUST NOT re-derive it from the diff, because a diff mutated (or reverted) between crash and restart would silently reclassify the task and defeat the point of persistence (cite `plan/contracts/orchestration.py` `RunManifest.diff_classification` docstring and `plan/test_harness_architecture.md` §3.9). Whoever executes H8 must define snapshot/restore semantics for both fields; without it, both persistences become dead metadata. |
| F10 | C2 Maker observation (design deviation) | H8 or a design pass touching §4.5 | pending | C2's §4.5 paragraph 3 inferred a phase-boundary decay rule for `RejectionEdge` staleness ("edges older than a phase boundary are stale evidence") that was NOT locked in at the C2 human gate. Reasonable default but worth confirming — alternatives include time-based decay (parallel to §4.6's per-clean-phase −1 counter decay) or no decay at all. Belongs with H8 since crash recovery decides whether persisted edges cross a resume boundary as fresh or stale. |
| F11 | C3 Maker observation | Housekeeping (design doc §2 clarification, independent of any remediation) | pending | The new `gate_coverage.minimum` meta-gate is a deterministic Core-owned gate (like `budget.within_ceiling`), consuming other `GateResult`s rather than producing one from an agent. `plan/agentic-sdlc-design-v0.5.md` §9.1 lists it, but §2 Agent Roster and Phase 6 prose don't explicitly assign it a runner — presumably the Core Orchestrator, matching the other deterministic middleware gates. A one-line clarification in §9.1's row or in Phase 6 prose naming the runner would remove the ambiguity for future readers. Not a new roster entry; a naming pass. |
| F12 | C4 Maker observation | H8 (crash recovery) | pending | `WorktreeSyncResult.source_commit_hash` (in `plan/contracts/adapter_surface.py`) is documented as a hash Core "can later use to prove sync freshness at other checkpoints," but no consumer is specified in C4. The natural consumer is H8 crash recovery: on resume, comparing the last-persisted `source_commit_hash` per active task against the current `shared/` branch head would tell Core which worktrees need reconciliation before Phase resumption. Requires deciding whether to add a `RunManifest.last_sync_hash_by_task: dict[str, str]` field (or equivalent), and defining the reconciliation semantics on resume (unconditional sync of all active tasks vs. only those whose persisted hash differs). Not blocking C4; C4's schema shape supports either resolution. |

## How to update this file

When starting a remediation, scan for items marked `pending` whose "Scope
for resolution" matches. Flip them to `in-scope` and note the remediation
in the Description or a new column if it helps.

When an item resolves in a commit, change status to `resolved` and append
the commit hash and one-line summary to the Description.

When a new item is discovered mid-remediation, add a new row with the
next `F<n>` ID. Prefer specificity over brevity — future readers won't
have the surrounding conversation context.
