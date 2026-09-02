---
title: "Remediation Plan: C2 - Deadlock Potential in Smart Mutex Rejection"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Remediation Plan: C2 - Deadlock Potential in Smart Mutex Rejection

## 1. Finding Summary
If two or more tasks submit mutually incompatible structural intents, they can enter circular rejection loops (ping-pong). Because the system uses Smart Mutex Rejection to bounce colliding intents back to the submitting agents without global coordination, these tasks can continuously retry incompatible changes. This burns task budget without generating diagnostic root-cause reporting, ultimately leading to silent budget exhaustion rather than a clear architectural failure.

## 2. Root Cause Analysis
The root cause stems from the lack of cycle detection within the Shared-File Intent Service. Currently, `IntentRejection` provides local blocking context (`blocking_task_id`, `blocking_op`, `blocking_keys`), but does not track historical rejections. When Task A is rejected because of Task B's lock, and Task B is subsequently rejected because of Task A's lock (or they enter a race condition retrying the same structural edit), the agents see independent rejections rather than a systemic cycle. Following Principle 8 ("Merge conflicts are decomposition errors"), this represents a breakdown in task isolation (a boundary failure), but the system currently treats it as a standard runtime rejection, allowing retries until budget exhaustion.

## 3. Concrete Remediation Plan
We will implement explicit cycle and deadlock detection at the Shared-File Intent Service level. Instead of allowing agents to infinitely retry, the service will track rejection edges and terminate the involved tasks as boundary failures when a cycle or threshold is reached.

### Cycle Detection Algorithm
1. **Rejection Graph Tracking**: The Intent Service will maintain an in-memory directed graph of rejection edges. An edge `A -> B` is added when Task A's intent is rejected because Task B currently holds the lock on the target file/resource.
2. **Cycle Detection**: On every rejection, the service traverses the rejection graph to detect cycles (e.g., `A -> B -> A`).
3. **Threshold Ceiling**: In addition to graph cycles, we will maintain a rejection counter per `(Task A, Task B, Resource)` tuple. If this counter exceeds a ceiling of `MAX_MUTEX_REJECTIONS = 3`, it is treated identically to a deadlock.
4. **Escalation**: When a cycle or threshold breach is detected, the Intent Service immediately escalates the event as a **Boundary Failure**.
5. **In-Flight Work**: All in-flight work for the deadlocked tasks is aborted. The tasks are marked as failed, and their worktrees are discarded. The failure is escalated to the Core orchestrator.

### Schema Updates
We will introduce a new model to track rejection edges and update the `IntentRejection` model to indicate deadlock termination.

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

# New Schema for Rejection Graph Edge
class RejectionEdge(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    rejected_task_id: str = Field(..., description="The task that was rejected")
    blocking_task_id: str = Field(..., description="The task holding the lock")
    resource_key: str = Field(..., description="The locked resource or file path")
    timestamp: float = Field(..., description="Epoch timestamp of the rejection")

# Updated IntentRejection
class IntentRejection(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    reason: Literal["lock_conflict", "stale_version", "deadlock_detected"] = Field(...)
    blocking_task_id: Optional[str] = Field(None, description="The task holding the lock, if applicable")
    blocking_op: Optional[str] = Field(None, description="The operation holding the lock")
    blocking_keys: Optional[list[str]] = Field(None, description="Keys/files involved in the block")
    deadlock_cycle: Optional[list[str]] = Field(None, description="List of task IDs involved in the detected cycle, present if reason is 'deadlock_detected'")
```

### Escalation as Boundary Failure
Per `budget_and_escalation_policy.md`, boundary-type loops must skip model escalation and proceed directly to failure. The deadlock triggers an immediate task termination. The parent orchestrator receives an exception of type `BoundaryDecompositionError`, indicating that the tasks must be fundamentally redesigned and rescheduled rather than retried.

## 4. Required Documentation Updates
The following existing plan documents must be updated:
- **`agentic-sdlc-design-v0.5.md`**: Update §4.5 (Smart Mutex Rejection) to include the cycle detection algorithm and threshold ceiling logic.
- **`agent_interface_contracts.py`**: Relocate schema definitions for `IntentRejection` (add `deadlock_cycle` and new Literal reason) and add the `RejectionEdge` model.
- **`budget_and_escalation_policy.md`**: Update §2.2 to explicitly classify structural intent deadlocks as boundary-type loops that trigger immediate task termination without LLM escalation.
- **`structural_change_runbook.md`**: Add a section describing how to manually resolve deadlocked intents when they are caught in the escape hatch.

## 5. Open Questions
- Should the `MAX_MUTEX_REJECTIONS` ceiling be configurable per-phase, or remain a global constant of 3?
- When a deadlock is detected and tasks are aborted, should the orchestrator automatically attempt to run them sequentially, or permanently fail the workflow and await user intervention?
- Does the rejection graph need persistence across Intent Service restarts, or is an in-memory graph sufficient given the typical task duration?
