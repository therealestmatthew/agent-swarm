"""Orchestration-layer contracts: the Core Orchestrator's own state
(RunManifest, Phase, HaltReason) and the shared-file intent outcome envelope
returned to a submitting agent (IntentOutcome, IntentRejection, RejectionEdge).
New schemas that describe Core's own bookkeeping, phase transitions, halt
conditions, or the outcome of submitting a shared-file intent belong here.

This module is Core-only for adapter-facing types. It imports the
`DiffClassification` enum from `verification` because `RunManifest` carries the
Core-computed diff label consumed by `gate_coverage.minimum`; `verification` is
a leaf module (no back-edge to orchestration), so this dependency does not
introduce a cycle. It still does not import from `governance` or
`reference_adapter/` -- see core_adapter_boundary.md §3.

Parsing discipline: strict (Core-internal). Models in this module are instantiated directly by deterministic Core components; they never hold LLM-generated content and are not routed through the normalization layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Any

from pydantic import BaseModel, Field

from design.plans.contracts import BaseContract
from design.plans.contracts.verification import DiffClassification

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
    restarting a planning cycle (design doc §4.5).

    `deadlock_cycle` is the escape valve: when the Intent Service's cycle detector or
    per-tuple rejection counter (governed by `GovernancePolicy.max_mutex_rejections`)
    fires, the rejection returned to every task in the cycle carries
    `reason = "deadlock_cycle"` and the full task-id set. That distinguishes a normal
    single-collision rejection (which the agent can resolve from the blocking context)
    from a systemic loop the agent cannot resolve on its own -- and is the signal Core
    uses to fail the involved task set as a boundary failure rather than let it burn
    budget on further retries.

    `pending_tier2_review` is distinct from all other reasons in that it is
    resumable: the submitting agent should park the dependent sub-task and pick up
    other work. When the human approves, the Intent Service applies the intent and
    the agent is notified. If rejected, the agent receives a `"structural"` reason
    on the retry, routing to the full Tier 3 SOP.

    `semantic_collision` is a Layer-2 sub-status of a Tier-1 intent under the
    Two-Layer Collision Model (`core_adapter_boundary.md` §2.1;
    `agentic-sdlc-design-v0.5.md` §4.2). Layer 1 (`collision`) is Core's exact-match
    predicate on `IntentOpSpec.collision_keys`; Layer 2 (`semantic_collision`) is an
    adapter-declared analyzer that runs synchronously inside the same Intent Service
    call and can reject an intent that passed Layer 1 -- overlapping regex routes,
    conflicting middleware, and other semantic conflicts that share no literal key.
    Distinct from `collision` (Layer 1, key match), from `pending_tier2_review`
    (Tier 2, human queue, resumable), and from `structural` (Tier 3, SOP). The
    accompanying `semantic_feedback` carries the analyzer's message; `override_key`
    is the token an agent submits back via `IntentSubmission.override_semantic_collisions`
    to bypass this specific verdict, converting the block into a hypothesis Phase 5
    integration testing will still catch if the analyzer was correct.

    `max_mutex_rejections` covers `semantic_collision` as well as `collision`: a stuck
    override loop between the same `(rejected_task, blocking_task, resource_key)` tuple
    degrades to `deadlock_cycle` once the counter trips, exactly like a Layer-1 rejection
    loop. This prevents an agent from indefinitely re-submitting an intent with the same
    override against an analyzer that will keep rejecting it."""

    reason: Literal[
        "collision",              # Layer 1: another pending/applied intent matches on every key
        "semantic_collision",     # Layer 2: adapter analyzer rejected an intent that passed Layer 1
                                  # (core_adapter_boundary.md §2.1). applied=False; the submitting
                                  # agent may resubmit via IntentSubmission.override_semantic_collisions
                                  # with the analyzer's `override_key`. Stuck override loops degrade
                                  # to `deadlock_cycle` under max_mutex_rejections like any other loop.
        "unmapped_anchor",        # no registered insertion point covers this -- a registration gap
        "not_registered",         # the target file is not in GovernancePolicy.registered_shared_files
        "op_not_declared",        # the op is absent from RepoDeclaration.intent_vocabulary
        "structural",             # Tier 3: high-blast-radius change -- exits via the full SOP
                                  # (structural_change_runbook.md Tier 3 Procedure). The run halts
                                  # for human architectural review.
        "pending_tier2_review",   # Tier 2: intent accepted into async review queue. applied=False
                                  # but NOT terminal -- the human approves/rejects asynchronously.
                                  # The proposing agent parks the dependent sub-task and continues
                                  # other work within its existing write scope. No run halt.
        "deadlock_cycle",         # graph cycle detected, or max_mutex_rejections breached -- §4.5
    ]
    blocking_task_id: str | None = None
    blocking_op: str | None = None
    blocking_keys: dict[str, str] = Field(default_factory=dict)
    # Populated iff reason == "deadlock_cycle": the ordered set of task IDs forming the
    # detected cycle (or the two ends of the repeatedly-colliding tuple when the counter
    # ceiling is what tripped). None for every other reason -- so a rejection is either a
    # single-collision fact (resolvable from blocking_*) or a systemic-loop fact
    # (task-scoped termination), never ambiguously both.
    deadlock_cycle: list[str] | None = None
    # Populated iff reason == "semantic_collision": the Layer-2 analyzer's human-readable
    # message explaining why the intent was refused (e.g. "route `/users/:id` overlaps
    # with pending route `/users/new`"). Structured data on the SECURITY path already noted
    # for `blocking_*` -- the receiving agent renders this string, never interprets it as
    # an instruction. None for every other reason.
    semantic_feedback: str | None = None
    # Populated iff reason == "semantic_collision": the token the submitting agent must
    # place in `IntentSubmission.override_semantic_collisions` to bypass this specific
    # Layer-2 verdict on resubmission. Bound to the specific rejection so a stale override
    # from a different rejection cannot silently pass; Core validates the key against the
    # last rejection before honoring it. None for every other reason.
    override_key: str | None = None


class RejectionEdge(BaseContract):
    """One edge in the Intent Service's rejection graph: task A was rejected because task B
    currently holds a lock (or a pending intent) on `resource_key`. The graph is what makes
    the §4.5 cycle detector cheap -- adding an edge, then running a bounded-depth cycle walk
    from the new node, is O(cycle length) rather than a rescan of all pending intents.

    Core-only, and stays that way: an adapter has no reason to observe the graph and no
    authority to mutate it. Persisted on `RunManifest.rejection_graph_edges` (see below) so
    a crashed-and-resumed run reconstructs the deadlock state it detected pre-crash, rather
    than silently starting the counters over and re-entering the same cycle -- the H8
    crash-recovery concern applied to this specific piece of Intent Service state.

    `timestamp` is epoch seconds; the counter decay Core applies (a cycle whose edges are
    all older than a phase boundary is stale evidence) reads it directly. `resource_key` is
    the target file path plus, when the collision was on an anchor, the anchor id -- the
    same tuple `blocking_keys` on `IntentRejection` describes for the human-readable case."""

    rejected_task_id: str
    blocking_task_id: str
    resource_key: str
    timestamp: float


class IntentOutcome(BaseContract):
    """Returned to the submitting agent, synchronously, before it continues. `applied_anchor`
    and `content_digest` are what the per-PR shared-file delta view is reconstructed from
    (execution_isolation.md §7.4), so the intent log is the audit record for content that
    appears in no task's diff."""

    # Typed as BaseModel rather than SharedFileIntent because SharedFileIntent lives in
    # `design.plans.contracts.reference_adapter.web_intents` and Core cannot import from the reference
    # adapter (core_adapter_boundary.md §3). Core does not need the concrete type: it routes on
    # the `op` string field and serializes the payload opaquely. Adapter-level code that
    # constructs or consumes an IntentOutcome still validates against the concrete union.
    intent: dict[str, Any]
    task_id: str
    target_file: str
    applied: bool
    applied_anchor: str | None = None   # where in the structural map it landed
    content_digest: str | None = None   # of the shared file after application
    rejection: IntentRejection | None = None


class IntentSubmission(BaseContract):
    """The envelope an agent submits to the Shared-File Intent Service. Wraps the
    Tier-1 intent (a `SharedFileIntent` union member) with submission-side metadata
    that is NOT part of the intent vocabulary itself -- keeping the reference-adapter
    intents (`AddExport`, `AddRoute`, `AddProviderBinding`, `RenameExport`, `MoveRoute`,
    `DeprecateExport`) untouched by Core-side collision governance.

    Introduced by H7 for the Two-Layer Collision Model
    (`core_adapter_boundary.md` §2.1). `override_semantic_collisions` is the seam the
    override protocol rides on: on a Layer-2 rejection the agent receives an
    `IntentRejection` carrying `override_key`, and resubmits the same intent with that
    key in this list to bypass the specific Layer-2 verdict. Layer 1 (deterministic key
    match) is not overrideable through this field -- a Layer-1 collision is a factual
    claim about pending intents, not a semantic judgement, and overriding it would
    silently corrupt the shared file.

    Empty `override_semantic_collisions` is the default and matches the pre-H7
    submission shape, so every existing call site is a valid `IntentSubmission` under
    the additive-default discipline. A non-empty list matches `override_key` values
    previously returned in an `IntentRejection` for this same intent; Core validates
    the keys against the last rejection before honoring them (design note -- no
    runtime validation code lives here).

    Repeated `semantic_collision` rejections on the same
    `(rejected_task, blocking_task, resource_key)` tuple accrue against
    `GovernancePolicy.max_mutex_rejections` and degrade to `deadlock_cycle` on breach,
    exactly like Layer-1 rejection loops -- an agent cannot spin indefinitely against
    an analyzer by cycling override keys. See `IntentRejection` docstring for the
    combined loop-ceiling semantics."""

    # Typed as BaseModel for the same core/adapter-boundary reason as
    # `IntentOutcome.intent`: `SharedFileIntent` lives in
    # `design.plans.contracts.reference_adapter.web_intents`, and Core routes on the `op` string
    # field without importing from the reference adapter (core_adapter_boundary.md §3).
    # Adapter-level code that constructs an IntentSubmission still validates the intent
    # against the concrete union before wrapping it here.
    intent: dict[str, Any]
    task_id: str
    override_semantic_collisions: list[str] = Field(default_factory=list)


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
    gate in design doc §9.3 that is currently awaiting sign-off.

    `BOUNDARY_FAILURE` is run-level and only set when boundary failure has emptied
    `active_task_ids` or otherwise blocked phase progress. A §4.5 deadlock that involves
    only a subset of tasks does NOT raise this: the Intent Service drops the involved tasks
    from `active_task_ids` via the existing per-task failure path (their rejection carries
    `IntentRejection.reason = "deadlock_cycle"`), and Core continues the phase for the
    remaining active tasks. The run-level halt is reserved for the case where the cascade
    leaves no work Core can still make progress on."""

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
    # Live snapshot of the Intent Service's rejection graph (design doc §4.5). Persisted here
    # so a crashed-and-resumed run cannot silently re-enter a deadlock it had already
    # detected -- H8 crash-recovery concern applied to §4.5's cycle detector. Additive and
    # defaulted to empty for backward compatibility with manifests recorded before the
    # detector existed. Core rewrites the field on every phase-transition snapshot, the same
    # cadence as the rest of this model; the graph is bounded by the number of live tasks,
    # so serialization cost is negligible.
    rejection_graph_edges: list[RejectionEdge] = Field(default_factory=list)
    # Diff triviality label for this task, computed once by Core before Phase 6 begins from
    # the task's write-scope diff (rule in test_harness_architecture.md §3.9). Read by the
    # `gate_coverage.minimum` meta-gate (design doc §9.1, §10): a NON_TRIVIAL_CODE diff whose
    # coverage-family gates all returned anything other than APPLIED-and-passed is a boundary
    # failure, propagated via the same `active_task_ids` drop the §4.5 detector uses.
    # Optional and defaulted to None so manifests recorded before this field existed still
    # validate; H8 crash-recovery must preserve it on resume, same discipline as
    # `rejection_graph_edges` above -- Core does not recompute from the diff on resume,
    # because the diff may have been mutated (or reverted) between crash and restart, and a
    # silently-reclassified task would defeat the point of persisting the label.
    diff_classification: DiffClassification | None = None
    last_sync_hash_by_task: dict[str, str] = Field(default_factory=dict)


class RecoveryStrategy(str, Enum):
    """Resume decision tree outcomes for the StartupReconciler."""

    RESUME_FROM_PHASE = "resume_from_phase"
    ROLLBACK_AND_RESTART = "rollback_and_restart"
    HALT_FOR_MANUAL_INTERVENTION = "halt_for_manual_intervention"


class RecoveryManifest(BaseContract):
    """The plan produced by the StartupReconciler for crash recovery."""

    run_id: str
    strategy: RecoveryStrategy
    recovered_phase: Phase | None = None


class ExactSymbolLookup(BaseContract):
    file_path: str = Field(..., description="Exact relative path to the target file")
    symbol_name: str = Field(..., description="Exact class, function, or variable name to retrieve")

