---
title: "Remediation Plan: Finding C3 - The NOT_APPLICABLE Gate Bypass"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Remediation Plan: Finding C3 - The NOT_APPLICABLE Gate Bypass

## 1. Finding Summary
**Finding C3:** An adversarial or poorly-prompted Task Dev agent can bypass the mutation gate by intentionally structuring code changes to fall outside the scope of hermetic test triggers. This forces the deterministic testing gates (like `mutation.diff_scoped`) to return `NOT_APPLICABLE`, effectively avoiding verification and allowing potentially untested or poorly-tested changes to pass.

## 2. Root Cause
The deterministic gates in the system, specifically `mutation.diff_scoped`, are designed to return `NOT_APPLICABLE` when a change doesn't intersect with hermetically testable code. However, the system architecture implicitly treats `NOT_APPLICABLE` as a non-blocking state. If an agent modifies critical code but evades test coverage mappings, all blocking testing gates might return `NOT_APPLICABLE`. Without a meta-check to ensure a minimum level of applicable verification for non-trivial code changes, the system is vulnerable to bypasses.

## 3. Detailed Remediation Plan

To address this, we must introduce a "coverage gap detector" that acts as a meta-gate. This meta-gate will evaluate the aggregate applicability of all testing gates against the nature of the diff.

### A. New Meta-Gate: `gate_coverage.minimum`
We will introduce a new deterministic gate named `gate_coverage.minimum`. 
- **Execution:** Runs in **Phase 6 (Verification)**, after all standard deterministic gates have executed.
- **Logic:** 
  1. Parse the diff to determine if it is a "trivial" or "docs-only" change (e.g., changes only to `.md` files, comments, or whitespace).
  2. If the diff contains non-trivial code modifications (e.g., changes to `.py` source files).
  3. Assert that at least one blocking gate (e.g., `tests.diff_covered`, `mutation.diff_scoped`) returned `APPLICABLE` and `PASS`.
  4. If all blocking testing gates return `NOT_APPLICABLE` on a non-trivial code diff, the `gate_coverage.minimum` gate returns `FAIL` with a detailed finding.

### B. Schema Modifications
We need to update the Pydantic schemas in `plan/agent_interface_contracts.py` to support meta-gate analysis and explicit triviality declarations, adhering to the `frozen=True` and `extra="forbid"` design constraints.

```python
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class GateApplicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class DiffClassification(str, Enum):
    TRIVIAL_DOCS = "TRIVIAL_DOCS"
    NON_TRIVIAL_CODE = "NON_TRIVIAL_CODE"

class GateResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    gate_name: str = Field(...)
    passed: bool = Field(...)
    applicability: GateApplicability = Field(...)
    findings: list[str] = Field(...)
    
    # New field to aid in meta-gate analysis
    diff_classification: DiffClassification | None = Field(
        default=None, 
        description="Populated by meta-gates to explicitly categorize the change type."
    )
```

### C. Phase Architecture Integration
- **Phase 6 Verification Pipeline:** The verification orchestrator must be updated to await the completion of all standard testing gates. It then collects their `GateResult` objects and passes them as input to the `gate_coverage.minimum` meta-gate.

## 4. Required Documentation Updates

The following plan documents must be updated to reflect this remediation:

- **`plan/agentic-sdlc-design-v0.5.md`**: 
  - Update **§9.1** to include the new `gate_coverage.minimum` meta-gate in the deterministic gates table.
  - Clarify the Phase 6 pipeline execution order to account for meta-gate aggregation.
  - Update **§10 Anti-Reward-Hacking Guards** to list `gate_coverage.minimum` as a specific defense against test evasion and scope bypassing, supplementing the `mutation.diff_scoped` guard.
- **`plan/agent_interface_contracts.py`**: Add `DiffClassification` enum and update the `GateResult` model schema.
- **`plan/test_harness_architecture.md`**: Update **§3.4-3.6** to define what constitutes a "trivial" vs "non-trivial" diff for the purpose of applicability bypassing.

## 5. Open Questions
- **Triviality Heuristics:** What precise heuristics will robustly distinguish `TRIVIAL_DOCS` from `NON_TRIVIAL_CODE` without being overly rigid? Should we rely purely on file extensions, or include AST-based analysis of the diff (e.g., changes only inside Python docstrings)?
- **Sub-Agent Escalation:** If `gate_coverage.minimum` fails, should the system automatically escalate back to the Task Dev agent to write new hermetic tests, or should it escalate to a human operator via the `budget_and_escalation_policy`?
