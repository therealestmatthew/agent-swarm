---
title: "Remediation Plan: Medium Findings (M1 - M6)"
status: live
part_of: repo-meta
doc_type: reference
layer: adapter-sdlc
---

# Remediation Plan: Medium Findings (M1 - M6)

## M1: CSV Glossary Maintenance

### Finding
`agentic_sdlc_glossary.csv` is cumbersome to review in PRs and prone to drift.

### Root Cause
CSV diffs are difficult to review in standard version control interfaces. Because the terminology is disconnected from the codebase and primary markdown documentation, developers experience high friction when trying to keep the glossary synchronized as the 8-phase pipeline evolves.

### Remediation
Convert the CSV glossary into a structured Markdown document. This format integrates cleanly with GitHub/GitLab PR diffs and fits naturally alongside the rest of the `plan/` documentation.

**File Changes:**
1. **`plan/agentic_sdlc_glossary.csv`**: Delete file.
2. **`plan/agentic_sdlc_glossary.md`**: Create file. Organize the 64 terms alphabetically with standard Markdown headings for enhanced readability.

### Required Document Updates
- `agentic-sdlc-design-v0.5.md`: Update all references pointing to the glossary to target the new `.md` extension.

### Open Questions
- Should we eventually extract glossary terms directly from docstrings of key Pydantic schemas (e.g., in `agent_interface_contracts.py`) to guarantee perfect synchronization with code?

---

## M2: Competing Inventory Files

### Finding
`AGENTIC_ARCHITECTURE_MANIFEST.md` and `FRONTMATTER_MANIFEST.md` overlap in defining architectural state.

### Root Cause
The system lacks a clear demarcation between structural architecture definitions (the 23 agents, 8 phases) and documentation metadata rules. As a result, both files attempt to catalog the agents, leading to duplicated state and synchronization failures.

### Remediation
Define explicit boundaries: `AGENTIC_ARCHITECTURE_MANIFEST.md` acts as the single source of truth for the pipeline and agent inventory. `FRONTMATTER_MANIFEST.md` will strictly define the frontmatter schema required for all `plan/` documents.

**File Changes:**
1. **`AGENTIC_ARCHITECTURE_MANIFEST.md`**: Retain agent and phase inventories. Remove any frontmatter enforcement rules.
2. **`FRONTMATTER_MANIFEST.md`**: Strip all agent inventory lists. Redefine entirely as a schema definition for required YAML frontmatter blocks.
3. **`scripts/check_frontmatter.py`** & **`scripts/sync_counts.py`**: Update to pull the metadata schema solely from `FRONTMATTER_MANIFEST.md` and the agent list from `AGENTIC_ARCHITECTURE_MANIFEST.md`.

### Required Document Updates
- None aside from the manifests themselves.

### Open Questions
- Should `check_frontmatter.py` automatically inject missing default frontmatter blocks based on the schema during CI?

---

## M3 & M4: Context Retrieval Optimization

### Finding
Vector search struggles with custom DSLs. Furthermore, the mandatory "broad-then-narrow" search imposes unnecessary sequential latency when target files are already known.

### Root Cause
Vector embeddings inherently prioritize natural language semantic similarity, causing them to perform poorly on syntax-heavy custom DSLs. The mandatory two-step "broad-then-narrow" search assumes the agent is always discovering context, penalizing scenarios where the agent already knows exactly which file or symbol it needs to access.

### Remediation
Introduce a lexical/symbol lookup bypass mechanism and add specialized lexical indexing for custom DSLs. This allows agents to bypass vector search entirely when exact paths or symbols are known.

**File Changes:**
1. **`plan/agent_interface_contracts.py`**: Add a new exact-match bypass schema.
```python
from pydantic import BaseModel, Field

class ExactSymbolLookup(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    file_path: str = Field(..., description="Exact relative path to the target file")
    symbol_name: str = Field(..., description="Exact class, function, or variable name to retrieve")
```

### Required Document Updates
- `plan/context_retrieval_strategy.md`: Add a new section detailing the lexical/symbol bypass strategy. Update search heuristics to specify that agents should default to `ExactSymbolLookup` when the target is deterministic.
- `agentic-sdlc-design-v0.5.md`: Note the addition of the new retrieval path.

### Open Questions
- How frequently should the lexical index be rebuilt during an active execution pipeline to ensure agents have up-to-date symbol resolution without exceeding cost budgets?

---

## M5: Hermeticity Verification Cost

### Finding
Randomized test order execution is combinatorial for large suites, creating excessive costs ($5-50/run budget pressure).

### Root Cause
Hermeticity verification currently attempts to run full suites in randomized orders to catch state-leakage. With an 8-phase pipeline, this combinatorial explosion exceeds standard compute budgets and adds excessive latency to the execution isolation phase.

### Remediation
Scope randomized execution exclusively to the changed test subsets (e.g., determined by AST diffing) or move full combinatorial runs to a periodic asynchronous pipeline.

**File Changes:**
1. **`plan/agent_interface_contracts.py`**: Add schema to configure test scope limits.
```python
from pydantic import BaseModel, Field

class HermeticityTestScope(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    max_permutations: int = Field(3, description="Maximum test permutations to run")
    target_changed_only: bool = Field(True, description="Limit randomization to changed subsets")
```

### Required Document Updates
- `plan/test_harness_architecture.md`: Update §1.2 (fresh construction) to enforce dependency-graph based scoped test execution rather than full suite randomization.
- `plan/core_adapter_boundary.md`: Clarify that Adapters should cache state resets based on target isolation requirements.
- `budget_and_escalation_policy.md`: Add explicit maximum compute caps for hermeticity verification.

### Open Questions
- What is the fallback mechanism if AST-diffing fails to accurately identify dependent tests for a modified file?

---

## M6: DOM Baseline False Positives

### Finding
Async browser events dirty the DOM state, misclassifying logic bugs as infrastructure failures based on DOM diffs.

### Root Cause
The `dom_state_diff_from_baseline` rule performs strict diffs on the DOM. Async operations (hydration, third-party scripts) cause non-deterministic mutations. The triage matrix interprets these fluctuations as infrastructure/environment deviations.

### Remediation
Standardize hydration quiescence checks before capturing the DOM, and introduce a filter to strip volatile, non-semantic attributes before comparison.

**File Changes:**
1. **`plan/agent_interface_contracts.py`**: Update baseline capture schema.
```python
from pydantic import BaseModel, Field

class DOMCaptureConfig(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    
    await_hydration_ms: int = Field(5000, description="Minimum time to wait for quiescence")
    ignore_selectors: list[str] = Field(default_factory=list, description="CSS selectors to exclude from baseline diff")
```

### Required Document Updates
- `plan/test_harness_architecture.md`: Update §1.4 (baseline) to mandate the use of `DOMCaptureConfig` and define "quiescence".
- `plan/infra_triage_matrix.md`: Modify the `dom_state_diff_from_baseline` rule to require filtering of volatile elements prior to triggering an infrastructure escalation.

### Open Questions
- How do we handle applications that utilize continuous animations where "quiescence" is never truly reached?
