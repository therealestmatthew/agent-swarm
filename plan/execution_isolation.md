---
title: Execution Isolation
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Execution Isolation

**Referenced by:** `agentic-sdlc-design-v0.5.md` §8 (Execution Isolation) · Principle 4 (Disjoint
Write Ownership) · Principle 12 (Enforce with permissions, not prompts)

**Status:** reinstated from `agentic-sdlc-design-v0.1.md` §6, absent v0.2 through v0.4. See
`plan/versions/REGRESSION.md` finding #2.

## Purpose

Disjoint write ownership (design doc Principle 4) guarantees that two Task Dev agents never edit
the same file. It says nothing about what happens when one of them *reads* the repo — and every
test run is a read of the whole repo, not just the file under test.

## 1. The problem this solves

The ownership map isolates writes. It does nothing for reads: the moment one Task Dev agent runs
its local test suite, the interpreter imports the whole package, including a file another agent is
halfway through rewriting. **Verification is repo-scoped even when editing is file-scoped.** A swarm
that only isolates writes can produce a spuriously green or spuriously red test run depending on the
accident of what another in-flight agent's file looked like at that instant.

## 2. Mechanism: one git worktree per task

```
git worktree add ../wt-<task-id> -b task/<task-id>
```

Each Task Dev agent gets its own worktree, its own branch, its own index, and its own `HEAD`. It
reads and writes only inside that tree for the duration of the task.

## 3. What this buys, concretely

- **No `index.lock` contention.** Two agents don't fight over one `.git/index`.
- **A stable read view.** An agent's test run sees only its own worktree's file contents — never a
  sibling task's in-progress edit — regardless of what else is running in parallel.
- **Atomic per-task revert.** Discarding a task's work is deleting its worktree and branch, not
  untangling partial changes out of a shared tree.
- **Per-task attribution for free.** Every commit in a task's history is unambiguously that task's,
  which is also what the verdict ledger (`calibration_and_measurement.md`) attributes findings
  against.
- **No re-clone cost.** The object store is shared across worktrees. With `uv`, a per-tree
  environment is a few warm-cache seconds, not a fresh install.

## 4. Lifecycle

1. Task Decomposer emits the task spec and `merge_order` (design doc §3, Phase 2 & 3).
2. Core Orchestrator (or the swarm dispatcher acting on its behalf) creates the worktree and branch
   for each task about to spawn.
3. Test Author commits failing tests into the worktree (`tests/**` only — Principle 12: this is a
   permission boundary, not an instruction).
4. Task Dev implements against those tests, running the full local suite unconditionally — a pure
   unit suite is fast enough to make this affordable on every iteration.
5. On completion, the branch is handed to Code Reviewer (shadow or gating, per
   `calibration_and_measurement.md`), then to the Integrator for merge in the planned order.
6. The worktree is torn down after its branch merges or its task is abandoned. Nothing about
   worktree teardown is itself a gate — the merge (`merge.no_conflict`, design doc §9.1) is.

## 5. Containers are not required — yet

For a pure unit suite with no external dependencies (databases, bound ports, real network calls), a
worktree is sufficient isolation. **Revisit this the moment any of that changes:** if a task's tests
start binding a port, hitting a real service, or running a migration, the isolation unit needs to
become a container, not just a worktree, because two agents' processes can otherwise collide on a
resource a worktree doesn't scope (a listening socket, a database file).

## 6. Merge order is planned, not emergent

Design doc §3 already states this for the swarm as a whole; it's restated here because it's the
reason worktree teardown order matters. The sequence is: interface contract commit, then tasks in
their planned dependency order, then the Integrator's shared-file commit last. An emergent merge
order — whichever worktree happens to finish first — reintroduces exactly the race worktrees exist
to remove, just at the merge step instead of the edit step.
