---
title: "Remediation: H7 Collision Key Semantics are Too Shallow"
status: live
part_of: repo-meta
doc_type: reference
---

# Remediation: H7 Collision Key Semantics are Too Shallow

## 1. Finding
Collision detection relies only on exact key matches (`collision_keys`). Two intents can be semantically destructive when combined but have different collision keys (e.g., conflicting middleware, overlapping regex routes like `/users/:id` vs `/users/new`, duplicate middleware that cancels each other out).

## 2. Root Cause
`core_adapter_boundary.md` §2.1 explicitly forbids adapter-supplied predicate functions to prevent untrusted repo code from running within the Core's arbitration loop. Consequently, arbitration is forced to rely solely on shallow exact-match keys, pushing any deeper semantic conflicts to surface as late-stage integration failures where they merely increment conflict counters. 

## 3. Remediation Strategy: Two-Layer Collision Model
We introduce a **Two-Layer Collision Model** to safely allow adapter-specific semantics without compromising Core's security:

1. **Layer 1: Deterministic Key Match (Core, Pre-Application)**. Remains exactly as is. Fast, universal, exact match on `collision_keys` operating purely in Core.
2. **Layer 2: Semantic Static Analysis (Adapter-Declared, Post-Application, Sandboxed)**. An optional, adapter-declared static analyzer that runs against the merged intent output, in a sandboxed isolation unit, before the combined changes are fully materialized for testing.

### 3.1 Running Analyzers Safely
To maintain security, Core does not accept predicate functions inside its own process. Instead, analyzers are declared by the adapter as executable commands that run inside the repo's declared `IsolationUnit`. 
- Core passes the applied intent file to the analyzer.
- The analyzer returns a structured JSON payload of collisions.
- Because it runs inside the isolation unit, it cannot compromise Core.

### 3.2 The Semantic Collision Check Phase
This check runs after intent application (Layer 1) but before full Phase 5 (Integration) testing. Core batches applied intents and runs the mapped semantic analyzers. 
- If the analyzer flags a semantic collision, Core rolls back the offending intent and issues an `IntentRejection` with `reason="semantic_collision"`.

### 3.3 Handling False Positives
To prevent an overly strict static analyzer from permanently blocking valid work, we introduce an override mechanism:
- Analyzers must surface an `override_key` in their failure output.
- An agent can resubmit the intent including the `override_key`.
- This converts the analyzer's block into a verifiable hypothesis, allowing the intent through to Phase 5. If it fails integration tests, the standard escalation ladder catches it.

## 4. Schema Changes (`agent_interface_contracts.py`)

Add the semantic analyzer declaration to `RepoDeclaration` and link it in `IntentOpSpec`:

```python
class SemanticAnalyzerSpec(BaseModel, frozen=True):
    """Declares a static analyzer for detecting semantic collisions post-application."""
    model_config = ConfigDict(extra="forbid")
    
    analyzer_id: str
    command: list[str]
    isolation_unit: IsolationUnit

class IntentOpSpec(BaseModel, frozen=True):
    op: str
    collision_keys: list[str]
    transformer_id: str
    # NEW: Analyzers to run post-application
    semantic_analyzer_ids: list[str] = Field(default_factory=list)

class RepoDeclaration(BaseModel, frozen=True):
    # ... existing fields
    semantic_analyzers: list[SemanticAnalyzerSpec] = Field(default_factory=list)
```

Update `IntentRejection` to support semantic collisions:

```python
class IntentRejection(BaseModel, frozen=True):
    # ... existing fields
    reason: Literal[
        "collision",
        "semantic_collision", # NEW
        "unmapped_anchor",
        "not_registered",
        "op_not_declared",
        "structural",
    ]
    # ... existing fields
    semantic_feedback: str | None = None # NEW: The analyzer's message
    override_key: str | None = None      # NEW: Key to bypass this specific check
```

Add an override envelope to `AdditiveIntent` types:

```python
class AddRoute(BaseModel, frozen=True):
    # ... existing fields
    override_semantic_collisions: list[str] = Field(default_factory=list) # NEW
```

## 5. Document Updates

### `plan/core_adapter_boundary.md`
- **§2.1**: Update to introduce the "Two-Layer Collision Model". Clarify that Core still owns arbitration logic, but uses sandboxed adapter-supplied executables for Layer 2. Define the exact contract for Semantic Analyzers (JSON output, runs in `IsolationUnit`).

### `plan/agentic-sdlc-design-v0.5.md`
- **§4.6 (Conflict counters & governance)**: Detail the override mechanism. Explain that overriding a semantic collision relies on Phase 5 tests to catch actual breakage.
- **§5 (Integration Phase)**: Insert the Semantic Collision Check phase before Phase 5 integration materialization.

## 6. Open Questions
1. **Performance Cost**: How much overhead does spinning up the isolation unit for static analysis add to the intent application loop? Should Core mandate batching all intents before running the analyzer?
2. **Analyzer Output Contract**: What is the exact JSON schema expected from the adapter's analyzer command, and how does it map failures back to specific `task_id`s or intents?
