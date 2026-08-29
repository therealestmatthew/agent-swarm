---
title: Crash Recovery
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Crash Recovery

**Referenced by:** `agentic-sdlc-design-v0.5.md` §3 · `execution_isolation.md` §4, §5, §7.2 · `CLAUDE.md`

## Purpose

Defines the Startup Reconciliation Protocol and how the orchestrator handles interrupted runs, orphans, and shared state integrity upon resume.

## 1. Startup Reconciliation Protocol (Step 0)

Before any phase resumes, the `StartupReconciler` determines if the run was previously active and crashed.
The resume decision tree governs whether to resume, rollback, or halt, as codified in `RecoveryStrategy`.

## 2. Orphan Cleanup

Container labeling with `run_id` ensures orphan detection. Any lingering containers from a crashed run are cleaned up during Step 0.

## 3. Shared Branch Integrity

Integrity of the `shared/` branch is guaranteed via `git reset --hard` to the last known good commit before resuming.

## 4. No-Recompute Posture for Diff Classification (F9)

The `StartupReconciler` MUST preserve `RunManifest.diff_classification` on resume. It MUST NEVER re-derive from the diff, as the diff may have been mutated between crash and restart. Recomputing it would defeat the point of persisting the label (as cited in the docstring of `RunManifest.diff_classification`).

## 5. Phase-Boundary Decay Rule for RejectionEdge (F10)

Edges in the rejection graph that are older than a phase boundary are stale evidence. The phase-boundary decay rule locks in that these edges are discarded across phase boundaries.

## 6. Sync-Freshness-on-Resume (F12)

The `RunManifest.last_sync_hash_by_task` field provides sync-freshness-on-resume via `source_commit_hash`. On resume, the `StartupReconciler` compares the stored hash in `last_sync_hash_by_task` against the current head of the shared branch to prove it is up to date and that no unauthorized out-of-band commits have occurred.
