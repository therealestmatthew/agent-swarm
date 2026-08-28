# Remediation Plan: Finding C4 - Race Conditions in Shared-File Materialization

## 1. Finding Summary
**Finding C4**: Atomic POSIX rename only guarantees filesystem-level atomicity, not runtime isolation. Python's `sys.modules` cache, mid-test file reads, and file watchers can all cause inconsistent state when shared files are materialized into a running worktree while an agent is actively executing tests or code.

## 2. Root Cause Analysis
The current design (`execution_isolation.md` §7.2) pushes shared-file updates to all running worktrees immediately upon successful application by the Intent Service. While the update uses an atomic rename, this occurs asynchronously from the perspective of the Task Dev agent's execution loop. 
If an agent is in the middle of a test run when the push occurs:
- Previously imported modules remain in Python's `sys.modules`, while dynamically loaded files or deferred imports might pick up the new version, leading to mixed-state failures.
- File watchers (like `pytest-watch`) can trigger redundant or partial reruns mid-execution.
- The read-view guarantee (§7.3) is technically maintained at the filesystem layer, but the *runtime* view becomes corrupted due to language-level caching.

## 3. Remediation Strategy

The core strategy shifts from an uncoordinated **push-based** materialization to a coordinated **pull-based** materialization that only occurs during safe windows in the agent's execution lifecycle (specifically, between test executions).

### 3.1 Materialization Window Protocol
Materialization is only safe when the runtime has no cached state of the shared files. The agent's work cycle must be formalized to include explicit "Synchronization Points". 

Safe materialization windows are strictly restricted to:
1. Before an agent spins up a sub-process (e.g., a test runner, script execution).
2. After a sub-process cleanly terminates.
3. Between LLM generation steps, provided no persistent execution environment is running.

### 3.2 Signaling and Pull-Based Materialization
To avoid interrupting mid-test executions:
- **Shift to Pull-Based:** The Intent Service will no longer write directly into active sibling worktrees.
- **Agent Notification:** Core will publish a `SharedStateUpdatedEvent` to an event bus or agent message queue.
- **Agent Action:** Before the next test execution cycle, the agent will process its queue and call a new Core Adapter method `SyncWorktree()` to pull the latest shared files. 

### 3.3 Handling Stale `sys.modules` Cache
Because materialization only happens between process executions, any Python sub-processes spawned by the agent (e.g., a test suite run via `subprocess.run(["pytest"])`) will start with a fresh interpreter and a clean `sys.modules` cache. 
- **Rule Enforcement:** Agents **MUST NOT** execute target system code within their own Python interpreter process. All code execution must occur in isolated, short-lived subprocesses.

### 3.4 Impact on the 'Synchronously Before Agent Continues' Guarantee
The original design (§4.7) stated shared file updates are "applied synchronously before the agent continues". 
- **Revised Guarantee:** The intent application is still synchronous for the *proposing* agent. However, for all *sibling* agents, the update is now applied **lazily** at their next Synchronization Point. 
- The proposing agent's worktree is updated immediately since it initiated the change and is implicitly at a safe Synchronization Point (waiting for the Intent Service response).

## 4. Required File Changes

### 4.1 Update `plan/agent_interface_contracts.py`
Add the synchronization contract to the Adapter interface schemas.

```python
from pydantic import BaseModel, Field

class SyncWorktreeRequest(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    task_id: str = Field(..., description="The ID of the task requesting synchronization.")

class SyncWorktreeResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    files_updated: list[str] = Field(..., description="List of shared files that were updated.")
    new_commit_hash: str = Field(..., description="The new canonical commit hash of the shared branch.")
```

### 4.2 Update `plan/execution_isolation.md`
Modify **§7. The Materialization Mechanism** and its sub-sections:

- **§7.2 Step 3 (Current):** "On successful application, Core writes the new file content into each running worktree's working directory"
- **§7.2 Step 3 (Revised):** "On successful application, Core writes the new file content into the proposing agent's worktree. Core then publishes a `SharedStateUpdatedEvent` to all other active tasks."
- **Add §7.4 (Materialization Window Protocol):** Detail the requirement that agents must invoke `SyncWorktree()` before starting any sub-process execution, ensuring safe runtime isolation.
- **Update §7.3 (Read-View Guarantee):** Clarify that isolation from governed shared state is maintained strictly at process execution boundaries, preventing mid-run state mutation.

### 4.3 Update `plan/agentic-sdlc-design-v0.5.md`
- **Modify §4.7:** Update the wording to clarify the synchronous guarantee: "Updates are applied synchronously before the *proposing* agent continues. Sibling agents synchronize lazily at their next execution boundary via a pull mechanism."

## 5. Open Questions Introduced
1. **Event Delivery Guarantees:** If an agent crashes and restarts, it might lose the in-memory `SharedStateUpdatedEvent`. Should `SyncWorktree()` be designed to be idempotent and called unconditionally as a standard prelude to every test run, rather than relying strictly on event notification?
2. **Long-Running Executions:** If an agent starts a long-running debug session (or a daemonized service) in its worktree, it might block materialization indefinitely. Do we need an explicit timeout or interrupt signal to forcibly break the execution if critical shared files are updated and the agent hasn't reached a Synchronization Point in X minutes?
