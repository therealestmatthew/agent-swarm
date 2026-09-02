---
title: Core vs. Adapter Classification
status: live
part_of: repo-meta
doc_type: classification
layer: shared
---

# Core vs. Adapter Classification

**Referenced by:** `core_adapter_boundary.md` §1 · `CLAUDE.md` · `implementation_roadmap.md` §3

## Purpose

`core_adapter_boundary.md` owns the *rule* for what belongs to the universal Core and what a target
declares for itself. This file applies that rule to every artifact currently in the set and records
the verdict, so "the Core is reusable" stops being a claim and becomes a table someone can argue
with.

It exists because a second and third adapter are being designed that are **not software
repositories** — see `optimization/charter.md`. Building those against an unexamined Core would
repeat the mistake the boundary file was written to prevent, one level up.

---

## 1. The criterion, and the flaw in how it was stated

The boundary file's rule:

> Core owns every mechanism; the adapter owns every noun. If a thing can be wrong in a way that is
> specific to one **codebase**, it is adapter data. If it can be wrong in a way that would be wrong
> for every **codebase**, it is Core code.

The rule is right. Its quantifier is too narrow. "Every codebase" ranges over *repositories* —
different languages, different test runners, different transformer engines — and never over *task
domains*. Nothing in the set, before this file, asked whether a mechanism would still be correct
for work that is not software delivery at all.

That is not a hypothetical gap. It is why `Capability` can only name testing capabilities, why
`IsolationUnit` offers a choice between two git-and-container nouns, and why a triage rule declared
by an adapter can only route to one of three named development agents. Each is a place where an
adapter is free to declare *values* but not to declare *the kind of thing it is*.

**The restated criterion used throughout this file:**

> A mechanism is Core if it would be wrong in the same way for every *task domain* — not merely for
> every codebase. A noun is adapter data if a different domain would name it differently or not
> need it at all.

---

## 2. The layer vocabulary

Recorded in the `layer:` front-matter field on every document. Values are defined in
`scripts/frontmatter.py:LAYERS` and validated on every commit.

| Value | Meaning |
|---|---|
| `core` | Universal orchestration machinery. One implementation, every domain |
| `adapter-sdlc` | The software-delivery adapter's declared nouns |
| `adapter-personal` | The Personal Optimization adapter |
| `adapter-team` | The Team Optimization adapter |
| `shared` | Genuinely spans layers; the per-section table below says which parts go where |
| `repo-meta` | Repository housekeeping; classifies neither |

A file's `layer` records its **dominant** classification. Most documents are not pure, so §4 carries
the section-level detail for the mixed ones. Where the two disagree, §4 is authoritative — a
front-matter field cannot express "80% of this is universal."

---

## 3. Verdicts — documents

Portability percentages are estimates from reading each file for domain-coupled nouns, not
measurements. They are here to rank, not to be quoted as data.

| Document | Layer | Survives a domain change | Why |
|---|---|---|---|
| `llm_output_normalization.md` | `core` | ~100% | Concerns LLM JSON against strict Pydantic models. Contains no software-delivery content whatsoever — the cleanest Core document in the set |
| `calibration_and_measurement.md` | `core` | ~90% | A general theory of how a validator earns the right to block. The ledger's four columns work verbatim for any checker |
| `context_retrieval_strategy.md` | `core` | ~90% | Distinguishes retrieval modes by *question type*, not by git. Only the literal `git log -S` / `git blame` calls are SDLC instantiation |
| `budget_and_escalation_policy.md` | `core` | ~80% | Its load-bearing insight is about *failure types* — a structural failure is not fixed by a smarter model. Only the loop-edge role names are SDLC |
| `crash_recovery.md` | `core` | ~80% | Startup reconciliation, orphan cleanup, no-recompute-on-resume and phase-boundary decay are pure orchestration. §3's `git reset --hard` on `shared/` is the one SDLC mechanism |
| `core_adapter_boundary.md` | `shared` | ~85% | The boundary rule, the declaration/policy split and §3.1's discriminating test are Core. The worked examples are all repo-shaped |
| `structural_change_runbook.md` | `shared` | ~70% | The SOP skeleton — targeted pause, snapshot, human sign-off, re-decompose — is domain-neutral. Its triggers (routers, export barrels, DI graphs) are SDLC examples |
| `agent_taxonomy.md` | `shared` | ~85% | The 6 agent types are wholly domain-neutral and become Core vocabulary. The roster it types, and the Vault's SDLC inputs, are adapter-side |
| `infra_triage_matrix.md` | `adapter-sdlc` | Engine ~100%, content ~0% | The boundary file already reclassified this from *the engine* to *one adapter's reference rule set*. Every field and every rule is browser/test specific |
| `adapter_onboarding.md` | `adapter-sdlc` | Ladder ~80%, content ~0% | The Level 0→3 progressive-onboarding **ladder** is a genuinely reusable idea (see §5). Everything filling it — test tiers, pytest, browser pools — is SDLC |
| `execution_isolation.md` | `adapter-sdlc` | ~25% | §2, §6 and §7.2 are git plumbing. §1 (writes-only isolation is insufficient) and §5 (isolation strength is derived, not discovered) are Core arguments trapped in an SDLC document |
| `test_harness_architecture.md` | `adapter-sdlc` | ~10% | Protocol fakes and mutation testing are irreducibly software. Two rules generalize — see §4 |
| `agentic-sdlc-design-v0.5.md` | `shared` | Principles ~85% | 10 of 12 principles are Core; the 8 phases and the roster are SDLC. See §4 |
| `implementation_roadmap.md` | `adapter-sdlc` | — | A build sequence for the SDLC system specifically |
| `agentic_sdlc_glossary.md` | `shared` | Schema 100%, terms ~50% | The category axis is reusable; the term set is weighted heavily toward Test Harness and Shared-File Governance |
| `versions/*` | `adapter-sdlc` | — | Superseded blueprints; classified for completeness, not for reuse |

---

## 4. Section-level detail for the mixed documents

Only the files where the file-level verdict hides something important.

### `agentic-sdlc-design-v0.5.md` §1 — the twelve principles

**10 of 12 are Core.** This is the substantive evidence that the design is reusable.

| # | Principle | Verdict |
|---|---|---|
| 1 | Maker/Checker pairing | `core`, verbatim |
| 2 | Minimal-context orchestration | `core`, verbatim |
| 3 | TDD-first build | **`adapter-sdlc`.** Generalizes as: *the acceptance criterion is fixed before the artifact is produced, and authored by someone other than the producer* |
| 4 | Disjoint write ownership | `core` mechanism; the adapter supplies the ownership unit |
| 5 | Human gates at irreversible points | `core` — and more load-bearing outside software, not less |
| 6 | Model escalation on repeated failure | `core`, verbatim |
| 7 | Budget and circuit-breaking | `core`, verbatim |
| 8 | Merge conflicts are decomposition errors | **`core`, restated**: *a write collision on a shared artifact is evidence the decomposer drew boundaries wrong.* "Merge conflict" is the SDLC noun for it |
| 9 | Shared state is governed, not merged | `core`, verbatim |
| 10 | Deterministic classification before LLM judgment | `core`, verbatim |
| 11 | Validator asymmetry | **`core`, one clause restated.** Information and model asymmetry carry over untouched; tooling asymmetry ("a validator can execute") becomes "a validator can independently verify against source data" |
| 12 | Enforce with permissions, not prompts | `core`, verbatim |

### `execution_isolation.md` — two Core arguments in an SDLC file

- **§1** — *"Verification is repo-scoped even when editing is file-scoped."* This is a general
  claim about any pipeline whose validation touches shared state, and it is the reason write
  isolation alone is insufficient. `core`.
- **§5** — isolation strength is *derived* from declared resource needs, so it is "a fact about a
  run rather than a discovery when the machine starts swapping." The derivation is `core`; the
  worktree/container answer it derives is `adapter-sdlc`.
- **§7.3** — isolated from *in-progress work*, deliberately **not** isolated from *governed shared
  state*. A reusable concurrency rule. `core`.

### `test_harness_architecture.md` — two rules worth extracting

- **§1.2** — *"clearing routines only reach what they explicitly enumerate,"* hence construct fresh
  rather than clean in place. True of any stateful fixture. `core`.
- **§1.5** — tightening a guard is automatic, loosening it is a human gate, because loosening "is
  self-rewarding for whoever proposes it." A governance asymmetry with no software content at all.
  `core`. It is the same shape as §3.1's declaration-vs-policy test in the boundary file.

Everything else in that file — Protocol fakes, `MagicMock`, diff-scoped mutation testing — is
`adapter-sdlc` and does not generalize.

---

## 5. Verdicts — contract modules

`design/plans/contracts/` was split out of the former single schema file. The package boundary already
tracks the layer boundary well, with the exceptions noted.

| Module | Layer | Notes |
|---|---|---|
| `contracts/orchestration.py` | `core` | `RunManifest`, `HaltReason`, `Phase`. Neutral except `Phase.DECOMPOSITION_TDD` |
| `contracts/verification.py` | `core` | `GateResult`, `Finding`, `GateApplicability`, `FailureSignature`. `GateApplicability`'s ability to say "I did not run" is among the strongest generic ideas in the set |
| `contracts/governance.py` | `shared` | `RepoDeclaration` / `GovernancePolicy` structure is Core; **five of the six closed constructs in §6 live here** |
| `contracts/adapter_surface.py` | `core` | `IntentOpSpec`, `SignalSpec` — the shape of a declaration rather than a declaration. The true reusability seam |
| `contracts/reference_adapter/web_intents.py` | `adapter-sdlc` | Correctly relocated out of Core by PR #5. The model to follow |

---

## 6. Findings: closed constructs in Core

An adapter can declare *values*. It cannot extend a closed `Enum` or `Literal` without forking the
schema — which is precisely the argument `core_adapter_boundary.md` §2.2 already makes about
`extra="forbid"` models. That argument was never generalized from fields to enums.

| Construct | Location | Problem |
|---|---|---|
| `Capability` | `governance.py:67` | Closed enum. 4 of 5 values are testing/browser concepts. Its own docstring says "Declared, never inferred" — but a repo may only declare from a fixed software-testing menu |
| `IsolationUnit` | `governance.py:58` | `WORKTREE` is a git noun; a non-software adapter has neither option |
| `TriageRule.routes_to` | `governance.py:217` | Closed `Literal` of three development agents, inside a model that is otherwise pure adapter data. An adapter may declare its own signals and rules but not its own routing destinations |
| `ResetStrategy.strategy_type` | `governance.py:120` | Closed `Literal` of four software-execution nouns |
| `TestTier.execution_tier` | `governance.py:142` | Closed `Literal` baking the unit/integration/browser ladder into a Core model |
| `Phase.DECOMPOSITION_TDD` | `orchestration.py:219` | Bakes one methodology into the universal phase enum |

**The pattern is active, not historical.** PR #5 fixed both known *field*-level leaks — it
relocated the web intent vocabulary to `reference_adapter/` (roadmap D2 / S0-6) and collapsed
`FailureSignature`'s two hard-coded browser fields into a declared `signals` map (§2.2 / S0-7) — and
in the same change introduced two new closed `Literal`s (`strategy_type`, `execution_tier`). The
rule has been learned for fields and not for enums, so the leak reproduces each time the schema
grows.

Registered in `implementation_roadmap.md` §3. None appear in the audit's C/H/M register.

---

## 7. Reusable ideas that are currently trapped in SDLC documents

Recorded here so the Optimization adapters can cite them rather than reinvent them:

1. **The progressive onboarding ladder** (`adapter_onboarding.md`) — Level 0 ad-hoc → Level 1
   execution → Level 2 state and triage → Level 3 full governance. The ladder is domain-neutral;
   only its rungs are SDLC. Optimization reuses the shape directly.
2. **Derived isolation strength** (`execution_isolation.md` §5).
3. **Tighten automatically, loosen at a human gate** (`test_harness_architecture.md` §1.5).
4. **A ceiling breach is a task-size signal, not just a limit** (`test_harness_architecture.md`
   §3.8).
5. **Structured rejection, because prose between agents is an injection channel**
   (`execution_isolation.md` §7.5, `IntentRejection`).

---

## 8. What this file does not claim

It does not claim the Core *is* domain-general. It claims the classification has been made and the
obstacles named. `core_adapter_boundary.md` §6 is explicit that an abstraction is not demonstrated
until a deliberately dissimilar adapter runs against an unmodified conformance kit:

> One adapter does not demonstrate an abstraction. It demonstrates a coupled system with an extra
> layer of indirection, and the two are indistinguishable from inside.

No code has been run against this classification. The percentages in §3 are reading estimates. The
verdicts are arguable by design — that is what makes them worth writing down.
