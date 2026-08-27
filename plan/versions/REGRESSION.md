---
title: v0.1 → v0.4 Regression Analysis
status: live
part_of: agentic-sdlc
doc_type: analysis
---

# v0.1 → v0.4 Regression Analysis

**Purpose:** v0.2's changelog documents six additions. It documents zero removals. Reading v0.1
against the live set (v0.4 + its six companions) turns up material that didn't survive the
transition and was never marked as cut — it just stopped appearing. This file catalogues that
material with a keep/reinstate/drop call for each, so the gaps get a decision rather than staying
invisible.

**Method:** every claim below was grepped against the live set before being written down. "Absent"
means zero hits for the concept, its close synonyms, and its schema field names — not that I didn't
notice it elsewhere.

---

## Why this matters now

The task at hand is formalizing the design. A formalization pass built on top of an undocumented
regression will re-solve problems v0.1 already solved, miss the reasoning that justified decisions
now stated as bare assertions, and inherit a false sense that "resolved" and "silently dropped" are
the same thing. They aren't, and v0.4's own §8 changelog convention — *"nothing here was demoted for
being unimportant"* — is a standard the design has already broken once.

---

## Findings, ranked by how load-bearing the gap is

### 1. Validator asymmetry is gone. Maker/checker without it is agreement, not review.

**v0.1 principle 2:** *"A validator only adds signal if it is asymmetric to the generator"* —
reviewers get the spec and the artifact, never the builder's rationale, because *"if the writer can
explain itself to the reviewer, you have built a persuasion channel, and the writer is better at
persuading than the reviewer is at resisting."* Detailed at three levels in v0.1 §3.8: information
asymmetry (spec + diff, not reasoning), tooling asymmetry (the reviewer can execute — run tests, run
mypy, grep for callers), model asymmetry (a different tier, at minimum).

**Current state:** v0.4's principle 1 keeps Maker/Checker pairing. Asymmetry — in any of its three
forms — appears nowhere in the live set.

**Why it matters:** this is the mechanism that makes "checker" mean something other than "second
opinion from someone who saw the same reasoning." Without it, a validator that reads the generator's
own justification is at real risk of grading the persuasion rather than the artifact. This is the
single highest-priority reinstatement in this document.

**Recommendation: reinstate**, as an explicit clause under Maker/Checker Pairing in the core
blueprint (not a companion — this is principle-level, not mechanics). State plainly what each
validator agent does and does not see, per agent.

---

### 2. Worktree isolation is gone, and "disjoint write ownership" alone doesn't cover what it covered.

**v0.1 §6:** one git worktree per task. The reasoning is specific and doesn't survive being
summarized as "isolation": *"Your ownership map isolates the writes. It does nothing for the reads:
the moment one agent runs pytest, the interpreter imports the whole package including the file
another agent is halfway through rewriting. Verification is repo-scoped even when editing is
file-scoped."*

**Current state:** v0.4 principle 4, Disjoint Write Ownership, covers only the write side. Nothing
in the live set addresses concurrent verification against a shared working tree.

**Why it matters:** this isn't a nice-to-have parallelization detail — it's the difference between
"two agents can't edit the same file" (true today) and "two agents can't observe each other's
in-progress state" (currently false). A Task Dev agent running its local test suite mid-swarm can
import another task's half-written module.

**Recommendation: reinstate**, as mechanics in a new companion file (matching v0.4's own pattern of
relocating mechanics out of the blueprint) — call it `execution_isolation.md`. Keep v0.1's caveat
too: containers are not required for a pure unit suite with no external dependencies; revisit if
tests start binding ports or needing a database.

---

### 3. Diff-scoped mutation testing is gone, and the thing it answered has no full replacement.

**v0.1 §7** calls it *"the standout recommendation... the only deterministic answer to 'did the
agent write a real test or a tautology?'"* — a fast hermetic unit suite makes `mutmut` affordable,
run per task branch against changed files only. It was also a named deterministic gate:
`mutation.diff_scoped`, blocking, at Verification.

**Current state:** `test_harness_architecture.md` §2 addresses a different, narrower failure —
Protocol fakes catch interface *drift* (a fake accepting a call the real dependency wouldn't). They
don't catch a syntactically real test with a weakened assertion (`>` quietly become `>=`). v0.1 was
explicit these are separate attacks with separate guards; only one guard survived.

**Recommendation: reinstate**, as a deterministic gate. Natural home is
`test_harness_architecture.md` §2, alongside the Protocol-fake standard it complements rather than
duplicates.

---

### 4. The Run Manifest doesn't exist, and the orchestrator's actual state representation is unspecified.

**v0.1 §3.1:** the Core Orchestrator's context is *only the manifest and the event log — never a
plan body, never a diff.* The transition function is pure over the manifest, so it's unit-testable
with no model client. The manifest persists after every transition, so a crashed run resumes from
the last phase.

**Current state:** the roster describes the Core Orchestrator's *job* ("coordination and routing
only; minimal context") but not its *data*. There is no `RunManifest` model in
`agent_interface_contracts.py`, and nothing else defines what "minimal context" is a manifest of, or
how a crashed run would resume.

**Why it matters:** this is different in kind from the other gaps — it's not a dropped mechanism,
it's a load-bearing data structure with no current specification at all. "Minimal-context
orchestration" (principle 2) is a design goal without a schema behind it.

**Recommendation: reinstate**, as a `RunManifest` schema in `agent_interface_contracts.py` (it's a
cross-agent contract, which is exactly what that file owns) plus a short section restoring v0.1
§3.1's resumability argument in the core blueprint.

---

### 5. Shadow Mode has no exit criterion anywhere in the live set.

**v0.1 §8 ("Measurement and calibration")** opens: *"Without this section the validator agents are
unfalsifiable, and expensive ceremony looks identical to expensive value from inside the loop."*
Defines: a **verdict ledger** (every `GateResult` appended with what happened next — did a human
overturn it, did the bug reach production), shadow-as-default onboarding (*"you are the oracle on
this repo... spend that advantage before it is gone"*), **agent spec versioning** (a `GateResult`
records the spec version that produced it, so a changed prompt doesn't silently invalidate
historical precision data), and per-pair cost tracking.

**Current state:** verified directly — the glossary's own Shadow Mode entry says a validator gates
"until their accuracy is calibrated against a baseline," and that sentence is the *only* place
calibration is mentioned anywhere in the live set. No baseline is defined. No ledger, no versioning,
no threshold.

**Why it matters:** `Code Reviewer | Validator (shadow mode)` sits in the roster today with
genuinely no defined path out of shadow mode. As written, it stays in shadow forever, or promotes on
someone's unstated judgment call.

**Recommendation: reinstate**, as its own companion (`calibration_and_measurement.md`), following
v0.4's own precedent of extracting mechanics. This is the second-highest priority after asymmetry —
it's not a nice-to-have, it's the missing other half of a mechanism (Shadow Mode) that's already in
the live glossary.

---

### 6. "Enforce with permissions, not prompts" — stated as an outcome, not as the required mechanism.

**v0.1 principle 4's consequence column, verbatim:** *"Write scopes are config, not instructions an
agent can reason its way past."*

**Current state:** v0.4 states the *outcome* ("Test Author... never touches implementation") without
the *commitment* that this must be enforced at the permission/config layer rather than told to the
agent in its instructions. That's a meaningful difference for anyone implementing this: a system
prompt saying "don't touch `src/**`" and a filesystem or git-hook enforcement of the same rule
produce identical-looking specs and very different failure modes.

**Recommendation: reinstate**, as one explicit line under Disjoint Write Ownership or TDD-First
Build. Cheap; skipping it is a bug waiting to happen once someone implements against the design.

---

### 7. Anti-reward-hacking framing is gone as a named threat model; the guards are scattered and one is unguarded.

**v0.1 §7** opens by naming the actual adversarial frame: *"The pipeline's objective is 'tests pass
and reviews approve.' Both are hackable, and the cheapest path to green is usually the dishonest
one."* Then an explicit attack table: delete/skip a test → Baseline Guard; weaken an assertion →
mutation testing (see #3, now unguarded); tautological test → Test Author's disjoint write scope;
mock away the behavior under test → Protocol fakes; silence a type error → CI Cleanup's diff-shape
check; reviewer ratifies the builder → asymmetry (see #1, also gone).

**Current state:** the individual guards mostly survive as agent behaviors (Baseline Guard,
Protocol Fake), but the *frame* — that these are deliberate, adversarial, and worth enumerating as a
threat model rather than a list of unrelated best practices — is gone. And per #3, one attack
(weakened assertions) currently has no guard at all.

**Recommendation: reinstate the framing**, once #1 and #3 land — at that point this is a
five-minute pass restating the table against current agent names, not new design work.

---

### 8. Five open questions were dropped, not answered.

v0.1 §10 lists five: task granularity ("the parameter most likely to be wrong on the first
attempt"), concurrency ceiling, Plan Writer dialogue depth, where the run manifest lives, secrets
posture. All five have zero hits anywhere from v0.2 onward — not resolved, not carried forward,
simply absent from every subsequent §8/§10.

Compare to how v0.4 actually handles a *closed* question — v0.1's threat-surface naming, v0.1's
manifest-location question (#4 above depends on resolving this one first) — each gets a changelog
row or a "resolved in vX" note. These five got neither.

**Recommendation:** re-list all five in `agentic-sdlc-design-v0.4.md` §8, explicitly marked as
"carried forward, unaddressed since v0.1" so the record is honest about their status. Secrets
posture and manifest location are prerequisites for #4 above and should be resolved together with
it, not independently.

---

### 9. Build order (v0.1 §9) — hold, not reinstate.

A sequencing list for implementation, ordered by decreasing certainty. `CLAUDE.md` currently states
*"we are in design, not build"* as the gating condition for this whole repo. A build order is
exactly the artifact that becomes relevant the moment that line changes and not before.

**Recommendation: do not reinstate now.** Note it here so it isn't lost, and revisit when
`CLAUDE.md`'s own gate opens.

---

## Naming drift (low effort, worth doing before more content lands on top of it)

- **"Synchronous Intent Service"** (original glossary term, and the title of §4 in v0.2/v0.3) vs
  **"Shared-File Intent Service"** (the v0.4 roster table and `agent_interface_contracts.py`'s
  docstring). Same agent. Both names are now in the glossary as cross-referenced aliases; the source
  documents themselves still disagree.
- **"Contract review"** (v0.1 §4.3) → **"Contract Freeze"** (v0.2 onward). Purely cosmetic, already
  settled by usage, no action needed — noted for completeness.
- **`orchestration_contracts.py`** (v0.1's companion artifact name) → **`agent_interface_contracts.py`**
  (the actual file in this repo). Also settled by usage.
- **"Promotion"** means three unrelated things across the live set: a shared file being promoted
  into the registry (§4.6), a QA build being promoted to Production (Phase 7), and a shadow validator
  being promoted to gating (glossary, Shadow Mode). Not a defect, but worth a disambiguating word
  choice if the design gets much denser — three meanings under one term is exactly the kind of
  ambiguity the rest of this design is built to eliminate everywhere else.

---

## Summary table

| # | Gap | Priority | Disposition |
|---|---|---|---|
| 1 | Validator asymmetry | **Highest** | Reinstate — core blueprint, principle-level |
| 2 | Worktree isolation | High | Reinstate — new companion, `execution_isolation.md` |
| 3 | Diff-scoped mutation testing | High | Reinstate — `test_harness_architecture.md` §2 |
| 4 | Run Manifest | High | Reinstate — schema in `agent_interface_contracts.py` + blueprint section |
| 5 | Calibration / verdict ledger | High | Reinstate — new companion, `calibration_and_measurement.md` |
| 6 | "Permissions, not prompts" | Medium | Reinstate — one line, cheap |
| 7 | Anti-reward-hacking framing | Medium | Reinstate — after #1 and #3 land |
| 8 | Five dropped open questions | Medium | Re-list explicitly in §8, mark status honestly |
| 9 | Build order | Low | Hold until the design phase ends |
| — | Naming drift (3 items) | Low | Cheap cleanup, any time |

Five items are marked reinstate at high or highest priority. None of the five is decorative — each
is either a mechanism the rest of the design still depends on (asymmetry underwrites Maker/Checker;
worktrees underwrite Disjoint Write Ownership; the manifest underwrites Minimal-Context
Orchestration) or a mechanism that's already half-present and currently non-functional without its
other half (Shadow Mode with no calibration path).
