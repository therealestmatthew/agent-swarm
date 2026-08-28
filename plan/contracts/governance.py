"""Governance-layer contracts: the two-artifact adapter contract that lets Core
operate a target repo without either side inventing facts about the other.
RepoDeclaration lives in the target repo and states facts about it;
GovernancePolicy lives in the control plane and states what the pipeline will
tolerate. Every sub-model they compose (IsolationUnit, Capability,
AbsentCapabilityPolicy, ResetResource, ResetStrategy, TestTier, IntentOpSpec,
SignalSpec, TriageRule, SecretSpec) belongs here too.

New schemas that describe repo-declared facts, control-plane policy bounds, or
the sub-models either artifact composes belong here. See
core_adapter_boundary.md §3 for the declaration/policy dividing test.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field

from plan.contracts import BaseContract

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


class ResetResource(str, Enum):
    """What one execution of a ResetStrategy needs from the host. This is what makes the
    isolation unit derivable instead of a judgment call: execution_isolation.md §5 used to say
    "containers are not required -- yet ... revisit the moment a task's tests bind a port," an
    escape condition discovered at runtime. Declaring the resource makes it arithmetic."""

    NONE = "none"                                  # in-process; nothing outside the worktree
    PROCESS = "process"                            # spawns a process (a driver, a subprocess)
    PORT = "port"                                  # binds a listening socket
    FILESYSTEM_EXCLUSIVE = "filesystem_exclusive"  # needs a path no sibling task may share
    EXTERNAL_SERVICE = "external_service"          # reaches a real service outside the host


class ResetStrategy(BaseContract):
    """How this repo produces a clean slate for one test.

    test_harness_architecture.md §1.2 hard-coded `browser.new_context()` / `context.close()`
    into a universal document. Playwright has that call; Selenium does not, and its nearest
    honest equivalent -- a fresh driver process with a fresh profile directory -- costs
    seconds rather than milliseconds. The *rule* (construct fresh, never clean in place) is
    universal; the mechanism and its price are not, so the mechanism is declared.

    `typical_cost_ms` is load-bearing rather than documentation: Core feeds it into the
    wall-clock ceiling estimate and the concurrency derivation (core_adapter_boundary.md §3.6).
    A strategy costing 2s per test across a large suite is a budget fact, not a footnote."""

    strategy_id: str
    recreates: str                  # e.g. "browser context", "driver process + fresh profile dir"
    requires: list[ResetResource]
    typical_cost_ms: int
    # What this adapter's equivalent of §1.4's comparison table checks. A browser adapter
    # checks cookies and localStorage; a backend adapter checks open connections and temp
    # files. Any single mismatch sets the clean-state signal False.
    clean_state_checks: list[str] = Field(default_factory=list)


class TestTier(BaseContract):
    """One runnable tier of a repo's suite. `hermetic` is what makes `mutation.diff_scoped`
    decidable instead of universally-blocking-or-waived: the gate applies to hermetic tiers
    and is not claimed of the others. Which gates actually block is GovernancePolicy's call,
    not this file's -- a repo declaring which gates it satisfies is a repo grading itself."""

    name: str
    command: list[str]
    isolation_unit: IsolationUnit
    # VERIFIED declaration (core_adapter_boundary.md §3.1): declaring a tier non-hermetic
    # exempts it from mutation.diff_scoped, which is self-rewarding -- so Core checks the
    # claim (run the tier isolated and in-suite under randomized order) rather than trusting
    # it. A tier that verifies as hermetic is held to the stricter gate regardless of what it
    # claimed, and the discrepancy is recorded.
    hermetic: bool
    # Which ResetStrategy wraps each test in this tier. Absent means the tier needs no reset
    # beyond a fresh process, which Core will hold it to rather than assume.
    reset_strategy_id: str | None = None


class IntentOpSpec(BaseContract):
    """One Additive Intent operation this repo accepts, and the fields Core arbitrates on.

    `collision_keys` is the whole of Core's collision predicate: two pending intents for the
    same op collide iff they match on every listed key. Deliberately under-powered -- Core
    does not execute an adapter-supplied predicate, because that would move arbitration into
    untrusted repo-declared code. See core_adapter_boundary.md §2.1."""

    op: str
    collision_keys: list[str]
    transformer_id: str


class SignalSpec(BaseContract):
    """Declares one key admissible in FailureSignature.signals for this repo."""

    name: str
    value_type: Literal["bool", "int", "str"]


class TriageRule(BaseContract):
    """One row of this repo's triage matrix. Core owns the evaluator (ordered, first-match-
    wins, non-matches fall through to the Test Investigator); the rows are adapter data
    written over that adapter's declared signals. infra_triage_matrix.md is the reference rule
    set for a browser-automation adapter, not the engine."""

    order: int
    when: str            # expression over declared signal names and envelope fields
    classification: str
    routes_to: Literal["infra_queue", "task_dev", "test_investigator"]


class SecretSpec(BaseContract):
    """A credential, by name and scope only. A value never appears in either artifact, on a
    worktree filesystem, or in an agent's context (core_adapter_boundary.md §5).

    Used on both sides of a request/grant pair: RepoDeclaration.requested_secrets says what
    the repo needs, GovernancePolicy.granted_secrets says what it may have. Needing is not
    getting -- a task-scope agent requesting promotion scope is a refusal to start, not a
    config line."""

    name: str
    scope: Literal["task", "integration", "promotion"]


class RepoDeclaration(BaseContract):
    """Repo-side half of the adapter contract. Lives in the target repo, versioned with the
    code, changed by maintainers through ordinary PR review.

    Every field here is a fact about the repo whose falsehood costs the repo (§3.1), except
    the two marked below. Validated before a run starts; invalid is a refusal to start, not a
    warning (Principle 7)."""

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
    reset_strategies: list[ResetStrategy] = Field(default_factory=list)
    hydration_fixture_ids: list[str] = Field(default_factory=list)

    # Vocabulary & transforms
    intent_vocabulary: list[IntentOpSpec] = Field(default_factory=list)

    # Telemetry
    signals: list[SignalSpec] = Field(default_factory=list)
    triage_rules: list[TriageRule] = Field(default_factory=list)

    # A REQUEST, not a grant. See GovernancePolicy.granted_secrets.
    requested_secrets: list[SecretSpec] = Field(default_factory=list)


class GovernancePolicy(BaseContract):
    """Control-plane half of the adapter contract. Lives outside every target repo, owned by
    whoever owns the pipeline's risk posture, changed rarely at a human governance gate.

    Everything here is a field whose falsehood would REWARD the repo that set it (§3.1), which
    is exactly why the repo does not get to set it. Policy always wins over a conflicting
    declaration: hard conflicts refuse the run, bounded conflicts clamp and record (§3.3)."""

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
    # Reset adequacy (test_harness_architecture.md §1.6). A clean-state diff at t=0 means the
    # reset did not work, so the rate of those diffs per strategy audits the strategy itself --
    # the signal already exists for failure triage and is simply also evidence about the
    # mechanism that produced it. Above this rate, Core demotes the tier to the strictest
    # declared strategy and records it. Tightening is automatic because it costs only time;
    # loosening is a human gate because it costs correctness.
    max_baseline_diff_rate: float = 0.02
    # Exceeding this halts the gate and reports the overflow -- never a silent sample, which
    # would report a partial run as a full one. Read it as a task-size signal.
    max_mutants_per_task: int | None = None
