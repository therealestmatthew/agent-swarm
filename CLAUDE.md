# Agentic SDLC Orchestration

## What we're trying to accomplish

**A specified, governed pipeline of AI agents that takes a software change from plan to production,
where every generated artifact is checked by a different agent than produced it.**

The thesis is that agent pipelines fail in predictable ways — context rot, merge conflicts on
"disjoint" work, infinite adversarial loops, unbounded spend, silent truncation — and that each of
those has a structural answer rather than a prompt-engineering one. The design encodes those
answers.

**We are in design, not build.** `plan/` is the source of truth and the current work is refining it.
Do not start implementing agents, services, or schemas until the design settles and this line
changes.

## Where things live

| Path | What it is |
|---|---|
| `plan/agentic-sdlc-design-v0.4.md` | The orchestration blueprint — principles, agent roster, the eight phases. **Read first.** |
| `plan/agent_interface_contracts.py` | Every schema exchanged between agents. Single source of truth. |
| `plan/infra_triage_matrix.md` | The deterministic failure-classification rules engine |
| `plan/test_harness_architecture.md` | Baseline capture and Protocol-fake test double standards |
| `plan/context_retrieval_strategy.md` | Context Gatherer search heuristics and token budgets |
| `plan/budget_and_escalation_policy.md` | Loop ceilings, the escalation ladder, cost ceilings |
| `plan/structural_change_runbook.md` | Human-gated SOP for non-additive shared-file changes |
| `plan/agentic_sdlc_glossary.csv` | Term definitions used across the set |
| `archive/glass-box/` | The hackathon project this grew out of. Frozen — see its README. |

v0.4 deliberately split mechanics out of the blueprint into companion files. Keep that split: if a
threshold, schema, or capture rule is being written into the core document, it belongs in a
companion instead.

## Principles that shape every decision

These are the design's own, condensed. When a proposal conflicts with one of these, the principle
wins unless the proposal argues explicitly for changing it.

1. **Maker/Checker.** Every agent that generates an artifact is paired with a different agent that
   validates it. No agent reviews its own output.
2. **Deterministic before LLM.** Anything classifiable from structured signals is classified by a
   fixed rules engine; an LLM sees only the ambiguous residue. Applies to failure triage and to
   shared-file intents alike.
3. **Shared state is governed, not merged.** Registered shared files change only through a closed
   vocabulary of typed additive intents, applied by a deterministic service. Anything non-additive
   exits through the Structural Change SOP.
4. **Merge conflicts are decomposition errors.** A conflict is evidence the Task Decomposer drew
   boundaries wrong — never something the PR Reviewer resolves, and never an infinite retry.
5. **Every loop is bounded.** Repeated failure signals a problem upstream of the current step, so
   retrying indefinitely spends budget without addressing the cause.
6. **Human gates at irreversible or judgment-heavy points**, and they are not delegable to an agent:
   plan approval, Contract Freeze, shared-file registration and promotion, invariant deprecation,
   structural changes, QA→Prod.
7. **Nothing fails silently.** Explicit `GateResult` verdicts, context overflow warnings rather than
   truncation, ceiling halts that never auto-resume, anti-deletion checks on the test suite.

## Working agreements

- **Docs before build.** The current phase is plan refinement. Changes land as design edits, not
  code.
- **Schemas live in one place.** `plan/agent_interface_contracts.py` is the only home for a schema.
  Two agents inventing two slightly different shapes for one thing is the drift the whole
  shared-file design exists to prevent — don't reintroduce it at the type level.
- **Pydantic v2, `extra="forbid"`, `frozen=True`** on every model. Agents produce new instances
  rather than mutating shared state.
- **Say what's unresolved.** Several thresholds in the set are explicitly illustrative
  (cost ceilings, context budgets, the additive-intent threshold, decay tuning). Don't present them
  as decided, and don't quietly harden one without saying so.
- **Don't assert what you haven't run.** Carried over from the archived project, where two review
  passes found claims the code didn't support.

## Open questions

Tracked in `plan/agentic-sdlc-design-v0.4.md` §8, and live:

- **Enterprise invariant arbitration** — who arbitrates when two repos disagree about whether an
  `enterprise_wide` invariant still holds. Carried unresolved since v0.3.
- **Decay tuning** — the −1-per-clean-phase conflict counter decay is untested against real
  promotion data.
- **Structural Change SOP cadence** — repeated triggering against one file may itself be a
  governance signal.
- **Modular file versioning** — do the companion files version independently of the blueprint?

Known drift to resolve: `plan/infra_triage_matrix.md:3` and `plan/structural_change_runbook.md:3`
and `:43` still reference `agentic-sdlc-design-v0.3.md`, which isn't in the set. Also
`infra_triage_matrix.md` §1 says the baseline capture method is unfinalized, but
`test_harness_architecture.md` §1 finalized it — that note is stale.

## Deliberately out of scope, for now

- **Visualization.** The archived Glass Box board made a running swarm watchable and won the
  hackathon, but it is not part of this design. It may return as an **agent health and monitoring
  dashboard** once the pipeline is real. If it does, the reusable parts are listed in
  `archive/glass-box/README.md` — and note that the board has no concept of a phase or a human
  gate, which an ops dashboard for this pipeline would need.
