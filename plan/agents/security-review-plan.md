---
title: Security Review (plan-time)
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: shared
---

# Security Review (plan-time)

## Type

Checker.

## Pairing

Reviews the **Plan Writer**'s plan, at the same gate as the Plan Reviewer and independently of it.

## Purpose

Catches security implications while they are still design choices. A plan-time finding changes a
paragraph; the same issue found at diff time changes an implementation, and found in production
changes an incident. This is the cheapest point on that curve.

Separate from the Plan Reviewer rather than folded into it because a single reviewer optimising for
both plan coherence and security posture reliably underweights the second.

## Inputs

- The plan artifact
- The invariant manifest, particularly `enterprise_wide` constraints

## Outputs

- `GateResult` with `Finding` list

## Write scope

None.

## Layer

**Shared.** The *mechanism* — an independent reviewer with a distinct remit at the same gate — is
Core. The remit is domain-shaped: injection surfaces and credential handling in software; data
sensitivity, access scope, and disclosure in Optimization. The Team adapter's routing standard
inherits this agent's shape with a rewritten checklist.

## Loop and escalation

Shares the plan loop, `max_retries=3`, competence-type. A **blocking** security finding halts to the
human gate rather than looping — the design does not retry its way past a security objection.

## Gates

Produces `security.plan` (§9.2).

## Calibration posture

Gating, with an asymmetric bar. Precision matters less here than recall: a false reject costs a
human read, a false accept ships a vulnerability. Promotion criteria should reflect that asymmetry
rather than inheriting the roster default — noted as unresolved rather than decided.

## Failure modes

- **Reviews what the plan says rather than what it implies.** Plan-time review works on intent, so
  a security consequence that only appears in implementation is out of reach here. The diff-time
  Security Reviewer exists for exactly that residue.
- **Enterprise invariant arbitration.** When an `enterprise_wide` invariant is contested across
  repos, nothing in the design says who arbitrates. Carried unresolved since v0.3 (§12).
