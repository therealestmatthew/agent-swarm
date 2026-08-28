"""Verification-layer contracts: the shape every Validator agent returns
(GateResult, Finding, GateApplicability), the shape the test harness captures
at failure (FailureSignature), and the scope enum that governs invariant
deprecation windows (InvariantScope). New schemas that describe validator
outputs, gate applicability, or invariant governance belong here.

Parsing discipline: mixed. GateResult and Finding are agent-produced (Validator agents generate them from LLM output) and MUST be routed through the normalization layer. FailureSignature is harness-captured (deterministic). NormalizationEvent is Core-produced (the normalizer emits it). InvariantScope and GateApplicability are enums.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

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
