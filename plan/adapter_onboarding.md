---
title: Adapter Onboarding
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Adapter Onboarding

This document guides the transition of a target repository from ad-hoc agentic interaction to fully governed, tiered execution. Rather than requiring a complete adapter schema on day one, repositories onboard progressively through Levels 0 to 3.

## Progressive Onboarding Levels

### Level 0: Ad-Hoc / Chat
No adapter is required. The repository is accessed read-only by the agent functioning as a simple chat assistant. There are no execution boundaries, verification steps, or orchestrated runs.

### Level 1: Execution
A minimal adapter is introduced. The repository declares:
- The execution image reference and bootstrap commands.
- **Tier 1 (Unit)** tests (`execution_tier: "tier1_unit"`).
At this level, the focus is on fast, fully hermetic, in-process testing.

### Level 2: State & Triage
The repository introduces structured failure handling and broader test coverage.
- **Tier 2 (Integration)** tests are added (`execution_tier: "tier2_integration"`).
- `ResetStrategy` is implemented for managing state between tests (e.g., `strategy_type: "transaction_rollback"`).
- Telemetry and deterministic triage rules are defined to catch issues like state leakage automatically.

### Level 3: Full Intent & Pooling
The repository reaches the full capability of the test harness.
- **Tier 3 (Browser/E2E)** tests are added (`execution_tier: "tier3_browser"`).
- High-cost reset strategies are optimized via a warm pool (`strategy_type: "browser_pool_checkout"`).
- Additive Intent operations and complex fixture hydration are defined.

## Browser Pool Lifecycle & Cost Attribution

When operating at **Level 3** and utilizing a warm pool (e.g., for browser environments), the following rules apply:

1. **Pool Lifecycle Ownership:** The Adapter's test harness owns the lifecycle of the warm pool. If a browser process or underlying instance crashes, the harness transparently triggers a cold start. The Core orchestrator does not manage these internals.
2. **Cost Attribution:** Warm pool costs are treated as fixed overhead. Instead of tracking the start-up time of the pool and attributing it to an individual agent's run budget, the cost is amortized across all runs in the suite. The `typical_cost_ms` declared in the `ResetStrategy` reflects the checkout time, not the cold start of the pool itself.

## Python Web App Starter Template

Below is a non-executable pseudo-code template for a typical Python Web Application onboarding adapter, reflecting the updated `governance.py` schemas.

```python
from plan.contracts.governance import (
    GovernancePolicy,
    TestTier,
    ResetStrategy,
    AbsentCapabilityPolicy
)

# Level 2/3 Onboarding: Reset Strategies
# Fast transaction rollback for integration tests
db_rollback_strategy = ResetStrategy(
    strategy_id="db_transaction_rollback",
    recreates="database transaction",
    requires=[],
    typical_cost_ms=50,
    clean_state_checks=["db_connection_count"],
    strategy_type="transaction_rollback"
)

# Browser pool for E2E tests
browser_pool_strategy = ResetStrategy(
    strategy_id="playwright_pool",
    recreates="browser context from warm pool",
    requires=[],
    typical_cost_ms=10,
    clean_state_checks=["cookie_count", "local_storage_keys"],
    strategy_type="browser_pool_checkout",
    pool_size=5
)

# Level 1-3 Onboarding: Test Tiers
unit_tier = TestTier(
    name="pytest_unit",
    command=["pytest", "tests/unit/"],
    isolation_unit="container",
    hermetic=True,
    execution_tier="tier1_unit",
    is_required=True
)

integration_tier = TestTier(
    name="pytest_integration",
    command=["pytest", "tests/integration/"],
    isolation_unit="container",
    hermetic=False,
    reset_strategy_id="db_transaction_rollback",
    execution_tier="tier2_integration",
    is_required=True
)

e2e_tier = TestTier(
    name="playwright_e2e",
    command=["pytest", "tests/e2e/"],
    isolation_unit="container",
    hermetic=False,
    reset_strategy_id="playwright_pool",
    execution_tier="tier3_browser",
    is_required=False
)

# Core Governance Policy linking the adapter configuration
repo_policy = GovernancePolicy(
    policy_version="1.0",
    repo_id="my-python-web-app",
    absent_capability_policy=AbsentCapabilityPolicy.DEGRADE,
    test_tiers=[unit_tier, integration_tier, e2e_tier],
    reset_strategies=[db_rollback_strategy, browser_pool_strategy],
    # other fields ...
)
```
