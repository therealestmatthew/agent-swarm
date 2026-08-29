---
title: H8 Remediation Handoff
status: live
part_of: audit
doc_type: handoff
layer: adapter-sdlc
---

# H8 Remediation — Handoff Summary

**Status:** Human gate cleared, Maker not yet dispatched. Ready for next agent to pick up.

## Approved design decisions (from user answers)

1. **Workspace:** Switch to main repo (`/code/agent-swarm/agent-swarm/`) with absolute paths; commit to `remediation/audit-v0.5-execution`. Leave `agent-taxonomy` worktree untouched.
2. **Schema home:** Extend `plan/contracts/orchestration.py` with `RecoveryStrategy` enum + `RecoveryManifest` model (parallel to how `RunManifest`, `RejectionEdge`, `diff_classification` land there). No new module.
3. **Prose shape:** New companion `plan/crash_recovery.md`. `execution_isolation.md` and `agentic-sdlc-design-v0.5.md` §3 get pointer paragraphs only.
4. **Followups:** Resolve F9 + F10 + F12 in this remediation.

## Files to modify (Maker's job)

| File | Change |
|---|---|
| `plan/contracts/orchestration.py` | Add `RecoveryStrategy` enum, `RecoveryManifest` model, `RunManifest.last_sync_hash_by_task: dict[str, str] = {}` field (F12) |
| `plan/contracts/__init__.py` | Re-export new symbols in imports + `__all__` |
| `plan/crash_recovery.md` (new) | Startup Reconciliation Protocol, orphan cleanup, shared/ branch integrity via `git reset --hard`, resume decision tree, no-recompute posture for `diff_classification` (F9), phase-boundary decay rule for `RejectionEdge` (F10), sync-freshness-on-resume via `source_commit_hash` (F12). YAML frontmatter required. |
| `plan/execution_isolation.md` | Pointer paragraph in §4 (worktree lifecycle) + §5 (container labeling with `run_id` for orphan detection) → new companion. Update §7.2's shared/ branch semantics to reference the crash reset protocol. |
| `plan/agentic-sdlc-design-v0.5.md` | §3 gains "Step 0: Startup Reconciliation" pointer paragraph. §4.5 gains phase-boundary decay rule for `RejectionEdge` (F10). §12 open questions updated. |
| `plan/budget_and_escalation_policy.md` | §3 clarifies that `CEILING_HALT` guarantees "Preserve and Resume" branch. |
| `AGENTIC_ARCHITECTURE_MANIFEST.md` | New row for `plan/crash_recovery.md`. Update orchestration.py row description. |
| `CLAUDE.md` | Add `crash_recovery.md` to "Where things live" table. Update companion count if referenced (check `scripts/sync_counts.py` REGISTRY). |
| `audit/2026-08-28_audit/followups.md` | Mark F9, F10, F12 as `in-scope` (Orchestrator's job before dispatch, then `resolved` post-commit). |
| `audit/2026-08-28_audit/status.md` | Update ledger post-commit. |

## Critical constraints for the Maker

- **No `HaltReason.CRASH_RECOVERY` value** — the plan's §4 speculates about it, but the decision tree treats crash-detected state via `RecoveryStrategy`, not a new halt reason. Do not add one.
- **No new sync-event persistence** — C4's unconditional-pre-subprocess sync deliberately removed event-loss risk. F12 is about `source_commit_hash` freshness proof on resume, not about persisting "unseen" events.
- **F9 no-recompute discipline** — `StartupReconciler` MUST preserve `RunManifest.diff_classification` on resume, NEVER re-derive from the diff. Cite `orchestration.py` `RunManifest.diff_classification` docstring.
- **F10 decision** — Lock in phase-boundary decay for `RejectionEdge` per what C2's Maker inferred (§4.5 paragraph 3). Alternative was time-based decay; user picked "resolve all three" so pick phase-boundary and document the choice.
- **Pydantic v2, frozen, extra=forbid** via `BaseContract` inheritance (never re-declare `model_config`).
- **Absolute paths only** — running from `agent-taxonomy` worktree; do not `cd` into main repo.
- **Frontmatter required** on `crash_recovery.md` (`title`, `status: live`, `part_of: agentic-sdlc`, `doc_type: companion`). Pre-commit hook will backfill and regenerate `FRONTMATTER_MANIFEST.md`.
- **Counts as digits** — if writing "N companion files" anywhere, must also update `scripts/sync_counts.py` REGISTRY.

## Maker/Checker pattern

Dispatch `general-purpose` Maker sub-agent with the above brief. Then dispatch independent `general-purpose` Checker sub-agent to verify: schema validity, cross-reference bidirectionality, F9/F10/F12 resolution, no `HaltReason.CRASH_RECOVERY` added, no runtime code, frontmatter present. Max 2 Maker iterations.

## Commit plan

Likely 2 commits (following C1's pattern):

1. `audit-fix(H8): scaffold RecoveryManifest schema and last_sync_hash_by_task` — contracts only
2. `audit-fix(H8): startup reconciliation protocol and crash recovery companion` — prose + manifest + cross-refs

## Next agent's first actions

1. Read `audit/2026-08-28_audit/orchestrator_reference_instructions.md`, `status.md`, `followups.md` (already-completed items C5, C1, H6, C2, C3, C4 documented in status.md).
2. Mark F9, F10, F12 as `in-scope` in `followups.md`.
3. Dispatch Maker with the brief above.
4. Then Checker → commits → update ledger → report to user.
