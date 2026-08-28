# Remediation Plan: H8 - No Crash Recovery for Stateful Isolation Units

## 1. Finding Summary
**Finding H8:** While `RunManifest` tracks the pipeline phase, there is no protocol to clean up orphaned Docker containers, rollback uncommitted `shared/` branch changes, or reconcile half-materialized files after a process crash. 
**Q5 Feedback Context:** For in-flight work during ceiling halts, a decision tree is needed to determine when state should be preserved and resumable versus when a restart from the last-committed state is mandated.

## 2. Root Cause
The `RunManifest` persistence model assumes graceful termination or controlled pauses (e.g., `HaltReason.CEILING_HALT`, `HaltReason.HUMAN_GATE`). Process crashes bypass these lifecycle hooks, leaving isolation units (Docker containers, Git worktrees) and the `shared/` branch locked or in an intermediate, unrecorded state. The pipeline lacks a deterministic initialization protocol (a startup reconciler) to assess the state of the workspace and infrastructure before beginning or resuming execution.

## 3. Detailed Remediation

### 3.1. Startup Reconciliation Protocol
We will introduce a `StartupReconciler` that executes at the launch of the pipeline, before any new or resumed run. The reconciler performs the following operations:
1. **Orphan Cleanup:** Identifies running Docker containers and Git worktrees associated with the agent-swarm. Removes any that do not correspond to an active, paused, or explicitly preserved `RunManifest`.
2. **Lock Clearing:** Releases stale locks on the `shared/` branch if the holding process no longer exists.
3. **State Assessment:** Compares the active workspace and `shared/` branch state against the last successfully persisted `RunManifest`.

### 3.2. Shared Branch Integrity
The `shared/` branch acts as the sole-writer integration point. To ensure integrity:
- Uncommitted changes in the `shared/` branch detected during reconciliation will be stashed and logged if they do not perfectly match the last recorded intent in the `RunManifest`. 
- If a crash occurred *during* a merge to `shared/`, the reconciler will perform a `git reset --hard` to the last known-good commit recorded in the `RunManifest`.

### 3.3. Decision Tree: Resumable vs. Restart-Required States
When resuming from a non-graceful halt (crash) or a graceful halt (ceiling halt, human gate), the reconciler applies the following decision tree:

1. **Did the halt occur during a state-mutating transition (e.g., merging to `shared/`, spinning up a container)?**
   - *Yes:* Discard in-flight work. Teardown the specific isolation unit and restart the phase from the last-committed state.
   - *No:* Proceed to 2.
2. **Is the `HaltReason` a `CEILING_HALT` or `HUMAN_GATE`?**
   - *Yes:* Preserve in-flight worktrees and containers. The state was snapshot via the Structural Change SOP's pause step. Resume execution directly.
   - *No (e.g., `BOUNDARY_FAILURE`, `ADAPTER_INVALID`, or process crash):* Proceed to 3.
3. **Can the state of the isolation unit be deterministically mapped to the `RunManifest` phase?**
   - *Yes:* Preserve and resume.
   - *No (or corrupted/unreachable):* Mandate a restart from the last-committed state and execute orphan cleanup.

### 3.4. Schema Additions
Because `RunManifest` is `frozen=True` (Pydantic v2), we cannot mutate it in place during reconciliation. We will introduce a new `RecoveryManifest` and a `RecoveryStrategy` enum.

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class RecoveryStrategy(str, Enum):
    RESUME_IN_PLACE = "RESUME_IN_PLACE"
    RESTART_PHASE = "RESTART_PHASE"
    ABORT_RUN = "ABORT_RUN"

class RecoveryManifest(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    original_run_id: str = Field(..., description="ID of the crashed or halted run.")
    strategy: RecoveryStrategy = Field(..., description="Chosen recovery strategy based on decision tree.")
    orphans_cleaned: int = Field(default=0, description="Count of orphaned containers/worktrees removed.")
    shared_branch_reset_to: Optional[str] = Field(None, description="Commit hash if shared/ branch was rolled back.")
    resumed_from_phase: str = Field(..., description="The pipeline phase from which execution is resuming.")
```

The system will mint a `RecoveryManifest` during startup reconciliation, logging it before generating the next immutable `RunManifest`.

## 4. Required Plan Document Updates

- **`plan/agent_interface_contracts.py`**:
  - Add the `RecoveryStrategy` and `RecoveryManifest` Pydantic schemas.
  - Update `HaltReason` (if needed) to ensure `CRASH_RECOVERY` is represented, though the reconciler handles actual crashes.
- **`plan/execution_isolation.md`**:
  - Update **§4** to include the `StartupReconciler` teardown rules for orphaned worktrees.
  - Update **§5** to mandate Docker container labeling with `run_id` to facilitate deterministic orphan detection.
  - Update **§7.2** to explicitly define the `git reset --hard` protocol for the `shared/` branch during recovery.
- **`plan/agentic-sdlc-design-v0.5.md`**:
  - Update **§3 (Persistence & State)** to introduce the Startup Reconciliation Protocol as step 0 of the pipeline execution sequence.
- **`plan/budget_and_escalation_policy.md`**:
  - Update **§3** to clarify that `CEILING_HALT` guarantees the "Preserve and Resume" branch of the new decision tree, protecting in-flight work.

## 5. Open Questions
1. **Container Labeling Constraint:** Do all Adapter environments support injecting custom labels/tags into the underlying isolation unit (Docker) to guarantee reliable orphan identification?
2. **Cost of Stashing vs Discarding:** If uncommitted changes in `shared/` are stashed rather than discarded, how and when do we prune the stash stack to prevent storage bloating over hundreds of runs?
3. **Nested Crashes:** If the `StartupReconciler` itself crashes while executing a rollback, is the system state left permanently corrupted, or is the reconciler completely idempotent?
