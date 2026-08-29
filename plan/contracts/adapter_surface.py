"""Adapter-surface contracts: the verbs Core invokes on the adapter runtime,
and the verbs the adapter runtime invokes into Core, at the process boundary
where an agent's own runtime meets the isolation unit it operates. Currently
one verb — `WorktreeSyncRequest`/`WorktreeSyncResult`, the unconditional
pre-subprocess shared-file reconciliation call — but the module is opened as
the future home for further adapter-surface schemas (e.g. capability
negotiation callbacks, subprocess lifecycle hooks) so they land alongside
the sync verb rather than accreting into `orchestration.py` or `governance.py`.

Core owns these schemas: the adapter surface is a contract Core defines and
the reference adapter implements, not the other way around. Import discipline
follows from that ownership. This module may import from `verification.py` or
standalone types only. It MUST NOT import from `orchestration.py` (which
preserves orchestration's Core-internal stance — RunManifest and phase state
are not adapter-observable), MUST NOT import from `governance.py` (the adapter
contract artifacts are a separate concern from the adapter's runtime surface),
and MUST NOT import from `reference_adapter/` (see `core_adapter_boundary.md`
§3 — Core does not import from a concrete adapter).

Parsing discipline: strict (Core-internal). Deterministic Core routes these
verbs; the payloads are structured filesystem-reconciliation facts, never
LLM-generated content, and are not routed through the normalization layer.
"""

from __future__ import annotations

from pydantic import Field

from plan.contracts import BaseContract

# ---------------------------------------------------------------------------
# Worktree Sync  (execution_isolation.md §7.2, §7.5, §7.6)
# ---------------------------------------------------------------------------
#
# The materialization-window protocol: an agent's runtime unconditionally
# issues a sync call at every subprocess boundary, so that any shared-file
# intent Core applied since the last such call is present on disk before the
# fresh subprocess starts. The call is a local filesystem reconciliation from
# the worktree's local `shared/` branch head into its working directory --
# never a wire read (see execution_isolation.md §7.5 "Reads stay local").


class WorktreeSyncRequest(BaseContract):
    """Submitted by an agent's adapter runtime as an unconditional pre-subprocess
    call, before any fresh target-system subprocess is spawned. The call is
    idempotent — when the worktree's shared-file view already matches the
    canonical `shared/` branch head, Core returns a no-op result rather than
    rewriting bytes that are already correct on disk.

    The unconditional discipline is why this schema does not carry any
    "expected commit" or "since-hash" hint: an agent that crashed and restarted
    would not know which hash it last saw, and adding a hint would reintroduce
    the event-loss failure mode the unconditional call was chosen to remove
    (execution_isolation.md §7.6). Core determines what is stale by comparing
    the local `shared/` branch head against the worktree's materialized
    content; the agent is not asked to remember."""

    task_id: str
    worktree_path: str


class WorktreeSyncResult(BaseContract):
    """Returned to the caller synchronously. `was_noop=True` is the normal
    steady-state outcome — every subprocess boundary hits Core, most of them
    find nothing to reconcile, and Core says so rather than pretending work
    was done.

    `source_commit_hash` is the `shared/` branch head Core reconciled the
    worktree against, recorded so the caller can log it for post-hoc audit and
    so Core can, at other checkpoints, prove sync freshness ("this task
    entered Phase 6 having last synced to commit X") without having to
    re-derive it. It is the local head, never a remote fetch: per
    `execution_isolation.md` §7.5 reads stay local, and this call is a local
    filesystem reconciliation from the worktree's local `shared/` branch into
    the worktree — a transport outage does not affect it, because the last-
    applied shared-file content is already on disk in the local branch.

    `files_updated` is the list of registered-shared-file paths whose content
    changed on this call, empty when `was_noop=True`. It is the audit trail
    for what the fresh subprocess is about to see that the previous one did
    not."""

    task_id: str
    files_updated: list[str] = Field(default_factory=list)
    source_commit_hash: str
    was_noop: bool
