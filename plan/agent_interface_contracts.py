"""
agent_interface_contracts.py

Single source of truth for all schemas exchanged between agents in the
Agentic SDLC Orchestration pipeline. Referenced by:
  - agentic-sdlc-design-v0.5.md (core orchestration blueprint)
  - infra_triage_matrix.md (FailureSignature)
  - budget_and_escalation_policy.md (GateResult, used in the escalation ladder)
  - test_harness_architecture.md (FailureSignature capture rules)
  - calibration_and_measurement.md (GateResult.reviewer_spec_version)
  - core_adapter_boundary.md (ProjectManifest and the adapter contract)

Conventions: Pydantic v2, `extra="forbid"`, `frozen=True` on every model.
Every model is immutable once constructed — agents produce new instances
rather than mutating shared state, matching the pipeline's broader
"typed, additive, deterministic" governance philosophy (design doc §4, §10).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared-File Additive Intents  (design doc §4.2)
# ---------------------------------------------------------------------------


class AddExport(BaseModel, frozen=True):
    """Register a new named export from a module in a shared export barrel."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["add_export"] = "add_export"
    name: str
    source_module: str


class AddRoute(BaseModel, frozen=True):
    """Register a new route on a shared router."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["add_route"] = "add_route"
    path: str
    handler: str
    middleware: list[str] = Field(default_factory=list)


class AddProviderBinding(BaseModel, frozen=True):
    """Register a new binding in a shared DI container."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["add_provider_binding"] = "add_provider_binding"
    interface: str
    implementation: str
    scope: Literal["singleton", "transient", "scoped"]


# Discriminated union so the Shared-File Intent Service can route an intent
# to the correct AST transformer (design doc §4.4) on `op` without an
# isinstance() chain.
AdditiveIntent = AddExport | AddRoute | AddProviderBinding


# ---------------------------------------------------------------------------
# Run Manifest  (design doc §3; reinstated from v0.1 §3.1, absent v0.2-v0.4)
# ---------------------------------------------------------------------------
#
# The Core Orchestrator's entire context. Never a plan body, never a diff — only this
# plus a reference to the event log. Persisted after every phase transition; a crashed
# run resumes from the last recorded phase. Because every model here is frozen, a
# transition produces a NEW RunManifest rather than mutating the current one, which is
# what makes "resume from the last recorded phase" well-defined in the first place.


class Phase(str, Enum):
    """The eight phases design doc §3 walks through, as one enum so a RunManifest's
    `phase` field can only ever hold a value the blueprint actually defines."""

    PLANNING = "planning"                  # Phase 1
    DECOMPOSITION_TDD = "decomposition_tdd"  # Phases 2 & 3
    PARALLEL_SWARM = "parallel_swarm"      # Phase 4
    INTEGRATION = "integration"            # Phase 5
    VERIFICATION = "verification"          # Phase 6
    PROMOTION = "promotion"                # Phases 7 & 8 (draft PR through QA->Prod)
    OBSERVATION = "observation"            # Phase 8 (post-merge)


class HaltReason(str, Enum):
    """Why a run is currently halted. Ceiling Halt (§7/Budget Accountant) and Boundary
    Failure (Principle 8) are the two the design already names; HUMAN_GATE covers every
    gate in design doc §9.3 that is currently awaiting sign-off."""

    CEILING_HALT = "ceiling_halt"
    BOUNDARY_FAILURE = "boundary_failure"
    HUMAN_GATE = "human_gate"
    # Adapter-contract halts (core_adapter_boundary.md §3.1-3.2). Both are refusals to
    # proceed rather than degradations: an invalid or mid-run-mutated manifest means Core
    # does not know what rules it is enforcing, which is never a condition to continue under.
    ADAPTER_INVALID = "adapter_invalid"
    ADAPTER_DIGEST_MISMATCH = "adapter_digest_mismatch"


class RunManifest(BaseModel, frozen=True):
    """Reinstated from v0.1 §3.1. The Core Orchestrator reads this, decides the next
    phase, dispatches the responsible agent, and persists a new instance — it never
    mutates this one. See agentic-sdlc-design-v0.5.md §3 for the resumability argument."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    phase: Phase
    event_log_ref: str  # pointer, never inlined content -- Principle 2
    halt_reason: HaltReason | None = None
    active_task_ids: list[str] = Field(default_factory=list)
    # Content digest of the ProjectManifest this run started under (core_adapter_boundary.md
    # §3.1). Pinned so a mid-run edit to the target repo's manifest cannot change the gates,
    # test commands, or write scopes under a pipeline that is already executing: Core halts on
    # a digest mismatch rather than adopting the new manifest. Optional and additive, so a run
    # recorded before the adapter contract existed still validates.
    adapter_digest: str | None = None


# ---------------------------------------------------------------------------
# Adapter Contract  (core_adapter_boundary.md)
# ---------------------------------------------------------------------------
#
# How a target repo declares its constraints to the Core Orchestrator. Core owns every
# mechanism in this system; the adapter owns every noun. A ProjectManifest is the whole of
# what one repo is allowed to say about itself.
#
# SECURITY: this file names test commands, bootstrap commands, and transformer entry points
# -- it is arbitrary code execution declared by the repo being operated on. It is a
# registered shared file outside every agent's write scope (Principle 12), a change to it is
# a human gate, and it is digest-pinned into the RunManifest for the duration of a run. See
# core_adapter_boundary.md §3.1.


class IsolationUnit(str, Enum):
    """The unit a task is executed inside. `execution_isolation.md` §5's escape condition --
    a task whose tests bind a port or reach a real service -- is answered here by declaration
    rather than discovered at runtime."""

    WORKTREE = "worktree"
    CONTAINER = "container"


class Capability(str, Enum):
    """Declared, never inferred. Core refuses to guess whether a repo supports something."""

    SHARED_FILE_GOVERNANCE = "shared_file_governance"
    MUTATION_TESTING = "mutation_testing"
    HYDRATION = "hydration"
    BROWSER_TIER = "browser_tier"
    COVERAGE = "coverage"


class AbsentCapabilityPolicy(str, Enum):
    """What Core does when a phase needs a capability the manifest does not declare. There is
    deliberately no option meaning "carry on and say nothing" -- silently falling back to
    ordinary git merges on shared files is a return to the failure mode design doc §4 exists
    to prevent, and it would be invisible (Principle 7)."""

    REFUSE = "refuse"    # the run does not start
    DEGRADE = "degrade"  # the run proceeds; the degradation is recorded and surfaced at the PR


class TestTier(BaseModel, frozen=True):
    """One runnable tier of a repo's suite. `hermetic` is what makes `mutation.diff_scoped`
    decidable instead of universally-blocking-or-waived: the gate applies to hermetic tiers
    and is not claimed of the others."""

    model_config = ConfigDict(extra="forbid")

    name: str
    command: list[str]
    hermetic: bool
    isolation_unit: IsolationUnit
    satisfies_gates: list[str] = Field(default_factory=list)  # gate ids from design doc §9.1


class IntentOpSpec(BaseModel, frozen=True):
    """One Additive Intent operation this repo accepts, and the fields Core arbitrates on.

    `collision_keys` is the whole of Core's collision predicate: two pending intents for the
    same op collide iff they match on every listed key. Deliberately under-powered -- Core
    does not execute an adapter-supplied predicate, because that would move arbitration into
    untrusted repo-declared code. See core_adapter_boundary.md §2.1."""

    model_config = ConfigDict(extra="forbid")

    op: str
    collision_keys: list[str]
    transformer_id: str


class SignalSpec(BaseModel, frozen=True):
    """Declares one key admissible in FailureSignature.signals for this repo."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value_type: Literal["bool", "int", "str"]


class TriageRule(BaseModel, frozen=True):
    """One row of this repo's triage matrix. Core owns the evaluator (ordered, first-match-
    wins, non-matches fall through to the Test Investigator); the rows are adapter data
    written over that adapter's declared signals. infra_triage_matrix.md is the reference rule
    set for a browser-automation adapter, not the engine."""

    model_config = ConfigDict(extra="forbid")

    order: int
    when: str            # expression over declared signal names and envelope fields
    classification: str
    routes_to: Literal["infra_queue", "task_dev", "test_investigator"]


class SecretSpec(BaseModel, frozen=True):
    """A credential the run requires, by name and scope only. A value never appears in a
    manifest, on a worktree filesystem, or in an agent's context (core_adapter_boundary.md §5)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    scope: Literal["task", "integration", "promotion"]


class ProjectManifest(BaseModel, frozen=True):
    """The adapter contract. Validated before a run starts; an invalid manifest is a refusal
    to start, not a warning (Principle 7)."""

    model_config = ConfigDict(extra="forbid")

    # Versions independently of the blueprint -- target repos upgrade on their own cadence,
    # which is the one case design doc §12's "modular file versioning" question must answer.
    manifest_version: str
    repo_id: str

    capabilities: list[Capability]
    absent_capability_policy: AbsentCapabilityPolicy

    # Execution & environment
    isolation_unit: IsolationUnit
    image_ref: str | None = None          # required when isolation_unit is CONTAINER
    bootstrap: list[list[str]] = Field(default_factory=list)
    declared_ports: list[int] = Field(default_factory=list)
    # Core divides available resources by this to derive the concurrency ceiling, then takes
    # the minimum against API rate limits and review throughput -- turning design doc §12's
    # open question into arithmetic. See core_adapter_boundary.md §3.3.
    resource_footprint_mb: int

    # Verification
    test_tiers: list[TestTier] = Field(default_factory=list)
    hydration_fixture_ids: list[str] = Field(default_factory=list)

    # Vocabulary & transforms
    intent_vocabulary: list[IntentOpSpec] = Field(default_factory=list)
    registered_shared_files: list[str] = Field(default_factory=list)

    # Telemetry
    signals: list[SignalSpec] = Field(default_factory=list)
    triage_rules: list[TriageRule] = Field(default_factory=list)

    # Secrets -- names and scopes, never values
    required_secrets: list[SecretSpec] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Invariant Curator  (design doc §5)
# ---------------------------------------------------------------------------


class InvariantScope(str, Enum):
    """Determines how a stored invariant's zero-hit deprecation window is computed.

    REPO_LOCAL: zero-hit window measured against usage in a single repo.
    ENTERPRISE_WIDE: zero-hit window measured across every repo the
    manifest serves — a single repo's disuse does not by itself make an
    enterprise-wide invariant a deprecation candidate.
    """

    REPO_LOCAL = "repo_local"
    ENTERPRISE_WIDE = "enterprise_wide"


# ---------------------------------------------------------------------------
# Failure Triage  (infra_triage_matrix.md §1)
# ---------------------------------------------------------------------------


class FailureSignature(BaseModel, frozen=True):
    """
    Captured by the test harness at the moment of failure — never
    reconstructed later from logs or stack traces. See
    test_harness_architecture.md for exact capture rules, especially
    for `dom_state_diff_from_baseline`.
    """

    model_config = ConfigDict(extra="forbid")

    error_class: str
    elapsed_ms: int
    configured_timeout_ms: int | None
    isolated_rerun_outcome: Literal["passed", "failed_again", "not_yet_run"]

    # Adapter-declared telemetry (core_adapter_boundary.md §2.2). Keys and value types are
    # declared by the target repo's ProjectManifest.signals and validated against it on
    # capture; the triage rules that read them are adapter data too. This exists because an
    # adapter cannot add fields to an extra="forbid" model without forking the schema per
    # repo -- exactly the drift this file exists to prevent.
    signals: dict[str, bool | int | str] = Field(default_factory=dict)

    # The two fields below are one adapter's signals, currently hard-coded into the universal
    # envelope. They belong in `signals`. Relocating them is a non-additive schema change and
    # goes through structural_change_runbook.md like any other -- so `signals` lands first,
    # additively, and these stay until that gate is cleared.
    dom_state_diff_from_baseline: bool
    network_calls_over_threshold: int


# ---------------------------------------------------------------------------
# Validator Output  (new in v0.4 — standardizes every Validator's return shape)
# ---------------------------------------------------------------------------


class Finding(BaseModel, frozen=True):
    """A single issue raised by a Validator agent."""

    model_config = ConfigDict(extra="forbid")

    severity: Literal["blocking", "advisory"]
    message: str
    evidence_ref: str  # e.g. "diff:src/foo.py#L42", "log:run_id/line_88"


class GateResult(BaseModel, frozen=True):
    """
    Standard return shape for every Validator agent (Plan Reviewer, Code
    Reviewer, Security Review, PR Reviewer, Baseline Guard, etc.).

    `passed` reflects blocking findings only — advisory findings never
    flip it to False, but should still surface to whoever consumes the
    result.
    """

    model_config = ConfigDict(extra="forbid")

    reviewer: str
    passed: bool
    findings: list[Finding] = Field(default_factory=list)
    # Reinstated from v0.1 §8 ("Version the agent specs"). Without this, changing a
    # reviewer's prompt silently invalidates every precision/recall number gathered
    # against its old behavior -- see calibration_and_measurement.md. Optional and
    # additive, so this does not break any GateResult already in a verdict ledger.
    reviewer_spec_version: str | None = None

    @property
    def blocking_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocking"]
