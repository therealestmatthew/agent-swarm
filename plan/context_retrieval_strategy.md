# Context Retrieval Strategy

**Referenced by:** `agentic-sdlc-design-v0.5.md` §3 (Phase 1) · Agent Roster (Context Gatherer)

## Purpose

This file owns the mechanics the core design document only names: how the Context Gatherer decides *where* to look, and how it stays inside a consumer's token budget without silently dropping information.

---

## 1. Search Heuristics: git history vs. vector search

### 1.1 Two different questions
- **`git log -S` / `git blame`** answer "when and why did this specific token or line come to exist." Precise and git-native, but you have to already know the exact symbol or string to search for.
- **Vector DB semantic search** answers "what existing code is conceptually related to X." Works without knowing exact symbol names, but returns ranked, approximate results rather than a single definitive answer.

These aren't interchangeable — one requires a known target, the other doesn't.

### 1.2 Default: broad-then-narrow
At planning time (Phase 1), default to **vector search first.** The querier doesn't yet know which specific files or symbols matter — that's exactly what semantic search is for. Once a candidate file or symbol surfaces from that pass, escalate to `git log -S` / `blame` for a narrow, specific follow-up ("when did this constant change, and in what commit") only if the plan actually needs that provenance detail.

Running both in parallel is reserved for the rare case where a task explicitly needs *both* an authorship answer and a conceptual-similarity answer up front. The default is sequential — running both by default would have the Context Gatherer generating two independent context injections for a question vector search alone would usually have resolved.

### 1.3 Invariant retrieval is a separate, always-on path
Matching `repo_local` and `enterprise_wide` invariants (design doc §5) is not folded into the general heuristic above. It always runs, regardless of what the code-search heuristic decides, because a matching invariant is a correctness constraint — not a "maybe relevant" suggestion. See §2.2 below for how this affects ranking.

---

## 2. Context Window Budgets

### 2.1 Per-consumer budgets
Different downstream consumers get different allowances. Illustrative starting point — tune against your actual model context windows and observed plan quality:

| Consumer | Relative budget | Rationale |
|---|---|---|
| Plan Writer (Phase 1) | Largest | Needs the broadest picture to produce a sound plan |
| Task Decomposer (Phase 2 & 3) | Medium | Needs interface-level detail, not full file bodies |
| Test Investigator (Phase 6) | Smallest, on-demand only | Queries per-failure rather than receiving a standing injection (design doc §6) |

### 2.2 Ranking heuristic
Score candidate context chunks by:

1. **Direct symbol/file overlap** with the task description — highest weight.
2. **Recency** — recently-modified files weighted higher.
3. **Invariant relevance.**

Invariants matching the task's domain are **hard-included regardless of score** — they're correctness constraints, not optional context, and shouldn't be droppable by a ranking algorithm the way a "maybe relevant" file legitimately can be.

### 2.3 Summarize, never silently drop
Chunks that don't make the top-K by score are compressed to a one-line digest (file path + one-sentence relevance note), not dropped outright. This lets downstream consumers know more context exists even when they weren't given it in full — avoiding the illusion of complete coverage.

### 2.4 Overflow handling
If total context exceeds budget even after summarization, the Context Gatherer surfaces an explicit warning to the Core Orchestrator (or the relevant human gate) rather than silently truncating. Silent truncation is exactly the class of invisible failure the rest of this pipeline is built to avoid everywhere else — Baseline Guard's anti-deletion check, `GateResult`'s explicit pass/fail, deterministic-first triage. The Context Gatherer shouldn't be the one place in the system that fails quietly.
