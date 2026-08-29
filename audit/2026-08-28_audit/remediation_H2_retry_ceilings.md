---
title: "Remediation: Finding H2 - Blanket `max_retries=3` is Too Coarse"
status: live
part_of: repo-meta
doc_type: reference
---

# Remediation: Finding H2 - Blanket `max_retries=3` is Too Coarse

## 1. Finding Summary
A uniform `max_retries=3` across all loop-back edges ignores cost differences and sub-step multiplication. Since each 'retry' iteration invokes 3-4 sub-steps per the escalation ladder (re-gather context, re-spec, model escalation from Claude Sonnet to Opus, human halt), a flat limit allows token-intensive loops to rapidly exceed per-run target costs ($5-$50).

## 2. Root Cause
The current `budget_and_escalation_policy.md` (§1) defines a simplistic, uniform retry ceiling for all loop types (planning, code review, test fix, decomposition) without accounting for the cascading cost of the escalation ladder (defined in §2) or the inherent token volume differences between phases (e.g., Phase 4 parallel swarm vs. early planning).

## 3. Remediation Design
We will replace the flat `max_retries` integer with a parameterized, cost-aware budget configuration per loop type. This includes defining specific ceilings based on the semantic weight of the loop and enforcing a hard token/cost budget rather than just iteration counts.

### 3.1. Sub-step Counting Clarification
An "iteration" is defined as a full traversal of the escalation ladder up to the model escalation step. 
- Sub-step 1: Re-gather context
- Sub-step 2: Re-spec prompt
- Sub-step 3: Model Escalation (Sonnet -> Opus)
If the loop fails after Opus, the iteration concludes. Thus, one "retry" equals the execution of these sub-steps.

### 3.2. Per-Loop-Type Retry Ceilings & Budgets
We establish the following distinct ceilings and budgets:
- **Planning Loop**: `max_retries=2`, Target Budget: $2.00 (Low volume, high importance; escalate to Opus quickly).
- **Decomposition Loop**: `max_retries=2`, Target Budget: $5.00 (Moderate volume; structural impact).
- **Code Review Loop**: `max_retries=3`, Target Budget: $15.00 (High token volume in Phase 4; restrict Opus usage to targeted files).
- **Test Fix Loop**: `max_retries=4`, Target Budget: $10.00 (Iterative by nature; Sonnet can handle most fixes; delay Opus escalation until retry 3).

### 3.3. Configuration Schema
We will introduce a `LoopBudgetConfig` Pydantic model to formalize this policy in `agent_interface_contracts.py`.

```python
from pydantic import BaseModel, Field

class EscalationConfig(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    escalate_to_opus_at_retry: int = Field(..., description="Retry index at which to switch from Sonnet to Opus")
    require_human_halt_at_retry: int = Field(..., description="Retry index at which to halt and request human intervention")

class LoopBudgetConfig(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    loop_type: str = Field(..., description="Identifier for the loop (e.g., 'code_review', 'test_fix')")
    max_retries: int = Field(..., description="Maximum allowed loop iterations before hard failure")
    max_cost_usd: float = Field(..., description="Maximum cumulative cost for this loop instance")
    escalation_policy: EscalationConfig
```

## 4. Required Document Updates

- **`plan/budget_and_escalation_policy.md`**:
  - Update **§1 (Loop ceilings table)**: Replace the uniform `max_retries=3` with the parameterized table from section 3.2 above.
  - Update **§2 (Escalation ladder)**: Clarify the sub-step counting mechanism (section 3.1) and specify that model escalation timing is parameterized via `EscalationConfig`.
  - Update **§3 (Cost ceilings)**: Replace illustrative TBDs with the concrete target budgets defined in section 3.2, mapping to Anthropic pricing (Sonnet vs. Opus).
- **`plan/agent_interface_contracts.py`**:
  - Add the `LoopBudgetConfig` and `EscalationConfig` schemas to the centralized contracts.
- **`plan/agentic-sdlc-design-v0.5.md`**:
  - Update the Phase 4 parallel swarm description to reference the specific budget constraints of the Code Review loop.

## 5. Open Questions
1. How do we track and aggregate costs in real-time within the parallel swarm (Phase 4) to ensure the $15.00 code review budget is not exceeded concurrently?
2. If a loop hits its `max_cost_usd` before `max_retries` is reached, does it immediately trigger a human halt, or fail silently back to the parent agent?
