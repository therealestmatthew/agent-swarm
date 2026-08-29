---
title: Infrastructure Triage Matrix
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Infrastructure Triage Matrix

**Referenced by:** `agentic-sdlc-design-v0.5.md` §6 (Test Investigator & Flake Handling)

## Purpose

Classify test failures — especially from browser automation (Selenium/Playwright) — using structured telemetry captured at the point of failure, *before* any LLM sees the failure. This avoids two problems with classifying off raw error strings or stack traces: it's brittle across frameworks and browser vendors, and it invites the same hallucination risk the Shared-File Intent Service (§4) was built to eliminate — text is a lossy proxy for what actually happened.

The table below is a **deterministic rules engine**. It runs first. Only failures that don't cleanly match a rule reach the Test Investigator agent for judgment.

---

## 1. The `FailureSignature` schema

Captured by the test harness itself at the moment of failure — not reconstructed later from logs.

```python
from enum import Enum
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field

class FailureSignature(BaseModel, frozen=True):
    model_config = ConfigDict(extra="forbid")

    error_class: str
    # e.g. TimeoutError, StaleElementReferenceError, AssertionError,
    # ElementNotInteractableError, NetworkError

    elapsed_ms: int
    # wall-clock time from action start to failure

    configured_timeout_ms: int | None
    # the timeout that was in effect for this action, if any

    isolated_rerun_outcome: Literal["passed", "failed_again", "not_yet_run"]
    # result of the automatic isolated re-run (design doc §6, step 1)

    # Adapter-declared telemetry (core_adapter_boundary.md §2.2). Keys and value types are
    # declared by the target repo's RepoDeclaration.signals and validated against it on
    # capture; the triage rules that read them are adapter data too. This exists because an
    # adapter cannot add fields to an extra="forbid" model without forking the schema per
    # repo -- exactly the drift this file exists to prevent.
    signals: dict[str, Any] = Field(default_factory=dict)
```

---

## 2. Deterministic rules engine

Rules are evaluated **in order**. The first matching rule wins; if none match, the signature falls through to the Test Investigator (§3).

| Order | Condition | Classification | Routes to |
|---|---|---|---|
| 1 | `dom_state_diff_from_baseline == True` (after applying `DOMCaptureConfig.ignore_selectors` to filter volatile elements) | **Infra — state leakage** (evaluated first; polluted state at t=0 isn't a timing question and shouldn't be shadowed by a timeout check below) | Environment/Infra queue |
| 2 | `configured_timeout_ms` is not `None` AND `elapsed_ms` within 10% of `configured_timeout_ms` AND `isolated_rerun_outcome == "passed"` | **Infra — timing** | Environment/Infra queue |
| 3 | `network_calls_over_threshold > 0` AND `isolated_rerun_outcome == "passed"` | **Infra — network** | Environment/Infra queue |
| 4 | `dom_state_diff_from_baseline == False` AND no timeout proximity AND `isolated_rerun_outcome == "failed_again"` | **Logic** | Task Dev (bounded loop, design doc §7) |
| — | *(no rule matches)* | **Ambiguous** | Test Investigator agent |

### Why order matters
Rule 1 is checked before rule 2 deliberately: a test that starts with dirty state can *also* run slow (cleanup code retrying against stale state, extra DOM queries against leftover elements), which would otherwise false-match the timing rule. State leakage is the more specific and more actionable diagnosis, so it takes priority.

### Explicit fallback behavior
A signature that partially matches — e.g., an `AssertionError` (not a timeout-class error) that also co-occurs with elevated `network_calls_over_threshold` — does **not** get forced into the nearest bucket. Rule 3 requires `isolated_rerun_outcome == "passed"`; an assertion failure that fails again on rerun won't match it, and correctly falls through to the Test Investigator rather than being misclassified as a network flake it might only coincidentally correlate with.

---

## 3. Test Investigator fallback

Failures that reach this stage get the full agent treatment described in the core design doc (§6): the Investigator queries the Context Gatherer for related test context on demand and applies judgment the deterministic table isn't confident enough to apply automatically. Its classification is logged alongside the `FailureSignature` that failed to match — this log is the raw material for periodically reviewing whether the rules engine needs a new rule (e.g., if the same ambiguous pattern recurs often enough to deserve its own deterministic bucket).

---

## 4. Environment/Infra queue

Failures classified as infra (rules 1–3) do **not** enter the standard Task Dev code-fix loop. They route to a separate queue for environment-level remediation (test harness configuration, timeout tuning, browser profile setup) — distinct from the code-fix path, since sending an infra issue through a code-fix loop would either fail to converge (there's no code bug to fix) or produce a spurious "fix" that papers over an environment problem (e.g., an agent adding an arbitrary sleep to mask a timing issue).
