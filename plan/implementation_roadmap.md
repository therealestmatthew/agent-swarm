---
title: Implementation Roadmap — Design to Execution
status: live
part_of: agentic-sdlc
doc_type: roadmap
version: "1.1"
---

# Implementation Roadmap — Design to Execution

**Referenced by:** `CLAUDE.md` (phase gate) · `agentic-sdlc-design-v0.5.md` §12 (Open Questions) ·
`core_adapter_boundary.md`

## What this builds

A **general-purpose orchestration pipeline** with a formal seam between a universal Core and a
per-repo Adapter Layer. The boundary itself is specified in `core_adapter_boundary.md`; this file
sequences the work of building it.

Connected Planning Model Intelligence (CPMI) — Python, Selenium, custom DOM extraction — is the
**forcing function, not a dependency**. It guides the design so the abstraction survives contact
with a genuinely awkward repo: browser processes, live tenant credentials, non-hermetic tests,
seeded external state. Nothing in Stage 0 through Stage 2 requires access to it. CPMI enters at
Stage 3 as the first *real* adapter, behind two synthetic reference adapters that exist to prove the
interface without it.

**Changelog from v1.0.** Restructured around the Core/Adapter split. D2 is restated (§3) rather than
withdrawn: the finding was never "we need CPMI," it was "the intent vocabulary is presented as
universal when it is one instance" — which this model resolves by relocating it. Stage 0 becomes
contract definition rather than repo inventory; Stage 1 builds Core against a null adapter; Stage 2's
AST work is reframed from a production transformer to an interface conformance proof.

---

## 1. Verdict on the backlog as submitted

The submitted backlog is a good inventory and a bad plan. Four structural problems:

1. **It is a flat priority list for deeply ordered work.** There are no dependency edges. Priority
   answers "how much do we care"; it does not answer "what can start Monday." This file replaces
   priority with sequence.
2. **It schedules the governed parts and omits the governor.** The Core Orchestrator, the event log,
   `RunManifest` persistence, and the agent dispatcher appear nowhere. Item 8 asks *where* the run
   manifest lives without asking *who writes it*. Nothing in the list, executed perfectly, produces a
   pipeline that runs once end to end.
3. **It re-opens closed questions and drops open ones.** Item 5 (Baseline Snapshot Mechanics) was
   resolved in v0.4 and lives in `test_harness_architecture.md` §1. Meanwhile 2 of the 5 open
   questions v0.5 §12 carries forward — **concurrency ceiling** and **Plan Writer dialogue depth** —
   are absent from the backlog entirely. That is the exact silent-drop pattern
   `plan/versions/REGRESSION.md` exists to document, recurring one document later.
4. **Its P2 tier is miscategorised.** Items 10–13 are tuning questions. They are not low-priority
   work that could be pulled forward with more people; they are **impossible** until first-run
   telemetry exists. They belong in a separate *blocked-by-data* tier (§6).

The one item whose stated priority rises on its own merits is **Secrets Posture (item 6, P1)** — now
generalized into a `CredentialProvider` interface (`core_adapter_boundary.md` §5), which is Core and
therefore moves earlier still.

---

## 2. What is missing, in one place

New items introduced by this roadmap, with the item they attach to:

| ID | Item | Why it is missing-critical | Attaches to |
|---|---|---|---|
| R1 | Adapter contract: `RepoDeclaration` + `GovernancePolicy` | The declaration/policy pair that makes "any repo" checkable rather than aspirational, without letting the beneficiary set its own limits | New — Core |
| R2 | Shared-file materialization model across worktrees | §4 and `execution_isolation.md` described incompatible mechanics (D1) — **resolved**; what remains is the precondition gate and the synthesized delta view | Blocks backlog #1 |
| R3 | Core Orchestrator skeleton: state machine, event log, manifest persistence, dispatcher | The governor, absent from the backlog entirely | Subsumes backlog #8 |
| R4 | Agent Spec format and registry | Supersedes "prompts" — prompt is 1 of 6 fields | Supersedes backlog #3 |
| R5 | Test tiers + `mutation.diff_scoped` scope predicate | A blocking gate that is unsatisfiable on non-hermetic tiers (D5); now adapter-declared | Blocks backlog #5 |
| R6 | Isolation unit as a declared property | `execution_isolation.md` §5's escape condition answered by declaration, not discovery (D6) | Blocks backlog #5 |
| R7 | Cost metering substrate + deterministic kill switch | Replaces the un-runnable half of backlog #4 | Reframes backlog #4 |
| R8 | Human gate control plane (sign-off with identity, written to the event log) | 8 human gates exist; nothing lets a human see or clear one | Distinct from backlog #7 |
| R9 | Evidence scrubbing and retention | `Finding.evidence_ref` may point at authenticated screenshots (D9) | Pairs with backlog #6 |
| R10 | Adapter conformance kit | The executable definition of the interface — prose describes it, the kit decides it | New — Core |
| R11 | Run abort and halt semantics | "Pause" is undefined for an agent holding a live driver (D12) | Follows R3 |
| R12 | `FailureSignature.signals` + triage rules as adapter data | An `extra="forbid"` model cannot take per-repo fields (D16); the rules engine is not universal (D15) | Amends contracts |
| R13 | Concurrency ceiling | v0.5 §12 open question dropped from the backlog; now derived from declared footprint | Standalone |
| R14 | Plan Writer dialogue depth | v0.5 §12 open question dropped from the backlog | Standalone |
| R15 | Hydration interface + baseline redefinition | Baseline as "canonical empty" is false for any repo that seeds state | New — Core |
| R16 | `CredentialProvider` + boundary scrubbing | One interface for a live tenant credential and a dummy string | Generalizes backlog #6 |
| R17 | Adapter governance: declaration/policy split, write-scope exclusion, human gates, digest pinning | The adapter interface creates a privilege-escalation path the moment it exists (D14) | Blocks R1 |
| R18 | Capability declaration + absent-capability policy | Otherwise governance disables silently, which violates Principle 7 | Blocks R1 |
| R19 | Second, deliberately dissimilar reference adapter | One adapter cannot distinguish abstraction from indirection | Stage 2 exit |

---

## 3. Design defects found

These need a **decision**, not a schedule. None are patched here — the roadmap records them; the
design set is where they get fixed.

| ID | Where | Defect | Severity |
|---|---|---|---|
| D1 | `v0.5` §4.2 vs. `execution_isolation.md` §6; **resolved in this pass** | §4 applied an intent "synchronously before the agent continues" while §6 committed shared files last, with no materialization path specified anywhere. **Resolved as canonical branch + read-only overlay** (`execution_isolation.md` §7): the Intent Service is sole writer of a `shared/` branch; registered files are `skip-worktree` in every task index and outside every agent's write scope; applied content is re-materialized into live worktrees by atomic rename, so the interpreter sees it and git does not; the Integrator fast-forwards at the end. The read-view guarantee is restated precisely — a worktree is isolated from sibling *in-progress work*, not from *governed shared state*. The reviewability cost is paid by a synthesized per-PR shared-file delta view (§7.4). | Resolved |
| D2 | `agent_interface_contracts.py` §4.2 intents | *Restated under the Core/Adapter model.* The defect is not that the vocabulary is web-shaped — it is that a **repo-specific vocabulary is sitting in the universal contracts file**, presented as the system's intent vocabulary rather than as one adapter's. `AddExport`/`AddRoute`/`AddProviderBinding` describe an Express/Nest/FastAPI codebase and describe nothing about a Selenium extraction tool, a data pipeline, or a CLI. **Resolution: they move out of Core into a reference web adapter**, and Core keeps only `IntentOpSpec` — the shape of a declaration. This is now a Stage 0 relocation, not a CPMI-access blocker. | **Load-bearing** |
| D14 | New, arising from the adapter interface | An adapter contract naming test commands, bootstrap commands, and transformer entry points is **arbitrary code execution declared by the repo being operated on** — and if the same file also says which gates block, the repo grades itself. Two mechanisms close it. **Structural:** the contract splits into a repo-side `RepoDeclaration` (facts, self-punishing if false) and a control-plane `GovernancePolicy` (blocking gates, secret grants, ceilings, degradation policy — self-rewarding if false, so the beneficiary does not set them), with the discriminating test in `core_adapter_boundary.md` §3.1 and two intermediate classes for fields that are self-rewarding but genuinely repo-specific: policy-bounded (clamp and record) and verified (`TestTier.hermetic` is checked, not trusted). **Procedural:** the declaration is a registered shared file outside every agent's write scope, human-gated on change, and both artifacts are digest-pinned into the `RunManifest` (§3.4). | **Load-bearing** |
| D15 | `infra_triage_matrix.md` | Written as *the* rules engine, with rules naming DOM state directly. A backend repo has no DOM. What is universal is the **evaluator** (ordered, first-match-wins, deliberate fallthrough to the LLM); the **rows are adapter data**. The file is reclassified from the engine to the reference rule set for a browser-automation adapter — which is what it has always actually been. | High |
| D16 | `FailureSignature` | Frozen, `extra="forbid"`, one home per schema. An adapter cannot add a field without forking the schema per repo — the exact drift the file exists to prevent, at the type level. Resolved by a declared `signals` map (added additively in this pass); relocating `dom_state_diff_from_baseline` and `network_calls_over_threshold` into it is itself a structural change and goes through the SOP. | High |
| D3 | `v0.5` Agent Roster vs. §9.1; **resolved in this pass** | The roster typed the Budget Accountant as a *Utility* agent that "can trigger a ceiling halt," while §9.1 listed `budget.within_ceiling` as a **deterministic** gate on every transition. A circuit breaker that is itself an LLM fails hardest under exactly the runaway conditions it exists to catch — those conditions saturate the same API it depends on, so it fails *open*. **Split** (`budget_and_escalation_policy.md` §4): a deterministic **Budget Enforcer** in the dispatch path reads `GovernancePolicy.budget_ceilings` and refuses the transition; the **Budget Accountant** survives as an advisory forecaster raising advisory findings only, which is what makes it safe to be an LLM — nothing depends on it firing. | Resolved |
| D4 | `test_harness_architecture.md` §1.2 | The mandate is `browser.new_context()` / `context.close()`. **Selenium has no `new_context()`.** More importantly under the new model: a *capture strategy* is adapter-declared, and §1.2 hard-codes one framework's API into a universal document. | High |
| D5 | `v0.5` §9.1 vs. `test_harness_architecture.md` §3.2 | `mutation.diff_scoped` is **blocking**, justified by "a pure, hermetic unit suite." Non-hermetic tiers cannot satisfy it, so it either blocks forever or gets waived — and a routinely-waived blocking gate is worse than none, because the ledger records it as enforced. Resolved by `TestTier.hermetic` + `satisfies_gates`: the gate applies to tiers that claim it and is not claimed of the others. | High |
| D6 | `execution_isolation.md` §5 | "Containers are not required — yet ... revisit the moment any task's tests bind a port or hit a real service." A discovered-at-runtime escape condition becomes a declared `IsolationUnit` in the manifest. | High |
| D7 | `FailureSignature` | In Python the dominant leak channels are module-level globals, an un-torn-down driver singleton, an unreverted monkeypatch, and import-order effects — all of which leave the DOM pristine. Triage rule 4 misroutes every one to Task Dev as **Logic**. Now expressible as an adapter-declared signal rather than a core schema change. | High |
| D8 | `infra_triage_matrix.md` §2 | No rule covers *passes alone, fails in suite* — `v0.5` §6 step 4 names the case; the rules engine does not implement it. Every instance falls through to the LLM Investigator, and it is the most common flake shape in a suite of this kind, so it will dominate triage spend. | Medium |
| D9 | `Finding.evidence_ref` | Nothing constrains what an evidence reference may point at, how long it is retained, or who may dereference it. Note the non-obvious constraint: a scrubber must know the values it redacts, so it runs **inside** the isolation unit, not in Core (`core_adapter_boundary.md` §5). | Medium |
| D10 | `v0.5` §12 vs. backlog | Concurrency ceiling and Plan Writer dialogue depth carried forward as open, then dropped from the backlog. The v0.2 regression pattern, repeating. | Medium |
| D11 | Glossary + `v0.5` §4 heading | "Shared-File Intent Service" and "Synchronous Intent Service" both exist as glossary terms cross-referencing each other as aliases, and §4's heading still uses the old name. Cosmetic **now**; stops being cheap once code and log field names are written against either spelling. | Low, urgent |
| D17 | Arose from the adapter contract; **resolved in this pass** | The set was about to carry `RunManifest`, a `ProjectManifest`, "Invariant Manifest" (a glossary term), and two repo-meta `*_MANIFEST.md` files — four unrelated things called *manifest*, in a design whose central thesis is closed vocabularies. The declaration/policy split retires the name: `RepoDeclaration` and `GovernancePolicy`. D11's naming pass now only has the Shared-File / Synchronous Intent Service drift to settle. | Resolved |
| D12 | `budget_and_escalation_policy.md` §3 | A ceiling halt "pauses the pipeline." Undefined: what a pause does to an agent mid-wait, to a held driver process, to an intent submitted but not applied, and to live worktrees. No general run-abort exists anywhere in the set. | Medium |
| D18 | `v0.5` §4.5, since v0.2 | **Smart Mutex Rejection has been named in every version since v0.2 without ever having a shape.** §4.5 promises a rejection carrying "the blocking context (what the other agent already claimed), so it can resolve in one shot" — but no schema anywhere defined what that context is, which meant the design's most novel mechanism was the one piece nothing could be built against. Closed by `IntentOutcome` / `IntentRejection` in `agent_interface_contracts.py`, with a closed `reason` enum covering collision, unmapped anchor, unregistered file, undeclared op, and structural overflow. | Resolved |
| D19 | `v0.5` §4.5, security | A rejection tells one agent what **another agent** claimed. Free-form prose on that path is a prompt-injection channel between agents inside the swarm — the one trust boundary the design never examined, because both parties are "our" agents. Closed by making blocking context structured data only (`blocking_task_id`, `blocking_op`, `blocking_keys`), rendered by the receiving side rather than replayed as a message. | Resolved |
| D20 | Deployment, arising from intent transport | If intent submission is served per-agent-session — the default shape for an MCP server — the swarm gets **N writers and no mutex**, and it appears to work until two agents collide. The arbitration in §4.5 is only arbitration if every worktree's agent talks to one long-lived process. Recorded as a hard constraint on any transport (`execution_isolation.md` §7.5) rather than left to discovery. | Resolved |
| D13 | `structural_change_runbook.md` §4 vs. `v0.5` §12 | The runbook's "additive-intent-count threshold" and §12's "task granularity" are the same knob from opposite ends: a task needing many intents against one file *is* a task drawn too coarsely. Resolving them independently produces two contradictory numbers. | Medium |

---

## 4. The sequence

Six stages. A stage starts when its predecessor's **exit criterion** is met, not when its
predecessor's tasks are mostly done. Original backlog numbers appear as `#n`.

### Stage 0 — Contracts and boundaries (documents and schemas; no runtime)

Nothing here needs a running system, and everything downstream is blocked on it.

| Task | Notes |
|---|---|
| **S0-1** Ratify the Core/Adapter boundary | `core_adapter_boundary.md`, including its three leak points: collision predicates (§2.1), telemetry schema (§2.2), triage rules as data (§2.3). Each is a decision, not a detail. |
| **S0-2** ~~Resolve D1~~ **Write up D1's resolution** | Decided: canonical `shared/` branch, `skip-worktree` overlay, atomic re-materialization, fast-forward at integration, synthesized delta view for reviewability (`execution_isolation.md` §7). Remaining Stage 0 work is the precondition gate — assert every registered shared file is `skip-worktree` and out of write scope *before* the swarm spawns — and the delta view's exact shape. |
| **S0-3** Adapter contract v0 (**R1**) | `RepoDeclaration` + `GovernancePolicy` in `agent_interface_contracts.py` — the schema home, same as `RunManifest`. Two artifacts, two trust levels, two change cadences. Each versions **independently of the blueprint**, because target repos upgrade on their own cadence; this is the concrete case backlog #13 has to answer. |
| **S0-4** Adapter governance (**R17**, closes D14) | Apply the §3.1 test field by field and settle the four classes (declaration, policy, policy-bounded, verified). Then the procedural rules: declaration is a registered shared file outside every agent's write scope; a change to it is a lightweight human gate (maintainer PR review), a change to policy is a governance gate; both digest-pinned. Precedence: hard conflicts refuse, bounded conflicts clamp-and-record. Write this before any code reads a contract. |
| **S0-5** Capability declaration + absent-capability policy (**R18**) | Capabilities declared by the repo, never inferred; the *response* to an absent one (`refuse` or `degrade`-and-record) is policy, precisely so the repo that benefits from degrading is not the one that chooses it. No third option in which a capability is absent and nobody is told (Principle 7). |
| **S0-6** Relocate the intent vocabulary (resolves D2) | `AddExport`/`AddRoute`/`AddProviderBinding` move out of the universal contracts file into a reference web adapter. Core retains `IntentOpSpec` — the shape of a declaration, not a declaration. |
| **S0-7** Generalize telemetry (**R12**, resolves D15, D16) | `FailureSignature.signals` as a declared map; triage rules become `TriageRule` rows over declared signals; `infra_triage_matrix.md` reclassified as the reference rule set for a browser adapter. Relocating the two hard-coded UI fields is a structural change and goes through the SOP — `signals` lands additively first. |
| **S0-8** Test tiers + gate applicability (**R5**, **R6**, resolves D4, D5, D6) | `TestTier{command, isolation_unit, hermetic}` repo-side; `blocking_gates` policy-side — a repo does not declare which gates it satisfies. `hermetic` is a **verified** claim (checked by running the tier isolated and in-suite under randomized order), since declaring non-hermetic is what exempts a tier from `mutation.diff_scoped`. Makes that gate decidable rather than universally-blocking-or-waived, and turns the containers question into a declaration. |
| **S0-9** Hydration interface + baseline redefinition (**R15**) | Adapter owns fixtures and apply/verify/teardown; Core owns the ordering guarantee: isolation up → hydrate → **capture baseline** → first action. Baseline stops meaning "canonical empty" and starts meaning "the declared post-hydration state." |
| **S0-10** `CredentialProvider` + scrubbing model (**R16**, **R9**) | A request/grant pair: the repo declares `requested_secrets`, policy holds `granted_secrets`, and an ungranted request refuses the run. Names and scopes only, never values. Scrubber supplied by Core, executed **inside** the isolation unit where values exist, filtering every artifact on the way out. Nothing unscrubbed becomes an `evidence_ref` target. |
| **S0-11** Agent Spec format (**R4**, supersedes #3) | `{system_prompt, input_schema, output_schema, tool_allowlist, write_scope, model_tier, spec_version}`. Core owns the format; the adapter supplies the tool allowlist and write-scope roots. `GateResult.reviewer_spec_version` already expects this record to exist. |
| **S0-12** Provisional granularity + intent threshold (**#2**, resolves D13) | Set both together, explicitly provisional, with Core defaults an adapter may narrow but not widen. Starting rule: one task owns one module directory plus its mirrored test path; more than 3 additive intents against one shared file is a decomposition error. Measured and revised in Stage 5. |
| **S0-13** Concurrency ceiling (**R13**, closes an open question) | Stops being a question: the repo declares a per-unit resource footprint (policy-bounded — understating it buys concurrency at co-tenants' expense), Core clamps, divides, then takes the minimum against `concurrency_cap`, API rate limits, and review throughput. Which constraint binds becomes a fact about a run rather than a discovery when the machine swaps. |
| **S0-14** Naming pass (**#14**, **#13**, resolves D11) | One spelling: **Shared-File Intent Service**. D17's fourth-*manifest* collision is already resolved by the declaration/policy naming. Settle companion-file versioning: companions version independently and each names the blueprint version it was last reconciled against. |

**Exit criterion:** D1, D2, D14, D15, D16 have written answers in the design set; both contract
artifacts validate under Pydantic; every field has a class under the §3.1 test; and every capability
the Core will implement is declarable. **No target
repo has been read.** If Stage 0 cannot be completed without CPMI access, the abstraction has
already failed and that is the finding.

### Stage 1 — Core walking skeleton, against a null adapter

The correction to the backlog's biggest structural flaw: build the governor end to end before any
component is good. The **null adapter** is a synthetic fixture repo whose manifest declares a
trivial test command, no governance, no hydration, no secrets, and a permissive policy alongside it. It exists so Core can be exercised
with zero repo-specific code in the loop.

| Task | Notes |
|---|---|
| **S1-1** Orchestrator state machine (**R3**) | Reads a `RunManifest`, dispatches, persists a new one. Phases 2→6. |
| **S1-2** Event log + manifest persistence (**#8**) | Resolves the run-manifest-location question by building it. Recommendation: **out of tree**, content-addressed, with an in-tree pointer committed to the PR — auditability without run state in every diff. |
| **S1-3** Contract loader, validator, reconciler, and digest pins | Load both artifacts, validate each, reconcile them per §3.3 — refuse on hard conflict, clamp-and-record on bounded conflict — and pin both digests. Refusals and mid-run digest mismatches are `HaltReason` values, not warnings. |
| **S1-4** Cost metering + Budget Enforcer (**R7**, implements D3) | Every invocation emits `{tokens_in, tokens_out, model, cost, task_id, phase}`. The Enforcer is **middleware in the dispatch path** reading `GovernancePolicy.budget_ceilings`, and ships now; the Budget Accountant's advisory forecasting waits for Stage 3 telemetry, and the calibrated cost model for Stage 6. Ship the thing that must fire before the thing that merely helps. |
| **S1-5** Isolation unit lifecycle | Worktree path first; container path stubbed behind the same interface so Stage 4 is a provider swap, not a rewrite. |
| **S1-6** Run abort / halt semantics (**R11**, resolves D12) | Define what pause does to a live process, a held lock, and a submitted-but-unapplied intent — then implement it, because Stage 4 will need it. |
| **S1-7** Human gate control plane (**R8**) | Authenticated approve/reject writing an identity into the event log. Most phases cannot complete without it. This is **control plane, not visualization** — not the dashboard `CLAUDE.md` scopes out. |

**Exit criterion:** a stub task traverses Phases 2→6 against the null adapter unattended, halts at a
human gate, resumes after sign-off, and **resumes correctly from `kill -9`**. Plus three negative
tests: a malformed contract refuses to start, a declaration requesting an ungranted secret scope
refuses to start, and a mid-run edit to either artifact halts the run. If the
manifest cannot survive a kill, resumability is a claim rather than a property.

### Stage 2 — The interface, proved with a dummy transformer

**Reframed goal.** Stage 2 does not produce a production transformer for any language. It proves
that the Core intent service and an arbitrary transformer can talk to each other under a contract
Core enforces. The dummy transformer manipulates a toy anchor format and understands no real
language — which is exactly why it is the right instrument: any obligation it can be held to is an
obligation of *every* transformer, with no libcst or ts-morph behavior confounding the result.

| Task | Notes |
|---|---|
| **S2-1** Intent service Core, **as a library with a lock** | The lock, serialization, `IntentOutcome`/`IntentRejection`, conflict counters, and the §7.2 materialization path. Collision arbitration by exact match on adapter-declared `collision_keys` and nothing else. **Transport stays out of Stage 2**: Stages 1–2 have no LLM agents to talk to a tool server, and a protocol dependency here would drag into the conformance kit. |
| **S2-2** Transformer interface + dummy implementation (**#1**, reframed) | Interface: `structural_map(file)` and `apply(file, intent) -> (text, anchor)`. Success is **contract conformance**, not a working edit: idempotent under replay, formatter round-trip stable, all-or-nothing, loud rejection on unmapped structure. Those four are what the conformance kit asserts. |
| **S2-3** Adapter conformance kit (**R10**) | The executable definition of the interface. Prose describes the boundary; the kit decides it. A Core change that breaks an adapter breaks the kit first. |
| **S2-4** Second reference adapter (**R19**) | Deliberately unlike the first: different declared vocabulary, different signal set, container rather than worktree, hydration present rather than absent. **This is the falsification test.** One adapter cannot distinguish abstraction from indirection, and two similar adapters prove nothing that one proves. |
| **S2-5** Triage evaluator over declared signals (resolves D8) | Core evaluator; rules as adapter data. Ship the reference rule set with the missing *passes-alone, fails-in-suite* rule added — as a reference row, not core code. |
| **S2-6** Deterministic-core conformance suite | Golden cases for every evaluator path, every gate evaluation, every rejection shape. Includes cases asserting that ambiguous signatures fall through to the LLM **deliberately** rather than by omission, and a concurrency case proving two simultaneous colliding submissions produce exactly one `applied` and one `rejection`. |

**Exit criterion:** two dissimilar reference adapters pass the same unmodified conformance kit; a
deliberately colliding pair of intents is rejected with usable blocking context under both; and
replaying an entire intent log twice produces byte-identical files.

### Stage 3 — First real adapter, and the first Maker/Checker pair

CPMI enters here, as an adapter written against a proven interface rather than as the thing the
interface was reverse-engineered from.

The backlog starts its agent work with Plan Writer / Task Decomposer. That is the **worst** first
pair: plan quality is subjective, and the verdict ledger that would grade it does not exist yet.
Start where the oracle is deterministic.

| Task | Notes |
|---|---|
| **S3-1** CPMI adapter, hermetic tier only | Declaration, vocabulary, signals, triage rules, `libcst` transformer against the conformance kit. Browser tier deferred to Stage 4. |
| **S3-1a** Intent transport (MCP server over the Stage 2 library) | The first stage with real LLM agents, so the first stage a transport has anything to talk to. **One shared long-lived server, not one per agent session** — the per-session default gives N writers and no mutex, and looks fine until two agents collide. Reads stay on disk per §7.2, so an outage blocks submissions without breaking test runs. |
| **S3-2** Test Author agent spec + Baseline Guard + mutation gate | Ground truth is a test suite, not an opinion. Falsifiable on day one. |
| **S3-3** Task Dev / Code Reviewer in Shadow Mode | Per `calibration_and_measurement.md` §2 — shadow is the default onboarding path. |
| **S3-4** Verdict ledger | Stands up the measurement substrate every Stage 6 item is blocked on. |
| **S3-5** Plan Writer / Task Decomposer specs (**#3**) | Last, not first — by now there is a ledger to grade them against. |
| **S3-6** Plan Writer dialogue depth (**R14**) | Answerable once S3-5 runs and review-loop cost is observable. |

**Exit criterion:** one real CPMI change goes plan → decomposition → tests → implementation → merge
with agents in the loop and humans at the gates. Single task, no parallelism.

### Stage 4 — The browser tier (the adapter's hard half)

| Task | Notes |
|---|---|
| **S4-1** Container isolation provider | The Stage 1 stub, implemented. |
| **S4-2** Selenium capture strategy (**#5**, resolves D4) | Driver-per-test with a fresh profile directory, declared as a capture strategy rather than hard-coded into the universal harness doc. |
| **S4-3** Hydration provider for CPMI | Seeded tenant state as a named fixture; baseline captured after it. |
| **S4-4** Credential provider, live tenant scope (**#6**) | Injected into the container environment at task start; never a file in a worktree an agent can read and echo. A permission boundary, not an instruction (Principle 12). |
| **S4-5** Evidence scrubbing in-unit (**R9**) | Ships **with** S4-4, not after. |
| **S4-6** Flake Registry | Only meaningful once a real browser suite generates real flakes. |

**Exit criterion:** the browser tier runs green twice consecutively from cold; a deliberately
injected state leak is classified as *Infra — state leakage*, not misrouted to Task Dev; and a
deliberately planted credential in a screenshot does not survive the scrubber.

### Stage 5 — Swarm at width

**S5-1** Parallel dispatch to the derived ceiling · **S5-2** Integrator, No-Conflict Gate,
cumulative conflict counters · **S5-3** Structural Change SOP, first live trigger ·
**S5-4** Swarm observability (**#7**) — correctly placed here, since there is nothing to observe
until there is parallelism; reuse candidates in `archive/glass-box/README.md`, noting that board has
no concept of a phase or a human gate · **S5-5** Task granularity, measured (**#2** revisited) — the
empirical answer that replaces S0-12's provisional one.

**Exit criterion:** a multi-task CPMI change merges clean, with at least one intent collision
correctly rejected and resolved in one shot per §4.5.

### Stage 6 — Unblocked by data

- **#11** Conflict decay-rate tuning — needs promotion data.
- **#4** Cost model, calibrated — needs S1-4's metering across real runs.
- Shadow → Gating promotion for `code.review` — needs the S3-4 ledger at volume.
- **#12** Structural Change SOP cadence — needs repeat triggers to exist.
- **#9** Vocabulary extension process — now sharper: with the vocabulary adapter-declared, this is
  the process for extending a *repo's* enum plus the Core rule for whether a new op requires a new
  transformer. Still needs the first genuine extension event to show what it must handle.

---

## 5. Revised priority, against the original

| # | Item | Was | Now | Why it moved |
|---|---|---|---|---|
| 1 | AST Transform Prototype | P0 | **Stage 2, reframed** | Goal changes from "a working transformer for a real router" to "the transformer contract, proved against a dummy." Blocked by D1 and the interface, not by repo access. |
| 2 | Task Granularity Heuristic | P0 | **Stage 0 (provisional) + Stage 5 (measured)** | Cannot be settled a priori; needs conflict-rate data. Now Core defaults an adapter may narrow. |
| 3 | Core Agent Prompts | P0 | **Stage 0 (format) + Stage 3 (content)** | Prompt is 1 of 6 fields in an agent spec; and Plan Writer is the wrong first pair. |
| 4 | Baseline Cost Model | P0 | **Stage 1 (metering + kill switch) + Stage 6 (model)** | The kill switch is the safety property and ships now; the model is unfalsifiable without measurement. |
| 5 | Baseline Snapshot Mechanics | P0 | **Stage 0 (interface) + Stage 4 (Selenium strategy)** | Split: the capture-and-order guarantee is Core and early; the framework-specific strategy is adapter and late. |
| 6 | Secrets Posture | P1 | **Stage 0 (interface) + Stage 4 (live provider)** | Raised. The interface is Core and belongs with the contract; the live tenant provider is a hard blocker on any browser run. |
| 7 | Swarm Observability | P1 | **Stage 5** | Nothing to observe before parallelism — but R8's gate control plane is Stage 1 and is a different thing. |
| 8 | Run-Manifest Location | P1 | **Stage 1** | Raised: not a filing question, it is the orchestrator's persistence layer. |
| 9 | Vocabulary Extension Process | P1 | **Stage 6** | Lowered, and reshaped: mostly a per-adapter concern once the vocabulary is declared. |
| 10 | Enterprise Invariant Arbitration | P2 | **Deferred, no stage** | Does not arise until a second real repo. Say that, rather than carrying it as perpetually-P2. |
| 11 | Conflict Decay-Rate Tuning | P2 | **Stage 6** | Blocked by data, not deprioritised. |
| 12 | Structural Change Cadence | P2 | **Stage 6** | Blocked by data. |
| 13 | Modular File Versioning | P2 | **Stage 0** | Raised hard. It is no longer a documentation-tidiness question: `RepoDeclaration` is consumed by repos on their own upgrade cadence, and `GovernancePolicy` changes on a different one again, so both *must* version independently of the blueprint and of each other. The adapter interface is the concrete case that answers it. |
| 14 | Naming Inconsistency | P2 | **Stage 0** | Raised on sequence. Costs an hour now, and D17 just added a fourth thing called *manifest*. |

---

## 6. What this changes in `CLAUDE.md`

`CLAUDE.md` currently states: *"We are in design, not build. Do not start implementing agents,
services, or schemas until the design settles and this line changes."*

That gate should not be flipped by this document. What it lacks is a release condition. Proposed:
the gate releases when **Stage 0's exit criterion is met**. Stage 0 is entirely documents and
schemas — and schemas are how this design set has always expressed contracts — so it is executable
under the gate as written.

---

## 7. Open decisions

Raised one at a time, in the order they block work.

1. ~~**D1 — shared-file materialization.**~~ **Decided:** canonical branch with a read-only
   `skip-worktree` overlay, plus a synthesized delta view to pay back the reviewability cost. Intent
   transport (MCP) is a separate, later, pluggable decision — it answers how an agent submits, not
   what the interpreter imports.
2. ~~**D14 — where the adapter contract lives and who owns it.**~~ **Decided:** split into a repo-side
   `RepoDeclaration` and a control-plane `GovernancePolicy`, with the self-punishing/self-rewarding
   test (`core_adapter_boundary.md` §3.1) deciding field placement. D17 resolved as a side effect.
3. ~~**D3 — Budget Accountant.**~~ **Decided:** deterministic Budget Enforcer in the dispatch path,
   Accountant retained as an advisory forecaster with no halt authority.
4. **The second reference adapter's shape.** Its whole value is being unlike the first; which axes
   it differs on is a deliberate choice.
5. **Who owns `GovernancePolicy` in practice.** The split assumes an approver distinct from repo
   maintainers. If that is the same person today, the split still buys the cadence separation but
   not the trust separation — worth being explicit about which benefit is real now.
6. **D5's scope predicate, concretely.** `TestTier.hermetic` decides where `mutation.diff_scoped`
   applies, and `blocking_gates` decides whether it blocks. Neither says what happens to a repo whose
   *only* tier is non-hermetic — the gate then applies nowhere, silently. Refuse, or record it as a
   declared degradation under §3.5? Not urgent until Stage 3, but it is the same class of quiet
   fail-open the rest of this pass has been closing.

---

## 8. Where each decision landed

Every resolved finding in §3 is written into the design set, not only recorded here. This table is
the provenance: what changed, and where to read the reasoning rather than the conclusion. It is a
snapshot — re-check it against `git log` if the set moves under it, the same discipline
`AGENTIC_ARCHITECTURE_MANIFEST.md` carries for the file inventory.

### 8.1 Files created

| File | Created for | Owns |
|---|---|---|
| `implementation_roadmap.md` | The backlog critique | This document — the design→build sequence, the finding register, and the provenance below |
| `core_adapter_boundary.md` | The Core/Adapter split | The seam: what Core owns vs. what a repo declares, the three leak points, the `RepoDeclaration`/`GovernancePolicy` contract, capability negotiation, hydration, credential injection, and how "universal" is made falsifiable |

### 8.2 Files changed, by decision

| Decision | Files changed | What changed in each |
|---|---|---|
| **Core/Adapter split** (D2, D15, D16) | `agent_interface_contracts.py`, `agentic-sdlc-design-v0.5.md`, `CLAUDE.md`, `AGENTIC_ARCHITECTURE_MANIFEST.md` | Contracts gained the adapter-contract block and `FailureSignature.signals`; the blueprint's Modular Reference Files table gained the new companion; both indexes updated |
| **Declaration / policy split** (D14, D17) | `agent_interface_contracts.py`, `core_adapter_boundary.md` | `ProjectManifest` split into `RepoDeclaration` + `GovernancePolicy`; `RunManifest` gained `declaration_digest`, `policy_digest`, `policy_adjustments`; `HaltReason` gained `adapter_policy_conflict`; boundary §3 rewritten around the self-punishing/self-rewarding test and the four field classes |
| **Shared-file materialization** (D1) | `execution_isolation.md`, `agentic-sdlc-design-v0.5.md`, `CLAUDE.md`, `AGENTIC_ARCHITECTURE_MANIFEST.md` | New `execution_isolation.md` §7 (canonical branch, `skip-worktree` overlay, atomic re-materialization, restated read-view guarantee, synthesized delta view, transport constraints); blueprint gained §4.7 and its Phase 4 prose corrected |
| **Intent outcome schema** (D18, D19) | `agent_interface_contracts.py` | `IntentOutcome` and `IntentRejection` added, with blocking context as structured fields and a security note on why it is never prose |
| **Intent transport constraints** (D20) | `execution_isolation.md` | §7.5 — transport is pluggable; one shared long-lived service, structured blocking context, reads stay local |
| **Budget enforcement split** (D3) | `budget_and_escalation_policy.md`, `agentic-sdlc-design-v0.5.md`, `calibration_and_measurement.md`, `agentic_sdlc_glossary.csv` | New `budget_and_escalation_policy.md` §4; Principle 7 rewritten; roster split into Budget Enforcer (Deterministic) and Budget Accountant (advisory); §9.1 gate re-attributed; §3 heading de-scoped; cost-per-pair attribution re-sourced to dispatch metering; glossary term added and two rewritten |
| **Tooling** (supporting the above) | `scripts/frontmatter.py`, `scripts/check_frontmatter.py`, `scripts/sync_counts.py` | `roadmap` registered as a doc type; `companion_file_count` now selects on front-matter `doc_type` rather than "every `plan/*.md` that isn't a design doc", which would have miscounted this file; `live_human_gate_count` added to the registry |

### 8.3 Findings still open, and where they will land when decided

| Finding | Will change |
|---|---|
| D4 (Selenium capture strategy) | `test_harness_architecture.md` §1.2 — capture strategy becomes adapter-declared rather than one framework's API |
| D5 (mutation gate scope) | `test_harness_architecture.md` §3, plus the §7 question on an all-non-hermetic repo |
| D6 (isolation unit) | `execution_isolation.md` §5 — "not required yet" becomes a declared `IsolationUnit` |
| D7 (in-process leakage signal) | The reference adapter's `SignalSpec` set, not the core schema |
| D8 (passes-alone/fails-in-suite rule) | `infra_triage_matrix.md` §2, as a reference rule |
| D9 (evidence retention) | `core_adapter_boundary.md` §5 has the scrubbing model; retention and dereference rules are unwritten |
| D10 (two dropped open questions) | `agentic-sdlc-design-v0.5.md` §12 — S0-13 answers concurrency ceiling; Plan Writer dialogue depth waits for Stage 3 |
| D11 (naming drift) | `agentic-sdlc-design-v0.5.md` §4 heading and `agentic_sdlc_glossary.csv`'s duplicate alias pair |
| D12 (run abort semantics) | `budget_and_escalation_policy.md` §3's pause step, which currently says "pauses" without saying what that does to a live process |
| D13 (granularity ↔ intent threshold) | `structural_change_runbook.md` §4 and `agentic-sdlc-design-v0.5.md` §12, together or not at all |

---

## 9. Deliberately not in this roadmap

- **Enterprise invariant arbitration** (#10) — genuinely out of scope until a second real repo, and
  better answered by that repo's actual disagreement than by anticipating it.
- **The dashboard as a product.** R8 builds a gate control plane because the pipeline cannot run
  without one. Visualization stays scoped out per `CLAUDE.md` until the pipeline is real.
