---
title: Structural Change Runbook
status: live
part_of: agentic-sdlc
doc_type: runbook
---

# Structural Change Runbook

**Referenced by:** `agentic-sdlc-design-v0.5.md` §4.2, §4.6, §8 · `plan/contracts/orchestration.py` (`IntentRejection.reason = "structural"` and `"pending_tier2_review"`) · `plan/contracts/governance.py` (`GovernancePolicy.max_intents_per_shared_file`)

## Purpose

The Shared-File Intent Service (design doc §4) handles three tiers of structural change:

- **Tier 1 (Auto-Resolved):** New deterministic operations (`RenameExport`, `MoveRoute`,
  `DeprecateExport` — schemas in `plan/contracts/reference_adapter/web_intents.py`) are
  handled synchronously by the Intent Service with no human gate. Low blast radius, fully
  reversible, mechanical AST transforms.
- **Tier 2 (Async Human Review):** Changes that affect consumer boundaries but do not
  inherently break the broader architecture. The Intent Service accepts the intent into a
  pending-review state and returns `IntentRejection.reason = "pending_tier2_review"`. The
  proposing agent parks the dependent sub-task and continues other work within its existing
  write scope. The run does not halt. A human reviews asynchronously; on approval, the Intent
  Service applies and materializes the change.
- **Tier 3 (Synchronous Full Pause):** High-blast-radius changes — splitting or merging
  shared files, restructuring dependency graphs in ways that affect existing consumers. The
  Intent Service returns `reason = "structural"`. This runbook's procedure fires: a targeted
  pause, human architectural review, re-decomposition.

This runbook owns Tier 2 and Tier 3 procedures. Tier 1 intents never reach it.

---

## 1. Triggers

### Tier 2 Triggers (async review — run continues)

A task enters Tier 2 review when any of the following hold:

- **Intent batch exceeding the per-file ceiling** — a single task submitting more than
  `GovernancePolicy.max_intents_per_shared_file` intents against the same registered shared
  file (illustrative threshold — `None` means off; tune per
  `structural_change_runbook.md §4`). The signal: a long sequence of individually-reasonable
  intents may be a structural change happening one step at a time.
- **Splitting or merging a shared file where the new boundaries are well-formed** — e.g.,
  splitting a large router into per-domain routers where each new file's interface is
  clear and the migration path for consumers is deterministic. If the boundaries are not
  well-formed, the change escalates to Tier 3.

### Tier 3 Triggers (synchronous full pause — run halts)

A task enters the full Tier 3 SOP instead of the standard Phase 4 swarm flow (or exits
mid-swarm into this SOP) when any of the following hold:

- **Splitting or merging a shared file where the new boundaries are not well-formed** — the
  migration path for consumers is ambiguous, or the target interface requires judgement to
  determine. Well-formed splits that fail Tier 2 review also escalate here.
- **Restructuring the dependency graph** — changing binding scope in a way that affects
  existing consumers (not just adding a new binding), or breaking a circular dependency that
  requires touching multiple shared files at once.
- **A task requiring removal of an existing shared symbol with no deterministic migration** —
  `RenameExport` and `DeprecateExport` (Tier 1) cover the deterministic cases. Pure removal
  with no forwarding path, or removal of a symbol with consumers the agent cannot enumerate,
  is Tier 3.
- **A task that would require more than N additive intents against the same shared file**
  *(parameterized as `GovernancePolicy.max_intents_per_shared_file`; `None` means off)* —
  when a Tier 2 async review of such a batch is itself rejected by the human reviewer, the
  change is re-routed here.
- **Escalation from the Shared-File Intent Service** — **non-cyclic** repeated Smart Mutex
  rejections (design doc §4.5) between the same two agents on the same file, where the
  blocking-context resolution is not converging but no full graph cycle has closed and the
  per-tuple `GovernancePolicy.max_mutex_rejections` counter has not yet tripped. Graph cycles
  and counter breaches are handled by the Intent Service's deadlock detector (design doc
  §4.5) as task-scoped boundary failures without entering this SOP. The two paths are
  non-overlapping by construction.

Layer-2 semantic rejections (`IntentRejection.reason = "semantic_collision"` — the
Two-Layer Collision Model, `core_adapter_boundary.md` §2.1) are neither a Tier 2 nor a
Tier 3 trigger. A `semantic_collision` stays inside the Intent Service's per-intent
verdict loop: the submitting agent resubmits via `IntentSubmission.override_semantic_collisions`
or accepts the rejection, and a stuck override loop degrades to `deadlock_cycle` under
`max_mutex_rejections` like any other loop (design doc §4.5). This mirrors the existing
non-overlap carve for the deadlock detector above — semantic-collision governance and
structural-change governance are non-overlapping paths.

## 2. Who's involved

- **Task Decomposer** — owns this SOP. It's the same agent responsible for task boundaries in the normal flow, and a structural change is fundamentally a boundary redefinition.
- **Human architecture reviewer** — required sign-off at the plan step (§4, step 3) and the resume step (§4, step 6). This is not optional or delegable to an agent, consistent with Principle 5 (human gates at irreversible points) — a structural change to shared infrastructure has blast radius beyond any single task.
- **Affected Task Dev agents** — any in-flight agent whose task touches the file(s) being restructured.

## 3. Tier 2 Procedure (Async Review)

1. **Queue the intent.** The Intent Service accepts the intent into a `pending_tier2_review`
   state and returns `IntentRejection.reason = "pending_tier2_review"` to the submitting
   agent. The proposing agent receives `applied=False` with this reason.
2. **Agent parks and continues.** The proposing agent parks the specific sub-task that
   depends on the pending intent and picks up other work within its existing write scope.
   No new constraint beyond its declared `src/**` scope applies — the shared file is
   registered and already outside any agent's direct write scope (design doc §4).
3. **Human reviews asynchronously.** A human reviews the queued intent — the proposed
   change, its declared consumers, and the migration path — and approves or rejects.
   This does not pause new task assignment against other files.
4. **On approval:** The Intent Service applies the intent, materializes it into every live
   worktree via the pre-subprocess sync protocol (`execution_isolation.md §7`), and notifies
   the waiting agent. The parked sub-task resumes.
5. **On rejection:** The human reviewer routes the intent to the Tier 3 Procedure (§4)
   if the change is genuinely structural, or returns it to the agent for redesign if the
   intent itself was malformed.

## 4. Tier 3 Procedure (Synchronous Full Pause)

1. **Pause.** The Core Orchestrator halts new task assignment against the affected shared file(s) and any in-flight Task Dev branches with pending intents against them. In-flight branches that don't touch the affected file continue unaffected — this is a targeted pause, not a full swarm halt.
2. **Snapshot current state.** Capture the current registered structural map (§4.3 of the core doc) for every file involved, plus the set of open/pending intents against them at the moment of pause. This is the rollback point if the restructure is aborted.
3. **Propose the new architecture.** The Task Decomposer (or a dedicated architecture-planning pass) proposes the target structure: the new file boundaries, the new interface contracts, and a migration path for existing consumers. This proposal goes to the human architecture reviewer for approval — the same Contract Freeze-style gate used in Phase 2/3 of the core flow.
4. **Re-decompose affected tasks.** Any paused or in-flight task whose work depended on the old structure gets its interface map regenerated against the new one. This is treated the same as a Merge Conflict boundary failure (design doc §7) in the sense that it's an explicit re-decomposition, not a patch — the task's contract genuinely changed.
5. **Re-register shared files.** Once the new structure is live, affected files go back through Shared-File Registration (§4.3) under their new shape before any new additive intents are accepted against them.
6. **Resume.** Human architecture reviewer confirms the migration is complete and consumers are updated. The Core Orchestrator resumes normal task assignment and intent submission against the newly registered files.

## 5. Open parameters

- **Additive-intent-count threshold** — now parameterized as
  `GovernancePolicy.max_intents_per_shared_file` (illustrative; `None` = off). Set per the
  target repo's observed intent burst sizes. Too low and legitimate multi-route features
  trigger unnecessary Tier 2 reviews; too high and a disguised structural change slips
  through as a long sequence of individually-reasonable intents. No calibrated default
  exists yet.
- **Partial-pause granularity** — step 1 assumes the Orchestrator can cleanly identify which in-flight branches touch the affected file(s). This depends on task metadata being accurate at assignment time; worth confirming this holds once the SOP has run in practice.

Tracked alongside the core design doc's own open questions (`agentic-sdlc-design-v0.5.md` §8): repeated triggering of this SOP against the same file or subsystem may itself be a signal worth feeding back into governance — e.g., a file that keeps needing structural intervention might need a heavier redesign rather than another round of this procedure.

## 6. Deadlocked-intent escape hatch

This section covers the path for tasks terminated by the deadlock detector — a separate path from the Tier 2 and Tier 3 triggers in §1, which govern structural-change governance. Deadlock detection and structural-change governance are non-overlapping: this section fires only when the detector terminates tasks, not when a structural change is proposed.

The Intent Service's deadlock detector (design doc §4.5) terminates the involved tasks automatically — they fail out of `RunManifest.active_task_ids` with `IntentRejection.reason = "deadlock_cycle"`, and Core continues the phase for the remaining tasks. That closes the immediate budget-burn hazard. It does not, on its own, decide whether the underlying incompatibility is a decomposition error (fixable by re-decomposing the task set against the current shared-file boundaries) or a genuine structural change (fixable only by running the full runbook above).

The reviewer picking up a deadlocked task set works from the evidence Core preserves:

1. **Read the persisted rejection graph.** `RunManifest.rejection_graph_edges` holds the full edge set the detector was operating on at termination. The involved tasks are named in `IntentRejection.deadlock_cycle`; the edges give the resource(s) and the sequence of rejections. A cycle over one resource key means the tasks were fighting for the same insertion point; a cycle over several means the interface itself is the shape of the conflict.
2. **Decide the resolution class.** If the cycle sits over one resource and the tasks' declared responsibilities do not actually require both to write there, the answer is re-decomposition: the Task Decomposer redraws the task boundaries and Core reschedules the involved tasks (§4.4 style — the boundary failure path). No full runbook run is needed; the SOP's plan/approve steps (§4.3, §4.6) are overkill for a decomposition fix.
3. **Or accept it as structural.** If the cycle reflects an interface that genuinely cannot express what both tasks need to do — different consumers of the same registered symbol needing incompatible extensions, for example — the answer is the full Tier 3 Procedure (§4 above), starting from the pause step. The rejection graph edges become part of the §4.2 snapshot as evidence for the §4.3 architecture proposal.

The runbook does not fire automatically on a deadlock detection. Whether a deadlocked set routes to re-decomposition or to §4 is a human call, made against the persisted graph. What is automatic is the containment: budget stops burning at the moment of detection, not at the moment of human review.
