---
title: Execution Isolation
status: live
part_of: agentic-sdlc
doc_type: companion
layer: adapter-sdlc
---

# Execution Isolation

**Referenced by:** `agentic-sdlc-design-v0.5.md` §8 (Execution Isolation) · Principle 4 (Disjoint
Write Ownership) · Principle 12 (Enforce with permissions, not prompts)

**Status:** reinstated from `agentic-sdlc-design-v0.1.md` §6, absent v0.2 through v0.4. See
`design/plans/versions/REGRESSION.md` finding #2.

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

> **Crash Recovery Pointer:** If a run crashes during task execution, the `StartupReconciler` handles orphan cleanup for these worktrees. See `crash_recovery.md` for the full lifecycle.

## 5. The isolation unit is derived, not discovered

This section previously read *"containers are not required — yet ... revisit the moment a task's
tests start binding a port, hitting a real service, or running a migration."* That is a correct
instinct expressed as an escape condition someone has to notice — and the whole posture of this
design is that a constraint which binds should be a fact about a run rather than a discovery at
runtime. It is also, for any browser-driven repo, already true on day one: a WebDriver reset spawns
a process, binds a port, and needs a profile directory no sibling task may share.

> **Crash Recovery Pointer:** To ensure orphan detection, containers are labeled with `run_id`. Lingering containers from crashed runs are cleaned up by the `StartupReconciler`. See `crash_recovery.md`.

### 5.1 The derivation

Each `ResetStrategy` a repo declares (`test_harness_architecture.md` §1.3) names the host resources
one execution needs. Core reads those and derives the **minimum** isolation unit:

| Any declared strategy requires | Minimum isolation unit | Why |
|---|---|---|
| `none` — in-process only | Worktree | Nothing escapes the tree |
| `process` — spawns a process | Worktree | A child process that touches nothing shared is scoped by the tree it runs in |
| `port` — binds a listening socket | **Container** | Two tasks' sockets collide on one host; a worktree does not scope a port |
| `filesystem_exclusive` — needs an unshared path | **Container** | A profile directory or database file is not scoped by a worktree |
| `external_service` — reaches a real service | **Container** | Blast radius and credential scope both need a boundary a worktree has not got |

### 5.2 Derived is a floor, not an assignment

`RepoDeclaration.isolation_unit` stays declared, and Core raises it to the derived minimum rather
than replacing it. A repo may always declare a **stronger** unit than its resources require — for
credential scoping, for blast radius, for reproducibility — and Core does not argue.

What it may not do is declare a weaker one. **Declaring `worktree` while declaring a strategy that
requires a port, an exclusive path, or an external service is incoherent**, and Core rejects it at
contract validation with `HaltReason.ADAPTER_INVALID` — the same treatment as claiming
`Capability.MUTATION_TESTING` with no hermetic tier (`test_harness_architecture.md` §3.7). A repo
may honestly need a container; it may not claim it does not while declaring the reasons it does.

### 5.3 What this costs, stated

Containers are not free, and the derivation makes the bill legible rather than smaller. A container
per task multiplies the per-unit resource footprint, which divides straight into the concurrency
ceiling (`core_adapter_boundary.md` §3.6): browser containers are hundreds of megabytes each before
a single test runs, so swarm width for a browser-tier repo is bound by memory long before it is
bound by API rate limits. That is the answer to design doc §12's concurrency-ceiling question for
this class of repo, and it falls out of the same declaration rather than needing a separate one.

### 5.4 Credential-bearing tasks floor to `CONTAINER`

**A task whose resolved `granted_secrets` set is non-empty floors to `CONTAINER`, independent of
what its `ResetStrategy.requires` values are.** The resource-based derivation of §5.1 and this
credential-based derivation are orthogonal sources; whichever is stronger wins.

The reason is not test-suite hygiene but network scope: the egress scrubber and its proxy
(`core_adapter_boundary.md` §5.2) rely on the container's network boundary to interpose on outbound
traffic. A worktree does not scope network egress; a container does. A task that can reach the
network unmediated is a task whose credentials can leave through a channel the scrubber never sees,
which is the exact failure mode C1 moved the scrubber to Core to prevent.

**The edge case is deliberate.** A task with a local-dummy credential provider still floors to
`CONTAINER`. The trust posture is a property of the code path, not the value provided to it — a
provider swap must not change the isolation guarantee, or a repo could weaken its own boundary by
declaring a dummy provider it later replaces. A container for dummy-credential tasks is cheap
insurance, and it keeps the derivation deterministic: two tasks with identical declarations resolve
to the same unit regardless of which provider is currently wired in.

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
3. **Applied intents are materialized pull-based, at each agent's next subprocess boundary.** On
   successful application, Core writes the new file content into the **proposing** agent's worktree
   only — that agent is at a safe sync boundary by construction, since it is blocked awaiting the
   Intent Service's response and no subprocess of its own is running. Sibling worktrees are **not**
   written to at this point; a sibling that is mid-execution has caches (module import caches, file
   watchers) that a mid-run byte-swap would corrupt at the runtime layer even where the filesystem
   layer stays atomic (§7.3, §7.6). Instead, every agent's runtime unconditionally calls
   `WorktreeSyncRequest` (`design/plans/contracts/adapter_surface.py`) before spawning any subprocess. That
   call is a local filesystem reconciliation between the worktree's local `shared/` branch head and
   its working directory — atomic per-file via temp-file-plus-`rename`, idempotent when nothing has
   changed. `skip-worktree` behavior is unchanged: git stays silent about the reconciled paths, the
   interpreter (in the fresh subprocess) sees current content, `git status` stays clean, and the
   task's eventual diff contains none of it.
4. **Integration order is unchanged.** Task branches merge first, carrying no shared-file changes —
   which makes `merge.no_conflict` (design doc §9.1) an honest gate rather than one that has been
   quietly exempted. The Integrator then fast-forwards `shared/` as the final commit. It is a
   fast-forward, never a merge: the service was the only writer, so there is nothing to reconcile.

> **Crash Recovery Pointer:** The `shared/` branch semantics interact with the crash reset protocol; branch integrity is guaranteed via `git reset --hard`. See `crash_recovery.md`.

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

**Where the guarantee is honored.** The read-view guarantee is honored *at process execution
boundaries*, not in mid-run. Filesystem-level atomicity (temp-file-plus-`rename`) is a necessary
condition, not a sufficient one: an in-process cache — a Python `sys.modules` entry, a Node
`require.cache` entry, a Ruby `$LOADED_FEATURES` entry, or a file watcher observing worktree files —
is not isolated from an applied intent while the agent's own runtime process persists. §7.6 is the
mechanism that eliminates this failure mode by forbidding in-process execution of target-system
code: the fresh subprocess is the boundary at which "current content on disk" becomes "current
content in the interpreter's caches."

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
  wire would make service availability a dependency of every test run. The pre-subprocess
  `WorktreeSyncRequest` call (§7.6) is a Core-internal reconciliation between the worktree's local
  `shared/` branch head and its working directory, **not** a wire read: a transport outage during a
  sibling agent's execution still does not break its next subprocess boundary, because the local
  `shared/` branch already holds the last-applied content on disk.

The intent service is therefore built as a library with a lock, with transport as an adapter over
it. That keeps the Stage 2 conformance work free of a protocol dependency it does not need — and
Stages 1 and 2 have no LLM agents in the loop to talk to a tool server in the first place.

### 7.6 Materialization Window Protocol

Filesystem atomicity is a necessary condition for §7.3's read-view guarantee, but it is not a
sufficient one. Every widely-used target-system runtime maintains in-process caches that survive
past the moment a file changes on disk: Python's `sys.modules` retains the previously-imported
module object; Node's `require.cache` retains the previously-resolved module; Ruby's
`$LOADED_FEATURES` records what has already been `require`d and will not reload it. A shared-file
byte-swap that lands under any of those caches leaves the runtime observing a mixed state — some
modules from the old bytes, some from the new — and no atomic rename downstream of that cache can
repair it.

The invariant is therefore expressed in terms of the boundary at which those caches are
constructed, not in terms of a language:

> **Target-system code MUST execute in a subprocess distinct from the agent's own runtime, so that
> materialization at the process boundary yields a fresh module/import cache.**

The language-specific caches above (`sys.modules`, `require.cache`, `$LOADED_FEATURES`) are
illustrative examples of what "fresh module/import cache" resolves to on the runtimes agents in
this pipeline will most often drive; the rule is orthogonal to which runtime a target repo happens
to be. An agent may itself be written in any language; what it may not do is import the target
system into its own interpreter and run tests there.

**How the invariant is honored operationally.** The agent's runtime hooks the sync call at every
subprocess-spawn site: before spawning a test runner, a script, a linter, or any other target-code
process, the runtime unconditionally issues a `WorktreeSyncRequest`
(`design/plans/contracts/adapter_surface.py`) and waits for the `WorktreeSyncResult`. Safe materialization
windows are therefore exactly the moments a fresh subprocess is about to start — which are also
exactly the moments the receiving cache does not yet exist. The `was_noop=True` case is the normal
steady-state result and costs nothing beyond a stat comparison; the `was_noop=False` case writes
the changed bytes and returns the `source_commit_hash` the caller can log for audit. Unconditional
call is why no `SharedStateUpdatedEvent` schema exists in this design: with the sync issued at
every boundary regardless of whether Core signaled anything, there is nothing for a missed event
to lose.

**Interaction with the C1 credential container.** This subprocess-only invariant is complementary
to §5.4's credential-bearing floor to `CONTAINER`. The container the credential rule requires is
also the enforcement boundary Core has for this rule: a Core-controlled container makes it
tractable to check that target-code execution actually crosses a process boundary the agent's own
runtime does not straddle, in the same way it makes egress scrubbing tractable. The two
requirements land at the same layer for the same structural reason — a boundary Core owns is a
boundary Core can enforce.

### 7.7 Sync starvation

The materialization-window protocol assumes an agent will eventually reach a subprocess boundary
and issue the sync call there. An agent that has entered a long-running debug session, a
daemonized service, or a hung LLM-generation loop may go arbitrarily long without one — and every
shared-file intent Core applies during that stretch fails to reach the starved worktree, no matter
how faithfully the protocol is otherwise being followed.

`GovernancePolicy.max_seconds_without_sync` (`design/plans/contracts/governance.py`) bounds that stretch.
It is illustrative and adapter-tunable: `None` means the bound is off. When Core observes that a
task has gone longer than this since its last `WorktreeSyncResult`, it treats the task as
materialization-starved and issues a task-scoped boundary failure — dropping the task from
`RunManifest.active_task_ids`, using the same mechanism C2 (structural-intent deadlocks) and C3
(coverage-family gaps) already use. See `budget_and_escalation_policy.md` §2.2 for the escalation
posture: sync starvation is boundary-type, skips rung 3, and terminates without model escalation
for the same reason the other boundary-type loops do — a stronger model does not resolve a
structural violation of the materialization-window protocol.
