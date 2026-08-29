---
title: "Remediation Plan: Finding H5 (Structural Change SOP Creates a Human Bottleneck)"
status: live
part_of: repo-meta
doc_type: reference
---

# Remediation Plan: Finding H5 (Structural Change SOP Creates a Human Bottleneck)

## 1. Finding Summary
**Finding H5**: Any non-additive structural change triggers a full pipeline pause and human architectural review, stalling autonomous runs during off-hours. The binary choice between 'fully additive intent' and 'full human halt' requires an intermediate tier to prevent bottlenecks.

## 2. Root Cause
The Shared-File Intent Service (`agentic-sdlc-design-v0.5.md` §4) deliberately restricts operations to purely additive intents (`AddExport`, `AddRoute`, `AddProviderBinding`). Any other structural change triggers the `structural_change_runbook.md` SOP, which halts task assignment and demands a synchronous human review. 

This model treats a simple deterministic rename (`RenameExport`) as identical in blast radius to a multi-file dependency graph restructure. By forcing all non-additive changes through the Tier 3 synchronous human gate, the swarm is unnecessarily stalled on trivial architectural evolutions, undermining its ability to operate autonomously off-hours.

## 3. Remediation: Risk-Tiered Structural Governance
To address this, we introduce a three-tiered risk classification for shared-file structural changes. The Intent Service vocabulary is expanded to include deterministic Tier 1 intents, and the Runbook is updated to support asynchronous review for Tier 2.

### 3.1 Tier Definitions

- **Tier 1 (Auto-Resolved, Synchronous Application)**: 
  Low-risk structural intents that are fully deterministic and require no human judgment. E.g., `RenameExport`, `MoveRoute`, `DeprecateExport`. 
  *Mechanism*: Handled synchronously by the Intent Service exactly like existing additive intents. No human gate.

- **Tier 2 (Async Human Review)**: 
  Moderate-risk changes that affect consumer boundaries but do not inherently break the broader architecture. E.g., `ChangeBindingScope`, `SplitRouter` (where new boundaries are clear). 
  *Mechanism*: The Intent Service accepts the intent into a `PendingReview` state. The proposing agent **does not halt**; it continues unrelated work or parks the specific sub-task and picks up a new one. A human reviews the intent asynchronously. Upon approval, the intent is applied and materialized.

- **Tier 3 (Synchronous Full Pause)**: 
  High-risk, high-blast-radius changes (e.g., breaking circular dependencies, merging monolithic modules). 
  *Mechanism*: Retains the existing `structural_change_runbook.md` procedure (Targeted Pause → Propose → Human Gate → Re-decompose).

### 3.2 Schema Additions (`agent_interface_contracts.py`)

Add the following new Tier 1 intents. The union `AdditiveIntent` will be renamed to `SharedFileIntent` to reflect the broader vocabulary.

```python
class RenameExport(BaseModel, frozen=True):
    """Tier 1: Rename an existing named export in a shared export barrel."""
    model_config = ConfigDict(extra="forbid")
    op: Literal["rename_export"] = "rename_export"
    old_name: str
    new_name: str

class MoveRoute(BaseModel, frozen=True):
    """Tier 1: Move an existing route to a different path."""
    model_config = ConfigDict(extra="forbid")
    op: Literal["move_route"] = "move_route"
    old_path: str
    new_path: str

class DeprecateExport(BaseModel, frozen=True):
    """Tier 1: Mark an export as deprecated, routing consumers to an alternative."""
    model_config = ConfigDict(extra="forbid")
    op: Literal["deprecate_export"] = "deprecate_export"
    name: str
    reason: str
```

### 3.3 Async Review Mechanism (Tier 2)

When an agent proposes a Tier 2 intent (or hits the N-intent threshold), the Core Orchestrator transitions the intent to a `Pending` queue. 
1. The Task Dev agent receives an `IntentQueued` response instead of an immediate materialization.
2. The agent is explicitly instructed to park the dependent workstream and continue other sub-tasks on its worktree.
3. Once the human approves, the Core Orchestrator applies the intent, materializes it via the canonical `shared/` branch (as defined in `execution_isolation.md` §7), and wakes the agent with a `ReviewApproved` notification.

## 4. Required Document Updates

### `structural_change_runbook.md`
- **§1 Triggers**: Categorize existing triggers into Tier 2 (Async) and Tier 3 (Full Pause). Specifically:
  - "Removing or renaming an existing shared symbol" -> Remove this trigger, as it is now a Tier 1 intent.
  - "Splitting or merging a shared file" -> Move to Tier 2 if the intent is well-formed, Tier 3 if it fails Tier 2 constraints.
  - "Task requiring more than N additive intents" -> Reclassify as Tier 2 (Async human review of the batch) rather than forcing a Tier 3 pause.
- **§3 Procedure**: 
  - Add a distinct "Tier 2 Procedure" defining the async flow (agent parks task, swarm continues).
  - Rename the current procedure to "Tier 3 Procedure (Synchronous Pause)".

### `agent_interface_contracts.py`
- Add schemas for `RenameExport`, `MoveRoute`, and `DeprecateExport`.
- Rename `AdditiveIntent` to `SharedFileIntent` and update the discriminated union.
- Introduce an `IntentStatus` enum (e.g., `Applied`, `PendingReview`, `Rejected`) to `IntentOutcome` to support Tier 2 async wait states.

### `agentic-sdlc-design-v0.5.md`
- **§4.2**: Rename "Typed, additive intents" to "Typed Structural Intents". List the Tier 1 additions and explicitly document the Tier 2 / Tier 3 escalation boundaries.

## 5. Open Questions
- **Tier 2 Parking Mechanics**: If a Task Dev agent parks a task awaiting a Tier 2 review, how do we constrain the rest of its worktree to avoid building on the unapproved state? Does it branch internally, or is it strictly forbidden from touching related consumers until approval?
- **N-Intent Threshold Limit**: The exact integer for the "N intents against a single file" trigger (§1) remains undefined. We need to measure typical route-addition bursts before setting this value.
