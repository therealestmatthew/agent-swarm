---
title: Audit Questions & Responses
status: live
part_of: repo-meta
doc_type: reference
---

# Audit Questions & Responses

## ❓ Clarifying Questions

---

### Q1. What is the target repo size and team context?

> **Question:**  
> The onboarding cost (H4) is dramatically different for a 10-person team on one repo vs. an enterprise with 200 repos. Is this designed for a single high-value repo, or for mass deployment?

#### Response
This is initially designed for a small team (Myself, the architect, and 2-3 additional developers).  However, the idea is to eventually scale it to support additional mono repos or, eventually, multi-repo ecosystems. 

---

### Q2. What LLM provider and rate limits are assumed?

> **Question:**  
> The concurrency ceiling derivation ([core_adapter_boundary.md §3.6](file:///code/agent-swarm/agent-swarm/plan/core_adapter_boundary.md)) mentions API rate limits, but the design doesn't name providers. Rate limits vary 10x+ between providers and tiers. Are you targeting Anthropic, OpenAI, Google, or provider-agnostic?

#### Response
Let's assume Anthropic (primary) and potentially OpenAI (secondary) - I would need to research the exact API limits.

---

### Q3. What is the expected cost per run?

> **Question:**  
> Even illustratively — are we talking $5/run, $50/run, or $500/run? The budget ceilings are TBD, but the *order of magnitude* shapes every design decision. A 23-agent roster with 3 retries each and model escalation on a large PR could easily reach hundreds of dollars.

#### Response
This is an excellent question.  We may want to consider how we can decompose the total 23-agent roster into smaller systems for smaller tasks.  I'm inclined to say somewhere between $5 and $50 per run.  This really depends on how the system is being used (and we should assume that it runs under strict human supervision and instruction for the first several cycles during the evaluation phase).  We may want to explore what sub-systems exist within this larger system and how can we scale it down versus using the entirety of the system.

---

### Q4. How does the system handle dependent test failures?

> **Question:**  
> If Task A's implementation breaks Task B's tests (discovered at integration), the current design treats it as a decomposition error. But what if the dependency is legitimate and was correctly declared in the interface map? The Test Investigator sees a logic failure, but the fix belongs to Task A, not Task B.

#### Response
I am really not sure - we would need to figure out how to handle this edge case.

---

### Q5. What happens to in-flight work during a ceiling halt?

> **Question:**  
> [budget_and_escalation_policy.md §3](file:///code/agent-swarm/agent-swarm/plan/budget_and_escalation_policy.md#L60) says the pipeline pauses and state is snapshotted. But during Phase 4, multiple Task Dev agents may be mid-execution. Are their containers/worktrees preserved? Can they be resumed, or must they restart from their last committed state?

#### Response
I really don't know.  My instinct says we should have a decision tree that helps us figure out which case should follow in such a scenario.  I would think they should be preserved and resumable, but what triggers would mandate a restart from last-committed state?

---

### Q6. Is Stage 0 of the roadmap implementation work?

> **Question:**  
> [implementation_roadmap.md](file:///code/agent-swarm/agent-swarm/plan/implementation_roadmap.md) Stage 0 involves defining `RepoDeclaration`/`GovernancePolicy` contracts and relocating web-specific intents out of Core — which requires modifying `agent_interface_contracts.py`. Does this count as "build" under the CLAUDE.md gate, or is schema relocation still "design"?

#### Response
Schema relocation is still design.  Also, we should consider decomposing the agent_interface_contracts.py file into multiple modular files by purpose - need to figure out if this makes sense and to what level of detail we should decompose.