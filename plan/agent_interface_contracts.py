"""
agent_interface_contracts.py

Single source of truth for all schemas exchanged between agents in the
Agentic SDLC Orchestration pipeline. Referenced by:
  - agentic-sdlc-design-v0.4.md (core orchestration blueprint)
  - infra_triage_matrix.md (FailureSignature)
  - budget_and_escalation_policy.md (GateResult, used in the escalation ladder)
  - test_harness_architecture.md (FailureSignature capture rules)

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

    @property
    def blocking_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocking"]
