---
title: Agentic Architecture Manifest
status: live
part_of: repo-meta
doc_type: manifest
---

# Agentic Architecture Manifest

A complete inventory of every file in this repository, as of `plan/agentic-sdlc-design-v0.5.md`.
57 tracked files, spanning two projects: the live Agentic SDLC design (`plan/`) and the frozen
hackathon project it grew out of (`archive/glass-box/`). Repo history runs 2026-08-25 to present.

**Reading this table:** *Description* is what the file literally is (form/type). *Summary* is what's
actually in it. *Purpose* is the job it does in the larger system — why it exists at all.

This file is a snapshot, not a live view — it will drift the moment a new file is added. Regenerate
it (or at least re-diff `git ls-files` against it) whenever the file set changes materially, the
same discipline `plan/versions/REGRESSION.md` exists to enforce for the design content itself.

---

## Root

| File | Description | Summary | Purpose |
|---|---|---|---|
| `CLAUDE.md` | Instructions file for an AI agent working in this repo | States the project's goal, the seven design principles, working agreements (schemas live in one place, thresholds stay labelled illustrative), open questions, and a file-location table | Onboards a future agent (or person) cold — the one file that must never drift out of sync with what's actually true of the repo |
| `.gitignore` | Git ignore rules | Excludes `__pycache__/`, build artifacts, and `archive/glass-box/`'s regenerable run output and demo parachute | Keeps generated/derived files out of version control without needing per-directory rules |
| `AGENTIC_ARCHITECTURE_MANIFEST.md` | This file | Full file-by-file inventory of the repository | The single index a newcomer (or an agent with no session memory) reads to know what exists before reading anything else |
| `FRONTMATTER_MANIFEST.md` | Generated Markdown, front matter present | Every tracked doc's `title`/`status`/`part_of`/`doc_type`/`version` in one table, plus per-status/per-type summary counts | Machine-checkable proof every doc has valid front matter — regenerated on every commit, never hand-edited |

---

## `scripts/` and `.githooks/` — Repo Tooling

Keeps this manifest, `FRONTMATTER_MANIFEST.md`, and every count-bearing sentence in the live docs
honest without relying on anyone remembering to update them by hand.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `scripts/frontmatter.py` | Python module, stdlib only | Minimal front-matter parser/serializer for this repo's actual schema — not a general YAML library, the same "contract is the file format" tradeoff `archive/glass-box/glassbox/events.py` made | Shared by the other two scripts so front matter is read and written exactly one way |
| `scripts/check_frontmatter.py` | Python CLI | Backfills missing front matter (title from the H1, status/part_of/doc_type from a curated table plus path-based rules, `superseded_by` recomputed from the actual version chain every run), then writes `FRONTMATTER_MANIFEST.md` | Guarantees every doc is self-describing; fails loudly on a doc with no H1 rather than guessing a title |
| `scripts/sync_counts.py` | Python CLI | A registry of every live count assertion in `plan/` and root docs (glossary terms/categories, tracked file count, principle/section/agent-roster counts, companion file count) and how to recompute each one, with a regex per place it's asserted in prose | Deterministically rewrites a drifted number in place — this is what caught the manifest's own "48 tracked files" going stale the moment it was committed |
| `scripts/install-hooks.sh` | Bash script | Sets `core.hooksPath` to `.githooks` and makes the hook executable | One command to activate the hook after cloning, since `.git/hooks/` isn't tracked and can't ship with the repo directly |
| `.githooks/pre-commit` | Bash hook, tracked | Runs both Python scripts on every commit across the whole repo, re-stages whatever they fix, aborts the commit with a specific message if either hits something no rule can fix deterministically | The enforcement point — without it, both scripts are just tools someone has to remember to run |

---

## `plan/` — Live Design (v0.5)

The current source of truth. `CLAUDE.md`'s own rule governs everything here: mechanics (thresholds,
schemas, capture rules) belong in a companion file, never inline in the core blueprint.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `agentic-sdlc-design-v0.5.md` | Core orchestration blueprint, Markdown, 12 sections | 12 principles → 23-agent roster → 8 phases → Shared-File Governance → Invariant deprecation → Failure triage → Circuit breakers → Execution Isolation → Gates → Anti-Reward-Hacking → Calibration → Open Questions | The one document that states *how the pipeline is shaped*; every companion file exists to keep this one legible by holding the mechanics elsewhere |
| `plan/contracts/__init__.py` | Python package init, Pydantic v2 | Defines `BaseContract` (frozen + extra=forbid config) and re-exports every public model so `from plan.contracts import GateResult` works | Single canonical import namespace across the plan docs and future consumers, without giving up per-module domain ownership |
| `plan/contracts/orchestration.py` | Pydantic v2 module, frozen models | Core Orchestrator state: `RunManifest`, `Phase`, `HaltReason`; shared-file intent outcome envelope: `IntentOutcome`, `IntentRejection` | Core is standalone — this module does not import from `governance`, `verification`, or `reference_adapter/` (see `core_adapter_boundary.md` §3) |
| `plan/contracts/governance.py` | Pydantic v2 module, frozen models | Adapter contract: `RepoDeclaration` + `GovernancePolicy` plus every sub-model they compose (`IsolationUnit`, `Capability`, `AbsentCapabilityPolicy`, `ResetResource`, `ResetStrategy`, `TestTier`, `IntentOpSpec`, `SignalSpec`, `TriageRule`, `SecretSpec`) | Adapter contract lives in one place; the declaration/policy split (`core_adapter_boundary.md` §3) is expressed as two top-level models with shared sub-models |
| `plan/contracts/verification.py` | Pydantic v2 module, frozen models | Validator return shapes (`GateResult`, `Finding`, `GateApplicability`), failure-triage capture (`FailureSignature`), invariant scope enum (`InvariantScope`) | Every Validator agent returns a `GateResult`; the shape lives with the other verification-layer contracts, not scattered across the pipeline |
| `plan/contracts/reference_adapter/__init__.py` | Python package init | Reference adapter sub-package marker; docstring names the boundary rule (Core does not import from here) | Package boundary that keeps `core_adapter_boundary.md` §3 enforceable at import time as well as in prose |
| `plan/contracts/reference_adapter/web_intents.py` | Pydantic v2 module, frozen models | Web-adapter additive-intent vocabulary: `AddExport`, `AddRoute`, `AddProviderBinding`, plus the `AdditiveIntent` union | D2 resolution — repo-specific intents live in a reference adapter rather than in the universal contracts file, so a non-web adapter can declare its own vocabulary without editing Core |
| `agentic_sdlc_glossary.csv` | CSV, 4 columns (Term, Definition, Category, Tags) | 64 defined terms spanning 12 categories, from `Additive Intents` to `Zero-hit Invariant` | Formal vocabulary for the whole design set — every term used in more than one document is defined exactly once here |
| `budget_and_escalation_policy.md` | Markdown companion | Loop ceilings (`max_retries=3` per loop-back edge), the 4-rung escalation ladder, Budget Accountant cost ceilings | Owns the exact thresholds `agentic-sdlc-design-v0.5.md` §7 only names in principle |
| `context_retrieval_strategy.md` | Markdown companion | Context Gatherer search heuristics (`git log -S`/blame vs. vector search, broad-then-narrow default), per-consumer token budgets, overflow handling | Owns Context Gatherer mechanics referenced but not detailed in §3 |
| `core_adapter_boundary.md` | Markdown companion | The Core/Adapter split, the three places a naive reading of it leaks (collision predicates, telemetry schema, triage rules), the `RepoDeclaration`/`GovernancePolicy` contract split (a field is a declaration if a false value punishes the declarer, policy if it rewards them) and its governance, capability negotiation, hydration, credential injection and boundary scrubbing, and how "universal" is made falsifiable | Turns "general-purpose orchestrator" from a claim into a checkable seam — the file that keeps one repo's specifics out of the Core |
| `execution_isolation.md` | Markdown companion, new in v0.5 | One git worktree per task; why disjoint write ownership alone doesn't isolate reads; lifecycle; when containers become necessary; and (§7) shared-file materialization — canonical branch, `skip-worktree` overlay, atomic re-materialization, synthesized delta view, and the constraints on intent transport | Reinstates v0.1 §6, which had no home in v0.2–v0.4: verification is repo-scoped even when editing is file-scoped |
| `calibration_and_measurement.md` | Markdown companion, new in v0.5 | Verdict ledger schema, Shadow Mode promotion criteria (illustrative), agent-spec versioning, cost-per-pair tracking | Reinstates v0.1 §8 — gives Shadow Mode (Agent Roster) an actual exit path; previously "calibrated against a baseline" named a baseline that didn't exist anywhere |
| `implementation_roadmap.md` | Markdown roadmap | Critique of the submitted implementation backlog, a defects table of contradictions found between live design files, the items the backlog omitted, and a six-stage build sequence keyed to the CPMI proving ground | Turns the design set into an ordered build plan — the first document here that describes work rather than architecture, and the one that states the release condition for `CLAUDE.md`'s design-not-build gate |
| `infra_triage_matrix.md` | Markdown companion | The deterministic `FailureSignature` rules engine — ordered rule table separating infra-class failures from logic failures before any LLM sees a failure | Owns the failure-classification mechanics `agentic-sdlc-design-v0.5.md` §6 only references |
| `structural_change_runbook.md` | Markdown runbook | Human-gated SOP for non-additive shared-file changes: triggers, who's involved, the pause/propose/re-decompose/resume procedure | The escape hatch for changes too large to express as an Additive Intent |
| `test_harness_architecture.md` | Markdown companion | Baseline capture rules (full teardown/rebuild, never surgical clearing), Protocol-fake test double standards, and (new in v0.5) diff-scoped mutation testing | Owns the verification-layer mechanics that make a passing test mean something |

---

## `plan/versions/` — Superseded Design History

Every prior version, kept rather than discarded, plus the analysis that compares them. Nothing here
is live guidance — `CLAUDE.md` and the live `plan/` files are current; this is the record of how they
got here.

| File | Description | Summary | Purpose |
|---|---|---|---|
| `REGRESSION.md` | Markdown analysis | v0.1-to-v0.4 diff: 9 load-bearing gaps found (validator asymmetry, worktree isolation, mutation testing, the Run Manifest, calibration, permissions-not-prompts, reward-hacking framing, 5 dropped open questions, build order), each with a verified quote and a keep/reinstate/hold call | The evidence behind v0.5's changelog — catches the exact failure mode it describes: v0.2's changelog documented six additions and zero removals |
| `agentic-sdlc-design-v0.1.md` | Markdown, original design proposal | 18 principles, 18-agent roster, full detail per agent (validator asymmetry, worktree isolation, `mutation.diff_scoped`, the Run Manifest, a verdict ledger) | The most detailed version ever written; roughly half its content didn't survive to v0.2 and is being selectively reinstated as of v0.5 |
| `agentic-sdlc-design-v0.2.md` | Markdown, versioned design doc | Adds the Shared-File Intent Service (typed additive intents replacing patch-based merges), Shared-File Registration, self-expanding governance, invariant deprecation, bounded loop ceilings | First version to introduce shared-state governance as a first-class mechanism; changelog documents only additions |
| `agentic-sdlc-design-v0.3.md` | Markdown, versioned design doc | Resolves all four v0.2 open questions: conflict-count promotion threshold, `InvariantScope` enum, infra-vs-logic triage split, the Structural Change SOP | Closes out v0.2's open questions cleanly — the one version whose changelog is fully honest about what it resolved |
| `agentic-sdlc-design-v0.4.md` | Markdown, versioned design doc | Pure reorganization: relocates schemas, thresholds, and capture rules out of the blueprint into `agent_interface_contracts.py` and four new companion files, changing no content | Established the "relocate mechanics, keep the blueprint legible" convention that `plan/`'s current structure — and this manifest's own organization — follows |

---

## `archive/glass-box/` — Frozen Hackathon Project

**Status: frozen.** Built for a 90-minute hackathon on the themes *agent swarms, always-on,
looping*; demoed in three minutes; won. Nothing here is live guidance for the current design work —
see `archive/glass-box/README.md` for what's worth reusing (four things) versus what's tied to demo
constraints that no longer apply.

### Documents

| File | Description | Summary | Purpose |
|---|---|---|---|
| `README.md` | Markdown, archive notice | Why it's frozen, what still runs, four reusable ideas, what not to carry forward, one flagged design gap (no concept of phase or human gate) | The entry point for anyone (or any agent) wondering why a working, award-winning project sits unused |
| `00-MASTER-PLAN.md` | Markdown, original plan | Architecture (one JSONL event log, pure-fold renderer), how the three hackathon themes land in one build, scope discipline, risk register | The founding document — states the "nothing renders from live agent state" invariant everything else depends on |
| `01-EVENT-SCHEMA.md` | Markdown, schema spec | The event envelope (8 fields), the full event-type table, five invariants, the reference `EventLog` implementation, concurrency options | The contract every emitter and the renderer both have to agree on |
| `02-DASHBOARD-DESIGN.md` | Markdown, visual design spec | The ATC dispatch-rack design direction, color/type tokens, layout, strip states and motion, replay modes | Documents the visual identity so it doesn't get silently redesigned |
| `03-AGENT-CONTRACTS.md` | Markdown, agent prompt templates | Dispatcher/Worker/Verifier/Reducer roles defined by the events each emits, plus filled prompt templates | Defines each swarm role by its event contract, not its internals — portable onto any payload |
| `04-TOMORROW-RUNBOOK.md` | Markdown, build runbook | Minute-by-minute plan for the 90-minute build, triage table, the one rule ("stop building at T+75") | Time-boxes the build so scope discipline survives contact with an actual clock |
| `05-DEMO-SCRIPT.md` | Markdown, demo script | Five-beat, 3-minute script with target timing per beat, on-stage failure fallbacks, anticipated Q&A | What was actually said on stage, word for word in places |
| `06-PAYLOAD-A-REPO-SWEEP.md` | Markdown, payload spec | Eight-lens repo risk sweep (Secrets, Validation, Error Paths, etc.), filled worker/verifier/reducer prompts, how the seeded verification failure was guaranteed | The primary demo payload actually used |
| `07-PAYLOAD-B-BUDGET-FALLBACK.md` | Markdown, payload spec | Budget-variance-hunt fallback payload, slice map, planted anomalies table, the "honeypot" timing-shift trap | The fallback payload prepared but not used — its honeypot finding is flagged as stronger than Payload A's |
| `08-ADVERSARIAL-REVIEW-PROMPT.md` | Markdown, review prompt | The exact prompt pasted into Claude Code to adversarially review the plan before building | Deliberately seeks the plan's own weaknesses rather than validating it |
| `09-REVIEW-FINDINGS.md` | Markdown, review findings | Response to `08`: kill shots (the agent_id="dispatch" bug, replay pacing, a seq-restart freeze, the payload-swap parachute cost), concrete defects, a cut list, deferred dependency enumeration | First adversarial pass; every finding here was verified against the code and (mostly) fixed in the same session |
| `10-SECOND-PASS.md` | Markdown, second review pass | A second adversarial pass (barred from re-reporting `09`'s findings) plus a design/visualization pass, both re-verified | Catches what the first review missed — 8 more silent failure modes, 4 places the board contradicted the demo script |
| `QUICKSTART.md` | Markdown, quickstart guide | Zero-install run commands, verified test/render claims, symptom table for common failures | The first file a new machine should run to confirm the parachute still works |

### Code

| File | Description | Summary | Purpose |
|---|---|---|---|
| `dashboard.html` | Single-file HTML/CSS/JS, ~478 KB (fonts embedded) | The board: a pure `state = events.reduce(apply, initialState())` fold, keyed-DOM renderer, live-poll and seeked-replay transports | The actual mission-control board — no build step, no dependencies, no network |
| `pyproject.toml` | Python project file | Declares the `glassbox` package with zero required dependencies; `validate` extra pulls in pydantic v2 | Makes `uv run` and a bare `python3 -m glassbox...` both work without an install step |
| `glassbox/__init__.py` | Python package init | Three-line package marker | Makes `glassbox` importable as a package |
| `glassbox/events.py` | Python module, dual pydantic-v2/dataclass implementation | `Event` model (frozen either way), `EventLog` writer (`emit`, `drain_outbox`), `read_log` | The event contract's actual implementation — degrades gracefully with no pydantic installed |
| `glassbox/simulate.py` | Python module, synthetic swarm | Generates a realistic 8-agent run with staggered spawns, a seeded verification failure and retry, a reducer pass, and an always-on second cycle | Produces the golden log — the entire dev loop and the demo parachute's source |
| `tests/fold.test.mjs` | Node test script, 18 assertions | Extracts the state fold straight out of `dashboard.html` at run time and asserts log integrity, schema invariants, purity, transport robustness, and seq-restart handling | Turns every "verified" claim in the docs into a command that can actually fail |
| `tools/beats.py` | Python CLI | Scans a run log and prints the `&from=<seq>` seek URL for every demo beat | Removes the need to hand-derive seek points from a JSONL file under stage pressure |
| `tools/save-parachute.sh` | Bash script | Saves `runs/current` to `logs/backup-live.jsonl`, keeps the previous parachute, refuses to overwrite a good one with a non-run | Turns the runbook's "save a real run as the parachute" step into one command |
| `tools/build-mobile-preview.py` | Python build script | Inlines the golden log and layers a narrow-viewport stylesheet plus touch playback controls onto a copy of `dashboard.html` | Produces `build/glassbox-mobile.html` — a phone-viewable, no-server-needed copy for review off a laptop |
| `tools/emit.mjs` | JavaScript module, paste-able emitter | `EventLog` class matching `glassbox/events.py`'s contract exactly, `agent_id` required and documented as "the agent this event is about, never whoever is writing it" | The nine-line emitter the docs promise for a non-Python starter repo |
| `tools/emit.ts` | TypeScript module, paste-able emitter | Same contract as `emit.mjs`, fully typed | TypeScript equivalent, for a starter repo that's typed |

### Data

| File | Description | Summary | Purpose |
|---|---|---|---|
| `fallback/generate_budget.py` | Python script, deterministic generator | Builds a 338-row budget-vs-actuals dataset with six planted anomalies (runaway overtime, unbudgeted spend, a duplicate posting, a credit misposting, an orphan account code, and a timing-shift "honeypot") | Regenerates Payload B's dataset byte-identically from one fixed seed |
| `fallback/budget_actuals.csv` | CSV, 338 rows | Program → Cost Center → Account → Period budget-vs-actual figures, six months, eight cost centers | The Payload B dataset workers actually read |
| `fallback/account_master.csv` | CSV, 7 rows | Valid account codes and categories | The join that makes an orphan-account-code finding mechanically checkable |
| `fallback/budget_actuals.xlsx` | Excel workbook | Same data as `budget_actuals.csv`, spreadsheet form | Excel-native copy of the same dataset |
| `fallback/account_master.xlsx` | Excel workbook | Same data as `account_master.csv`, spreadsheet form | Excel-native copy of the same dataset |

### Generated (gitignored patterns exist for these; committed anyway where noted)

| File | Description | Summary | Purpose |
|---|---|---|---|
| `logs/golden.jsonl` | JSONL, 96 events | The synthetic run `glassbox/simulate.py` produces — 14 agents, 17 findings, 1 rejection, 1 retry, 1 watch trigger, every demo beat timed to land inside `05-DEMO-SCRIPT.md`'s window | The board's replay parachute — committed deliberately, unlike a real-run parachute, since it's the fixture the whole demo was built and rehearsed against |
| `build/glassbox-mobile.html` | Single-file HTML, ~1,086 lines rendered, log inlined | Generated by `tools/build-mobile-preview.py`; renders correctly over `file://` with no server | Tracked (not gitignored) so the phone-viewable board serves straight from a checkout with no build step — goes stale if `dashboard.html` or the golden log change without a rebuild |
