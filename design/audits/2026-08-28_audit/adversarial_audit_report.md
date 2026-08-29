---
title: "Adversarial Audit: SDLC Agentic Development System (v0.5)"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Adversarial Audit: SDLC Agentic Development System (v0.5)

**Date:** 2026-08-27  
**Scope:** All 12 files in `plan/`, plus `CLAUDE.md`, `AGENTIC_ARCHITECTURE_MANIFEST.md`, `FRONTMATTER_MANIFEST.md`, and `plan/versions/`  
**Methodology:** Two parallel deep-read passes (core design + operations/policy), followed by cross-reference verification

---

## Executive Summary

This is an unusually rigorous design for an agentic system. The self-auditing discipline (REGRESSION.md, the defect registry in the roadmap, the explicit "illustrative" markers on thresholds) is significantly above average. The Core/Adapter split, the maker/checker asymmetry, and the deterministic-before-LLM principle are all well-reasoned.

That said, the audit found **5 critical issues**, **8 high-severity concerns**, and **6 clarifying questions** that should be resolved before implementation begins.

---

## 🔴 Critical Issues

### C1. Security — In-Unit Secret Scrubbing is Defeatable

**Where:** [core_adapter_boundary.md §5](file:///code/agent-swarm/agent-swarm/plan/core_adapter_boundary.md)  
**The claim:** Secrets are injected into the isolation unit, and scrubbing runs *inside* the unit before artifacts leave — so Core never handles raw secrets.

**The problem:** Task Dev agents operate *inside* that same isolation unit with write access to `src/`. A hallucinating or adversarial agent could:
1. Tamper with or bypass the scrubber process before it runs
2. Encode credentials into file names, commit messages, or binary artifacts that the scrubber doesn't inspect
3. Exfiltrate secrets via network calls during test execution (if containers allow outbound traffic)

**Recommendation:** The scrubber must run in a separate trust boundary from the agent — either as a post-exit step outside the container, or in a sidecar with its own filesystem view. The agent should never have write access to the scrubbing mechanism itself.

---

### C2. Deadlock Potential in Smart Mutex Rejection

**Where:** [agentic-sdlc-design-v0.5.md §4.5](file:///code/agent-swarm/agent-swarm/plan/agentic-sdlc-design-v0.5.md#L138-L139), [agent_interface_contracts.py](file:///code/agent-swarm/agent-swarm/plan/agent_interface_contracts.py)  
**The claim:** Colliding intents are rejected back to the submitting agent with blocking context.

**The problem:** If two tasks have fundamentally incompatible structural requirements (e.g., Task A needs route `/api/v2/users` and Task B needs the same path for a different handler), they will ping-pong rejections. The budget ceiling will eventually kill the run, but it will burn significant tokens/dollars before it does. More subtly, three or more tasks can create a circular wait where no ordering of intent submissions resolves the collision.

**What's missing:** There is no explicit deadlock detection. The budget enforcer is a blunt instrument for this — it stops the bleeding but doesn't diagnose the cause. A collision that persists after N rejections should escalate as a **boundary failure** (Principle 8), not just burn retries.

---

### C3. The `NOT_APPLICABLE` Gate Bypass

**Where:** [agent_interface_contracts.py `GateApplicability`](file:///code/agent-swarm/agent-swarm/plan/agent_interface_contracts.py), [agentic-sdlc-design-v0.5.md §9.1](file:///code/agent-swarm/agent-swarm/plan/agentic-sdlc-design-v0.5.md#L216-L217)  
**The claim:** Gates can return `NOT_APPLICABLE` when their scope doesn't cover the diff.

**The problem:** An adversarial or poorly-prompted Task Dev agent could structure its changes to intentionally fall outside the scope of hermetic test triggers (e.g., modifying only files that aren't covered by any hermetic test tier), effectively bypassing the mutation gate by forcing it to return `NOT_APPLICABLE`. 

**What's missing:** The design needs a rule that a `NOT_APPLICABLE` result from a *blocking* gate on a non-trivial diff is itself suspicious and should trigger a human review or at minimum an advisory finding. A change that somehow avoids *all* verification gates is more dangerous, not less.

---

### C4. Race Conditions in Shared-File Materialization

**Where:** [execution_isolation.md §7](file:///code/agent-swarm/agent-swarm/plan/execution_isolation.md), [agentic-sdlc-design-v0.5.md §4.7](file:///code/agent-swarm/agent-swarm/plan/agentic-sdlc-design-v0.5.md#L144-L156)  
**The claim:** Shared files are re-materialized into live worktrees via atomic POSIX rename while agents work.

**The problem:** "Atomic rename" only guarantees filesystem-level atomicity. It does **not** protect against:
- A Python runtime that has already cached the old module in `sys.modules` (the agent sees stale code until process restart)
- A test that reads the file mid-execution and gets a mixture of old/new state within a single test run
- File-watcher tools or IDEs that react to the change mid-test

The design correctly identifies that worktrees are isolated from sibling *in-progress work*, but the materialization of *governed shared state* into a running worktree reintroduces exactly the instability the isolation was meant to prevent. The safe window for materialization is *between* test runs, not during them.

---

### C5. Design/Build Phase Contradiction

**Where:** [CLAUDE.md L20-22](file:///code/agent-swarm/agent-swarm/CLAUDE.md#L20-L22) vs. [agent_interface_contracts.py](file:///code/agent-swarm/agent-swarm/plan/agent_interface_contracts.py)  
**The claim:** "We are in design, not build."

**The problem:** `agent_interface_contracts.py` is 569 lines of fully executable, import-ready Pydantic code. The implementation roadmap demands immediate creation of a conformance kit (Stage 0). The glossary is a machine-readable CSV. These are all build artifacts. The gating line in CLAUDE.md creates an impossible instruction for agents: contribute to the design while the design *is* executable code.

**Recommendation:** Either redefine "design" to explicitly include schema and contract code (making the gate meaningful: "don't build agents, services, or orchestrators"), or acknowledge that Stage 0 of the roadmap is already "build" and update the gate accordingly.

---

## 🟠 High-Severity Concerns

### H1. Calibration Loop Can't Close — Downstream Attribution is Impractical

**Where:** [calibration_and_measurement.md §1](file:///code/agent-swarm/agent-swarm/plan/calibration_and_measurement.md#L26-L38)

The verdict ledger records "downstream outcome" (did the artifact a validator passed later fail?). In a mutating codebase with continuous deploys, attributing a production bug to the specific `GateResult` that let it through weeks earlier is functionally impossible to automate. The document acknowledges this implicitly by leaving thresholds as TBD, but the *mechanism* for downstream attribution is not just untuned — it's architecturally undefined.

> [!WARNING]
> Without a concrete attribution mechanism, the "cost per genuinely-caught defect" metric (§4) is aspirational. The precision-against-human-review metric is achievable; the downstream metric may never be.

---

### H2. Blanket `max_retries=3` is Both Too High and Too Low

**Where:** [budget_and_escalation_policy.md §1](file:///code/agent-swarm/agent-swarm/plan/budget_and_escalation_policy.md#L20-L25)

A uniform `max_retries=3` across all loop-back edges ignores both cost and complexity:
- For Plan Writer ↔ Plan Reviewer on Opus, 3 retries could burn $20–50+ in tokens per cycle
- For a genuinely complex decomposition problem, 3 attempts at re-decomposition may be insufficient
- The escalation ladder (context re-gather → retry → model escalation → human) means each "retry" is actually 3–4 sub-steps, so 3 retries is really 9–12 LLM calls

**Recommendation:** Parametrize ceilings per loop type or at minimum per cost tier.

---

### H3. Fresh Test Environment Per Test is Prohibitively Expensive

**Where:** [test_harness_architecture.md §1.2](file:///code/agent-swarm/agent-swarm/plan/test_harness_architecture.md#L24-L64)

The document correctly identifies that Selenium's fresh-driver-per-test costs ~1–3 seconds. A 500-test browser suite would spend 8–25 minutes on browser startup alone. Combined with parallel agents each running their own suites, this interacts catastrophically with:
- The wall-clock ceiling in [budget_and_escalation_policy.md §3](file:///code/agent-swarm/agent-swarm/plan/budget_and_escalation_policy.md#L49-L60)
- Container memory limits (each WebDriver is a full browser process)
- The concurrency ceiling derivation in [core_adapter_boundary.md §3.6](file:///code/agent-swarm/agent-swarm/plan/core_adapter_boundary.md)

The document *acknowledges* this tension but doesn't resolve it. It just says the cost was "priced for milliseconds" and at seconds "it is a different decision." What decision? This needs an actual answer.

---

### H4. Onboarding Complexity is Astronomical

**Where:** [core_adapter_boundary.md §1.2](file:///code/agent-swarm/agent-swarm/plan/core_adapter_boundary.md#L39-L49)

To onboard a new repo, a team must provide:
- Isolation unit specs (worktree vs. container, image reference, bootstrap commands, port bindings, resource footprint)
- Test tiers with commands, hermeticity declarations, and reset strategies
- Additive intent vocabulary with collision keys and AST transformers
- Telemetry signal definitions and ordered triage rules
- Hydration hooks (fixture states, apply/verify/teardown)
- Credential names and scopes

This is not a "fill out a config file" onboarding — it's weeks of work per repository, requiring deep understanding of both the repo *and* the SDLC system. The 64-term glossary alone is a barrier.

---

### H5. Structural Change SOP Creates a Human Bottleneck

**Where:** [structural_change_runbook.md](file:///code/agent-swarm/agent-swarm/plan/structural_change_runbook.md)

In a mature codebase, file renames, route restructuring, and module splits happen regularly. Every one of these triggers the Structural Change SOP: pause affected swarm tasks → snapshot → human architecture review → new decomposition → resume. During off-hours, the entire pipeline stalls. The "agentic" system degrades into a ticketing queue.

The design correctly identifies that LLMs shouldn't attempt non-additive refactors autonomously, but the binary choice between "fully additive intent" and "full human halt" needs a middle tier for low-risk structural changes.

---

### H6. `extra="forbid"` + LLM Output = Chronic Parse Failures

**Where:** [agent_interface_contracts.py L13-16](file:///code/agent-swarm/agent-swarm/plan/agent_interface_contracts.py#L13-L16)

LLMs frequently hallucinate extra fields in structured output. With `extra="forbid"` on every model, any hallucinated field causes a hard Pydantic validation error, killing the pipeline step. The design rationale (prevent silent mutation) is sound, but the failure mode is chronic — especially with weaker models in the escalation ladder.

**Recommendation:** Consider a two-pass approach: validate with `extra="forbid"`, but on failure, retry with `extra="ignore"` + a logged warning, before escalating.

---

### H7. Collision Key Semantics are Too Shallow

**Where:** [core_adapter_boundary.md §2.1](file:///code/agent-swarm/agent-swarm/plan/core_adapter_boundary.md#L61-L74), [agent_interface_contracts.py](file:///code/agent-swarm/agent-swarm/plan/agent_interface_contracts.py)

Collision detection relies only on exact key matches. Two intents can be semantically destructive when combined but technically have different collision keys:
- Two middleware additions that cancel each other out
- Two route additions that create ambiguous matching (e.g., `/users/:id` and `/users/new`)
- Two provider bindings for the same interface with different scopes

The document acknowledges this is "deliberately under-powered" but doesn't quantify the residue. In a complex routing setup, this could be a frequent source of silent integration failures.

---

### H8. No Crash Recovery for Stateful Isolation Units

**Where:** [agentic-sdlc-design-v0.5.md §3](file:///code/agent-swarm/agent-swarm/plan/agentic-sdlc-design-v0.5.md#L100-L103)

The RunManifest supports resumability from the last recorded phase, but there's no defined mechanism for:
- Cleaning up orphaned containers from a mid-Phase-4 crash
- Rolling back half-applied intents on the `shared/` branch
- Handling a crash between "intent applied" and "materialized into worktrees"

The immutable RunManifest pattern is good for the state machine, but the *side effects* (containers, worktrees, branch state) need explicit cleanup/rollback semantics.

---

## 🟡 Medium-Severity Observations

| # | Issue | Where | Notes |
|---|---|---|---|
| M1 | CSV glossary will rot | [agentic_sdlc_glossary.csv](file:///code/agent-swarm/agent-swarm/plan/agentic_sdlc_glossary.csv) | Difficult to review in PRs, likely to fall out of sync with rapidly evolving docs. Markdown table would integrate better with the review workflow |
| M2 | Two competing inventory files | [AGENTIC_ARCHITECTURE_MANIFEST.md](file:///code/agent-swarm/agent-swarm/AGENTIC_ARCHITECTURE_MANIFEST.md) + [FRONTMATTER_MANIFEST.md](file:///code/agent-swarm/agent-swarm/FRONTMATTER_MANIFEST.md) | Both claim to be the repository map; neither tracks semantic dependencies between docs |
| M3 | Vector search weakness for DSLs | [context_retrieval_strategy.md](file:///code/agent-swarm/agent-swarm/plan/context_retrieval_strategy.md) | Semantic search is poor at custom DSLs, specific syntax idioms, and highly abstracted code |
| M4 | Sequential latency in context retrieval | [context_retrieval_strategy.md](file:///code/agent-swarm/agent-swarm/plan/context_retrieval_strategy.md) | Broad-then-narrow forces two sequential calls even when the agent already knows the exact target |
| M5 | Hermeticity verification is expensive | [core_adapter_boundary.md](file:///code/agent-swarm/agent-swarm/plan/core_adapter_boundary.md) | Running tests in randomized order to verify hermeticity is combinatorially expensive for large suites |
| M6 | DOM baseline false positives | [infra_triage_matrix.md](file:///code/agent-swarm/agent-swarm/plan/infra_triage_matrix.md) | Third-party scripts, service workers, background syncs can dirty DOM state, causing logic failures to be misclassified as infra |

---

## ✅ Notable Strengths

| Strength | Why It Matters |
|---|---|
| **REGRESSION.md** | A version-over-version audit trail that catches silent feature loss is rare and valuable. The v0.5 reinstatement pass is evidence of genuine intellectual honesty. |
| **Deterministic-before-LLM principle** | Structurally prevents the most expensive and unreliable failure mode (LLM-as-circuit-breaker). The Budget Enforcer / Budget Accountant split is particularly well-reasoned. |
| **Core/Adapter boundary with the discriminating test** | "A field belongs in the Adapter if a false value punishes the declarer; it belongs in GovernancePolicy if a false value rewards them" — this is an unusually crisp ownership heuristic. |
| **The defect registry** | D1–D22 in the roadmap, with severity and resolution status, is more rigorous than most production systems' bug tracking. |
| **Maker/Checker asymmetry** | The insight that a validator reading the builder's rationale is "grading persuasion, not the artifact" is precise and well-forced. |
| **Immutable state transitions** | `frozen=True` everywhere, producing new RunManifest instances instead of mutating — this makes the state machine auditable by construction. |

---

## Summary of Findings by Severity

| Severity | Count | Key Themes |
|---|---|---|
| 🔴 Critical | 5 | Security (scrubbing trust boundary), deadlock potential, gate bypass, race conditions, phase contradiction |
| 🟠 High | 8 | Calibration loop closure, cost realism, onboarding complexity, human bottleneck, LLM parse fragility, shallow collision semantics, crash recovery |
| 🟡 Medium | 6 | Tooling format, inventory duplication, search limitations, verification cost |
| ✅ Strengths | 6 | Self-auditing rigor, deterministic governance, crisp ownership heuristics, defect tracking |
