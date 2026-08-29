---
title: Log Monitor
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: core
---

# Log Monitor

## Type

Executor.

## Pairing

None — not a Maker/Checker pair. It emits telemetry; the Error Analyzer forms the judgment.

## Purpose

Always-on observation in production. Emits structured telemetry and **does not classify** — the
same separation as the Test Runner, and for the same reason: an observer that interprets its own
signal removes the possibility of interpreting it differently later.

## Inputs

- Production log and metric streams

## Outputs

- Structured telemetry events, consumed by the Error Analyzer

## Write scope

None.

## Layer

**Core.** "Observe continuously, emit structured signals, classify elsewhere" carries into any
domain that has a production phase. What is observed is adapter data; that observation and
classification are separated is not.

Adapter-supplied nouns: the signal set, declared via `SignalSpec`
(`contracts/adapter_surface.py`). PR #5's relocation of `FailureSignature`'s two hard-coded browser
fields into a declared `signals` map is what makes this agent's Core status honest rather than
nominal.

## Failure modes

- **Volume without signal.** Always-on observation produces continuous data; without the Error
  Analyzer's pattern-matching it is storage, not monitoring.
- **Classifying at the edge.** If this agent ever starts labelling events, the classification
  becomes unreviewable — it happens before anything with a verdict is involved.
