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
| F5 | C5 commit 1 (Maker observation during scaffold) | H6 (schema validation two-pass) or a documentation pass | pending | `GovernancePolicy.absent_capability_policy` has no default while `non_hermetic_coverage_posture` defaults to `DEGRADE`. Asymmetry is defensible (top-level vs. scoped posture) but not called out in prose. Either add a docstring explanation or standardize the defaulting behavior. H6 touches the model layer and can carry this. |
| F6 | C1 commit 2 (Maker observation during prose rewrite) | Housekeeping / stylistic sweep | pending | Two references to "boundary scrubbing" survive C1 and now read ambiguously under the new design (does "boundary" mean the isolation-unit boundary or the trust boundary?): `plan/core_adapter_boundary.md:37` in the §1.1 Core-owns table and `AGENTIC_ARCHITECTURE_MANIFEST.md:66` in the row for `core_adapter_boundary.md` itself. Defensible as-is but a sweep to "egress scrubbing" would align both with the new §5 header ("Credential injection and egress scrubbing"). |
| F7 | C1 remediation §5 open questions | Deferred to build phase (needs binary-format investigation) | pending | Binary artifact redaction strategy is unresolved: how do we safely scrub binary files (images, PDFs, HAR attachments) without corrupting them? Either strictly forbid binary exfiltration while credentials are active, or rely on filename/metadata scrubbing only. Design docs currently note this via `EgressPayload.content` field comment (base64/hex for binary), but the actual scrubbing pass strategy is unwritten. Belongs with concrete scrubber implementation in build phase. |
| F8 | C1 remediation §5 open questions | Deferred to build phase (needs OS-level memory-wipe primitives) | pending | Core memory lifecycle for `SecretScrubberConfig` is unwritten. Holding raw credential values in Python string memory means values survive garbage collection until the memory is reused; a Core memory dump could expose them even after the task ends. Options: explicit `mlock`/wipe via `ctypes`, use of a keyring/vault process that returns opaque handles, or acceptance of the risk under container process boundaries. Depends on the deployment posture, not on any specific remediation. |

## How to update this file

When starting a remediation, scan for items marked `pending` whose "Scope
for resolution" matches. Flip them to `in-scope` and note the remediation
in the Description or a new column if it helps.

When an item resolves in a commit, change status to `resolved` and append
the commit hash and one-line summary to the Description.

When a new item is discovered mid-remediation, add a new row with the
next `F<n>` ID. Prefer specificity over brevity — future readers won't
have the surrounding conversation context.
