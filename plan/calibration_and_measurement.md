---
title: Calibration and Measurement
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Calibration and Measurement

**Referenced by:** `agentic-sdlc-design-v0.5.md` §11 (Measurement and Calibration) · §9.2 (Agent
Gates — `code.review` promotion) · `agentic_sdlc_glossary.csv` (Shadow Mode) · `plan/contracts/verification.py`
(`GateResult.reviewer_spec_version`) · `plan/llm_output_normalization.md`

**Status:** reinstated from `agentic-sdlc-design-v0.1.md` §8, absent v0.2 through v0.4. See
`plan/versions/REGRESSION.md` finding #5 — verified before reinstating that the only reference to
calibration anywhere in v0.2 through v0.4 is the Shadow Mode glossary entry's own text, with no
baseline, ledger, or threshold defined anywhere else.

## Purpose

Without this file, the validator agents are unfalsifiable. Shadow Mode (design doc Agent Roster;
`agentic_sdlc_glossary.csv`) says a new validator "cannot gate or block progression until their
accuracy is calibrated against a baseline" — but nothing else in the design set says what the
baseline is, how it's measured, or what crossing it looks like. This file is that missing half.

## 1. The verdict ledger (Tiers 1-3)

Every `GateResult` a Validator agent produces is appended to a ledger alongside what happened next. We structure calibration into three distinct tiers based on observability:

*   **Tier 1: Human Agreement Rate (Immediate):** The frequency with which the validator's verdict matches a human reviewer's explicit override or approval on the PR/diff. This is 100% observable.
*   **Tier 2: Integration-Time Catch Rate (Near-Term):** The rate at which integration testing (e.g., test harness runs, staging deployments, post-merge CI) catches a defect that the validator *approved*. This is highly observable as it occurs within hours/days of the verdict.
*   **Tier 3: Downstream Outcome (Aspirational/Optional):** Manual or highly heuristic-driven attribution of production bugs. This is no longer on the critical path for agent promotion.

| Field | Source | Why it's recorded |
|---|---|---|
| The `GateResult` itself | The validator | Subject ref, findings, severities — the verdict being graded |
| `reviewer_spec_version` | `GateResult` (`plan/contracts/verification.py`) | So a later prompt change doesn't silently invalidate this row's precision data — see §3 |
| `human_override` | Whichever human gate follows | Tier 1: Explicit human verdict overriding or confirming the agent |
| `integration_catch_outcome` | CI / Integration Harness | Tier 2: True if integration tests caught an issue on the approved code within the CI window. The CI window is defined purely by the immediate post-merge CI pipeline success. Attribution uses a simple overlap heuristic: if modified files overlap with the failing test suite, count it as a potential miss. |
| `downstream_outcome` | Manual / Log Monitor | Tier 3: Optional manual notation of a production bug attributed to this verdict |

This is what "calibrated against a baseline" in Shadow Mode's definition actually means: the ledger
*is* the baseline, built from real verdicts on real diffs in this repo, not an externally imported
benchmark.

## 2. Shadow-mode promotion

Shadow Mode is the **default onboarding path** for every new or changed Validator agent, not an
exception. It exists because you are the oracle on your own repo in a way you are not on an
unfamiliar one — you can grade the graders here. That advantage is temporary; spend it during the
shadow window rather than promoting on faith.

To promote an agent from Shadow Mode to Active Blocking Mode, it must meet the following criteria over a rolling window of **N = 50** executions (illustrative — tune N and the thresholds to your repo's actual review volume and error rate before treating these as settled):
*   **Tier 1 (Precision against human review):** $\ge 95\%$ agreement rate with human overrides/approvals.
*   **Tier 2 (Integration catch rate on agent approvals):** $\le 5\%$ false positive approval rate (integration tests catch a defect the agent approved in fewer than 5% of cases).

A validator promotes from Shadow to Gating (design doc §9.2) only when its precision over that
window meets or exceeds this bar. There is no automatic promotion — this is itself
effectively a human gate, consistent with Principle 6 (human gates at judgment-heavy points):
moving a validator from advisory to blocking is a judgment call about the validator, not just
arithmetic on the ledger.

## 3. Agent spec versioning

`GateResult.reviewer_spec_version` (`plan/contracts/verification.py`) records which version of a
validator's prompt/spec produced a given verdict. Without this field, changing a reviewer's prompt
silently invalidates every precision and recall number gathered under the old one — the ledger keeps
accumulating rows, but they no longer describe the validator currently running. A version bump on a
validator's spec should be treated the same way a version bump on `agentic-sdlc-design` itself is
treated: as a change worth a line in whatever changelog covers that validator, precisely so old
ledger rows can be filtered out rather than silently blended with new ones.

## 4. Cost-per-Integration-Catch (CPIC)

Precision is only half the question a Maker/Checker pair has to answer. Per-agent spend is
attributed by the dispatch-path metering the Budget Enforcer reads (`budget_and_escalation_policy.md`
§4.3), not by the advisory Accountant; cross that with the
ledger's precision numbers per validator to calculate **Cost-per-Verdict** and **Cost-per-Integration-Catch (CPIC)**.

*   **Cost-per-Verdict:** Total inference spend (tied to the `VerdictLedgerEntry` ID) divided by total evaluations.
*   **Cost-per-Integration-Catch:** Total inference spend of the validator divided by the number of legitimate defects it caught before integration.

A validator with excellent precision that costs more than the defects it catches are worth is still
the wrong trade — this is the check that would surface that, ensuring the cost of running the agent is strictly bounded and justified by the immediate defects it prevents from entering the integration branch.

## 5. Schema Hallucination Rate

- Define the metric: count of `NormalizationEvent` records per model class, per agent, per model tier, over a rolling window.
- Computed from `NormalizationEvent` instances (schema: `plan/contracts/verification.py`; design rationale and escalation interaction: `plan/llm_output_normalization.md` §4).
- A high hallucination rate on a specific LLM tier or model class is a signal for prompt refinement, not runtime escalation.
- Per-tier analysis: if Sonnet hallucination rate on `GateResult` exceeds a threshold (illustrative, not settled), it surfaces as a prompt-engineering work item, not a budget event.
