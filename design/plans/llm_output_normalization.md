---
title: LLM Output Normalization
status: live
part_of: agentic-sdlc
doc_type: companion
layer: core
---

# LLM Output Normalization

**Referenced by:** `agentic-sdlc-design-v0.5.md` §3 (Phase-by-Phase Architecture) · `core_adapter_boundary.md` · `CLAUDE.md` (Working agreements) · `design/plans/contracts/__init__.py` · `design/plans/calibration_and_measurement.md` §5 (Schema Hallucination Rate)

## Purpose

Combining `extra="forbid"` on Pydantic models with LLM JSON generation leads to chronic parse failures (as identified in audit finding H6). LLMs frequently hallucinate extra keys in their output. When validation fails completely on extra keys, agents enter infinite adversarial loops trying to correct a structural issue they do not understand. The normalization layer is the structural answer to this problem, creating a bridge between permissive text generation and strict type enforcement.

## 1. The Two-Pass Strategy

The system processes LLM-generated JSON using a two-pass approach:

- **Pass 1 (Normalization):** Walk the incoming JSON object graph recursively. At each level, compare the provided keys against the target model's `model_fields`. Strip any extra fields, log each removal via a `NormalizationEvent`, and continue into nested models.
- **Pass 2 (Strict Validation):** Hand the cleaned data to `model_class.model_validate(data)`. The model itself still carries `extra="forbid"`, so any remaining structural mismatch (wrong types, missing required fields) becomes a hard error that enters the standard escalation ladder.

> **Design note:** A `parse_agent_output` normalizer will be implemented during the build phase. This pseudo-code sketch is a build-phase deliverable and should recursively strip extra keys according to the target model schema.

## 2. Model Categories

Schemas fall into two distinct parsing disciplines:

- **Category 1: Core-internal (strict).** Models passed between deterministic Core components. These are instantiated directly by deterministic code, never hold LLM-generated content, and are not routed through the normalization layer. Examples: `RunManifest`, `Phase`, `HaltReason`, `RepoDeclaration`, `GovernancePolicy`.
- **Category 2: Agent-produced (normalized).** Models whose content originates from LLM generation. These MUST be routed through the normalizer. Examples: `GateResult`, `Finding`, additive intents (`AdditiveIntent` subtypes in `reference_adapter/`).

Reference: each contract module's docstring carries a `Parsing discipline:` annotation declaring its category.

## 3. Dispatch Path Integration

The normalizer sits in the dispatch path:
- **Core owns the normalizer.** It is a deterministic mechanism (strip-and-log) with no LLM calls, aligning with the principle that "Core owns every mechanism; Adapter owns every noun."
- The Adapter hands raw JSON strings to Core. The normalizer is the first thing that processes this inbound payload before it crosses into Core's typed pipeline.
- For Validator agents: It sits between the raw `GateResult` JSON and the `GateResult` instance that enters the gate evaluation logic.
- For Task Dev agents: It sits between the raw intent JSON and the `AdditiveIntent` instance that enters the Shared-File Intent Service.

## 4. Escalation Interaction

How normalization interacts with the escalation ladder:
- Stripping extra fields is **not** a failure and does **not** consume error budget. It is a normalization event, logged for telemetry.
- A hard validation error after stripping (e.g., wrong type, missing required field) IS a failure and enters the standard escalation ladder (e.g., Sonnet → Opus).
- A high `schema_hallucination_rate` per model tier is a prompt-improvement signal, not a runtime escalation trigger.

## 5. Open Questions

- What threshold of `NormalizationEvent` occurrences constitutes a reliable signal for prompt-refinement versus acceptable background noise for a given model tier?

## 6. Schema Defaulting Convention

Required fields with no default on top-level governance postures force explicit, conscious choice by the policy owner. Scoped or per-tier decisions may default to the conservative option. The reference case: `GovernancePolicy.absent_capability_policy` (no default — a top-level posture that must never be silently inherited) vs. `GovernancePolicy.non_hermetic_coverage_posture` (defaults to `DEGRADE` — a scoped, per-tier decision where degradation is the safe, conservative default). See `design/plans/contracts/governance.py` L309 for the inline rationale.
