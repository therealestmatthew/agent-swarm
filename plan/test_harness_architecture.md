---
title: Test Harness Architecture
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Test Harness Architecture

**Referenced by:** `agentic-sdlc-design-v0.5.md` §6 (Test Investigator & Failure Triage) · §9.1 (`mutation.diff_scoped`, `gate_coverage.minimum`) · §10 (anti-reward-hacking, the coverage-bypass row) · `infra_triage_matrix.md` §1 (`FailureSignature.dom_state_diff_from_baseline`) · `plan/contracts/`

## Purpose

This file owns the mechanics of the verification layer that the core design document only references: how a clean test environment is guaranteed, what standard test doubles must meet so a passing test actually means something, and how a test that passes for the wrong reason gets caught.

---

## 1. Baseline Management

### 1.1 The problem this solves
`FailureSignature.dom_state_diff_from_baseline` (see `plan/contracts/verification.py`) is only trustworthy if "baseline" is unambiguous and the mechanism that produces it can't itself leak state. This section defines both.

### 1.2 Execution Tiers and Reset Mandates

The previous strict mandate of "construct fresh, never clean in place" has been relaxed in favor of tiered execution. Some environments (like Selenium) face start-up times in seconds rather than milliseconds. Instead of universally enforcing a slow cold-start per test, testing is organized into tiers (`TestTier.execution_tier`):

- **Tier 1 (Unit):** (`tier1_unit`) Fully hermetic. Fast, in-process or pure-memory resets.
- **Tier 2 (Integration):** (`tier2_integration`) Transaction rollbacks or local service state resets.
- **Tier 3 (Browser/E2E):** (`tier3_browser`) May utilize a warm **browser pool** (via the `browser_pool_checkout` strategy) to dramatically lower per-test cost. In-place cleaning is permitted here.

**State Leakage Protection:** To prevent the classic problem of state leakage from in-place cleaning (e.g., lingering service workers, IndexedDB, or leaked database connections), we rely entirely on the deterministic triage table (`infra_triage_matrix.md`). If a test passes in isolation but fails when run in the suite, the triage matrix automatically classifies it as state leakage. This makes the relaxed rule safe: the system functionally catches and flags leaky state resets rather than statically banning them at the cost of high overhead.

### 1.3 Reset strategies are declared, not assumed

The mechanism is therefore adapter data: `ResetStrategy` in `plan/contracts/governance.py`, named
per tier by `TestTier.reset_strategy_id`. A strategy declares its `strategy_type` (e.g., `browser_pool_checkout`), `pool_size` if applicable, what it recreates, what the host must give it (`ResetResource`), what it costs, and what its clean-state check actually inspects.

`typical_cost_ms` is load-bearing rather than documentation. Core feeds it into the wall-clock
estimate and the concurrency ceiling, so a two-second reset is a budget fact the pipeline reasons
with rather than a footnote someone reads later.

`requires` is what makes the isolation unit derivable rather than a judgment call — see
`execution_isolation.md` §5, which is the other half of this decision.

### 1.4 What "baseline" is, and when it's captured

Baseline is the **declared clean state** — which, once hydration exists, means the declared
*post-hydration* state, not canonical emptiness (`core_adapter_boundary.md` §4). It is captured
**immediately after instance construction and hydration, before the test's first action**. The
clean-state signal is the comparison of actual state at that t=0 moment against the declaration —
never against the previous test's end state, which per §1.2 should not exist.

The reference browser adapter's checks, which is what this table always was:

| Check | Flags as diff if |
|---|---|
| Cookie count/keys | Nonzero |
| `localStorage` / `sessionStorage` key count | Nonzero |
| Open dialog/modal count | Nonzero |
| Active WebSocket / pending fetch count | Nonzero |
| Viewport dimensions | Differ from configured default |

A backend adapter's list is different in every row and identical in shape: open connections, temp
files, registered signal handlers, module-registry delta. Any single mismatch sets the strategy's
clean-state signal `True`, which is what `dom_state_diff_from_baseline` — and its successors in
`FailureSignature.signals` — report.

### 1.5 Verifying that the reset actually worked

§1.2 asserted that full teardown produces a clean slate. Nothing checked. That is a load-bearing
assertion about a mechanism, in a design whose stated rule is not to assert what has not been run —
and the evidence needed to check it already exists, unused for this purpose.

**A clean-state diff at t=0 means the reset did not work.** Per-test, that is a state-leakage
failure and `infra_triage_matrix.md` rule 1 already routes it. In *aggregate over a strategy*, it is
something else: evidence about the mechanism rather than about any one test. A strategy whose
diff rate exceeds `GovernancePolicy.max_baseline_diff_rate` is not isolating, whatever it claims.

Core therefore audits each strategy against its own diff rate and, above the threshold, **demotes
the tier to the strictest strategy the repo declares**, recording the demotion in
`RunManifest.policy_adjustments`.

The asymmetry is deliberate:

- **Tightening is automatic.** Moving to a stricter reset costs wall-clock time and nothing else.
- **Loosening is a human gate.** Moving to a cheaper reset trades correctness for speed, and it is
  self-rewarding for whoever proposes it (`core_adapter_boundary.md` §3.1) — so it is never
  something the pipeline does to itself.

This is the same shape as the cumulative conflict counter driving shared-file promotion (design doc
§4.6): evidence accumulates against a threshold, and crossing it changes governance rather than
being noted and forgotten. It also closes the loophole that would otherwise open the moment resets
became declarable — an adapter could declare a cheap reset, gain a fast suite, and push the cost
onto triage quality where it would look like flakiness rather than like a declaration.

---

## 2. Test Double Standards

### 2.1 Protocol fakes over `Any`-shaped mocks
Every fake used in a Task Dev agent's tests must implement a named `typing.Protocol` matching the real dependency's interface, enforced under strict mypy. Bare `unittest.mock.MagicMock` (or any untyped stub) standing in for a collaborator is not permitted.

### 2.2 Why this matters specifically here
Because Test Author writes tests before implementation exists (TDD-first, Principle 3), a loosely-typed mock will happily accept calls to methods that don't exist yet or accept the wrong signature — and the test still passes. That's a tautological test: it validates the mock's leniency, not the code's conformance to a real contract. Under strict mypy, a Protocol-typed fake fails to type-check the moment the implementation's actual interface drifts from what the test expects — turning a silent runtime gap into a caught type error during the Code Reviewer loop, well before it could ever reach the Test Investigator as a mystery flake.

### 2.3 Where Protocol definitions come from
Protocol definitions for shared dependencies are produced at **Contract Freeze** (design doc §3, Phase 2 & 3) as part of the interface map — not invented ad hoc by whichever Test Author or Task Dev agent happens to need a fake first. Two agents independently inventing two slightly different Protocols for the same dependency reintroduces, at the type level, the same kind of semantic drift the Shared-File Intent Service (design doc §4) exists to prevent for shared files.

### 2.4 Fixture data
Where a fake needs to return structured data — not just satisfy a call signature — that data is constructed from the same Pydantic models in `plan/contracts/` that the real code uses, not parallel dict literals or ad hoc dataclasses. A fixture built from the shared schema can't silently drift from what the real code actually produces; a hand-rolled one can.

---

## 3. Diff-Scoped Mutation Testing

*Reinstated from `agentic-sdlc-design-v0.1.md` §7, absent v0.2 through v0.4 — see `plan/versions/REGRESSION.md`.*

### 3.1 What Protocol fakes don't catch
§2 makes a mock's *shape* honest: a fake can't silently accept a call the real dependency wouldn't. It says nothing about a test's *assertions*. A test that calls the real code with the real shape and then asserts `result >= expected` where the spec means `result > expected` type-checks perfectly and passes forever, on both the correct implementation and a subtly wrong one. Weakening an assertion is a different attack from mocking away behavior, and it needs a different guard.

### 3.2 The gate
`mutation.diff_scoped` (design doc §9.1): run `mutmut` per task branch, scoped to the lines the task actually changed — never the whole repo, and (per §3.4) never the whole of a file the task only partly touched. A surviving mutant — a code mutation that makes no test fail — on an in-scope line is a blocking Verification-phase finding: some line in the diff has a test that exercises its shape but not its behavior.

*This section originally scoped the gate to "files the task changed" and justified its affordability with "a pure, hermetic unit suite (this project's stated target environment)." Both were too loose to implement against, and the second silently assumed the whole repo was hermetic. §3.4 onward is the predicate that replaces them (D5 in `implementation_roadmap.md`).*

### 3.3 Why diff-scoped, not repo-wide
Scoping to the diff is what makes this a per-task gate rather than a nightly job — it runs inside the same Verification phase as `tests.baseline_delta` and reports on the same timescale a Task Dev agent can act on. Repo-wide mutation testing on every change would reintroduce the runtime cost this design otherwise avoids by keeping the Task Author/Task Dev split and Protocol fakes cheap.

### 3.4 The scope predicate

The unit of scope is the **changed line**, not the changed file. A task that edits line 12 of a
500-line module has not made lines 13–500 its responsibility, and blocking its PR on a surviving
mutant at line 400 would be exactly the "widening the PR" the rest of this design forbids — it
reports someone else's untested code as this task's failure. Scope is the union of the diff's added
and modified lines in the task's write scope, excluding `tests/**` (mutating a test asserts nothing,
and it is Test Author's scope anyway).

Within that set, each line is classified against the **hermetic** tiers declared in
`RepoDeclaration.test_tiers` — `hermetic` being a verified claim, not a trusted one
(`core_adapter_boundary.md` §3.1):

| Line is | Verdict | Handled by |
|---|---|---|
| Covered by at least one hermetic tier | **In scope.** A surviving mutant is blocking | `mutation.diff_scoped` |
| Covered only by non-hermetic tiers | Out of mutation scope, **not unexamined** | §3.6 |
| Covered by no tier at all | Never reaches mutation | `tests.diff_covered` (§3.5) |

### 3.5 Coverage first, mutation second

A line with no test coverage produces a surviving mutant *by construction* — nothing fails because
nothing runs it. So a naive predicate makes mutation testing double as a coverage check, and pays
for the privilege at (mutants × full suite runtime) to learn what one coverage run reports in
seconds. On a diff touching untested code that is the dominant cost in the Verification phase, and
it charges it against the Budget Enforcer's ceiling (`budget_and_escalation_policy.md` §4) for no
additional signal.

A cheap gate therefore runs first:

> **`tests.diff_covered`** — every in-scope changed line is covered by at least one tier. Blocking.
> Measured against hermetic tiers for the mutation decision, and against all tiers for the
> coverage decision, so the two questions do not get conflated.

Only lines that survive it enter the mutation run, where mutation answers the question it is
actually good at: *the covering test exists — is it real, or is it a tautology?* This ordering is
the same deterministic-before-expensive discipline as `infra_triage_matrix.md`'s rules-before-LLM:
run the cheap decisive check first and hand the expensive one only the residue.

### 3.6 Lines covered only by a non-hermetic tier

This is where the gate would fail open, and it is not a corner case — it is the common case for the
kind of repo this pipeline exists to govern. Browser-driven DOM extraction logic is frequently
exercised *only* by browser tests, which means the code the project cares most about would be the
code no mutation gate ever touches, silently.

So "out of mutation scope" must not resolve to "passed." The gate returns
`GateApplicability.NOT_APPLICABLE` for those lines with the reason attached, which surfaces in the
PR as *not applicable — no hermetic coverage for these lines*, never as a green check. What happens
next is `GovernancePolicy`'s call, not the repo's:

- **Refuse** — the lines must gain hermetic coverage before the task can merge. Strong, and it
  applies steady pressure toward testable decomposition.
- **Degrade and record** — the task merges with the shortfall named in the PR and recorded in
  `RunManifest.policy_adjustments`.

Both are visible. Neither is a silent pass.

### 3.7 A repo with no hermetic tier at all

If `RepoDeclaration.test_tiers` contains no hermetic tier, every changed line falls into §3.6 and
the gate applies nowhere. Rather than inventing an escape for this, it reuses the machinery that
already exists: `mutation.diff_scoped` is simply an **absent capability**, and
`GovernancePolicy.absent_capability_policy` decides between refusing the run and degrading it
visibly (`core_adapter_boundary.md` §3.5).

That makes one contract combination incoherent, and Core rejects it at validation rather than
discovering it in Phase 6: **declaring `Capability.MUTATION_TESTING` while declaring no hermetic
tier** is a contradiction, and yields `HaltReason.ADAPTER_INVALID`. A repo may honestly have no
hermetic tier; it may not claim a capability its own declaration rules out.

### 3.8 Equivalent mutants, timeouts, and the cost ceiling

Three ways this gate misbehaves if left unspecified:

**Equivalent mutants.** Some mutations are semantically identical to the original — `x * 1` for
`x`, a reordering with no observable effect. No test can kill them, so a blocking finding on one is
both unfair and unfixable, and an agent told to fix it will burn its whole loop ceiling against a
target that does not exist. These need the same treatment as a known flaky test: an
**equivalent-mutant registry**, structured exactly like the Flake Registry, where an entry is
**signed by a human**. An agent may propose an equivalence; it may never record one — this is a
test-suppression decision, and design doc §9.3 already puts every one of those behind a person.

**Timeouts.** A mutant that makes the suite hang is counted as **killed**, not surviving. The
mutation changed observable behavior; that the observation is "it never terminates" does not make
the test weak.

**Cost.** Mutation cost is (mutants × suite runtime), and a large diff multiplies both.
`GovernancePolicy` therefore carries a **max-mutants-per-task ceiling**. Exceeding it is not handled
by silently sampling — that would report a partial run as a full one, which is the failure this
whole document exists to prevent. It halts the gate and reports the overflow, and it should be read
as a **task-size signal**: a diff generating more mutants than the ceiling is a diff the Task
Decomposer drew too large. That is the same signal as the additive-intent threshold
(`structural_change_runbook.md` §4) and task granularity (design doc §12) — three ceilings that are
three views of one knob, which is why D13 records that resolving any of them alone will produce
numbers that contradict the other two.

### 3.9 Diff triviality classification

§3.6 and §3.7 answer, per line and per repo, what the mutation gate does when nothing hermetic
covers the code. Both branches can honestly return `NOT_APPLICABLE` or `DEGRADED` on every line
of a diff — and under `absent_capability_policy = DEGRADE` (the default), that is a merge with
the shortfall named in the PR rather than a block. That is the right call for a genuinely trivial
change; it is the wrong call for an adversarial diff shaped so *every* changed line lands where the
hermetic tiers do not run. Design doc §10 names the attack: modify code paths the hermetic tiers do
not cover so `mutation.diff_scoped` and `tests.diff_covered` both scope out, then walk past a silent
green built out of honest per-line scope-outs.

The `gate_coverage.minimum` meta-gate (design doc §9.1) is the answer, and it needs one input this
section owns: whether the *diff itself* is code that the coverage family should have applied to.
That label is `DiffClassification` (`plan/contracts/verification.py`), computed once by Core before
Phase 6 begins from the task's write-scope diff and carried on `RunManifest.diff_classification`
(`plan/contracts/orchestration.py`), the same place the §4.5 rejection graph lives so H8 crash
recovery preserves both together.

**The starting rule (illustrative, per CLAUDE.md convention):**

- `TRIVIAL_DOCS` iff **every** changed path in the task's write-scope diff matches Core's
  built-in extension allow-list (`.md`, `.rst`, `.txt`) **or** matches one of
  `RepoDeclaration.trivial_path_globs` (`plan/contracts/governance.py`) — adapter-tunable, so
  a repo whose `docs/**` tree, `CHANGELOG.*`, or `LICENSE` file is trivial by construction can
  extend the rule without editing Core.
- `NON_TRIVIAL_CODE` otherwise.

This is extension-only and deliberately conservative. A source file whose diff is comment-only
classifies as `NON_TRIVIAL_CODE` under this rule, because Core has no AST-aware detection in the
starting version. That is a **fail-safe misclassification**: it forces the coverage family to
apply to a change that likely does not need it, which costs a re-plan or a policy-recorded
degrade — never a silent pass. AST-aware detection (whitespace-only Python hunks, docstring-only
changes, per-language rules for header/import blocks) is a defensible upgrade and is deferred to
design doc §12's open questions rather than smuggled into the starting rule.

**How this differs from §3.6 and §3.7.** Both prior sections are line-level or capability-level
policy answers: one line has no hermetic tier over it (§3.6), or the whole repo has no hermetic
tier declared (§3.7). §3.9 is the *diff-level aggregate* — the observation that even when every
line's policy branch is legitimately `DEGRADE`, the *whole diff* is untested by construction, and
that is a task-scoped boundary failure rather than a recorded adjustment. §3.6 says "this line
lacks hermetic coverage — degrade or refuse per policy"; §3.9 says "the whole `NON_TRIVIAL_CODE`
diff has no `APPLIED`-and-passing coverage-family result — task drops from
`RunManifest.active_task_ids`, same mechanism §4.5's deadlock detector uses." The two never fire on
the same evidence: §3.6 governs per-line policy, §3.9 governs per-diff aggregate.

**Cross-references:** design doc §9.1 (`gate_coverage.minimum` row), §10 (the attack row this
guard closes), §12 (the triviality-heuristic upgrade open question);
`plan/contracts/verification.py` (`DiffClassification`); `plan/contracts/orchestration.py`
(`RunManifest.diff_classification`); `plan/contracts/governance.py`
(`RepoDeclaration.trivial_path_globs`).
