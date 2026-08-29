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

Illustrative starting values — tune to your repo's observed retry distributions and cost tolerance before treating these as settled (same convention as §3 Cost Ceilings).

| Loop-back edge | Ceiling | Target Budget (Cost Units) | On exhaustion |
|---|---|---|---|
| Plan Writer ↔ Plan Reviewer | `max_retries=2` | 2.00 | Escalate to human plan review |
| Task Dev ↔ Code Reviewer | `max_retries=3` | 15.00 | Halt, route to human (after model-tier escalation within the ladder — see §2) |
| Test Runner → Test Investigator → Task Dev | `max_retries=4` | 10.00 | Escalate to human triage |
| Integrator → Merge Conflict → Task Decomposer | `max_retries=2` | 5.00 | Halt and escalate as a boundary failure (Principle 8) |

---

## 2. Escalation Ladder

### 2.1 Standard ladder — competence-type loops
For loops where the failure plausibly reflects the current agent/model not yet succeeding, rather than a structural problem:

An "iteration" is defined as a full traversal of the escalation ladder up to the model escalation step. One "retry" equals the execution of these sub-steps:
1. **Re-gather context** — first retry assumes the initial context injection may have been incomplete.
2. **Re-spec / retry at current model tier** — a second attempt at the same task.
3. **Escalate model tier** (e.g., Sonnet → Opus) — parameterized via `EscalationConfig.escalate_to_opus_at_retry`.
4. **Halt to human** — parameterized via `EscalationConfig.require_human_halt_at_retry`. If the loop fails after model escalation, the iteration concludes.

Applies to: Plan Writer ↔ Plan Reviewer, Task Dev ↔ Code Reviewer.

### 2.2 Boundary-type loops skip model escalation
The Merge Conflict → Task Decomposer loop does **not** use rung 3. A merge conflict is evidence of a decomposition error (Principle 8), not evidence the current model reasoned poorly — escalating model tier wouldn't address the actual cause. For this loop, "re-spec" (rung 2) *is* the corrective action: the Task Decomposer redefines the interface seam itself. After `max_retries=2` redefinition attempts, the loop halts directly to human escalation as a boundary failure, skipping rung 3 entirely.

**Structural-intent deadlocks** (detected by the Intent Service's cycle detector or a `GovernancePolicy.max_mutex_rejections` breach — see `agentic-sdlc-design-v0.5.md` §4.5) are the same class of failure and skip rung 3 for the same reason: an architectural incompatibility between two tasks' intents is not a stochastic miss a stronger model would resolve. Detection is task-scoped termination — the involved tasks drop out of `RunManifest.active_task_ids` and route to the Structural Change SOP (`structural_change_runbook.md`) or to human triage per the SOP's own procedure — with no rung 1 or rung 2 retry either, because the detector fires precisely when re-planning has already failed enough times to prove it will not resolve the collision on its own.

**Coverage-family gaps** (the `gate_coverage.minimum` meta-gate returning FAIL — see `agentic-sdlc-design-v0.5.md` §9.1, §10) are boundary-type for the same reason: a `NON_TRIVIAL_CODE` diff whose coverage family entirely scoped out is a decomposition or test-design shortfall, not a stochastic miss a stronger model would close. Task-scoped termination via `RunManifest.active_task_ids` drop, no rung 3.

**Sync starvation** (a task exceeding `GovernancePolicy.max_seconds_without_sync` — see `plan/execution_isolation.md` §7.7 and `plan/contracts/governance.py`) is boundary-type for the same reason: an agent that has gone longer than the bound without reaching a subprocess boundary is violating the materialization-window protocol (`plan/execution_isolation.md` §7.6), and a stronger model does not resolve a structural violation of that protocol. Task-scoped termination via `RunManifest.active_task_ids` drop, no rung 3.

### 2.3 Test Investigator loop
Also skips model-tier escalation by default. A Test Investigator loop back to Task Dev is specifically a logic-fix loop — infra-class failures are routed to the Environment/Infra queue instead (`infra_triage_matrix.md` §4), so what reaches Task Dev here is already known to be a code issue. This loop follows the ladder through rung 2, then proceeds to human triage (rung 4), unless the specific failure pattern gives a concrete reason to believe model competence is the limiting factor.

---

## 3. Cost Ceilings

Global run constraints that trigger a ceiling halt. These targets map to abstract cost units (where the Adapter handles the conversion to actual currency like USD). Illustrative starting values — tune to your org's actual cost tolerance and repo size before relying on these:

| Constraint | Scope | Notes |
|---|---|---|
| Total token budget | Full run, all agents combined | Set per repo size / task complexity |
| Dollar cost ceiling | Full run | Set per org budget policy |
| Wall-clock ceiling | Full run | Set per SLA for the target repo |
| Phase 4 (swarm) sub-budget | Parallel swarm specifically | Largest share of the total — the most token-intensive phase |

On breach of any global ceiling: the Budget **Enforcer** issues a ceiling halt (see §4 for why not the Accountant). The pipeline pauses, current state is snapshotted (same discipline as the Structural Change SOP's pause step, `structural_change_runbook.md` §3), and a human is notified to either raise the ceiling and resume or abort the run. **A ceiling halt is never silent and never auto-resumes.** This guarantees a "Preserve and Resume" branch under crash recovery (see `crash_recovery.md`).

If a specific loop hits its `max_cost_units` ceiling before `max_retries` is reached, it DOES NOT fail silently. It immediately triggers a human `HaltReason.CEILING_HALT`, strictly consistent with global ceilings.

---

## 4. Where the ceiling is enforced

*Resolves D3 in `implementation_roadmap.md`: the Agent Roster typed the Budget Accountant as a
Utility **agent** that "can trigger a ceiling halt," while design doc §9.1 listed
`budget.within_ceiling` as a **deterministic** gate on every transition. Those describe different
things, and the difference is load-bearing.*

### 4.1 Enforcement is deterministic middleware

The ceiling check runs **in the dispatch path**, as middleware the Core Orchestrator cannot route
around. It reads `GovernancePolicy.budget_ceilings` (`plan/contracts/governance.py`) directly and
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

`calibration_and_measurement.md` §4 crosses per-agent spend against per-validator precision to calculate **Cost-per-Verdict** and **Cost-per-Integration-Catch (CPIC)**. That attribution is produced by the same metering the Enforcer reads, not by the Accountant. Crucially, this dispatch-path metering must explicitly tag costs to the `VerdictLedgerEntry` ID — so the cost calculations stay available whether or not the Accountant is running, and do not inherit an advisory agent's error bars.
