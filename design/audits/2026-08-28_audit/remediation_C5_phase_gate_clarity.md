---
title: "Remediation Plan: Finding C5 (Design/Build Phase Contradiction)"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Remediation Plan: Finding C5 (Design/Build Phase Contradiction)

## 1. Finding Summary
**Finding C5: Design/Build Phase Contradiction**
The project guidelines (`CLAUDE.md`) mandate that "We are in design, not build" and forbid implementing schemas. However, `agent_interface_contracts.py` contains 569 lines of executable Pydantic schema code, Stage 0 of the implementation roadmap requires building a conformance kit, and glossary files are maintained in machine-readable formats. This creates a contradictory mandate for the LLM agents, leading to confusion over whether modifying these structural artifacts constitutes forbidden "building" or permitted "design".

## 2. Root Cause
The boundary between "design" (planning, specifying, and documenting) and "build" (implementing functional application code) was drawn too rigidly along the lines of "no executable code". In an Agentic SDLC system, executable contracts (like Pydantic schemas) and machine-readable definitions *are* the design artifacts. When `agent_interface_contracts.py` grew to encompass the entire system's boundaries (Core, Adapters, Gates, Intents), it crossed the threshold from a conceptual design document into a monolithic executable file, exacerbating the phase contradiction.

## 3. Remediation Strategy
The remediation will redefine the design/build boundary to explicitly allow defining executable schemas (Pydantic) as part of the design phase. Concurrently, `agent_interface_contracts.py` must be decomposed into a modular structure aligned with the Core/Adapter boundary principles. Schema definition and relocation will be explicitly classified as "design" work.

### 3.1. Re-defining the "Design vs. Build" Phase Gate
Modify `CLAUDE.md` to clearly delineate that system contracts (Pydantic models, JSON schemas, structural boundaries) belong to the design phase.

**Specific change to `CLAUDE.md`:**
*Remove:*
> We are in design, not build. design/plans/ is the source of truth. Do not start implementing agents, services, or schemas until the design settles and this line changes.

*Replace with:*
> We are in the structural design phase. `design/plans/` is the source of truth.
> **Permitted:** Defining, refining, and modularizing Pydantic schemas, system contracts, glossary definitions, and interface boundaries. Schema relocation is design.
> **Forbidden:** Implementing agent logic, service execution code, internal pipeline routing logic, or API integrations. Do not build application logic until the design settles and this phase gate changes.

### 3.2. Decomposing `agent_interface_contracts.py`
Decompose the monolithic `agent_interface_contracts.py` into a modular package structure within `design/plans/contracts/`.

**New Directory Structure:**
```text
design/plans/
└── contracts/
    ├── __init__.py
    ├── core_schemas.py      # RunManifest, GateResult, IntentRejection, Error models
    ├── adapter_schemas.py   # Adapter boundary interfaces, registration models
    ├── gate_schemas.py      # Phase transition structures, audit trails
    └── reference_adapter/
        ├── __init__.py
        └── web_intents.py   # AddRoute, AddExport, AddProviderBinding
```

This alignment fulfills the D2 resolution by moving web-specific adapter intents (such as `AddRoute`, `AddExport`) out of the core contract definitions and into a reference adapter specification.

### 3.3. Pydantic Model Alignment and Import Conventions
All relocated schemas must strictly adhere to the Pydantic v2 configuration standard for the project (`frozen=True`, `extra="forbid"`).

**Example Snippet (`design/plans/contracts/core_schemas.py`):**
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    run_id: str = Field(..., description="Unique identifier for the execution run")
    target_budget: float = Field(..., description="Maximum budget allocated for this run")
    # ... additional fields ...
```

**Example Snippet (`design/plans/contracts/reference_adapter/web_intents.py`):**
```python
from pydantic import BaseModel, ConfigDict, Field
from plan.contracts.core_schemas import IntentRejection

class AddRoute(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    route_path: str = Field(..., description="The URL route path to add")
    handler_signature: str = Field(..., description="Signature of the route handler")
```

To maintain the "single source of truth" principle, `design/plans/contracts/__init__.py` may expose the fundamental models so that external tooling can still import from a unified namespace if necessary, though direct module imports are preferred for clarity.

## 4. Updates Required to Existing Plan Documents

1. **`CLAUDE.md`**
   - Update the gating line as specified in Section 3.1.
2. **`agent_interface_contracts.py`**
   - Delete this file entirely after migrating its contents to the new `design/plans/contracts/` structure.
3. **`implementation_roadmap.md`**
   - Update Stage 0 to reflect the decomposed directory structure (`design/plans/contracts/`).
   - Note the completion of the D2 resolution regarding the relocation of web-specific intents to `design/plans/contracts/reference_adapter/web_intents.py`.
4. **`core_adapter_boundary.md`**
   - Add a section defining the strict import rules: Core schemas (`core_schemas.py`) may not import from Adapter schemas (`adapter_schemas.py` or `reference_adapter/`).

## 5. Open Questions Introduced
- **Schema Validation:** If schemas are now spread across multiple files, how do we enforce that the "frozen=True, extra=forbid" rule is consistently applied? Should a linter or test be added to the Stage 0 conformance kit?
- **Dependency Graphs:** With 23 agents in an 8-phase pipeline, how do we track which agents depend on which specific intent schemas now that they are distributed into adapter-specific modules?
- **Conformance Kit Location:** Will the Stage 0 conformance kit reside in `design/plans/` (as it validates design), or does it belong in the main code directory since it executes validation logic?
