---
title: Structural Change Runbook
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Structural Change Runbook

**Referenced by:** `agentic-sdlc-design-v0.5.md` §4.2, §4.6, §8

## Purpose

The Shared-File Intent Service (design doc §4) only handles **additive** operations against **registered** shared files — adding an export, a route, a provider binding. It deliberately cannot express structural changes: splitting a router into multiple files, restructuring a DI graph, renaming or removing an existing binding that other code depends on. Forcing these through the additive intent vocabulary would either be impossible to express or would silently reintroduce the hallucination risk the typed-intent model exists to remove.

This runbook defines what happens instead: a human-gated procedure that pauses the relevant part of the swarm, re-maps the affected architecture, and resumes execution once new boundaries are agreed.

---

## 1. Triggers

A task enters this SOP instead of the standard Phase 4 swarm flow (or exits mid-swarm into this SOP) when any of the following hold:

- **Splitting or merging a shared file** — e.g., breaking a monolithic router into per-domain routers, or consolidating several export barrels into one.
- **Restructuring the dependency graph** — changing binding scope in a way that affects existing consumers (not just adding a new binding), or breaking a circular dependency that requires touching multiple shared files at once.
- **Removing or renaming an existing shared symbol** — any operation that isn't purely additive, since the intent vocabulary (§4.2 of the core doc) has no `RemoveExport` or `RenameRoute` operation by design.
- **A task that would require more than N additive intents against the same shared file in a single task** *(threshold TBD — see §4 below)* — a signal that what looks additive is actually a structural change happening one intent at a time.
- **Escalation from the Shared-File Intent Service** — repeated Smart Mutex rejections (design doc §4.5) between the same two agents on the same file, where the blocking-context resolution isn't converging, suggests the underlying interface itself needs to change, not just one agent's proposed intent.

## 2. Who's involved

- **Task Decomposer** — owns this SOP. It's the same agent responsible for task boundaries in the normal flow, and a structural change is fundamentally a boundary redefinition.
- **Human architecture reviewer** — required sign-off at the plan step (§3, step 3) and the resume step (§3, step 6). This is not optional or delegable to an agent, consistent with Principle 5 (human gates at irreversible points) — a structural change to shared infrastructure has blast radius beyond any single task.
- **Affected Task Dev agents** — any in-flight agent whose task touches the file(s) being restructured.

## 3. Procedure

1. **Pause.** The Core Orchestrator halts new task assignment against the affected shared file(s) and any in-flight Task Dev branches with pending intents against them. In-flight branches that don't touch the affected file continue unaffected — this is a targeted pause, not a full swarm halt.
2. **Snapshot current state.** Capture the current registered structural map (§4.3 of the core doc) for every file involved, plus the set of open/pending intents against them at the moment of pause. This is the rollback point if the restructure is aborted.
3. **Propose the new architecture.** The Task Decomposer (or a dedicated architecture-planning pass) proposes the target structure: the new file boundaries, the new interface contracts, and a migration path for existing consumers. This proposal goes to the human architecture reviewer for approval — the same Contract Freeze-style gate used in Phase 2/3 of the core flow.
4. **Re-decompose affected tasks.** Any paused or in-flight task whose work depended on the old structure gets its interface map regenerated against the new one. This is treated the same as a Merge Conflict boundary failure (design doc §7) in the sense that it's an explicit re-decomposition, not a patch — the task's contract genuinely changed.
5. **Re-register shared files.** Once the new structure is live, affected files go back through Shared-File Registration (§4.3) under their new shape before any new additive intents are accepted against them.
6. **Resume.** Human architecture reviewer confirms the migration is complete and consumers are updated. The Core Orchestrator resumes normal task assignment and intent submission against the newly registered files.

## 4. Open parameters

- **Additive-intent-count threshold** for auto-detecting a disguised structural change (§1, fourth trigger) — not yet set. Too low and legitimate multi-route features trigger unnecessary SOP runs; too high and a structural change slips through as a long sequence of individually-reasonable intents.
- **Partial-pause granularity** — step 1 assumes the Orchestrator can cleanly identify which in-flight branches touch the affected file(s). This depends on task metadata being accurate at assignment time; worth confirming this holds once the SOP has run in practice.

Tracked alongside the core design doc's own open questions (`agentic-sdlc-design-v0.5.md` §8): repeated triggering of this SOP against the same file or subsystem may itself be a signal worth feeding back into governance — e.g., a file that keeps needing structural intervention might need a heavier redesign rather than another round of this procedure.
