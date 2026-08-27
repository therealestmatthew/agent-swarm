---
title: Budget & Escalation Policy
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Budget & Escalation Policy

**Referenced by:** `agentic-sdlc-design-v0.5.md` §7 (Circuit Breakers) · Principle 7

## Purpose

This file owns the exact thresholds the core design document only names in principle: how many retries each loop gets, what the escalation ladder looks like rung by rung, and what triggers a global ceiling halt.

---

## 1. Loop Ceilings

| Loop-back edge | Ceiling | On exhaustion |
|---|---|---|
| Plan Writer ↔ Plan Reviewer | `max_retries=3` | Escalate to human plan review |
| Task Dev ↔ Code Reviewer | `max_retries=3` | Halt, route to human (after model-tier escalation within the ladder — see §2) |
| Test Runner → Test Investigator → Task Dev | `max_retries=3` | Escalate to human triage |
| Integrator → Merge Conflict → Task Decomposer | `max_retries=3` | Halt and escalate as a boundary failure (Principle 8) |

---

## 2. Escalation Ladder

### 2.1 Standard ladder — competence-type loops
For loops where the failure plausibly reflects the current agent/model not yet succeeding, rather than a structural problem:

1. **Re-gather context** — first retry assumes the initial context injection may have been incomplete; the Context Gatherer re-runs with the failure as an added signal.
2. **Re-spec / retry at current model tier** — a second attempt at the same task, same model, covering stochastic variance.
3. **Escalate model tier** (e.g., Sonnet → Opus) — used once retries at the current tier are exhausted without success.
4. **Halt to human** — final rung; the loop has exhausted its ceiling (§1) without a passing result.

Applies to: Plan Writer ↔ Plan Reviewer, Task Dev ↔ Code Reviewer.

### 2.2 Boundary-type loops skip model escalation
The Merge Conflict → Task Decomposer loop does **not** use rung 3. A merge conflict is evidence of a decomposition error (Principle 8), not evidence the current model reasoned poorly — escalating model tier wouldn't address the actual cause. For this loop, "re-spec" (rung 2) *is* the corrective action: the Task Decomposer redefines the interface seam itself. After `max_retries=3` redefinition attempts, the loop halts directly to human escalation as a boundary failure, skipping rung 3 entirely.

### 2.3 Test Investigator loop
Also skips model-tier escalation by default. A Test Investigator loop back to Task Dev is specifically a logic-fix loop — infra-class failures are routed to the Environment/Infra queue instead (`infra_triage_matrix.md` §4), so what reaches Task Dev here is already known to be a code issue. This loop follows the ladder through rung 2, then proceeds to human triage (rung 4), unless the specific failure pattern gives a concrete reason to believe model competence is the limiting factor.

---

## 3. Cost Ceilings (Budget Accountant)

Global run constraints that trigger a ceiling halt. Illustrative starting values — tune to your org's actual cost tolerance and repo size before relying on these:

| Constraint | Scope | Notes |
|---|---|---|
| Total token budget | Full run, all agents combined | Set per repo size / task complexity |
| Dollar cost ceiling | Full run | Set per org budget policy |
| Wall-clock ceiling | Full run | Set per SLA for the target repo |
| Phase 4 (swarm) sub-budget | Parallel swarm specifically | Largest share of the total — the most token-intensive phase |

On breach of any ceiling: the Budget Accountant issues a ceiling halt. The pipeline pauses, current state is snapshotted (same discipline as the Structural Change SOP's pause step, `structural_change_runbook.md` §3), and a human is notified to either raise the ceiling and resume or abort the run. **A ceiling halt is never silent and never auto-resumes.**
