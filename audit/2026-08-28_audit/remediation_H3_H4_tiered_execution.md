---
title: "Remediation Plan: Findings H3 & H4 (Tiered Execution & Onboarding)"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Remediation Plan: Findings H3 & H4 (Tiered Execution & Onboarding)

## 1. Findings Restatement
**H3 (Fresh Test Environment Cost):** Fresh WebDriver initialization per test takes 1-3 seconds. In a suite of 500 tests, environment spin-up alone consumes 8-25 minutes, violating strict wall-clock time constraints for the pipeline.
**H4 (Onboarding Complexity):** Onboarding a new repository requires weeks of effort to define isolation specs, test tiers, intent vocabularies, AST transformers, triage rules, hydration hooks, and secret management.

## 2. Root Cause
The `test_harness_architecture.md` (§1.2) unconditionally mandates a fresh, fully hermetic construction per test regardless of the test's resource requirements. Furthermore, `core_adapter_boundary.md` (§1.2) expects full and complete adapter definitions upfront. By coupling the highest degree of isolation (hermetic browser environments) with the highest requirement for specification (full adapter definitions) across all tests universally, the system creates insurmountable onboarding friction and excessive execution cost.

## 3. Detailed Remediation

### 3.1. Generalized Test Tiers
We will categorize tests into generalized execution tiers, mapping directly to isolation constraints and cost.

*   **Tier 1: Fast/Unit:** No external I/O, no browser instances, rapid execution. Execution strategy: Process reuse, test suite pooling (e.g., standard pytest runner). Required for most pipeline progressions.
*   **Tier 2: Integration/Slow:** Requires DB or backend services, localized network I/O. Execution strategy: Container pooling, DB transaction rollbacks per test. Required depending on the domain being touched.
*   **Tier 3: Browser/Flaky:** Requires WebDriver, heavy UI components. Execution strategy: Eager pool of warm browsers, or parallelized isolated containers. Optional or parallelized asynchronously for basic PR checks, required for release gates.

### 3.2. Tiered Adapter Onboarding System
We introduce progressive onboarding levels to drastically reduce time-to-first-value for new repositories.

*   **Level 0 (Minimal):** Build scripts, static analysis, linting, basic discovery. No execution isolation required.
*   **Level 1 (Basic Tests):** Supports Tier 1 (Fast/Unit) tests. Requires basic `ResetStrategy` (e.g., process wipe or simply process reuse).
*   **Level 2 (Integration & Additive Intents):** Supports Tier 2 tests. Introduces DB resets, service mocking, and intent vocabularies for standard domain operations.
*   **Level 3 (Full Hermetic):** Supports Tier 3 (Browser) tests. Full WebDriver lifecycle hooks, complete AST transformers, and triage rules.

### 3.3. Cost-Aware Execution Strategies (Pydantic Schemas)

We will update the `ResetStrategy` and `ExecutionStrategy` models in `agent_interface_contracts.py` to support pooling and reuse based on the test tier. The system uses Pydantic v2.

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional, List

class TestTierSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    tier: Literal["tier1_unit", "tier2_integration", "tier3_browser"]
    is_required: bool = Field(description="Whether this tier must pass for pipeline progression.")
    
class ResetStrategy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    type: Literal["process_restart", "transaction_rollback", "browser_pool_checkout", "full_hermetic"]
    typical_cost_ms: int = Field(description="Typical cost in ms for this reset strategy.")
    pool_size: Optional[int] = Field(None, description="Max warm instances for pool strategies.")

class ExecutionStrategy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    tier_spec: TestTierSpec
    reset_strategy: ResetStrategy
    max_retries: int = 0
```

### 3.4. Starter Adapter Template (Python Web App)
To accelerate onboarding, we will provide a Level 1 adapter scaffold targeted at standard Python web applications (e.g., FastAPI/Django + Pytest), matching the user's context.

```python
# scaffold/python_web_adapter.py (Pseudocode)

from typing import Dict
from agent_interface_contracts import ExecutionStrategy, TestTierSpec, ResetStrategy

class PythonWebAdapter:
    """Level 1+ Starter Adapter for Python Web Apps"""
    
    def discover_tests(self) -> Dict[str, str]:
        # Default pytest discovery
        return {"command": "pytest --collect-only"}
        
    def get_tier_execution(self, test_node_id: str) -> ExecutionStrategy:
        if "browser" in test_node_id or "ui" in test_node_id or "e2e" in test_node_id:
            return ExecutionStrategy(
                tier_spec=TestTierSpec(tier="tier3_browser", is_required=False),
                reset_strategy=ResetStrategy(
                    type="browser_pool_checkout", 
                    typical_cost_ms=50, 
                    pool_size=5
                )
            )
        elif "integration" in test_node_id:
            return ExecutionStrategy(
                tier_spec=TestTierSpec(tier="tier2_integration", is_required=True),
                reset_strategy=ResetStrategy(
                    type="transaction_rollback", 
                    typical_cost_ms=10
                )
            )
        # Default to Tier 1
        return ExecutionStrategy(
            tier_spec=TestTierSpec(tier="tier1_unit", is_required=True),
            reset_strategy=ResetStrategy(type="process_restart", typical_cost_ms=2)
        )
```

## 4. Required Documentation Updates

1.  **`test_harness_architecture.md` (§1.2 & §1.3):**
    *   *Update:* Relax the "fresh construction per test" mandate. Document the generalized test tiers (Tier 1/2/3).
    *   *Update:* Define how `ResetStrategy` delegates to resource pools for Tier 2/3 instead of hard resets, using `pool_size`.
2.  **`core_adapter_boundary.md` (§1.2):**
    *   *Update:* Restructure the adapter declaration requirements to follow the Level 0 -> Level 3 progressive onboarding system. Remove the mandate for full definitions upfront.
3.  **`agent_interface_contracts.py`:**
    *   *Update:* Integrate the updated `TestTierSpec`, `ResetStrategy`, and `ExecutionStrategy` Pydantic models.
4.  **`adapter_onboarding.md` (NEW):**
    *   *Create:* Detailed guide for developers, describing how to transition a repository from Level 0 to Level 3, and providing the Python Web App starter template.

## 5. Open Questions
*   **State Leakage:** How do we detect state leakage in Tier 1 tests if we are reusing processes? Do we inject a stochastic full-reset monkey tester?
*   **Browser Pool Lifecycle:** For `browser_pool_checkout`, who owns the lifecycle of the warm pool? The Core system or the Adapter's test harness? If the pool crashes, does it fail the suite or transparently trigger a cold start?
*   **Cost Attribution:** For pooled resources, how do we accurately attribute the persistent infrastructure cost (e.g. keeping 5 WebDriver containers warm) to a specific agent run?
