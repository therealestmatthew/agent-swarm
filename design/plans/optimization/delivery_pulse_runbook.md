---
title: Delivery Pulse Runbook
status: draft
part_of: optimization
doc_type: runbook
layer: adapter-team
---

# Delivery Pulse Runbook

**Referenced by:** `charter.md` §5 · `routing_standard.md` rule 4 · `project_state_model.md`

The first end-to-end Team Optimization workflow: a recurring status update, produced from governed
registers, checked, and released only by a human.

Chosen first because it exercises every Core mechanism — retrieval, validation, synthesis, review,
evidence binding, human gates — without requiring any agent to change source-of-truth state. It is
the domain equivalent of the roadmap's Stage 3 "one real change, single task, no parallelism."

## The sequence

| # | Step | Agent | Output |
|---|---|---|---|
| 0 | Registers updated before the reporting cutoff | Humans | Current register state |
| 1 | Snapshot pinned; record leases derived | Core Orchestrator | Work packets |
| 2 | Data-quality validation | Project-State Validator | `GateResult` + exceptions |
| 3 | Evidence assembly | Evidence Retriever | Evidence set, scoped and freshness-stamped |
| 4 | Draft the update | Status Synthesizer | Draft, every claim evidence-bound |
| 5 | Check the draft | Quality Reviewer | `GateResult` |
| 6 | Omission check against the last approved update | Omission Guard | `GateResult` |
| 7 | Surface what needs judgment | Core Orchestrator | Human-attention queue |
| 8 | Approve, edit, or reject | **Human gate** | Released update + ledger row |

Steps 2 and 3 are independent and may run concurrently; 4 depends on both.

## Step 1 — pinning

The snapshot is pinned **before** validation, not after. Validating one state and synthesizing from
another would make every exception in step 2 unfalsifiable — the discrepancy could always be
attributed to churn between the two reads.

This is `execution_isolation.md` §5 applied: the isolation unit is derived, not discovered.

## Step 2 — validation before synthesis

Deterministic rules first, per Principle 10. Overdue actions, missing owners, unassigned risks,
milestone dates changed since the last approved update, decisions with no recorded rationale — all
mechanically checkable from the registers, no LLM required.

**Validation gates synthesis.** Drafting a confident update over registers known to be incomplete
produces the most expensive failure this workflow has: a clean-looking report that is wrong, which
is worse than a report that says data is missing.

## Step 6 — the Omission Guard

The Baseline Guard, retyped for this domain (`../agents/baseline-guard.md`).

Its SDLC job is catching silent test deletion, because the cheapest way to make a suite green is to
delete the failing test. The cheapest way to make a status report clean is to omit the failing risk.
Structurally identical, so the guard is identical: compare against the last approved update, block
on unexplained disappearance, and require a **human gate** to clear it.

The asymmetry carries over intact — tightening automatic, loosening human-gated — because dropping a
risk *"is self-rewarding for whoever proposes it"* (`test_harness_architecture.md` §1.5).

## Step 7 — the human-attention queue

Every queued item shows source, date, owner, and the reason it was escalated. Never a bare priority
ordering — the external review's "no opaque prioritization" is the same requirement as Principle 7,
and an attention queue that cannot say why an item is on it is asking for trust it has not earned.

## Step 8 — the gate, and the ledger

Approval is a human gate and not delegable. The disposition — accepted, edited, rejected — appends a
row to the **Verdict Ledger** against the Quality Reviewer's verdict.

This is the calibration loop, and it is unusually well-conditioned here: a human disposition lands
on *every* pulse, so the ledger fills at the reporting cadence rather than waiting for incidents.
The Quality Reviewer should reach a promotion decision faster than the Code Reviewer does in SDLC.

The reviewer's edits are a **controlled improvement signal**, not a memory write. Nothing an
approver changes updates any register or any agent's behaviour automatically. That is the external
review's "no self-modifying prompts" and Principle 12, and it is why the loop runs through
`reviewer_spec_version` rather than through the agents learning in place.

## Failure modes

- **Registers stale at cutoff.** The workflow's precondition, and outside its control. Step 2 makes
  it visible rather than absorbing it: an update built on stale registers must say so.
- **Evidence-bound and still wrong.** `claims.all_bound` proves each claim cites a live record. It
  does not prove the claim follows from the record, and no deterministic gate can. That residue is
  what the Quality Reviewer and the human approver are for — stating it plainly so the gate is not
  mistaken for more than it is.
- **Approval fatigue.** A recurring gate a human always approves stops being a gate. The ledger's
  edit rate is the measurement; a rate near zero means either the agents are excellent or the gate
  is ceremonial, and those are distinguishable only by sampling.
