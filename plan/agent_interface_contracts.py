"""
agent_interface_contracts.py

Single source of truth for all schemas exchanged between agents in the
Agentic SDLC Orchestration pipeline. Referenced by:
  - agentic-sdlc-design-v0.5.md (core orchestration blueprint)
  - infra_triage_matrix.md (FailureSignature)
  - budget_and_escalation_policy.md (GateResult, used in the escalation ladder)
  - test_harness_architecture.md (FailureSignature capture rules)
  - calibration_and_measurement.md (GateResult.reviewer_spec_version)
  - core_adapter_boundary.md (RepoDeclaration / GovernancePolicy, the adapter contract)

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
# Intent Submission Outcome  (design doc §4.5; execution_isolation.md §7)
# ---------------------------------------------------------------------------
#
# Smart Mutex Rejection has been named since v0.2 without a shape. This is it.
#
# SECURITY: `blocking_*` fields tell one agent what another agent claimed. They are structured
# data and never free-form text, because prose on this path is an injection channel between
# agents -- the receiving side renders these fields, it does not replay a message.


class IntentRejection(BaseModel, frozen=True):
    """Why an intent was refused, with enough context to resolve in one shot rather than
    restarting a planning cycle (design doc §4.5)."""

    model_config = ConfigDict(extra="forbid")

    reason: Literal[
        "collision",         # another pending/applied intent matches on every collision key
        "unmapped_anchor",   # no registered insertion point covers this -- a registration gap
        "not_registered",    # the target file is not in GovernancePolicy.registered_shared_files
        "op_not_declared",   # the op is absent from RepoDeclaration.intent_vocabulary
        "structural",        # exceeds the additive vocabulary -- exits via the SOP
    ]
    blocking_task_id: str | None = None
    blocking_op: str | None = None
    blocking_keys: dict[str, str] = Field(default_factory=dict)


class IntentOutcome(BaseModel, frozen=True):
    """Returned to the submitting agent, synchronously, before it continues. `applied_anchor`
    and `content_digest` are what the per-PR shared-file delta view is reconstructed from
    (execution_isolation.md §7.4), so the intent log is the audit record for content that
    appears in no task's diff."""

    model_config = ConfigDict(extra="forbid")

    intent: AdditiveIntent
    task_id: str
    target_file: str
    applied: bool
    applied_anchor: str | None = None   # where in the structural map it landed
    content_digest: str | None = None   # of the shared file after application
    rejection: IntentRejection | None = None


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
    # Adapter-contract halts (core_adapter_boundary.md §3.3-3.5). All three are refusals to
    # proceed rather than degradations: an invalid, mutated, or over-reaching contract means
    # Core does not know what rules it is enforcing, which is never a condition to continue
    # under. ADAPTER_POLICY_CONFLICT is the hard-conflict case -- a declaration asking for a
    # secret scope, capability, or model tier that policy does not grant.
    ADAPTER_INVALID = "adapter_invalid"
    ADAPTER_DIGEST_MISMATCH = "adapter_digest_mismatch"
    ADAPTER_POLICY_CONFLICT = "adapter_policy_conflict"


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
    # Content digests of the two adapter-contract artifacts this run started under
    # (core_adapter_boundary.md §3.4). Pinned so a mid-run edit to either cannot change the
    # gates, test commands, or write scopes under a pipeline that is already executing: Core
    # halts on a mismatch rather than adopting the new value. Optional and additive, so a run
    # recorded before the adapter contract existed still validates.
    declaration_digest: str | None = None
    policy_digest: str | None = None
    # Every place Core narrowed this run against policy: a clamped policy-bounded declaration,
    # a failed verification held to its conservative value, or a capability degraded under
    # `degrade`. Recorded rather than applied silently -- a run that was narrowed is a run
    # whose reviewer needs to know it was narrowed (Principle 7).
    policy_adjustments: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Adapter Contract  (core_adapter_boundary.md §3)
# ---------------------------------------------------------------------------
#
# How a target repo declares its constraints to the Core Orchestrator. Core owns every
# mechanism in this system; the adapter owns every noun.
#
# Deliberately TWO artifacts, not one. RepoDeclaration lives in the target repo and states
# facts about it; GovernancePolicy lives in the control plane and states what the pipeline
# will tolerate. The dividing test (core_adapter_boundary.md §3.1):
#
#     A field is a declaration if a false value PUNISHES the declarer.
#     It is policy if a false value REWARDS them.
#
# Lie about a test command and your own tests break. Un-block a gate and you gain while the
# org absorbs the risk. Two intermediate classes cover fields that are self-rewarding but
# genuinely repo-specific: policy-bounded declarations (Core clamps to a policy bound and
# records the clamp) and verified declarations (Core checks the claim empirically).
#
# SECURITY: RepoDeclaration names test commands, bootstrap commands, and transformer entry
# points -- arbitrary code execution declared by the repo being operated on. It is a
# registered shared file outside every agent's write scope (Principle 12), a change to it is
# a human gate, and both artifacts are digest-pinned into the RunManifest for the duration of
# a run. See core_adapter_boundary.md §3.4.


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
    and is not claimed of the others. Which gates actually block is GovernancePolicy's call,
    not this file's -- a repo declaring which gates it satisfies is a repo grading itself."""

    model_config = ConfigDict(extra="forbid")

    name: str
    command: list[str]
    isolation_unit: IsolationUnit
    # VERIFIED declaration (core_adapter_boundary.md §3.1): declaring a tier non-hermetic
    # exempts it from mutation.diff_scoped, which is self-rewarding -- so Core checks the
    # claim (run the tier isolated and in-suite under randomized order) rather than trusting
    # it. A tier that verifies as hermetic is held to the stricter gate regardless of what it
    # claimed, and the discrepancy is recorded.
    hermetic: bool


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
    """A credential, by name and scope only. A value never appears in either artifact, on a
    worktree filesystem, or in an agent's context (core_adapter_boundary.md §5).

    Used on both sides of a request/grant pair: RepoDeclaration.requested_secrets says what
    the repo needs, GovernancePolicy.granted_secrets says what it may have. Needing is not
    getting -- a task-scope agent requesting promotion scope is a refusal to start, not a
    config line."""

    model_config = ConfigDict(extra="forbid")

    name: str
    scope: Literal["task", "integration", "promotion"]


class RepoDeclaration(BaseModel, frozen=True):
    """Repo-side half of the adapter contract. Lives in the target repo, versioned with the
    code, changed by maintainers through ordinary PR review.

    Every field here is a fact about the repo whose falsehood costs the repo (§3.1), except
    the two marked below. Validated before a run starts; invalid is a refusal to start, not a
    warning (Principle 7)."""

    model_config = ConfigDict(extra="forbid")

    # Versions independently of the blueprint -- target repos upgrade on their own cadence,
    # which is the one case design doc §12's "modular file versioning" question must answer.
    declaration_version: str
    repo_id: str

    capabilities: list[Capability]

    # Execution & environment
    isolation_unit: IsolationUnit
    image_ref: str | None = None          # required when isolation_unit is CONTAINER
    bootstrap: list[list[str]] = Field(default_factory=list)
    declared_ports: list[int] = Field(default_factory=list)
    # POLICY-BOUNDED declaration (core_adapter_boundary.md §3.1): only the repo knows the real
    # number, but understating it buys concurrency at every co-tenant's expense. Core clamps
    # to GovernancePolicy.max_resource_footprint_mb and records the clamp.
    resource_footprint_mb: int

    # Verification
    test_tiers: list[TestTier] = Field(default_factory=list)
    hydration_fixture_ids: list[str] = Field(default_factory=list)

    # Vocabulary & transforms
    intent_vocabulary: list[IntentOpSpec] = Field(default_factory=list)

    # Telemetry
    signals: list[SignalSpec] = Field(default_factory=list)
    triage_rules: list[TriageRule] = Field(default_factory=list)

    # A REQUEST, not a grant. See GovernancePolicy.granted_secrets.
    requested_secrets: list[SecretSpec] = Field(default_factory=list)


class GovernancePolicy(BaseModel, frozen=True):
    """Control-plane half of the adapter contract. Lives outside every target repo, owned by
    whoever owns the pipeline's risk posture, changed rarely at a human governance gate.

    Everything here is a field whose falsehood would REWARD the repo that set it (§3.1), which
    is exactly why the repo does not get to set it. Policy always wins over a conflicting
    declaration: hard conflicts refuse the run, bounded conflicts clamp and record (§3.3)."""

    model_config = ConfigDict(extra="forbid")

    policy_version: str
    repo_id: str  # the RepoDeclaration this policy governs

    # Which gates actually block. Not the repo's call: a repo declaring which gates it
    # satisfies is a repo grading itself.
    blocking_gates: list[str] = Field(default_factory=list)  # gate ids from design doc §9.1

    # Policy, not declaration, precisely so the repo that benefits from degrading is not the
    # one that chooses to degrade (core_adapter_boundary.md §3.5).
    absent_capability_policy: AbsentCapabilityPolicy

    # Shared-file registration is already a human gate (design doc §9.3) -- a governance
    # decision, not a repo fact.
    registered_shared_files: list[str] = Field(default_factory=list)

    # The grant half of the request/grant pair.
    granted_secrets: list[SecretSpec] = Field(default_factory=list)

    # Spend and escalation posture. Illustrative bounds live in
    # budget_and_escalation_policy.md; these are where a run actually reads them.
    max_resource_footprint_mb: int | None = None
    concurrency_cap: int | None = None
    model_tier_allowlist: list[str] = Field(default_factory=list)

    # Mutation gate scope policy (test_harness_architecture.md §3.6-3.8). Policy rather than
    # declaration because both are self-rewarding if the repo sets them: a low ceiling and a
    # permissive posture together retire the gate.
    #
    # `non_hermetic_coverage_posture` decides what happens to a changed line covered only by a
    # non-hermetic tier -- refuse the merge until it gains hermetic coverage, or degrade and
    # record the shortfall in the PR. There is no option that reports it as passing.
    non_hermetic_coverage_posture: AbsentCapabilityPolicy = AbsentCapabilityPolicy.DEGRADE
    # Exceeding this halts the gate and reports the overflow -- never a silent sample, which
    # would report a partial run as a full one. Read it as a task-size signal.
    max_mutants_per_task: int | None = None


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
    # declared by the target repo's RepoDeclaration.signals and validated against it on
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


class GateApplicability(str, Enum):
    """Whether a gate's `passed` value means anything for this artifact.

    Added for `mutation.diff_scoped` (test_harness_architecture.md §3.6) and load-bearing for
    every scoped gate after it. A bare pass/fail cannot express "I did not run": a scoped gate
    with nothing in scope must either report True -- a green check for a check that never
    happened, which is the silent fail-open this design closes everywhere else -- or report
    False and block work it never examined. Neither is honest, so the shape gains a third
    thing to say.

    A NOT_APPLICABLE or DEGRADED result is never rendered as a passing gate, whatever
    `passed` holds."""

    APPLIED = "applied"                  # ran; `passed` is meaningful
    NOT_APPLICABLE = "not_applicable"    # nothing in scope; `passed` is vacuous
    DEGRADED = "degraded"                # capability absent, running under `degrade` policy


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
    # Defaults to APPLIED so every GateResult already in a verdict ledger stays valid and
    # keeps meaning what it meant. A validator that can be scoped out must set this
    # explicitly, and record why in `findings`.
    applicability: GateApplicability = GateApplicability.APPLIED

    @property
    def blocking_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocking"]

    @property
    def is_green(self) -> bool:
        """True only for a gate that actually ran and actually passed. Consumers rendering a
        PR summary use this rather than `passed`, so a gate that was scoped out or degraded
        can never display as a green check."""
        return self.passed and self.applicability is GateApplicability.APPLIED
