---
title: Core / Adapter Boundary
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Core / Adapter Boundary

**Referenced by:** `agentic-sdlc-design-v0.5.md` §4 (Shared-File Governance) · §6 (Failure Triage) ·
§8 (Execution Isolation) · `implementation_roadmap.md` Stage 0 · `agent_interface_contracts.py`
(`ProjectManifest`)

## Purpose

The pipeline is a **general-purpose orchestrator**, not a tool for one repository. This file owns
the seam that makes that claim checkable: what the Core owns for every repo it will ever govern,
what a target repo declares for itself, and — the part that is easy to get wrong — the three places
where a naive reading of that split leaks.

A specific repository (CPMI: Python, Selenium, DOM extraction) guides the design so it survives
contact with reality. It is not a dependency of the Core, and nothing in Stage 0 through Stage 2 of
`implementation_roadmap.md` requires access to it.

---

## 1. The split

### 1.1 Core — universal, one implementation, governs every repo

| Area | Core owns |
|---|---|
| State & flow | Orchestrator state machine, phase routing, `RunManifest` persistence, worktree lifecycle, deterministic circuit breakers |
| Agent roles | Maker/Checker pairing, validator asymmetry, bounded loops, escalation ladder, Shadow Mode calibration and the verdict ledger |
| Governance | The intent lock, serialization, the rejection protocol and its blocking-context envelope, conflict counters, registry promotion logic |
| Verification | The *engine* that evaluates ordered rules first-match-wins, the LLM-fallback edge, anti-deletion baseline guards, gate evaluation and `GateResult` routing |
| Safety | Budget metering and the ceiling halt, secret resolution and boundary scrubbing, evidence retention |

### 1.2 Adapter — declared per target repo

| Area | Adapter declares |
|---|---|
| Execution | Isolation unit (worktree or container), image reference, bootstrap commands, port bindings, per-unit resource footprint |
| Verification | Test tiers, their commands, whether each is hermetic, which gates each tier satisfies |
| Vocabulary | Its Additive Intent operations, their collision keys, and the transformer that applies each |
| Telemetry | The signals its harness can capture, and the ordered triage rules written over those signals |
| Hydration | Named fixture states and the hooks that apply, verify, and tear them down |
| Secrets | The **names and scopes** of credentials the run requires — never values |

The rule of thumb: **Core owns every mechanism; the adapter owns every noun.** If a thing can be
wrong in a way that is specific to one codebase, it is adapter data. If it can be wrong in a way
that would be wrong for every codebase, it is Core code.

---

## 2. Where the split leaks

Three places where "Core owns the mechanism, adapter owns the specifics" is not sufficient on its
own. Each of these is a decision, not a detail.

### 2.1 Collision detection is not fully universal

The lock, the serialization, and the rejection protocol are Core. **Whether two intents collide is
not** — it is a semantic question about a vocabulary Core has never seen. `AddRoute(path="/x")`
twice is an obvious collision on `path`; two `AddSelector` intents with different names pointing at
the same DOM element collide semantically while sharing no key.

**Resolution:** every declared operation carries a **collision key set**
(`IntentOpSpec.collision_keys`). Core arbitrates by exact match on those keys and nothing else. That
makes arbitration deterministic and repo-independent, at the cost of being deliberately
under-powered: an adapter that needs richer collision semantics expresses it by choosing keys that
capture it, or accepts that the residue surfaces at integration as an ordinary conflict and
increments the file's counter. **Core does not accept an adapter-supplied predicate function** —
that would move arbitration logic into untrusted repo-declared code, which §4 exists to prevent.

### 2.2 Telemetry cannot be adapter fields on a `extra="forbid"` model

`FailureSignature` is frozen with `extra="forbid"`, and `CLAUDE.md` requires exactly one home per
schema. An adapter cannot add fields to it without either breaking that rule or forking the schema
per repo — which is the drift the whole design exists to prevent, reintroduced at the type level.

**Resolution:** Core owns a fixed universal envelope (`error_class`, `elapsed_ms`,
`configured_timeout_ms`, `isolated_rerun_outcome`). Everything else moves into a
`signals: dict[str, bool | int | str]` map whose *keys and types the adapter declares*
(`SignalSpec`) and Core validates a captured signature against.

This makes `dom_state_diff_from_baseline` and `network_calls_over_threshold` what they always were:
signals of one adapter, currently hard-coded into the universal schema. Per this design's own
additive discipline, `signals` lands first as a non-breaking addition; relocating those two fields
into it is a structural change and goes through the same gate as any other
(`structural_change_runbook.md`).

### 2.3 Triage rules are data, not code

`infra_triage_matrix.md` is currently written as *the* rules engine, and its rules name DOM state
directly. A pure backend repo has no DOM, and a rules engine that hard-codes one repo's signals is
not universal.

**Resolution:** Core owns the evaluator — ordered, first-match-wins, non-matches fall through to the
LLM Investigator, with the deliberate-fallthrough guarantee intact. The **rules are adapter data**
(`TriageRule`), written over that adapter's declared signals. `infra_triage_matrix.md` is
reclassified from *the engine* to *the reference rule set for a browser-automation adapter* — which
is what it has always actually been.

---

## 3. The adapter contract: `ProjectManifest`

Schema: `agent_interface_contracts.py`. A target repo declares its constraints in one file that
Core reads before a run starts.

### 3.1 Governance — the part that matters most

A manifest that names a test command, a bootstrap script, and a transformer entry point is
**arbitrary code execution declared by the repo being operated on**. If an agent working inside that
repo can edit the manifest, an agent can rewrite its own gates: point the test command at `true`,
drop the mutation tier, widen its own write scope. That is a privilege-escalation path running
straight through Principle 12, and it is created the moment the adapter interface exists.

Four rules close it:

1. **The manifest is a registered shared file by construction** — it is in the registry before any
   task spawns, not promoted into it by a conflict counter.
2. **It is outside every agent's write scope**, enforced by permission, not instruction
   (Principle 12). No Task Dev, Test Author, or CI Cleanup agent can write it. It accepts no
   Additive Intent.
3. **A change to it is a human gate**, joining `agentic-sdlc-design-v0.5.md` §9.3 — the same
   standard as shared-file registration, because it is a superset of that decision.
4. **It is pinned by content digest into the `RunManifest` at run start.** A mid-run edit cannot
   change the rules under a running pipeline; Core halts on digest mismatch rather than adopting the
   new manifest.

### 3.2 Validation and capability negotiation

Core validates the manifest against the contract schema before the run starts. **An invalid manifest
is a refusal to start, not a warning** — Principle 7, nothing fails silently.

Capabilities are **declared, never inferred**. An adapter that declares no
`shared_file_governance` capability does not get Shared-File Governance quietly disabled — because
silently falling back to ordinary git merges on shared files is a return to the exact failure mode
§4 exists to prevent, and it would be invisible. Instead the manifest states an
`absent_capability_policy`:

- **`refuse`** — the run cannot start. Correct for a repo that needs the guarantee.
- **`degrade`** — the run proceeds with the capability off, and the degradation is recorded in the
  `RunManifest` and surfaced at the PR. Visible, attributable, and reviewable.

There is no third option in which a capability is simply absent and nobody is told.

### 3.3 The concurrency ceiling falls out of this

`agentic-sdlc-design-v0.5.md` §12 carries "concurrency ceiling" as an open question. Under this
model it stops being a question and becomes arithmetic: the adapter declares a per-isolation-unit
resource footprint, Core divides available resources by it, and takes the minimum against API rate
limits and review throughput. Which constraint binds is then a fact about a specific run rather than
something discovered when the machine starts swapping.

---

## 4. Hydration, and what "baseline" means once it exists

`test_harness_architecture.md` §1.3 defines baseline as **canonical empty state**. That definition
only holds for a repo whose tests need nothing seeded. The moment a database, a mock API, or an
external system must be populated first, "empty" is the wrong reference — a correctly hydrated
environment differs from empty on every axis §1.4 checks.

Hydration and baseline are therefore the same concept viewed twice:

- **Adapter owns** what hydration *is*: named fixture states, and hooks to apply, verify, and tear
  down.
- **Core owns** the ordering and the guarantee: isolation unit up → hydration applied → **baseline
  captured** → first test action. `dom_state_diff_from_baseline` and its successors compare against
  *the declared post-hydration state*, never against empty and never against the previous test's end
  state.

The full-teardown mandate (`test_harness_architecture.md` §1.2) survives unchanged and gets
stronger: a reused environment cannot be re-hydrated to a known state any more reliably than it can
be cleared to an empty one.

---

## 5. Credential injection

The adapter declares **names and scopes**. Values never appear in a manifest, never appear on a
worktree filesystem, and never pass through an agent's context.

- **Core owns** a `CredentialProvider` interface: `resolve(names, scope)` injects resolved values
  into the environment of an isolation unit at start, scoped to the phase that needs them.
- A repo needing a live tenant credential and one needing a local dummy string use the same
  interface. The difference is which provider is configured, not which code path runs.

**Scrubbing runs inside the isolation unit, at the boundary.** This is the non-obvious part: a
redaction filter must know the values it is redacting, which conflicts with Core never holding them.
So Core supplies the scrubber, the scrubber executes inside the unit where the values already exist,
and it filters every artifact — logs, screenshots, DOM dumps, HARs — on the way out. Nothing that
has not passed the scrubber becomes an `evidence_ref` target.

---

## 6. Making "universal" falsifiable

One adapter does not demonstrate an abstraction. It demonstrates a coupled system with an extra
layer of indirection, and the two are indistinguishable from inside.

Two mechanisms keep the claim honest:

1. **The adapter conformance kit.** Core ships an executable suite that any adapter must pass. The
   kit *is* the interface definition — prose describes it, the kit decides it. An adapter is
   certified when it passes, and a Core change that breaks an adapter breaks the kit first.
2. **Two dissimilar reference adapters.** The second one is the falsification test, and it is only
   worth building if it is deliberately unlike the first: different language, different transformer
   engine, different isolation unit, different signal set, one with hydration and one without. Two
   similar adapters prove nothing that one proves.

Both are Stage 2 deliverables in `implementation_roadmap.md`, and the second adapter is the exit
criterion — not a nice-to-have after it.

---

## 7. What a transformer must promise

The transformer is adapter-supplied, so Core cannot inspect its internals. It can and must enforce
a contract, checked by the conformance kit:

| Obligation | Why Core enforces it |
|---|---|
| **Idempotent under replay** | Retries and resumed runs will re-apply intents; a transformer that appends twice corrupts the file the governance layer exists to protect |
| **Formatter round-trip stable** | A transform that reformats untouched lines manufactures merge conflicts on precisely the file the design keeps conflict-free |
| **All-or-nothing** | A partially applied intent leaves a shared file in a state no agent declared and no human approved |
| **Loud on unmapped structure** | An insertion point the structural map does not cover is a registration gap, not a place to guess — it returns a rejection, never a best-effort edit |

These are obligations of *any* transformer, which is why they are testable against a dummy one that
manipulates a toy format and understands no real language at all.
