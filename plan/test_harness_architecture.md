---
title: Test Harness Architecture
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Test Harness Architecture

**Referenced by:** `agentic-sdlc-design-v0.5.md` §6 (Test Investigator & Failure Triage) · §9.1 (`mutation.diff_scoped`) · `infra_triage_matrix.md` §1 (`FailureSignature.dom_state_diff_from_baseline`) · `agent_interface_contracts.py`

## Purpose

This file owns the mechanics of the verification layer that the core design document only references: how a clean test environment is guaranteed, what standard test doubles must meet so a passing test actually means something, and how a test that passes for the wrong reason gets caught.

---

## 1. Baseline Management

### 1.1 The problem this solves
`FailureSignature.dom_state_diff_from_baseline` (see `agent_interface_contracts.py`) is only trustworthy if "baseline" is unambiguous and the mechanism that produces it can't itself leak state. This section defines both.

### 1.2 Capture rule: full teardown/rebuild, not surgical clearing
For DOM-heavy automation (Selenium/Playwright): **every test gets a freshly constructed browser context.** No context reuse across tests, even for performance — surgically clearing cookies/localStorage in place is explicitly disallowed as the sole isolation mechanism.

```
Mandate:
  before each test:  browser.new_context()   (or framework equivalent)
  after each test:   context.close()
  never:             clear cookies/storage on a reused context and call it clean
```

**Why:** cookie- and storage-clearing routines only reach what they explicitly enumerate. Service workers, cache storage, IndexedDB, open native dialogs, and in-flight download state routinely fall outside that enumeration and persist silently between tests. A leaky clearing mechanism doesn't just cause occasional flakiness — it undermines the signal `dom_state_diff_from_baseline` exists to produce, and `infra_triage_matrix.md`'s rule ordering (state-leakage checked *before* timing) depends on that signal being trustworthy. If the field can be wrong, the whole ordering rationale collapses.

**Cost tradeoff, stated explicitly:** full teardown/rebuild costs more wall-clock time per test than in-place clearing. This is accepted deliberately — the alternative degrades a load-bearing signal in the triage system, and a flake-detection mechanism that can't trust its own inputs is worse than a slower one that can.

### 1.3 What "baseline" is, and when it's captured
Baseline is a canonical empty state, defined once:

- Zero cookies
- Empty `localStorage` / `sessionStorage`
- No open modals or native dialogs
- Default configured viewport
- No pending network requests

It is captured **immediately after context creation, before the test's first action.** `dom_state_diff_from_baseline` is the comparison of actual state at that t=0 moment against this canonical empty state — never against the previous test's end state, which (per §1.2) shouldn't exist anyway since contexts aren't reused.

### 1.4 What's actually compared
| Check | Flags as diff if |
|---|---|
| Cookie count/keys | Nonzero |
| `localStorage` / `sessionStorage` key count | Nonzero |
| Open dialog/modal count | Nonzero |
| Active WebSocket / pending fetch count | Nonzero |
| Viewport dimensions | Differ from configured default |

Any single nonzero mismatch sets `dom_state_diff_from_baseline = True`.

---

## 2. Test Double Standards

### 2.1 Protocol fakes over `Any`-shaped mocks
Every fake used in a Task Dev agent's tests must implement a named `typing.Protocol` matching the real dependency's interface, enforced under strict mypy. Bare `unittest.mock.MagicMock` (or any untyped stub) standing in for a collaborator is not permitted.

### 2.2 Why this matters specifically here
Because Test Author writes tests before implementation exists (TDD-first, Principle 3), a loosely-typed mock will happily accept calls to methods that don't exist yet or accept the wrong signature — and the test still passes. That's a tautological test: it validates the mock's leniency, not the code's conformance to a real contract. Under strict mypy, a Protocol-typed fake fails to type-check the moment the implementation's actual interface drifts from what the test expects — turning a silent runtime gap into a caught type error during the Code Reviewer loop, well before it could ever reach the Test Investigator as a mystery flake.

### 2.3 Where Protocol definitions come from
Protocol definitions for shared dependencies are produced at **Contract Freeze** (design doc §3, Phase 2 & 3) as part of the interface map — not invented ad hoc by whichever Test Author or Task Dev agent happens to need a fake first. Two agents independently inventing two slightly different Protocols for the same dependency reintroduces, at the type level, the same kind of semantic drift the Shared-File Intent Service (design doc §4) exists to prevent for shared files.

### 2.4 Fixture data
Where a fake needs to return structured data — not just satisfy a call signature — that data is constructed from the same Pydantic models in `agent_interface_contracts.py` that the real code uses, not parallel dict literals or ad hoc dataclasses. A fixture built from the shared schema can't silently drift from what the real code actually produces; a hand-rolled one can.

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
