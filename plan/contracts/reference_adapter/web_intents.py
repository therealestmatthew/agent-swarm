"""Reference-adapter web intents: the concrete Additive Intent vocabulary for a
web/backend adapter that governs shared export barrels, routers, and DI
containers. New intent operations for the reference web adapter (or a variant
of it) belong here.

This module is adapter-side. Core does not import from it -- IntentOutcome.intent
in `plan.contracts.orchestration` is typed as BaseModel precisely so Core can
route on the `op` string field without knowing the concrete union defined below.
See core_adapter_boundary.md §3.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from plan.contracts import BaseContract

# ---------------------------------------------------------------------------
# Shared-File Additive Intents  (design doc §4.2)
# ---------------------------------------------------------------------------


class AddExport(BaseContract):
    """Register a new named export from a module in a shared export barrel."""

    op: Literal["add_export"] = "add_export"
    name: str
    source_module: str


class AddRoute(BaseContract):
    """Register a new route on a shared router."""

    op: Literal["add_route"] = "add_route"
    path: str
    handler: str
    middleware: list[str] = Field(default_factory=list)


class AddProviderBinding(BaseContract):
    """Register a new binding in a shared DI container."""

    op: Literal["add_provider_binding"] = "add_provider_binding"
    interface: str
    implementation: str
    scope: Literal["singleton", "transient", "scoped"]


# Discriminated union so the Shared-File Intent Service can route an intent
# to the correct AST transformer (design doc §4.4) on `op` without an
# isinstance() chain.
AdditiveIntent = AddExport | AddRoute | AddProviderBinding
