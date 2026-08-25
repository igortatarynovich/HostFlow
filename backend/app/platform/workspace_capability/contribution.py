"""Contribution Definition — only legal add-path onto a host.

``permissions`` / ``actions`` / ``events`` / ``license`` are references
to existing canons, not local vocabularies.
"""

from __future__ import annotations

from typing import Literal

WorkspaceLicenseView = Literal["default", "optional", "paid"]

WORKSPACE_LICENSE_VIEWS: tuple[WorkspaceLicenseView, ...] = (
    "default",
    "optional",
    "paid",
)

WORKSPACE_CONTRIBUTION_FIELD_KEYS: tuple[str, ...] = (
    "capability_id",
    "class",
    "owner",
    "contributor",
    "host",
    "consumer",
    "component_id",
    "placement",
    "ordering",
    "visibility",
    "permissions",
    "state_owner",
    "actions",
    "events",
    "license",
    "conflicts",
)

REFERENCE_FIELD_CANONS = {
    "permissions": "ADR-036",
    "actions": "Action Canon / already-shipped named actions",
    "events": "backend.app.platform.events.registry",
    "license": "ADR-004 / ADR-019 entitlement",
}
