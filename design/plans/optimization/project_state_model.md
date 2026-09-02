---
title: Project State Model
status: draft
part_of: optimization
doc_type: companion
layer: adapter-team
---

# Project State Model

**Referenced by:** `charter.md` §3.2 · `delivery_pulse_runbook.md` · `personal_adapter.md`

The governed shared artifact for the Team Optimization adapter — what the Shared-File Intent Service
writes when the domain is project delivery rather than source code.

## 1. The registers

Eight registers. Each is a governed shared artifact in the sense of Principle 9: registered,
mutated only through typed additive intents, never edited directly by any agent.

| Register | Holds | Record identity |
|---|---|---|
| `actions` | Commitments with an owner and a due date | `action_id` |
| `decisions` | Resolved choices, with rationale and decision date | `decision_id` |
| `raid` | Risks, assumptions, issues, dependencies | `raid_id` |
| `milestones` | Dated checkpoints and their current state | `milestone_id` |
| `deliverables` | Work products and their quality gates | `deliverable_id` |
| `stakeholders` | People, roles, RACI | `stakeholder_id` |
| `meetings` | Approved meeting records | `meeting_id` |
| `sources` | The knowledge-source manifest — what may be cited | `source_id` |

`sources` is the one that makes the others checkable. `claims.all_bound` (`charter.md` §3.3) can
only resolve an `evidence_ref` if the set of citable sources is itself governed; otherwise "cite
your evidence" degrades into "name a plausible document."

## 2. The intent vocabulary

Declared per adapter via `IntentOpSpec` (`contracts/adapter_surface.py`) — Core never sees these
names, exactly as it never sees `AddRoute`.

### 2.1 Additive

| Op | Collision key |
|---|---|
| `AddAction` | `(register, action_id)` |
| `AddDecision` | `(register, decision_id)` |
| `AddRisk` | `(register, raid_id)` |
| `AddMilestone` | `(register, milestone_id)` |
| `AddEvidenceLink` | `(register, record_id, source_id)` |
| `AddStakeholder` | `(register, stakeholder_id)` |

Collision keys are **exact match only**, per `core_adapter_boundary.md` §2.1. Core does not accept
an adapter-supplied predicate function — that would move arbitration into untrusted declared code.
The keys are deliberately under-powered, and the cost of that is stated in §5.

### 2.2 Non-additive — Structural Change SOP

Deliberately absent from the vocabulary, so that attempting one cannot succeed quietly:

`CloseAction` · `ReviseDecision` · `ChangeMilestoneDate` · `ReassignOwner` · `DeleteRisk` ·
`MergeRecords` · `RenameRegister`

Each mutates or removes agreed state. `structural_change_runbook.md` applies unchanged: targeted
pause of affected work only, snapshot as rollback point, human sign-off, re-decompose, re-register,
human-confirmed resume.

**This is the load-bearing design choice in the whole adapter.** Closing an action and revising a
decision are the operations a productivity system most wants to automate, and they are exactly the
operations that overwrite a human commitment. Putting them outside the additive vocabulary means an
agent cannot perform them at all — Principle 12, enforced by the vocabulary's shape rather than by
asking agents nicely.

## 3. Source precedence

Folded in here rather than made a separate document, since it is a property of the register set.

When sources conflict, precedence is:

1. **Governed registers** — the records above. Authoritative by construction
2. **Approved documents** — items in `sources` marked approved, with an approval date
3. **Meeting records** — in `meetings`, i.e. already approved
4. **Messages and chat** — provisional, never authoritative, may only produce *candidate* records
   for human confirmation

The rule that matters: **a lower tier never silently overrides a higher one.** A chat message
contradicting a decision record does not update the decision; it raises an exception to the
human-attention queue. Anything else would let the least reviewed channel rewrite the most reviewed
one.

This extends `context_retrieval_strategy.md` §1's priority ordering rather than replacing it — same
idea, different corpus.

## 4. Freshness

Every record carries `last_confirmed_at`. Every work packet carries a freshness threshold
(`../work_packet_contract.md`). A record older than the threshold is **stale**, and a stale record
cannot satisfy `claims.all_bound` — it fails the gate rather than passing quietly with old data.

Staleness is not deletion. A stale record is still a record; it just cannot be cited as current.
That distinction is the same one `agent_taxonomy.md` §3.4 draws for `StalenessFlag`: flag for human
review, never auto-remove.

## 5. Known limits

- **Exact-match collision keys are under-powered here.** Two agents adding *semantically duplicate*
  actions with different `action_id`s do not collide, and the register accumulates near-duplicates.
  SDLC has the same limit, and `core_adapter_boundary.md` §2.1 accepts it deliberately rather than
  admitting adapter predicates. Named, not solved.
- **The additive-only vocabulary will feel wrong before it feels right.** Most register churn in
  practice is closing and revising, so a large fraction of real work routes through the Structural
  Change SOP. Whether that is correct discipline or an unusable bottleneck is the open question
  `structural_change_runbook.md` §4 already raises about SOP cadence — and this adapter will hit it
  far harder than SDLC does.
- **Nothing here has been run.** The registers, the ops, and the precedence rules are a design.
