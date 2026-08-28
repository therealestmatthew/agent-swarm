"""Orchestration-layer contracts: the Core Orchestrator's own state
(RunManifest, Phase, HaltReason) and the shared-file intent outcome envelope
returned to a submitting agent (IntentOutcome, IntentRejection). New schemas
that describe Core's own bookkeeping, phase transitions, halt conditions, or
the outcome of submitting a shared-file intent belong here.

This module is Core-only. It does not import from `governance`, `verification`,
or `reference_adapter/` -- Core is standalone (see core_adapter_boundary.md §3).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from plan.contracts import BaseContract

# ---------------------------------------------------------------------------
# Intent Submission Outcome  (design doc §4.5; execution_isolation.md §7)
# ---------------------------------------------------------------------------
#
# Smart Mutex Rejection has been named since v0.2 without a shape. This is it.
#
# SECURITY: `blocking_*` fields tell one agent what another agent claimed. They are structured
# data and never free-form text, because prose on this path is an injection channel between
# agents -- the receiving side renders these fields, it does not replay a message.


class IntentRejection(BaseContract):
    """Why an intent was refused, with enough context to resolve in one shot rather than
    restarting a planning cycle (design doc §4.5)."""

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


class IntentOutcome(BaseContract):
    """Returned to the submitting agent, synchronously, before it continues. `applied_anchor`
    and `content_digest` are what the per-PR shared-file delta view is reconstructed from
    (execution_isolation.md §7.4), so the intent log is the audit record for content that
    appears in no task's diff."""

    # Typed as BaseModel rather than AdditiveIntent because AdditiveIntent lives in
    # `plan.contracts.reference_adapter.web_intents` and Core cannot import from the reference
    # adapter (core_adapter_boundary.md §3). Core does not need the concrete type: it routes on
    # the `op` string field and serializes the payload opaquely. Adapter-level code that
    # constructs or consumes an IntentOutcome still validates against the concrete union.
    intent: BaseModel
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


class RunManifest(BaseContract):
    """Reinstated from v0.1 §3.1. The Core Orchestrator reads this, decides the next
    phase, dispatches the responsible agent, and persists a new instance — it never
    mutates this one. See agentic-sdlc-design-v0.5.md §3 for the resumability argument."""

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
