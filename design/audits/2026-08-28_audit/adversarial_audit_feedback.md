---
title: "Adversarial Audit Feedback: SDLC Agentic Development System (v0.5)"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Adversarial Audit Feedback: SDLC Agentic Development System (v0.5)

**Date:** 2026-08-28  
**Purpose:** Collect user feedback, decisions, and action items on the key findings from the v0.5 Adversarial Audit.  
*(Note: Clarifying questions Q1–Q6 are handled separately in [audit_questions_response.md](file:///code/agent-swarm/agent-swarm/design/audits/2026-08-28_design/audits/audit_questions_response.md).)*

---

## 🔴 1. Critical Issues

### C1. Security — In-Unit Secret Scrubbing is Defeatable
- **Location:** [core_adapter_boundary.md §5](file:///code/agent-swarm/agent-swarm/design/plans/core_adapter_boundary.md)
- **Problem:** Secrets are scrubbed inside the isolation unit where Task Dev agents have write access to `src/`. An agent could tamper with the scrubber, encode credentials in filenames/commit messages, or exfiltrate them via network calls.
- **Recommendation:** Run the scrubber in a separate trust boundary (outside the container or in a sidecar with its own filesystem view).

#### Feedback / Decision:
I agree with the recommendation.

---

### C2. Deadlock Potential in Smart Mutex Rejection
- **Location:** [agentic-sdlc-design-v0.5.md §4.5](file:///code/agent-swarm/agent-swarm/design/plans/agentic-sdlc-design-v0.5.md#L138-L139), [agent_interface_contracts.py](file:///code/agent-swarm/agent-swarm/design/plans/agent_interface_contracts.py)
- **Problem:** When multiple tasks submit mutually incompatible structural intents, they can enter circular rejection loops, burning budget without diagnostic root-cause reporting.
- **Recommendation:** Implement explicit cycle/deadlock detection. Escalate repeated collisions as **boundary failures** (Principle 8) rather than consuming retries blindly.

#### Feedback / Decision:
I agree with the recommendation.

---

### C3. The `NOT_APPLICABLE` Gate Bypass
- **Location:** [agent_interface_contracts.py `GateApplicability`](file:///code/agent-swarm/agent-swarm/design/plans/agent_interface_contracts.py), [agentic-sdlc-design-v0.5.md §9.1](file:///code/agent-swarm/agent-swarm/design/plans/agentic-sdlc-design-v0.5.md#L216-L217)
- **Problem:** An agent could modify files not covered by hermetic test tiers, causing blocking gates to return `NOT_APPLICABLE` and bypassing mutation checks entirely.
- **Recommendation:** Treat `NOT_APPLICABLE` from a blocking gate on non-trivial diffs as suspicious, triggering advisory warnings or human review.

#### Feedback / Decision:
I agree with the recommendation.

---

### C4. Race Conditions in Shared-File Materialization
- **Location:** [execution_isolation.md §7](file:///code/agent-swarm/agent-swarm/design/plans/execution_isolation.md), [agentic-sdlc-design-v0.5.md §4.7](file:///code/agent-swarm/agent-swarm/design/plans/agentic-sdlc-design-v0.5.md#L144-L156)
- **Problem:** Atomic POSIX rename only guarantees filesystem atomicity, not runtime isolation (e.g. Python module caches in `sys.modules`, mid-test reads, or file watchers).
- **Recommendation:** Materialize shared files strictly *between* test executions, not while tests/agents are running.

#### Feedback / Decision:
This makes sense - I agree with the recommendation.

---

### C5. Design/Build Phase Contradiction
- **Location:** [CLAUDE.md L20-22](file:///code/agent-swarm/agent-swarm/CLAUDE.md#L20-L22) vs. [agent_interface_contracts.py](file:///code/agent-swarm/agent-swarm/design/plans/agent_interface_contracts.py)
- **Problem:** CLAUDE.md mandates "design, not build", yet contracts are 569 lines of executable Pydantic code and Stage 0 requires building a conformance kit.
- **Recommendation:** Clarify the definition of "design" to explicitly permit contract/schema definition, or formally mark Stage 0 as beginning the "build" phase.

#### Feedback / Decision:
Agreed.

---

## 🟠 2. High-Severity Concerns

### H1. Calibration Loop Can't Close — Downstream Attribution is Impractical
- **Location:** [calibration_and_measurement.md §1](file:///code/agent-swarm/agent-swarm/design/plans/calibration_and_measurement.md#L26-L38)
- **Problem:** Automatically attributing post-deployment bugs back to specific validator verdicts weeks earlier is undefined and unrealistic in fast-moving repos.
- **Recommendation:** Focus metrics on precision-against-human-review and near-term integration catch rates rather than downstream production attribution.

#### Feedback / Decision:
Agreed.

---

### H2. Blanket `max_retries=3` is Too Coarse
- **Location:** [budget_and_escalation_policy.md §1](file:///code/agent-swarm/agent-swarm/design/plans/budget_and_escalation_policy.md#L20-L25)
- **Problem:** Fixed 3-retry limit across all loop edges ignores the vast cost differences (e.g., Opus planning vs. local unit test fix) and sub-step multiplication.
- **Recommendation:** Parameterize retry ceilings per loop type and cost tier.

#### Feedback / Decision:
Agreed.

---

### H3. Fresh Test Environment Per Test is Prohibitively Expensive
- **Location:** [test_harness_architecture.md §1.2](file:///code/agent-swarm/agent-swarm/design/plans/test_harness_architecture.md#L24-L64)
- **Problem:** Spinning up a fresh WebDriver per test takes 1–3s, making a 500-test suite take 8–25 minutes solely on browser initialization, violating wall-clock limits.
- **Recommendation:** Define concrete pooling, browser context reuse, or tiered execution strategies.

#### Feedback / Decision:
Agreed - specifically on the tiered execution strategies.  My main repo, for example, has tests split by the fast tests and the slow/flaky tests (namely browser-based tests).  We need to figure out generalized tiers and which tiers are necessary in which contexts.

---

### H4. Onboarding Complexity is Astronomical
- **Location:** [core_adapter_boundary.md §1.2](file:///code/agent-swarm/agent-swarm/design/plans/core_adapter_boundary.md#L39-L49)
- **Problem:** Onboarding requires writing specs for isolation, test tiers, intent vocabularies, AST transformers, triage rules, hydration hooks, and secrets.
- **Recommendation:** Define tiered adapter onboarding (e.g., Level 1: basic tests, Level 2: additive AST intents, Level 3: full hermetic DOM triage) or scaffolding tooling.

#### Feedback / Decision:
Agreed (see my comment in H3).

---

### H5. Structural Change SOP Creates a Human Bottleneck
- **Location:** [structural_change_runbook.md](file:///code/agent-swarm/agent-swarm/design/plans/structural_change_runbook.md)
- **Problem:** Any non-additive structural change triggers a pipeline pause and human architectural review, stalling autonomous runs during off-hours.
- **Recommendation:** Introduce a middle tier for low-risk structural refactors (e.g. single-file moves, simple rename intents) with scoped automated checks.

#### Feedback / Decision:
Agreed.

---

### H6. `extra="forbid"` + LLM Output = Chronic Parse Failures
- **Location:** [agent_interface_contracts.py L13-16](file:///code/agent-swarm/agent-swarm/design/plans/agent_interface_contracts.py#L13-L16)
- **Problem:** LLMs hallucinating harmless extraneous keys cause fatal validation errors across all Pydantic models.
- **Recommendation:** Implement a two-pass validation strategy (`extra="forbid"` with fallback to `extra="ignore"` + logged warning) or normalization pre-parsers.

#### Feedback / Decision:
Agreed.

---

### H7. Collision Key Semantics are Too Shallow
- **Location:** [core_adapter_boundary.md §2.1](file:///code/agent-swarm/agent-swarm/design/plans/core_adapter_boundary.md#L61-L74), [agent_interface_contracts.py](file:///code/agent-swarm/agent-swarm/design/plans/agent_interface_contracts.py)
- **Problem:** Exact-match string collision keys miss semantic conflicts (e.g., conflicting middleware, overlapping regex routes like `/users/:id` vs `/users/new`).
- **Recommendation:** Expand collision detection or ensure adapter-provided static analyzers run at integration staging.

#### Feedback / Decision:
Agreed.

---

### H8. No Crash Recovery for Stateful Isolation Units
- **Location:** [agentic-sdlc-design-v0.5.md §3](file:///code/agent-swarm/agent-swarm/design/plans/agentic-sdlc-design-v0.5.md#L100-L103)
- **Problem:** RunManifest tracks pipeline phase, but has no protocol to clean up orphaned Docker containers, rollback uncommitted `shared/` branch changes, or reconcile half-materialized files after a process crash.
- **Recommendation:** Define an explicit recovery/reconciliation protocol on startup.

#### Feedback / Decision:
Agreed, this is necessary.

---

## 🟡 3. Medium-Severity Observations

### M1. CSV Glossary Maintenance
- **Finding:** [agentic_sdlc_glossary.csv](file:///code/agent-swarm/agent-swarm/design/plans/agentic_sdlc_glossary.csv) is cumbersome to review in PRs and prone to drift.
- **Proposal:** Convert to a Markdown table or generate it from structured docstrings.

#### Feedback / Decision:
Agreed.

---

### M2. Competing Inventory Files
- **Finding:** [AGENTIC_ARCHITECTURE_MANIFEST.md](file:///code/agent-swarm/agent-swarm/AGENTIC_ARCHITECTURE_MANIFEST.md) and [FRONTMATTER_MANIFEST.md](file:///code/agent-swarm/agent-swarm/FRONTMATTER_MANIFEST.md) overlap in purpose without tracking semantic inter-doc dependencies.
- **Proposal:** Unify into a single source of truth or define explicit boundaries.

#### Feedback / Decision:
Agreed - either unification or defining explicit boundaries will work.

---

### M3 & M4. Context Retrieval Optimization
- **Finding:** Vector search struggles with custom DSLs ([context_retrieval_strategy.md](file:///code/agent-swarm/agent-swarm/design/plans/context_retrieval_strategy.md)); broad-then-narrow forces unnecessary sequential latency when target files are already known.
- **Proposal:** Add lexical/symbol lookup bypass for known targets and specialized DSL symbol indexes.

#### Feedback / Decision:
Agreed.

---

### M5. Hermeticity Verification Cost
- **Finding:** Randomized test order execution for hermeticity verification is combinatorial and heavy for large suites.
- **Proposal:** Scope verification to changed test subsets or periodic shadow runs.

#### Feedback / Decision:
Agreed.

---

### M6. DOM Baseline False Positives
- **Finding:** Async background browser events can dirty DOM state, misclassifying logic bugs as infra triage failures ([infra_triage_matrix.md](file:///code/agent-swarm/agent-swarm/design/plans/infra_triage_matrix.md)).
- **Proposal:** Filter volatile DOM elements and standardize hydration quiescence checks.

#### Feedback / Decision:
Agreed.

---

## 💬 4. General / Overall Direction Feedback

#### Feedback / Decision:
These are all very reasonable points.  It would be worthwhile to generate multiple files (one for each key finding) investigating solutions in more detail as part of this audit before we can close it out.
