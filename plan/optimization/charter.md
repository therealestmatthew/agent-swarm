---
title: Optimization System Charter
status: draft
part_of: optimization
doc_type: companion
layer: shared
---

# Optimization System Charter

**Referenced by:** `core_vs_adapter.md` · `core_adapter_boundary.md` §6 · `CLAUDE.md`

## 1. What this is

Two adapters on the existing Core, for work that is not software delivery:

- **Personal Optimization** — an individual's goals, commitments, habits, and notes
- **Team Optimization** — a team's project state: actions, decisions, RAID, milestones,
  deliverables, status reporting, handovers

They are **adapters, not a new system**. Every mechanism they use — Maker/Checker pairing, bounded
loops, the escalation ladder, governed shared state, deterministic-before-LLM triage, Shadow Mode
calibration, human gates — is the Core the SDLC pipeline already uses. What is new here is the
declared nouns.

## 2. Why two, and why now

`core_adapter_boundary.md` §6 already requires a second, deliberately dissimilar adapter, and says
why:

> One adapter does not demonstrate an abstraction. It demonstrates a coupled system with an extra
> layer of indirection, and the two are indistinguishable from inside.

Its dissimilarity axes were all *technical* — different language, transformer, isolation unit,
signal set. **This charter adds one more: a different task domain.** That is the strongest available
falsifier, because the SDLC adapter's most load-bearing nouns (a test suite, a git worktree, a diff)
have no counterpart here at all. If the Core survives that, the abstraction is real. If it does not,
the failure is informative rather than embarrassing — which is the point of writing a falsifier down
before running it.

Personal and Team are deliberately dissimilar *from each other*, too. Team has multiple concurrent
writers, an approval hierarchy, and an audience; Personal has one writer, no approval chain, and no
audience. Two adapters that differ only cosmetically would prove nothing beyond one.

## 3. The three substitutions

The SDLC adapter answers three questions the Core cannot answer for itself. Optimization answers
them differently, and these three answers *are* the adapter:

| Question | SDLC answer | Optimization answer |
|---|---|---|
| What is the isolation unit? | A git worktree | A **snapshot-pinned read view** plus an **enumerated record-ID write lease** |
| What is the governed shared artifact? | A registered source file, mutated by typed additive intents | The **register set**, mutated by the same intent mechanism with a different vocabulary |
| What is the oracle? | The test suite | **Evidence binding** — every claim resolves to a live, in-scope, non-stale record |

### 3.1 Isolation

`execution_isolation.md` §1 argues write isolation alone is insufficient because *"verification is
repo-scoped even when editing is file-scoped."* The analogue holds exactly: a status synthesis is
**project-scoped** even when the edit is **record-scoped**. Two agents can hold non-overlapping
record leases and still invalidate each other's output, because each reads the whole project.

So the same argument that forces one worktree per task forces a **consistent register snapshot
pinned at task start**. The write lease is an enumerated set of record IDs, *derived from the
decomposition rather than discovered at runtime*, per §5.

### 3.2 Governed state

Detailed in `project_state_model.md`. The additive vocabulary — `AddAction`, `AddDecision`,
`AddRisk`, `AddMilestone`, `AddEvidenceLink` — and the non-additive operations that exit through the
Structural Change SOP.

This is where the external review's demand for "no direct writes to source-of-truth registers" is
satisfied, and satisfied more strictly than it asked: agents do not write at all. They emit typed
intents that one deterministic service applies. It is a structural property, not a policy someone
enforces.

### 3.3 Verification without a test suite

The hardest substitution, because the test suite is the SDLC adapter's entire claim to knowing
whether anything worked.

**Every claim in a generated artifact carries an `evidence_ref`** resolving to a record in the
governed store, with a freshness stamp. The deterministic gate is `claims.all_bound`: every
assertion resolves to a live, in-scope, non-stale record. Unbound claim, stale record, or
out-of-scope reference fails the gate.

This is mechanically checkable and resists gaming in the way a test suite does — an agent cannot
make it pass by writing more confidently, only by citing something real. `Finding.evidence_ref`
already exists in `contracts/verification.py`; the mechanism is a use of the schema, not an
extension of it.

**And the Baseline Guard generalizes.** Its SDLC job is catching silent test deletion; the cheapest
way to make a suite green is to delete the failing test. The cheapest way to make a status report
clean is to omit the failing risk. So the same guard becomes an **Omission Guard**: a status update
that drops a risk carried in the prior approved update is blocked, and clearing it is a human gate.
Same asymmetry — tightening automatic, loosening human-gated — for the same reason.

## 4. What is deliberately not adopted

The external review listed 9 anti-patterns. **8 are already structurally prevented by the Core**,
several more strictly than it proposed. Only one is new:

- **No cross-project memory.** A genuine gap. `InvariantScope` has the right shape
  (`REPO_LOCAL` / `ENTERPRISE_WIDE`) but nothing obliged an Archivist to declare its scope. Now
  every Archivist card carries a required `Retention and scope` section
  (`../agents/types/archivist.md`). For these adapters that field is load-bearing: a Vault spanning
  clients or engagements is the failure mode.

Also not adopted, with reasons:

- **A separate Evaluation Pack** — this is the adapter conformance kit (`core_adapter_boundary.md`
  §6, roadmap R10). Optimization's golden scenarios go into that kit. A parallel structure would be
  a second vocabulary for one concept.
- **A Run Log and Feedback Register** — this is the Verdict Ledger
  (`calibration_and_measurement.md` §1). Its accepted/edited/rejected vocabulary extends the
  ledger's `human override` column.
- **An Orchestration Policy document** — `budget_and_escalation_policy.md` plus
  `GovernancePolicy.concurrency_cap` plus `core_adapter_boundary.md` §3.6 already own this.

## 5. Onboarding ladder

Reusing the shape from `adapter_onboarding.md`, whose Level 0–3 progression is domain-neutral even
though every rung filling it is SDLC:

| Level | Optimization meaning |
|---|---|
| 0 | Ad-hoc chat over project documents. No adapter, no governance, read-only |
| 1 | Registers exist and are readable. Evidence Retriever operates; nothing writes |
| 2 | Project-State Validator runs; deterministic data-quality rules; exceptions queue |
| 3 | Full additive-intent governance; Status Synthesizer and Quality Reviewer gate; human approval |

## 6. Status and what is not claimed

**Draft. Nothing here has been run.** No adapter has been built, no conformance kit exists, and the
Core has not been exercised against a non-software domain even once.

The claim is narrow: the three substitutions in §3 are stated precisely enough to be argued with,
and the Core mechanisms they rely on are named. `core_adapter_boundary.md` §6's standard — a
dissimilar adapter passing an *unmodified* conformance kit — is explicitly not met, and this
charter should not be read as evidence toward it.

Six closed constructs in Core (`core_vs_adapter.md` §6) will block this adapter as written. That is
the concrete prediction this charter makes, and the first thing an implementation attempt would
confirm or refute.
