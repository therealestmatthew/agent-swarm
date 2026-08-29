---
title: "Remediation Plan: Finding H6 (extra='forbid' + LLM Output = Chronic Parse Failures)"
status: live
part_of: repo-meta
doc_type: reference
---

# Remediation Plan: Finding H6 (extra='forbid' + LLM Output = Chronic Parse Failures)

## 1. Finding Summary
LLMs frequently hallucinate extra fields in structured output. Because the system universally enforces `extra='forbid'` on all Pydantic models, any hallucinated field results in a hard validation error that immediately terminates the pipeline step.

## 2. Root Cause
The architectural decision to mandate `ConfigDict(extra='forbid', frozen=True)` across all schemas in `agent_interface_contracts.py` was intended to prevent agents from silently mutating state or adding undeclared fields. However, this strictness ignores the probabilistic nature of LLM generation. Weaker models in the escalation ladder (e.g., Sonnet) often inject explanatory but undeclared fields into JSON payloads. By applying a rigidly deterministic validation standard directly to non-deterministic generation, the system suffers chronic parse failures rather than gracefully recovering or safely stripping the invalid fields.

## 3. Detailed Remediation Strategy

We will implement a **Two-Pass Validation (Normalization Pre-Parsing)** strategy. We will maintain the strict schema definitions but introduce an active normalization layer at the Core/Adapter boundary.

### 3.1. Two-Pass Validation Layer Strategy
Instead of directly instantiating Pydantic models from LLM JSON strings (or using Pydantic's built-in parsing), all agent-produced structural outputs will pass through a new parsing utility module. 

The strategy:
1. **Category 1 (Internal/Core Models)**: Models passed between deterministic Core components (e.g., `RunManifest`, worktree state) remain purely strict and are instantiated directly.
2. **Category 2 (Agent-Produced Models)**: LLM outputs are routed through the pre-parser which identifies, logs, and strips extra fields before instantiating the strict Pydantic model. 

### 3.2. Code Snippets & File Changes

**New Utility: `core/llm_output_parser.py`**
```python
import json
import logging
from typing import Type, TypeVar, Any, Dict
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

def parse_agent_output(model_class: Type[T], raw_json: str, agent_id: str, run_id: str) -> T:
    """
    Two-pass validation for LLM outputs.
    Strips and logs undeclared fields to prevent extra='forbid' hard failures.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Agent {agent_id} returned invalid JSON: {e}")

    # Pass 1: Identify and strip extra fields top-level
    schema_fields = set(model_class.model_fields.keys())
    provided_fields = set(data.keys())
    extra_fields = provided_fields - schema_fields

    if extra_fields:
        # Principle 7: Nothing fails silently. 
        # Log stripped fields for telemetry and prompt improvement.
        stripped_data = {k: data[k] for k in extra_fields}
        logger.warning(
            f"audit_event=schema_hallucination agent_id={agent_id} run_id={run_id} "
            f"model={model_class.__name__} extra_fields={list(extra_fields)} "
            f"stripped_data={json.dumps(stripped_data)}"
        )
        
        # Remove extra fields from data payload
        for field in extra_fields:
            del data[field]

    # Pass 2: Strict instantiation
    # model_class retains extra='forbid', ensuring core integrity
    return model_class.model_validate(data)
```

**Changes to `plan/agent_interface_contracts.py`**
*No schema changes required.* We will keep `ConfigDict(extra='forbid', frozen=True)` on **ALL** 20+ models. The strictness remains in the domain models themselves; the leniency is explicitly handled in the parser boundary, avoiding the need to conditionally loosen schemas.

### 3.3. Dispatch Path Integration
The normalization layer sits in the Adapter layer, immediately after the Anthropic/OpenAI provider API call returns, before the payload crosses into the Core. 

Inside the agent dispatch loop (likely within `adapter/llm_client.py` or `core/orchestrator.py`), the raw string must be passed to `parse_agent_output()` to generate the validated Pydantic object. Only the valid object is handed back to the 8-phase pipeline.

## 4. Document Updates Required

1. **`plan/agentic-sdlc-design-v0.5.md`**
   - Update the "Agent Execution Loop" section to include the `llm_output_parser` normalization step.
2. **`plan/core_adapter_boundary.md`**
   - Explicitly define that raw LLM output normalization occurs on the Adapter side. The Core only ever receives strict, valid Pydantic objects.
3. **`plan/calibration_and_measurement.md`**
   - Add a new metric tracking "Schema Hallucination Rate" based on the `audit_event=schema_hallucination` logs. 
   - State that high hallucination rates on specific models should trigger prompt refinement.
4. **`CLAUDE.md`**
   - Update the Pydantic working agreement: `Pydantic v2, extra="forbid", frozen=True on every model. Use parse_agent_output() for all LLM-generated JSON to strip/log extra fields safely.`

## 5. Open Questions
1. **Nested Objects**: The proposed `parse_agent_output` only strips top-level extra fields. If an LLM hallucinates an extra field deep inside a nested object (e.g., a sub-model in a list), Pydantic will still throw a hard error. Do we need to build a recursive stripping utility, or do we rely on the existing Sonnet → Opus escalation ladder to handle complex nested parsing failures?
2. **Escalation Triggers**: Should the stripping of an extra field count as a "soft failure" that consumes part of the error budget or triggers an Opus retry? Or is logging it sufficient, allowing us to save budget if the core schema constraints are otherwise satisfied?
