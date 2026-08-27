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

## 7. Shared-file materialization

*Resolves the contradiction recorded as D1 in `implementation_roadmap.md`: design doc §4.2 applied an
intent "synchronously before the agent continues," while §6 above commits shared files last. Both
could not be true, and no materialization path was specified anywhere in the set.*

### 7.1 What the question actually is

Not "how does an agent learn that an intent was applied" — that is a messaging problem with many
good answers. The question is: **when a Task Dev's interpreter imports the package to run the suite,
what does that import resolve to on disk?** §1 above is the reason: verification is repo-scoped even
when editing is file-scoped. Any answer that informs the agent without changing the bytes under the
interpreter leaves the agent writing code against a route its own test run cannot import.

### 7.2 Mechanism: canonical branch, read-only overlay

1. **Single writer.** The Shared-File Intent Service is the sole writer of a canonical
   `shared/` branch containing registered shared files and nothing else. Every application is
   serialized through one lock; collision arbitration (design doc §4.5) happens here, before any
   write.
2. **Worktrees do not track shared files.** At worktree creation, Core marks every registered
   shared file `git update-index --skip-worktree` in that worktree's index, and the path sits
   outside the agent's write scope at the filesystem layer. The agent cannot commit the file, and
   cannot edit it — Principle 12, a permission rather than an instruction, and checkable as a
   precondition before the swarm spawns.
3. **Applied intents are re-materialized into every live worktree.** On successful application, Core
   writes the new file content into each running worktree's working directory. `skip-worktree` keeps
   git silent about it: the interpreter sees current content, `git status` stays clean, and the diff
   the task eventually produces contains none of it. The write is a temp-file-plus-`rename`, which
   is atomic on POSIX — a concurrent test run reads the old content or the new one, never half of
   either.
4. **Integration order is unchanged.** Task branches merge first, carrying no shared-file changes —
   which makes `merge.no_conflict` (design doc §9.1) an honest gate rather than one that has been
   quietly exempted. The Integrator then fast-forwards `shared/` as the final commit. It is a
   fast-forward, never a merge: the service was the only writer, so there is nothing to reconcile.

This is what §4.2's "applied synchronously before the agent continues" was always describing. It is
now a mechanism rather than an assertion.

### 7.3 The read-view guarantee, restated precisely

§3 above promises an agent "never a sibling task's in-progress edit." Re-materialization does change
a file underneath a running agent, so the guarantee needs stating exactly rather than loosely:

> A worktree is isolated from sibling tasks' **in-progress work**. It is not isolated from
> **governed shared state**, and should not be.

An applied intent is not an in-progress edit. It has already been through collision arbitration and
deterministic application; it is the agreed content of a file both tasks depend on. Isolating an
agent from it would mean the agent codes against a shared file it knows to be stale, and discovers
the divergence at integration — which is the failure mode §4 exists to remove.

### 7.4 Reviewability: the synthesized diff

The cost of this mechanism, stated plainly: a task's PR diff contains no shared-file content, so a
reviewer cannot see what was added to a router or registry on that task's behalf. In a design whose
posture is that nothing is invisible, that is a regression, and it needs compensating for rather
than accepting.

Core synthesizes a **shared-file delta view** for every PR from the intent log: each hunk of the
`shared/` fast-forward commit attributed to the intent that produced it and the task that submitted
it. The reviewer sees "task-7 · `AddRoute(path=/reports)` · +4 lines" against real diff hunks,
rather than one anonymous blob commit at the end of the branch. The intent log already carries
everything this needs — submitter, op, payload, applied anchor — because Smart Mutex Rejection and
the conflict counters require it.

### 7.5 Transport is a separate decision

How an agent *submits* an intent and *learns the outcome* is orthogonal to all of the above, and is
deliberately pluggable. §7.2 fixes where bytes live; it says nothing about the wire.

An MCP server is a good fit for that transport, and better than a file-based or queue-based
protocol, for three reasons: submission and Smart Mutex Rejection are natively request/response with
a typed result, so a rejection with blocking context lands directly in the agent's context instead
of having to be discovered; making the tool call the *only* path to a registered shared file turns
§4.2's rule into a permission (Principle 12) rather than an instruction; and the synthesized delta
of §7.4 exposes cleanly as a read-only resource.

Three constraints on any such transport, each a real failure mode rather than a preference:

- **One shared service, not one per agent.** The mutex in §7.2 is only a mutex if every worktree's
  agent talks to the same long-lived process. A server instance spawned per agent session — the
  default shape for most MCP deployments — yields N writers and no arbitration at all, while
  appearing to work until two agents collide.
- **Blocking context is structured data, never prose.** A rejection tells one agent what another
  agent claimed. Free-form text there is an injection channel between agents; the payload is the
  op, the colliding keys, and the owning task id, rendered by the receiving side.
- **Reads stay local.** Because §7.2 puts current content on disk, a transport outage blocks new
  submissions but does not break a running suite. A design that served shared-file *reads* over the
  wire would make service availability a dependency of every test run.

The intent service is therefore built as a library with a lock, with transport as an adapter over
it. That keeps the Stage 2 conformance work free of a protocol dependency it does not need — and
Stages 1 and 2 have no LLM agents in the loop to talk to a tool server in the first place.
