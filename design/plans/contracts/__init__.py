"""
design.plans.contracts

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
Agent-produced models are routed through the normalization layer.

Package layout (each module's own docstring declares its domain scope; new
schemas should be added to the module whose scope they fit):
  - orchestration.py     -- Core Orchestrator's own state (RunManifest, Phase,
                            HaltReason) and the shared-file intent outcome
                            envelope (IntentOutcome, IntentRejection,
                            RejectionEdge).
  - governance.py        -- The adapter contract: RepoDeclaration,
                            GovernancePolicy, and every sub-model they compose.
  - adapter_surface.py   -- Verbs Core invokes on the adapter runtime, or the
                            adapter runtime invokes into Core, at the process
                            boundary (currently WorktreeSyncRequest /
                            WorktreeSyncResult; opened for further
                            adapter-surface schemas).
  - verification.py      -- Validator return shapes, failure-triage captures,
                            invariant governance scopes.
  - reference_adapter/   -- Concrete adapter contracts. Core does not import
                            from this sub-package.

Readers should import from this package directly:
    from design.plans.contracts import GateResult, RunManifest, RepoDeclaration
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseContract(BaseModel):
    """Base class for every contract in this package. Sets the project-wide
    Pydantic config once so individual models don't repeat it and can't drift.
    Subclasses may override model_config; Pydantic v2 merges ConfigDicts correctly."""

    model_config = ConfigDict(frozen=True, extra="forbid")


from design.plans.contracts.governance import (
    AbsentCapabilityPolicy,
    Capability,
    EgressPayload,
    EscalationConfig,
    GovernancePolicy,
    HermeticityTestScope,
    IntentOpSpec,
    IsolationUnit,
    LoopBudgetConfig,
    RepoDeclaration,
    ResetResource,
    ResetStrategy,
    ScrubbedEgressPayload,
    SecretScrubberConfig,
    SecretSpec,
    SemanticAnalyzerSpec,
    SignalSpec,
    TestTier,
    TriageRule,
)
from design.plans.contracts.adapter_surface import (
    WorktreeSyncRequest,
    WorktreeSyncResult,
)
from design.plans.contracts.orchestration import (
    ExactSymbolLookup,
    HaltReason,
    IntentOutcome,
    IntentRejection,
    IntentSubmission,
    Phase,
    RecoveryManifest,
    RecoveryStrategy,
    RejectionEdge,
    RunManifest,
)
from design.plans.contracts.verification import (
    DiffClassification,
    FailureSignature,
    Finding,
    GateApplicability,
    GateResult,
    InvariantScope,
    NormalizationEvent,
    VerdictLedgerEntry,
)
from design.plans.contracts.reference_adapter.web_intents import (
    DOMCaptureConfig,
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
    "IntentSubmission",
    "RecoveryManifest",
    "RecoveryStrategy",
    "RejectionEdge",
    "ExactSymbolLookup",
    # Governance
    "RepoDeclaration",
    "GovernancePolicy",
    "IsolationUnit",
    "Capability",
    "AbsentCapabilityPolicy",
    "EscalationConfig",
    "LoopBudgetConfig",
    "ResetResource",
    "ResetStrategy",
    "TestTier",
    "IntentOpSpec",
    "SemanticAnalyzerSpec",
    "SignalSpec",
    "TriageRule",
    "SecretSpec",
    "SecretScrubberConfig",
    "EgressPayload",
    "ScrubbedEgressPayload",
    "HermeticityTestScope",
    # Adapter surface
    "WorktreeSyncRequest",
    "WorktreeSyncResult",
    # Verification
    "DiffClassification",
    "Finding",
    "GateApplicability",
    "GateResult",
    "FailureSignature",
    "InvariantScope",
    "NormalizationEvent",
    "VerdictLedgerEntry",
    # Reference Adapter
    "DOMCaptureConfig",
]
