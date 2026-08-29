---
title: Core / Adapter Boundary
status: live
part_of: agentic-sdlc
doc_type: companion
---

# Core / Adapter Boundary

**Referenced by:** `agentic-sdlc-design-v0.5.md` §4 (Shared-File Governance) · §6 (Failure Triage) ·
§8 (Execution Isolation) · `implementation_roadmap.md` Stage 0 · `plan/contracts/governance.py`
(`RepoDeclaration`, `GovernancePolicy`) · `plan/llm_output_normalization.md` (§3 dispatch path)

## Purpose

The pipeline is a **general-purpose orchestrator**, not a tool for one repository. This file owns
the seam that makes that claim checkable: what the Core owns for every repo it will ever govern,
what a target repo declares for itself, and — the part that is easy to get wrong — the three places
where a naive reading of that split leaks.

The design is tested against contact with real repositories of varying complexity and tooling.
It is not a dependency of the Core, and nothing in Stage 0 through Stage 2 of
`implementation_roadmap.md` requires access to a specific implementation.

---

## 1. The split

### 1.1 Core — universal, one implementation, governs every repo

| Area | Core owns |
|---|---|
| State & flow | Orchestrator state machine, phase routing, `RunManifest` persistence, worktree lifecycle, deterministic circuit breakers |
| Agent roles | Maker/Checker pairing, validator asymmetry, bounded loops, escalation ladder, Shadow Mode calibration and the verdict ledger |
| Governance | The intent lock, serialization, the rejection protocol and its blocking-context envelope, conflict counters, registry promotion logic |
| Verification | The *engine* that evaluates ordered rules first-match-wins, the LLM-fallback edge, anti-deletion baseline guards, gate evaluation and `GateResult` routing |
| Safety | Budget metering and the ceiling halt, secret resolution and egress scrubbing, evidence retention |

### 1.2 Adapter — declared per target repo (Progressive Onboarding)

Adapters onboard in stages (Levels 0 through 3). A repo does not need a full schema to start.

- **Level 0 (Ad-Hoc / Chat):** No adapter needed. The agent acts as a simple chat assistant with read access.
- **Level 1 (Execution):** Minimal adapter. Declares the image reference, basic bootstrap commands, and Tier 1 (Unit) tests.
- **Level 2 (State & Triage):** Adds Tier 2 (Integration) tests, Reset Strategies (e.g., transaction rollbacks), and telemetry/triage rules for structured failure handling.
- **Level 3 (Full Intent & Pooling):** Adds Tier 3 (Browser) tests with warm pools (`browser_pool_checkout`), Additive Intent operations, custom hooks, and fixture hydration.

| Area | Adapter declares |
|---|---|
| Execution | Isolation unit (worktree or container), image reference, bootstrap commands, port bindings, per-unit resource footprint |
| Verification | Test tiers (`execution_tier`), their commands, whether each is hermetic, and the reset strategy wrapping each test — what it recreates, what host resources it needs, and what it costs |
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

### 2.1 Collision detection is not fully universal — the Two-Layer Collision Model

The lock, the serialization, and the rejection protocol are Core. **Whether two intents collide is
not** — it is a semantic question about a vocabulary Core has never seen. `AddRoute(path="/x")`
twice is an obvious collision on `path`; two `AddRoute` intents on `/users/:id` and `/users/new`
overlap semantically while sharing no literal key; two `AddSelector` intents with different names
pointing at the same DOM element collide semantically while sharing no key at all.

**Resolution: a Two-Layer Collision Model.** Layer 1 is Core's deterministic key match. Layer 2 is
an optional adapter-declared static analyzer, sandboxed inside the repo's isolation unit. Both run
inside the same synchronous Intent Service call, and either can reject an intent — but for
different reasons and with different override semantics. Audit finding H7
(`audit/2026-08-28_audit/remediation_H7_collision_semantics.md`) drove this from a Layer-1-only
design; the pre-H7 shape is preserved as the additive-default behavior when a repo declares no
analyzers.

**Layer 1 — deterministic key match (Core, universal, unchanged).** Every declared operation
carries a **collision key set** (`IntentOpSpec.collision_keys`, `plan/contracts/governance.py`).
Core arbitrates by exact match on those keys and nothing else. That makes Layer 1 deterministic and
repo-independent, at the cost of being deliberately under-powered: an adapter that needs richer
collision semantics expresses it by choosing keys that capture it, by declaring a Layer 2 analyzer,
or by accepting that the residue surfaces at integration as an ordinary conflict and increments the
file's counter. **Core does not accept an adapter-supplied predicate function inside its own
process** — that would move arbitration logic into untrusted repo-declared code, which §4 exists to
prevent. A Layer-1 collision returns `IntentRejection.reason = "collision"` and is not overrideable
through the submission envelope: it is a factual claim about pending intents, not a judgement.

**Layer 2 — adapter-declared semantic analyzer (sandboxed, per-op, opt-in).** A repo declares zero
or more analyzers via `RepoDeclaration.semantic_analyzers`
(`SemanticAnalyzerSpec` — `plan/contracts/governance.py`), each an executable command plus an
`IsolationUnit`. Every `IntentOpSpec` that needs semantic checking cites the analyzers it needs by
`semantic_analyzer_ids`; multiple ops MAY share an `analyzer_id`. Empty `semantic_analyzer_ids` on
an op means Layer 2 is skipped for that op and Core runs Layer 1 only. A repo that declares no
analyzers at all keeps the pre-H7 arbitration shape.

Ordering is fixed and per-intent synchronous. Inside one Intent Service call: Layer 1 evaluates
first; on a Layer-1 pass Core dispatches the op's mapped analyzers as subprocesses inside the
declared `IsolationUnit` (per the `execution_isolation.md` §7.6 subprocess-only invariant),
aggregates their structured JSON verdicts, and either applies the intent or returns
`IntentRejection.reason = "semantic_collision"` with `semantic_feedback` and `override_key`
populated. No batching, no Phase-4-boundary rollback, no `shared/`-branch rewind path: on a
semantic_collision the intent is simply not applied (`IntentOutcome.applied = False`), and the
submitting agent sees one outcome per submission just as it did pre-H7.

**Egress crosses the trust boundary** (SECURITY). The analyzer's JSON verdict leaves the isolation
unit on its way back to Core and therefore passes through the §5 credential scrubber like any other
egress artifact — reusing `EgressPayload` / `ScrubbedEgressPayload`, no new schema. An analyzer
that echoes a secret it observed inside the unit is redacted at the boundary, exactly as a log line
would be.

**Override semantics.** A Layer-2 rejection is not final. The rejection carries `override_key`,
and an agent may resubmit the same intent through the `IntentSubmission` envelope
(`plan/contracts/orchestration.py`) with that key placed in `override_semantic_collisions`. The
wrapper is the seam — the intent members (`AddRoute`, `AddExport`, `AddProviderBinding`,
`RenameExport`, `MoveRoute`, `DeprecateExport`) stay untouched, so the vocabulary is not polluted
by submission-side governance metadata. An honored override converts the analyzer's block into a
hypothesis that Phase 5 integration testing will still catch if the analyzer was correct. Repeated
`semantic_collision` on the same `(rejected_task, blocking_task, resource_key)` tuple accrues
against `GovernancePolicy.max_mutex_rejections` and degrades to `deadlock_cycle` on breach — a
stuck override loop is caught by the same ceiling that catches a stuck Layer-1 loop
(design doc §4.5). This is deliberately non-overlapping with the structural-change tiers: a
semantic_collision stays inside the Intent Service's per-intent verdict loop and is neither a
Tier 2 (`structural_change_runbook.md` §1) nor a Tier 3 trigger.

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

### 2.4 Agent output normalization

Agent-produced JSON (Validator verdicts, additive intents) enters Core as raw JSON strings.
Core's **normalization layer** is the first mechanism applied to this inbound payload: it
recursively strips hallucinated extra fields, logs each removal as a `NormalizationEvent`
(`plan/contracts/verification.py`), and then hands the cleaned data to strict Pydantic
validation (`extra="forbid"`). Only validated, typed objects enter the downstream pipeline.

This is an *inbound* data-cleaning path, distinct from the *outbound* credential-scrubbing
egress path in §5: normalization handles what agents produce; scrubbing handles what leaves an
isolation unit. Both are Core-owned deterministic mechanisms. See
`plan/llm_output_normalization.md` for the full specification, including model categories
(which schemas cross this boundary) and escalation interaction.

---

## 3. The adapter contract: two artifacts, two trust levels

Schemas: `plan/contracts/governance.py`. The contract is deliberately **not** one file. A target
repo declares facts about itself; the control plane owns what the pipeline will tolerate. They have
different authors, different change cadences, and different blast radii on compromise.

| Artifact | Lives | Owner | Changes |
|---|---|---|---|
| `RepoDeclaration` | In the target repo, versioned with the code | Repo maintainers, via ordinary PR review | Whenever the repo changes — routine |
| `GovernancePolicy` | Control plane, outside every target repo | Whoever owns the pipeline's risk posture | Rarely, at a human governance gate |

The single-file alternative was rejected for three reasons. Routine edits (a changed test command)
would have to clear the same heavyweight gate as governance edits (un-blocking a gate), which makes
that gate fire on trivia and therefore get rubber-stamped — the same argument that makes a
routinely-waived blocking gate worse than no gate. Enterprise-scope policy (`InvariantScope`
§5, org budget ceilings) would have no home but a copy in every repo, which is the drift this
design exists to prevent, at the config layer. And a repo compromise would reach the definition of
the gates rather than only the declarations.

### 3.1 The discriminating test

Deciding which artifact a field belongs to does not require adjudicating each one:

> **A field is a declaration if a false value punishes the declarer. It is policy if a false value
> rewards them.**

Lie about a test command and your own tests break — self-limiting, so the repo can be trusted with
it. Lower a budget ceiling or un-block a gate and the declarer gains while the org absorbs the risk
— not self-limiting, so it cannot live where the beneficiary can edit it.

Two classes are not quite enough, because some fields are self-rewarding *and* only the repo knows
the true value:

- **Policy-bounded declaration.** The repo declares; the control plane sets a bound; Core clamps to
  the bound and **records the clamp** in the `RunManifest`. `resource_footprint_mb` is the type
  case: understate it and you get more concurrency while every co-tenant's machine swaps.
- **Verified declaration.** The claim is self-rewarding but empirically checkable, so Core checks it
  instead of trusting or adjudicating it. `TestTier.hermetic` is the type case: declaring a tier
  non-hermetic exempts it from `mutation.diff_scoped`, and hermeticity is testable by running the
  tier isolated and in-suite under randomized order.

### 3.2 Field assignment

| Field | Class | Reasoning |
|---|---|---|
| `repo_id`, `declaration_version`, `capabilities` | Declaration | Facts; a false value fails the run |
| `isolation_unit`, `image_ref`, `bootstrap`, `declared_ports` | Declaration | Only the repo knows; wrong values break the repo's own runs |
| `test_tiers[].command`, `.name`, `.isolation_unit` | Declaration | Self-punishing |
| `test_tiers[].hermetic` | **Verified** declaration | Non-hermetic exempts a tier from the mutation gate — self-rewarding, and checkable |
| `resource_footprint_mb` | **Policy-bounded** declaration | Understating buys concurrency at co-tenants' expense |
| `intent_vocabulary`, `signals`, `triage_rules`, `hydration_fixture_ids` | Declaration | Repo-shaped facts; errors surface as the repo's own failures |
| `requested_secrets` | Declaration (a **request**) | The repo states what it needs; needing is not getting |
| `blocking_gates` | **Policy** | A repo declaring which gates it satisfies is a repo grading itself |
| `granted_secrets` | **Policy** | The grant half of the request/grant pair — a task-scope agent asking for promotion scope is a refusal, not a config line |
| `registered_shared_files` | **Policy** | Already a human gate (design doc §9.3); registration is a governance decision, not a repo fact |
| `absent_capability_policy` | **Policy** | Left repo-side, a repo opts out of governance by declaring `degrade` |
| `budget_ceilings`, `concurrency_cap`, `model_tier_allowlist` | **Policy** | Spend and escalation posture are org decisions |

### 3.3 Precedence and conflict

Policy always wins. How it wins depends on the class:

- **Hard conflict** — a declaration asks for something policy does not grant (a secret scope, a
  capability, a model tier). Core **refuses to start**. Not a clamp, not a warning: the repo asked
  for something it may not have, and proceeding quietly would make the grant meaningless.
- **Bounded conflict** — a policy-bounded declaration exceeds its bound. Core **clamps and records**
  the clamp in the `RunManifest`, so a run that was silently narrowed is still visibly narrowed.
- **Failed verification** — a verified declaration does not survive its check. Core treats the claim
  as its conservative value (a tier claiming `hermetic=false` that verifies as hermetic is simply
  held to the stricter gate) and records the discrepancy.

### 3.4 Governance of the declaration itself

Even reduced to declarations, the repo-side file names test commands, bootstrap commands, and
transformer entry points — **arbitrary code execution declared by the repo being operated on**. If
an agent working in that repo can edit it, an agent can change what "run the tests" means. That is a
privilege-escalation path through Principle 12, created the moment the interface exists. Four rules
close it:

1. **The declaration is a registered shared file by construction** — in the registry before any task
   spawns, not promoted into it by a conflict counter.
2. **It is outside every agent's write scope**, enforced by permission, not instruction
   (Principle 12). No Task Dev, Test Author, or CI Cleanup agent can write it, and it accepts no
   Additive Intent.
3. **A change to it is a human gate**, joining `agentic-sdlc-design-v0.5.md` §9.3. It is a lighter
   gate than a policy change — ordinary PR review by repo maintainers — but it is never an agent's
   to clear.
4. **Both artifacts are digest-pinned into the `RunManifest` at run start.** A mid-run edit to
   either cannot change the rules under a running pipeline; Core halts on a mismatch rather than
   adopting the new value.

### 3.5 Validation and capability negotiation

Core validates both artifacts before the run starts. **An invalid one is a refusal to start, not a
warning** — Principle 7, nothing fails silently.

Capabilities are **declared, never inferred**. An adapter that declares no
`shared_file_governance` capability does not get Shared-File Governance quietly disabled — silently
falling back to ordinary git merges on shared files is a return to the exact failure mode §4 exists
to prevent, and it would be invisible. `GovernancePolicy.absent_capability_policy` decides:

- **`refuse`** — the run cannot start. Correct where the guarantee is the point.
- **`degrade`** — the run proceeds with the capability off, and the degradation is recorded in the
  `RunManifest` and surfaced at the PR. Visible, attributable, reviewable.

There is no third option in which a capability is absent and nobody is told. Note that this field is
policy precisely so the repo that benefits from degrading cannot be the one that chooses it.

### 3.6 The concurrency ceiling falls out of this

`agentic-sdlc-design-v0.5.md` §12 carries "concurrency ceiling" as an open question. Under this
model it stops being a question and becomes arithmetic: the repo declares a per-isolation-unit
resource footprint (bounded by policy per §3.1), Core divides available resources by it, and takes
the minimum against `GovernancePolicy.concurrency_cap`, API rate limits, and review throughput.
Which constraint binds becomes a fact about a specific run rather than something discovered when
the machine starts swapping.

## 4. Hydration, and what "baseline" means once it exists

`test_harness_architecture.md` §1.3 defines baseline as **canonical empty state**. That definition
only holds for a repo whose tests need nothing seeded. The moment a database, a mock API, or an
external system must be populated first, "empty" is the wrong reference — a correctly hydrated
environment differs from empty on every axis §1.4 checks.

Hydration and baseline are therefore the same concept viewed twice:

- **Adapter owns** what hydration *is*: named fixture states, and hooks to apply, verify, and tear
  down.
- **Core owns** the ordering and the guarantee: isolation unit up → per-test instance constructed
  (`test_harness_architecture.md` §1.2) → hydration applied → **baseline captured** → first test
  action. Core also derives the isolation unit itself from the declared reset strategies'
  resource needs (`execution_isolation.md` §5), so "which unit" is arithmetic rather than a
  judgment call. `dom_state_diff_from_baseline` and its successors compare against
  *the declared post-hydration state*, never against empty and never against the previous test's end
  state.

The tiered reset mandates (`test_harness_architecture.md` §1.2) govern what the baseline is captured against: for Tier 1 and Tier 2, construction is always fresh; for Tier 3, in-place cleaning via a warm pool is permitted, with state-leakage protection via the deterministic triage table. In all tiers, a reused environment that has not been verifiably reset cannot be re-hydrated to a known state any more reliably than it can be cleared to an empty one — the baseline is the declared post-hydration state, never an assumed empty.
Furthermore, Adapters should cache state resets based on target isolation requirements (such as matching isolation unit boundaries) rather than re-computing them indiscriminately, provided doing so does not compromise hermeticity guarantees.

---

## 5. Credential injection and egress scrubbing

The adapter declares **names and scopes**. Values never appear in a `RepoDeclaration`, never appear
on a worktree filesystem, and never pass through an agent's context. **Core holds resolved values in
memory for exactly one task's duration** — the scrubbing trust boundary — and nowhere else.

### 5.1 Credential resolution

- **Core owns** a `CredentialProvider` interface: `resolve(names, scope)` injects resolved values
  into the environment of an isolation unit at start, scoped to the phase that needs them.
- A repo needing a live tenant credential and one needing a local dummy string use the same
  interface. The difference is which provider is configured, not which code path runs.

### 5.2 Egress scrubbing

**The scrubber runs in Core, at the Core/adapter trust boundary — not inside the isolation unit.**
Every log line, screenshot filename, DOM dump, HAR file, git commit message, and network payload
leaving the unit passes through it as an `EgressPayload` (`plan/contracts/governance.py`) and
returns as a `ScrubbedEgressPayload` (`plan/contracts/governance.py`). Nothing that has not been
transformed is admissible as an `evidence_ref` target or as a network egress destination.

The scrubber holds active values via `SecretScrubberConfig` (`plan/contracts/governance.py`),
populated at task start from `GovernancePolicy.granted_secrets`. Instances live only in Core memory
for the task's duration and are never persisted, logged, or serialized into the `RunManifest` event
log.

Network egress is constrained by a Core-operated egress proxy with a **strict allow-list of
destination domains** derived from the adapter's declared external services. Deep packet inspection
on the egress stream is a possible extension for adapters that need finer-grained control, but is
not the design's baseline stance: allow-listing sidesteps the MITM-cert-install surface a DPI proxy
would require inside every container.

Isolation implication: because the egress proxy is a network boundary, container isolation is a
floor for any task consuming a credential. See `execution_isolation.md` §5.4 for the derivation
rule.

### 5.3 Why the trust boundary moved

Earlier drafts of this design placed the scrubber **inside** the isolation unit, on the argument
that a redaction filter must know its values, which conflicts with Core never holding them. Audit
finding C1 (`audit/2026-08-28_audit/adversarial_audit_report.md`) established that in-unit
scrubbing is defeatable: an agent with `src/` write access can tamper with the scrubber, encode
credentials in filenames or commit messages, or exfiltrate them via network calls the scrubber never
sees. The trade-off changed. **Core-memory exposure of raw values for one task's duration is a
smaller attack surface than in-unit tamperability under an adversarial agent.** Principle 12 —
enforce with permissions, not prompts — puts security controls outside the trust boundary they
defend.

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
