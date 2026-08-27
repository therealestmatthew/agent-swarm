---
title: Agentic SDLC Orchestration — Design Proposal
status: superseded
part_of: agentic-sdlc
doc_type: blueprint
version: "0.1"
superseded_by: plan/versions/agentic-sdlc-design-v0.2.md
---

# Agentic SDLC Orchestration — Design Proposal

**Status:** proposal, v0.1
**Target:** existing repo, known well, pure unit test suite, no external test dependencies
**Companion artifact:** `orchestration_contracts.py` (the executable version of §4 and §5)

---

## 1. What we are building

A multi-agent software development pipeline that takes a user request and carries it
to a merged, monitored production change. A context-minimal **Core Orchestrator**
coordinates the run. Every agent that *produces* an artifact is paired with a
validator that *judges* it. Humans gate at two points and can be escalated to at any
point.

The system is designed around eight principles. Most of the specific decisions below
follow from one of them, and where a decision looks arbitrary it is usually principle
3 or principle 4 doing the work.

| # | Principle | Consequence |
|---|---|---|
| 1 | The orchestrator holds pointers, never content | Constant-size context, resumable runs, real audit trail |
| 2 | A validator only adds signal if it is **asymmetric** to the generator | Reviewers get the spec and the artifact, never the builder's rationale |
| 3 | Prefer a deterministic validator to an LLM validator | mypy, ruff, pytest, mutmut, and git merge are reviewers with zero sycophancy |
| 4 | Enforce with permissions, not prompts | Write scopes are config, not instructions an agent can reason its way past |
| 5 | Bound every loop; escalate context before model | Repeated failure is usually an underspecified task, not an underpowered model |
| 6 | Freeze contracts before parallelism | File-disjointness is not semantic independence |
| 7 | Shadow before gate | A new validator records verdicts for N runs before it can block anything |
| 8 | Isolate at the git layer | One worktree per task; a merge conflict is a decomposition error, not a text problem |

### What "done" looks like for v1

A single request flows: context → plan → human approval → decomposition → contract
freeze → parallel build with paired review → integration → verification → CI → PR →
human promotion → observation. The orchestrator never reads a diff. No agent can
edit a test it is being judged by. No agent can trigger a rollback.

---

## 2. Agent roster

Generators are marked **G**, validators **V**, coordinators **C**, and utility **U**.
"Shadow" means the agent runs and records but does not gate until calibrated.

| Agent | Type | Triggered by | Consumes | Produces | Hands off to |
|---|---|---|---|---|---|
| Core Orchestrator | C | User request | Run manifest, event log | Phase transitions, gate decisions | Everyone |
| Context Gatherer | G | Phase `CONTEXT` | Request, repo, invariant manifest | Context bundle (ref) | Plan Writer |
| Plan Writer | G | Context bundle ready | Context bundle, user dialogue | Plan (ref) | Plan Reviewer |
| Plan Reviewer | V | Plan produced or revised | Plan, context bundle, repo | Findings (blocking/advisory) | Plan Writer, or human gate |
| Task Decomposer | G | Plan approved by human | Plan, ownership map | Interface contract, task specs, merge order | Test Author, Task Dev swarm |
| Test Author | G | Task spec exists | Task spec, interface contract | Failing tests (`tests/**`) | Task Dev |
| Task Dev (swarm) | G | Failing tests committed | Task spec, contract, failing tests | Diff in `src/**` | Code Reviewer |
| Code Reviewer | V *(shadow)* | Task dev reports complete | Task spec, diff, repo | Findings | Task Dev, or Integrator |
| Integrator | G | All tasks approved | Task branches, merge order | Merged branch, shared-file edits | Test Runner |
| Test Runner | U | Integration complete | Merged branch, baseline | Failing test IDs only | Test Investigator |
| Test Investigator | V | Failing tests exist | Failing tests, git history, flake registry | Classification + fix or escalation | Task Dev, Integrator, or human |
| CI Cleanup | G | Verification green | Lint/type/doc failures | Formatting-only diff | Code Reviewer (re-review) |
| PR Reviewer | V | Draft PR opened | Full PR diff, plan | Findings | Orchestrator |
| Security Reviewer | V | Draft PR opened; also at plan time | Plan or diff, threat surface list | Findings | Orchestrator |
| Log Monitor | U | Always on, post-merge | Deterministic alerts, metrics | Correlation summary | Error Analyzer |
| Error Analyzer | V | Alert correlated | Logs, diffs, known patterns | Rollback **proposal** | Human or alerting rule |
| Budget Accountant | U | Every agent completion | Token/cost telemetry | Warnings, hard halt | Orchestrator |
| Invariant Curator | U | Human flags a violation | Human note, run history | Updated invariant manifest | Context Gatherer |

### Agents added that were not in the original sketch

These close specific holes and are argued for in their detail sections below:
**Test Author**, **Integrator**, **Security Reviewer** (split from PR Reviewer and
moved earlier), **Budget Accountant**, **Invariant Curator**.

---

## 3. Agent details

### 3.1 Core Orchestrator (C)

**Function.** Owns the phase state machine and nothing else. Reads the run manifest,
decides the next phase, dispatches the responsible agent, records the result, persists.

**Key properties**
- Context contains only the manifest and the event log. Never a plan body, never a diff.
- The transition function is pure over the manifest, so it is unit-testable with no model client.
- Persists the manifest after every transition. A crashed run resumes from the last phase.
- Holds the only authority to halt a run (budget, blocking findings, human abort).

**Failure mode it guards.** Context rot in the coordinator, which is the failure that
silently degrades every downstream decision at once.

---

### 3.2 Context Gatherer (G)

**Function.** Searches the codebase, RAG index, and git history to assemble a targeted
context bundle for one request, in its own window, so that retrieval noise never enters
the planning window.

**Key properties**
- Read-only. No write scope at all.
- Small model tier, high step budget. This is search, not reasoning.
- Reads the **invariant manifest** first (see 3.18) and does not re-derive documented
  architecture. Retrieval is for what changes; the manifest is for what does not.
- Mines `git log -S` and blame for *why* code exists, not just what it does.
- Output is a bundle written to disk and passed by ref, never inlined into the orchestrator.

**Trigger:** phase `CONTEXT`. **Re-triggered** as escalation step 1 when a task fails
review repeatedly, scoped to that task.

---

### 3.3 Plan Writer (G)

**Function.** Turns the context bundle into an implementation plan, collaboratively with
the user.

**Key properties**
- Large model tier. This is the highest-leverage reasoning step in the pipeline.
- The only build-phase agent with an `ask_user` tool.
- Writes acceptance criteria in a form the Test Author can consume directly. If the plan
  cannot express a criterion as a testable assertion, that is a planning defect, not a
  testing problem.
- Plan must name the threat surfaces it touches (auth, PII, external I/O, secrets) for
  the Security Reviewer's plan-time pass.

---

### 3.4 Plan Reviewer (V)

**Function.** Adversarial critique of the plan before any code exists, which is where
critique is cheapest.

**Key properties**
- **Does not see the Plan Writer's rationale**, only the plan and the context bundle.
  If the writer can explain itself to the reviewer, you have built a persuasion channel,
  and the writer is better at persuading than the reviewer is at resisting.
- Has independent read access to the repo, so it can check the plan's claims rather than
  accept them.
- Classifies every finding **blocking** or **advisory**. Only blocking findings reopen the
  loop; advisory findings become backlog items. Without this you get review ping-pong
  where each round surfaces fresh nits and the plan never converges.
- Bounded: max rounds, then escalate to the human.

---

### 3.5 Task Decomposer (G)

**Function.** Converts an approved plan into an interface contract, a set of mutually
exclusive task specs, and an explicit merge order.

**Key properties**
- **Emits the interface contract first, as a serialized step, before any parallel work.**
  Types, function signatures, API schemas, event shapes. The swarm implements *against*
  frozen seams. This is the single fix for the fact that two agents editing different
  files still collide through type signatures, DI wiring, config keys, and shared exports.
- Consumes a **pre-computed module-to-domain ownership map** supplied by the human rather
  than inferring file ownership from a search. Fewer inferred boundaries, fewer conflicts.
- Emits `merge_order` explicitly. Emergent merge order reintroduces the race you used
  worktrees to remove.
- Ownership disjointness is asserted programmatically before the swarm spawns, not
  discovered when the merges collide.
- Names the shared files no task owns and assigns them to the Integrator.

---

### 3.6 Test Author (G) — **added**

**Function.** Writes the failing tests for a task from the plan's acceptance criteria and
the frozen interface contract.

**Why it exists.** If the same agent writes the failing test and the implementation, it
writes a test its implementation satisfies. That is not TDD, it is a rubber stamp with
extra steps. This is the highest-leverage single change in the design.

**Key properties**
- Write scope is `tests/**` only.
- Runs **before** the Task Dev agent and commits red tests.
- Uses `Hypothesis` for pure functions where practical, since property-based tests remove
  the agent's ability to hand-pick inputs that flatter its own mental model.
- Given a pure unit suite with no external dependencies, test doubles are **typed fakes
  implementing a `Protocol`**, not `unittest.mock.Mock`. `Mock` is `Any`-shaped and
  silently defeats strict mypy; a typed fake turns mock drift into a compile-time error.
  `create_autospec` is the minimum acceptable fallback.

---

### 3.7 Task Dev (G, swarm)

**Function.** Implements one task against frozen contracts until its assigned tests pass.

**Key properties**
- Write scope is `src/**`, **explicitly excluding `tests/**`**. The tautology fix is a
  permission, not a prompt instruction, because a permission holds and an instruction does not.
- One git worktree and one branch per task. Own index, own HEAD, own test runs.
- Runs the full suite locally. A pure unit suite is fast enough to make this unconditional.
- Bounded steps and token budget; reports completion with a diff ref.
- Concurrency ceiling set by review throughput and API rate limits, not by task count.

---

### 3.8 Code Reviewer (V)

**Function.** Judges a task diff against its spec.

**Key properties**
- **Starts in shadow mode.** Records verdicts, gates nothing. Promote only after measured
  precision against your own reviews on the same diffs.
- Information asymmetry: sees the task spec and the diff, not the dev agent's reasoning.
- Tooling asymmetry: **can execute**. Runs the tests, runs mypy, greps for callers. A
  reviewer that only reads is a style checker.
- Model asymmetry: different tier from the builder, at minimum.
- Rubric seeded from the repo's own historical PR review comments. That encodes
  repo-specific knowledge the builder does not have in context, which is real asymmetry
  rather than a differently-worded prompt.
- Findings classified blocking or advisory, same as the Plan Reviewer.

---

### 3.9 Integrator (G) — **added**

**Function.** Merges task branches in the planned order and owns the files no single task
can own: routers, DI containers, `__init__` exports, migrations, dependency manifests.

**Why it exists.** Some files must be touched by every task. Without a designated owner,
the swarm fights over them, and file-disjoint ownership quietly becomes a fiction.

**Key properties**
- The only agent permitted to modify `pyproject.toml` or the lockfile. Dependency changes
  **never** parallelize.
- A **merge conflict is escalated, never auto-resolved.** A conflict means two agents
  believed they owned the same thing. Resolving the text hides the ownership error and
  returns a plausible-looking merge. The task goes back to the Decomposer.
- Runs the full suite after each merge, not just at the end. Catches the case where every
  branch is individually green and the merged result is red.

---

### 3.10 Test Runner (U)

**Function.** Runs the suite on the integrated branch and returns failing test IDs only.

**Key properties**
- Returning only failures is correct for context economy and **dangerous without a
  baseline**, because a deleted test does not fail. Paired with §7's baseline guard.
- Emits a structured report ref, not prose.

---

### 3.11 Test Investigator (V)

**Function.** Classifies each failure as a newly introduced bug, test rot, a spec change,
or a known flake, and routes accordingly.

**Key properties**
- Consumes a **flake registry** you seed by hand from the repo you already know, rather
  than re-deriving "this test is unreliable" every run.
- Has git history access so it can distinguish "this test never passed on this branch"
  from "this test passed before the merge."
- Cannot mark a test as rot and delete it unilaterally. Deleting or skipping a test is a
  blocking finding that requires human sign-off. This is the single most abusable action
  in the pipeline.

---

### 3.12 CI Cleanup (G)

**Function.** Fixes lint, formatting, and documentation gate failures.

**Key properties**
- **Its diff is re-reviewed.** In the original sketch, cleanup ran after code review,
  meaning unreviewed code reached the PR. Either cleanup runs before the review gate or
  its output goes back through it. This design does the latter.
- Constrained to formatting-level changes. Explicitly forbidden from satisfying mypy with
  `cast(Any, ...)` or `# type: ignore`, and from satisfying ruff by deleting an "unused"
  variable that is actually a bug signal. Enforce with a diff-shape check, not a prompt.
- Small model, low step budget. If cleanup needs more than a few steps, it is not cleanup.

---

### 3.13 PR Reviewer (V)

**Function.** Reviews the whole change as a unit, which is the first time anything does.

**Key properties**
- Sees the plan and the full diff. Its question is different from the Code Reviewer's:
  not "is this task correct" but "does the assembled change do what the plan promised,
  and is anything missing."
- Catches the integration-level defect that per-task review structurally cannot.

---

### 3.14 Security Reviewer (V) — **added, and moved earlier**

**Function.** Threat-surface review at **plan time** and again on the PR diff.

**Why it exists.** Security review only at the PR is security review after the
architecture is fixed. The plan-time pass is cheap and catches the class of problem that
cannot be fixed in review.

**Key properties**
- Plan-time pass consumes the threat surfaces the Plan Writer named. If the plan names
  none and touches auth, I/O, or secrets, that itself is a blocking finding.
- Diff-time pass covers injection, secrets in code, dependency changes, and permission
  widening.
- Dependency manifest changes always trigger a supply-chain check, regardless of size.

---

### 3.15 Log Monitor (U)

**Function.** Watches production after promotion and correlates deterministic alerts to
the run that likely caused them.

**Key properties**
- **Detection is not its job.** Deterministic alerting rules fire (error rate over X for
  Y minutes, p99 regression, exception-class spike). LLMs are expensive, latent,
  non-deterministic anomaly detectors, and conventional observability is simply better at
  this. The agent's value is correlation and diagnosis.
- **No rollback tool in its allowlist.** It cannot execute a rollback under any prompt.
- Read-only, scoped production credentials. Never write access, never broad access.

---

### 3.16 Error Analyzer (V)

**Function.** Given a correlated alert, reads the suspect diffs, matches against known
failure patterns, and produces a `RollbackProposal` with evidence and a confidence score.

**Key properties**
- Produces a proposal. **The trigger stays a deterministic rule or a human.** An LLM
  holding the production kill switch is the highest-authority, lowest-evidence component
  in the whole design, and a spurious spike should not be able to revert your main branch.
- Its output includes the specific task IDs it suspects, so the proposal is actionable
  rather than "something is wrong."

---

### 3.17 Budget Accountant (U) — **added**

**Function.** Tracks tokens and spend per run, warns at thresholds, hard-halts at ceiling.

**Why it exists.** A parallel swarm with review loops and model escalation is exactly how
you get a surprise five-figure bill. Unbounded loops plus escalation is a cost multiplier,
not a cost adder.

**Key properties**
- Per-run ceilings on tokens, dollars, wall clock, and review rounds per task.
- Halting is a first-class phase, not an exception.
- Per-agent attribution, so you learn which pair is actually expensive.

---

### 3.18 Invariant Curator (U) — **added**

**Function.** Maintains a static invariant manifest: the architectural facts, prohibitions,
and load-bearing weirdness that live in your head and not in the files.

**Why it exists.** A repo you know well is a repo where the important constraints are
undocumented. "We never call that service directly." "This looks dead but the nightly job
imports it." Agents will violate these confidently, and the violation will be obvious to
you and invisible to every reviewer in the chain.

**Key properties**
- Populated by capture, not by generation. Every time an agent does something that makes
  you wince, that is a line in the manifest.
- Read by the Context Gatherer first, every run.
- Treat the first several runs as an invariant-extraction exercise rather than a
  productivity exercise. That is the actual deliverable of week one.

---

## 4. Gates

Every gate returns the same shape: pass/fail, findings classified blocking or advisory,
an evidence ref, and a shadow flag. That uniformity is what lets a deterministic check
replace an agent check later without touching the orchestrator.

### 4.1 Deterministic gates (preferred wherever they exist)

| Gate | Phase | Blocking | Notes |
|---|---|---|---|
| `ownership.disjoint` | Contract freeze | Yes | Asserted before the swarm spawns |
| `typecheck.strict` | Build, Verification | Yes | mypy strict; catches what no reviewer reliably does |
| `lint.ruff` | CI | Yes | |
| `tests.pass` | Verification | Yes | Full suite, integrated branch |
| `tests.baseline_delta` | Verification | Yes | See §7 — the anti-deletion guard |
| `mutation.diff_scoped` | Verification | Yes | Surviving mutants on changed files only |
| `merge.no_conflict` | Integration | Yes | A conflict routes to the Decomposer, not to an agent |
| `deps.unchanged_or_reviewed` | CI | Yes | Lockfile changes force supply-chain review |
| `budget.within_ceiling` | Every transition | Yes | Halts the run |

### 4.2 Agent gates

| Gate | Phase | Initially | Promotes when |
|---|---|---|---|
| `plan.review` | Planning | Gating | — |
| `code.review` | Build | **Shadow** | Precision measured against human review over N tasks |
| `test.classification` | Verification | Gating, with human sign-off required for any deletion |
| `pr.review` | Pull request | Gating | — |
| `security.plan` | Planning | Gating | — |
| `security.diff` | Pull request | Gating | — |

### 4.3 Human gates

| Gate | Phase | Type | What the human is actually deciding |
|---|---|---|---|
| Plan approval | `PLAN_APPROVAL` | Blocking | Is this the right change, and is the decomposition sane |
| Contract review | `CONTRACT_FREEZE` | **Recommended, blocking** | Are the interface seams and the file ownership map correct |
| Test deletion sign-off | Verification | Blocking, conditional | Only fires if an agent proposes removing or skipping a test |
| QA to prod promotion | `PROMOTION` | Blocking | Is this safe to ship |
| Escalation terminus | Any | On demand | Reached when the escalation ladder exhausts |
| Rollback authorization | `OBSERVATION` | Blocking | Human or deterministic rule; never the agent |

**The contract review gate is new and worth the two minutes.** Reading the frozen
interface and the ownership map is the cheapest possible intervention point, and it
prevents the most expensive class of failure — a swarm that runs to completion against
the wrong seams.

**Human decisions are recorded structurally**, including which shadow gates the human
overturned. That record is the calibration dataset (§8).

---

## 5. Loop control and escalation

Every generator/validator pair is a bounded loop.

1. Validator returns findings.
2. **Blocking** findings reopen the loop. **Advisory** findings become backlog items and
   never reopen it.
3. On re-review, the validator sees only the delta plus the original spec.
4. Round count increments. At each threshold, climb the escalation ladder:

| Step | Action | Rationale |
|---|---|---|
| 1 | **Re-gather context**, scoped to this task | Cheapest, and most often the actual cause |
| 2 | **Re-spec the task** via the Decomposer | Repeated failure usually means an ambiguous task |
| 3 | **Escalate the model** tier | Only after the two cheaper explanations are excluded |
| 4 | **Human** | Terminus |

Escalating the model first treats a specification problem as a capability problem, which
is how you end up paying large-model rates to fail at an underspecified task.

---

## 6. Isolation and integration

**One git worktree per task**, `git worktree add ../wt-<task-id> -b task/<task-id>`.

The reason is narrower than it looks. Your ownership map isolates the *writes*. It does
nothing for the *reads*: the moment one agent runs pytest, the interpreter imports the
whole package including the file another agent is halfway through rewriting. Verification
is repo-scoped even when editing is file-scoped.

Worktrees also give you a separate git index per agent (no `index.lock` contention),
atomic per-task revert, and per-task attribution. The object store is shared, so there is
no re-clone cost, and with `uv` a per-tree environment is a few warm-cache seconds.

**Containers are not required here**, because the suite is pure unit tests with no
external dependencies. Revisit only if tests start binding ports, needing a database, or
running migrations.

**Merge order is planned, not emergent**: interface contract commit, then tasks in
dependency order, then the Integrator's shared-file commit.

---

## 7. Anti-reward-hacking guards

The pipeline's objective is "tests pass and reviews approve." Both are hackable, and the
cheapest path to green is usually the dishonest one.

| Attack | Guard |
|---|---|
| Delete or skip a failing test | Baseline snapshot before the swarm: test count, skip count, coverage. Any reduction is a blocking CI failure, not a review comment |
| Weaken an assertion | Diff-scoped mutation testing. A test that still passes when `>` becomes `>=` is theater |
| Write a test the implementation trivially satisfies | Test Author is a separate agent with a disjoint write scope |
| Mock away the behaviour under test | Typed `Protocol` fakes checked by strict mypy; `Mock` is `Any`-shaped and invisible to the type checker |
| Silence a type error | CI Cleanup diff-shape check forbids `cast(Any, ...)`, `# type: ignore`, and bare `except: pass` |
| Reviewer ratifies the builder | Information, tooling, and model asymmetry; shadow-mode calibration |

**Mutation testing scoped to the diff is the standout recommendation.** A fast hermetic
unit suite makes `mutmut` affordable, and it is the only deterministic answer to "did the
agent write a real test or a tautology?" Run it per task branch against changed files only.

---

## 8. Measurement and calibration

Without this section the validator agents are unfalsifiable, and expensive ceremony looks
identical to expensive value from inside the loop.

**Verdict ledger.** Every `GateResult` is appended with its subject ref, its findings, and
what happened next: did a human overturn it, did the bug reach production, did the plan
materially change after the reviewer objected. Over time this yields per-gate precision
and recall.

**Shadow mode as the default onboarding path.** New validators record for N runs, gate
after. You are the oracle on this repo, which is exactly the condition that makes
calibration possible — you can grade the graders here in a way you could not on an
unfamiliar codebase. Spend that advantage before it is gone.

**Version the agent specs.** Every `GateResult` records the spec version that produced it.
Change a reviewer's prompt and your historical precision data for that reviewer is
invalidated; without versioning you will not notice.

**Track cost per pair.** Precision is only half the question. A reviewer with good
precision that costs more than the defects it catches is still the wrong trade.

---

## 9. Build order

Ordered by decreasing certainty, so that the components with the most authority are built
last, on the most evidence.

1. Run manifest persistence and the pure `next_phase` transition — makes everything resumable
2. `assert_disjoint_ownership` plus the worktree lifecycle
3. Baseline snapshot and the test-count/skip/coverage guard
4. Test Author split out from Task Dev, with disjoint write scopes
5. Code Reviewer in shadow, accumulating verdicts against your own reviews
6. Diff-scoped mutation gate
7. Interface contract freeze and the human contract-review gate
8. Integrator and planned merge order
9. Budget Accountant
10. PR Reviewer and Security Reviewer
11. Log Monitor and Error Analyzer, proposal-only
12. Rollback authorization, deterministic rule or human

---

## 10. Open questions

1. **Task granularity.** What is one task — a file, a module, a vertical slice? This sets
   swarm width and conflict rate, and it is the parameter most likely to be wrong on the
   first attempt.
2. **Concurrency ceiling.** Set by API rate limits, review throughput, or machine
   resources? Whichever binds first should be explicit rather than discovered.
3. **Plan Writer dialogue depth.** How much user interaction before the plan is "drafted"?
   Too little and the review loop does work the human could have done in one sentence.
4. **Where does the run manifest live?** Repo-local `.runs/`, or out of tree? In-tree gives
   you free versioning and PR-visible provenance, but it puts run state in the diff.
5. **Secrets posture.** Which agents get which credentials, and does anything in the build
   phase need more than read access to the repo?
