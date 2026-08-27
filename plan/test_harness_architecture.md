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
`mutation.diff_scoped` (design doc §9.1): run `mutmut` per task branch, scoped to files the task actually changed — never the whole repo. A pure, hermetic unit suite (this project's stated target environment) makes this affordable at diff scope where it would be too slow to run on every commit at repo scope. A surviving mutant (a code mutation that doesn't make any test fail) on a changed file is a blocking Verification-phase finding: it means some line in the diff has no test that actually exercises its behavior, only its shape.

### 3.3 Why diff-scoped, not repo-wide
Scoping to the diff is what makes this a per-task gate rather than a nightly job — it runs inside the same Verification phase as `tests.baseline_delta` and reports on the same timescale a Task Dev agent can act on. Repo-wide mutation testing on every change would reintroduce the runtime cost this design otherwise avoids by keeping the Task Author/Task Dev split and Protocol fakes cheap.
