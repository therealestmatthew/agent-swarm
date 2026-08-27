---
title: Calibration and Measurement
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Calibration and Measurement

**Referenced by:** `agentic-sdlc-design-v0.5.md` §11 (Measurement and Calibration) · §9.2 (Agent
Gates — `code.review` promotion) · `agentic_sdlc_glossary.csv` (Shadow Mode) · `agent_interface_contracts.py`
(`GateResult.reviewer_spec_version`)

**Status:** reinstated from `agentic-sdlc-design-v0.1.md` §8, absent v0.2 through v0.4. See
`plan/versions/REGRESSION.md` finding #5 — verified before reinstating that the only reference to
calibration anywhere in v0.2 through v0.4 is the Shadow Mode glossary entry's own text, with no
baseline, ledger, or threshold defined anywhere else.

## Purpose

Without this file, the validator agents are unfalsifiable. Shadow Mode (design doc Agent Roster;
`agentic_sdlc_glossary.csv`) says a new validator "cannot gate or block progression until their
accuracy is calibrated against a baseline" — but nothing else in the design set says what the
baseline is, how it's measured, or what crossing it looks like. This file is that missing half.

## 1. The verdict ledger

Every `GateResult` a Validator agent produces is appended to a ledger alongside what happened next:

| Field | Source | Why it's recorded |
|---|---|---|
| The `GateResult` itself | The validator | Subject ref, findings, severities — the verdict being graded |
| `reviewer_spec_version` | `GateResult` (`agent_interface_contracts.py`) | So a later prompt change doesn't silently invalidate this row's precision data — see §3 |
| Human override | Whichever human gate follows | Did a human overturn this verdict (approved something the validator blocked, or blocked something it approved) |
| Downstream outcome | Test Runner, Log Monitor, or a later phase | Did the artifact the validator passed later fail (a bug reached production; a plan materially changed after a reviewer's advisory finding was ignored) |

This is what "calibrated against a baseline" in Shadow Mode's definition actually means: the ledger
*is* the baseline, built from real verdicts on real diffs in this repo, not an externally imported
benchmark.

## 2. Shadow-mode promotion

Shadow Mode is the **default onboarding path** for every new or changed Validator agent, not an
exception. It exists because you are the oracle on your own repo in a way you are not on an
unfamiliar one — you can grade the graders here. That advantage is temporary; spend it during the
shadow window rather than promoting on faith.

Promotion criterion — illustrative, matching this project's own convention of stating thresholds as
starting points rather than settled numbers (see `budget_and_escalation_policy.md` §3):

- Precision measured against human review, over **N runs** *(N unset — tune to this repo's actual
  review volume before relying on it)*.
- A validator promotes from Shadow to Gating (design doc §9.2) only when its precision over that
  window meets or exceeds a human-set bar. There is no automatic promotion — this is itself
  effectively a human gate, consistent with Principle 6 (human gates at judgment-heavy points):
  moving a validator from advisory to blocking is a judgment call about the validator, not just
  arithmetic on the ledger.

## 3. Agent spec versioning

`GateResult.reviewer_spec_version` (`agent_interface_contracts.py`) records which version of a
validator's prompt/spec produced a given verdict. Without this field, changing a reviewer's prompt
silently invalidates every precision and recall number gathered under the old one — the ledger keeps
accumulating rows, but they no longer describe the validator currently running. A version bump on a
validator's spec should be treated the same way a version bump on `agentic-sdlc-design` itself is
treated: as a change worth a line in whatever changelog covers that validator, precisely so old
ledger rows can be filtered out rather than silently blended with new ones.

## 4. Cost per pair

Precision is only half the question a Maker/Checker pair has to answer. The Budget Accountant
(`budget_and_escalation_policy.md` §3) already attributes spend per agent; cross that with the
ledger's precision numbers per validator to get cost per genuinely-caught defect, per pair. A
validator with excellent precision that costs more than the defects it catches are worth is still
the wrong trade — this is the check that would surface that, and nothing else in the design
currently computes it.
