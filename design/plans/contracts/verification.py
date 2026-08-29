"""Verification-layer contracts: the shape every Validator agent returns
(GateResult, Finding, GateApplicability), the shape the test harness captures
at failure (FailureSignature), and the scope enum that governs invariant
deprecation windows (InvariantScope). New schemas that describe validator
outputs, gate applicability, or invariant governance belong here.

Parsing discipline: mixed. GateResult and Finding are agent-produced (Validator agents generate them from LLM output) and MUST be routed through the normalization layer. FailureSignature is harness-captured (deterministic). NormalizationEvent is Core-produced (the normalizer emits it). InvariantScope, GateApplicability, and DiffClassification are enums; DiffClassification is Core-produced (the deterministic triviality classifier emits it, `test_harness_architecture.md` §3.9).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Any, Optional

from pydantic import Field

from plan.contracts import BaseContract

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


class FailureSignature(BaseContract):
    """
    Captured by the test harness at the moment of failure — never
    reconstructed later from logs or stack traces. See
    test_harness_architecture.md for exact capture rules, especially
    for `dom_state_diff_from_baseline`.
    """

    error_class: str
    elapsed_ms: int
    configured_timeout_ms: int | None
    isolated_rerun_outcome: Literal["passed", "failed_again", "not_yet_run"]

    # Adapter-declared telemetry (core_adapter_boundary.md §2.2). Keys and value types are
    # declared by the target repo's RepoDeclaration.signals and validated against it on
    # capture; the triage rules that read them are adapter data too. This exists because an
    # adapter cannot add fields to an extra="forbid" model without forking the schema per
    # repo -- exactly the drift this file exists to prevent.
    signals: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validator Output  (new in v0.4 — standardizes every Validator's return shape)
# ---------------------------------------------------------------------------


class Finding(BaseContract):
    """A single issue raised by a Validator agent."""

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


class DiffClassification(str, Enum):
    """Deterministic label for a task's diff, produced once by Core before Phase 6 begins.
    Consumed exclusively by `gate_coverage.minimum` (agentic-sdlc-design-v0.5.md §9.1, §10),
    the meta-gate that catches the case where an adversarial diff shapes itself so every
    coverage-family gate returns NOT_APPLICABLE — a silent green built out of honest
    scope-outs, which the per-gate applicability enum alone cannot distinguish from a
    genuinely trivial change.

    Triviality is a property of the *diff*, not of any single gate's result — a diff either
    is or is not code the coverage family should have applied to, regardless of what any one
    gate returned. That is why this lives here as an enum but is carried on `RunManifest`
    (`design/plans/contracts/orchestration.py`) rather than on `GateResult`: it is one label per task,
    not per gate. The starting rule is extension-only, defined in
    `test_harness_architecture.md` §3.9 and adapter-tunable via
    `RepoDeclaration.trivial_path_globs`."""

    TRIVIAL_DOCS = "trivial_docs"
    NON_TRIVIAL_CODE = "non_trivial_code"


class GateResult(BaseContract):
    """
    Standard return shape for every Validator agent (Plan Reviewer, Code
    Reviewer, Security Review, PR Reviewer, Baseline Guard, etc.).

    `passed` reflects blocking findings only — advisory findings never
    flip it to False, but should still surface to whoever consumes the
    result.
    """

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


# ---------------------------------------------------------------------------
# Normalization Layer  (llm_output_normalization.md §1)
# ---------------------------------------------------------------------------


class NormalizationEvent(BaseContract):
    """
    Emitted by the normalization layer when hallucinated extra fields are stripped
    from an agent's JSON output before it enters strict validation.
    
    A high rate of these events is a signal for prompt refinement, not a runtime
    escalation trigger (llm_output_normalization.md §4).
    """

    model_class: str
    agent_id: str
    run_id: str
    stripped_fields: list[str]
    stripped_data_summary: dict[str, str]
    nesting_depth: int
    source_model_tier: str | None = None


# ---------------------------------------------------------------------------
# Verdict Ledger  (calibration_and_measurement.md §1)
# ---------------------------------------------------------------------------


class VerdictLedgerEntry(BaseContract):
    """
    Records a validator's verdict and its subsequent outcomes to calibrate
    precision and compute Cost-per-Integration-Catch (CPIC).
    """

    entry_id: str = Field(..., description="Unique identifier for this ledger entry. Dispatch-path metering tags costs to this ID so Cost-per-Verdict and CPIC calculations remain available whether or not the Budget Accountant is running (budget_and_escalation_policy.md §4.3).")
    gate_result: GateResult = Field(..., description="The full GateResult produced by the validator — reviewer, passed, findings, applicability, and spec version. Stored in full so a later prompt change (§3) does not silently invalidate the precision data this row carries.")
    human_override: Optional[str] = Field(None, description="Tier 1: Explicit human verdict overriding or confirming the agent")
    integration_catch_outcome: Optional[bool] = Field(None, description="Tier 2: True if integration tests caught an issue on the approved code within the CI window")
    downstream_outcome: Optional[str] = Field(None, description="Tier 3: Optional manual notation of a production bug attributed to this verdict")
