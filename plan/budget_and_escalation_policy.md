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

## 3. Cost Ceilings

Global run constraints that trigger a ceiling halt. Illustrative starting values — tune to your org's actual cost tolerance and repo size before relying on these:

| Constraint | Scope | Notes |
|---|---|---|
| Total token budget | Full run, all agents combined | Set per repo size / task complexity |
| Dollar cost ceiling | Full run | Set per org budget policy |
| Wall-clock ceiling | Full run | Set per SLA for the target repo |
| Phase 4 (swarm) sub-budget | Parallel swarm specifically | Largest share of the total — the most token-intensive phase |

On breach of any ceiling: the Budget **Enforcer** issues a ceiling halt (see §4 for why not the Accountant). The pipeline pauses, current state is snapshotted (same discipline as the Structural Change SOP's pause step, `structural_change_runbook.md` §3), and a human is notified to either raise the ceiling and resume or abort the run. **A ceiling halt is never silent and never auto-resumes.**

---

## 4. Where the ceiling is enforced

*Resolves D3 in `implementation_roadmap.md`: the Agent Roster typed the Budget Accountant as a
Utility **agent** that "can trigger a ceiling halt," while design doc §9.1 listed
`budget.within_ceiling` as a **deterministic** gate on every transition. Those describe different
things, and the difference is load-bearing.*

### 4.1 Enforcement is deterministic middleware

The ceiling check runs **in the dispatch path**, as middleware the Core Orchestrator cannot route
around. It reads `GovernancePolicy.budget_ceilings` (`agent_interface_contracts.py`) directly and
refuses the transition on breach, emitting `HaltReason.CEILING_HALT`.

The reason it cannot be an agent: a circuit breaker that is itself an LLM can be slow, wrong, or
unavailable — and it fails hardest under exactly the runaway conditions it exists to catch, because
those are the conditions that saturate the same API it depends on. A breaker that fails open under
load is not a breaker. This is Principle 10 (deterministic before LLM judgment) applied to the one
check whose failure is unbounded rather than merely wrong.

It also puts enforcement at the same layer as the policy that defines it. `budget_ceilings` is
control-plane state changed at a governance gate (`core_adapter_boundary.md` §3.2); reading it in
middleware means there is one place a ceiling is set and one place it is applied.

### 4.2 The Budget Accountant forecasts, and gates nothing

What remains for an agent is the genuinely judgment-shaped half: *is this run trending toward a
ceiling, and why.* Extrapolating burn from partial-run telemetry, spotting that one task's retry
loop is consuming a disproportionate share, noticing a swarm width that will not finish inside the
wall-clock ceiling — none of that reduces to a threshold comparison, and all of it is useful before
a halt rather than at one.

The Accountant therefore raises **advisory** `Finding`s only (`GateResult.passed` is never flipped
by it) and holds no halt authority. That is what makes it safe to be an LLM: nothing depends on it
firing. A missed forecast costs a warning that would have been nice to have; a missed enforcement
costs the budget.

### 4.3 Consequences for the ledger

`calibration_and_measurement.md` §4 crosses per-agent spend against per-validator precision to get
cost per genuinely-caught defect. That attribution is produced by the same metering the Enforcer
reads, not by the Accountant — so the cost-per-pair calculation stays available whether or not the
Accountant is running, and does not inherit an advisory agent's error bars.
