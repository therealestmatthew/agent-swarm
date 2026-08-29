---
title: Routing Standard
status: draft
part_of: optimization
doc_type: companion
layer: shared
---

# Routing Standard

**Referenced by:** `charter.md` · `delivery_pulse_runbook.md` · `../work_packet_contract.md`

## Purpose

Decides *whether a request should reach an agent at all*, and if so which one — before any agent is
dispatched.

The Core Orchestrator routes between **phases** of an already-accepted run. Nothing routes at the
entry point. In SDLC that gap is invisible: everything arriving is a code change, and the pipeline
has one shape. In Optimization the arriving work varies enormously in consequence — "what did we
decide about the vendor" and "publish the status update to the steering committee" are not the same
kind of request, and running both through the full pipeline is as wrong as running neither.

This is the one genuinely new mechanism the external review identified. It is `layer: shared`: the
*axes* below are domain-neutral and belong to Core if this is ever generalized; the thresholds and
the destinations are adapter data.

## The four axes

Every request is scored on four axes before routing. Deterministically, from structured signals —
Principle 10 applies here as everywhere: an LLM sees only what the rules cannot classify.

| Axis | Question | Signal |
|---|---|---|
| **Data sensitivity** | What is being read? | The `sources` register's classification of each approved source |
| **Consequence** | What happens if the output is wrong and nobody catches it? | Whether the output leaves the team, and who receives it |
| **Repeatability** | Has this exact shape of request been handled before? | Match against the capability registry |
| **Action risk** | Does anything change as a result? | Whether the request implies any intent against a register |

## The routing table

First match wins, evaluated in order — the same ordered-rules-first-match discipline as
`infra_triage_matrix.md` §2, and for the same reason: ordering encodes precedence, so an unordered
table hides its own conflicts.

| # | Condition | Route to |
|---|---|---|
| 1 | Action risk is non-zero **and** the implied op is non-additive | **Structural Change SOP.** Never an agent |
| 2 | Data sensitivity exceeds the requester's read permissions | **Refuse.** Not a degraded answer — a refusal |
| 3 | Consequence is external **and** repeatability is low | **Full pipeline** with human approval before release |
| 4 | Consequence is external **and** repeatability is high | **Delivery Pulse runbook** |
| 5 | Action risk is zero **and** consequence is internal | **Single specialist**, evidence-bound, no gate |
| 6 | Otherwise | **Refuse and ask.** An unclassifiable request is a signal, not a default case |

Rule 6 is the one that matters. A routing table whose fallback is "do something reasonable" will
route its hardest cases to its least examined path. Falling through to a refusal makes the gap
visible, and the volume of rule-6 hits is the signal for extending the table — the same way
Test Investigator classifications are raw material for new deterministic triage rules.

## Why refusal is a first-class outcome

Rules 2 and 6 both refuse. This mirrors `AbsentCapabilityPolicy`, which offers `REFUSE` or
`DEGRADE` and deliberately no third option meaning "carry on and say nothing."

A router that always produces an answer has no way to express "this should not have been asked of
an agent," and every request it cannot classify becomes an answer nobody checked.

## What this does not do

- **It does not decide correctness.** Routing decides *which path*; the gates on that path decide
  whether the output is good.
- **It does not create tasks.** A request routed to the full pipeline still passes the human plan
  approval gate. The external review's "no automatic task creation" is satisfied here.
- **It is not calibrated.** The thresholds on all four axes are illustrative. Nothing has been
  measured, and the table's rule order is an argument rather than a finding.
