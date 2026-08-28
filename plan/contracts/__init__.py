"""
plan.contracts

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

Package layout (each module's own docstring declares its domain scope; new
schemas should be added to the module whose scope they fit):
  - orchestration.py     -- Core Orchestrator's own state (RunManifest, Phase,
                            HaltReason) and the shared-file intent outcome
                            envelope (IntentOutcome, IntentRejection).
  - governance.py        -- The adapter contract: RepoDeclaration,
                            GovernancePolicy, and every sub-model they compose.
  - verification.py      -- Validator return shapes, failure-triage captures,
                            invariant governance scopes.
  - reference_adapter/   -- Concrete adapter contracts. Core does not import
                            from this sub-package.

Readers should import from this package directly:
    from plan.contracts import GateResult, RunManifest, RepoDeclaration
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseContract(BaseModel):
    """Base class for every contract in this package. Sets the project-wide
    Pydantic config once so individual models don't repeat it and can't drift.
    Subclasses may override model_config; Pydantic v2 merges ConfigDicts correctly."""

    model_config = ConfigDict(frozen=True, extra="forbid")


from plan.contracts.governance import (
    AbsentCapabilityPolicy,
    Capability,
    EgressPayload,
    GovernancePolicy,
    IntentOpSpec,
    IsolationUnit,
    RepoDeclaration,
    ResetResource,
    ResetStrategy,
    ScrubbedEgressPayload,
    SecretScrubberConfig,
    SecretSpec,
    SignalSpec,
    TestTier,
    TriageRule,
)
from plan.contracts.orchestration import (
    HaltReason,
    IntentOutcome,
    IntentRejection,
    Phase,
    RunManifest,
)
from plan.contracts.verification import (
    FailureSignature,
    Finding,
    GateApplicability,
    GateResult,
    InvariantScope,
)

__all__ = [
    # Base class
    "BaseContract",
    # Orchestration
    "RunManifest",
    "Phase",
    "HaltReason",
    "IntentOutcome",
    "IntentRejection",
    # Governance
    "RepoDeclaration",
    "GovernancePolicy",
    "IsolationUnit",
    "Capability",
    "AbsentCapabilityPolicy",
    "ResetResource",
    "ResetStrategy",
    "TestTier",
    "IntentOpSpec",
    "SignalSpec",
    "TriageRule",
    "SecretSpec",
    "SecretScrubberConfig",
    "EgressPayload",
    "ScrubbedEgressPayload",
    # Verification
    "Finding",
    "GateApplicability",
    "GateResult",
    "FailureSignature",
    "InvariantScope",
]
