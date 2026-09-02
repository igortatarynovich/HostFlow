"""Four capability classes — separate catalogs, not one flat enum."""

from __future__ import annotations

from typing import Literal

WorkspaceCapabilityClassId = Literal[
    "shell_primitive",
    "shared_capability",
    "platform_surface",
    "module_contribution",
]

SHELL_PRIMITIVE_IDS: tuple[str, ...] = (
    "identity",
    "status",
    "ownership",
    "actions",
    "audit",
)

SHARED_CAPABILITY_IDS: tuple[str, ...] = (
    "contacts",
    "notes",
    "consent",
    "tasks",
    "relations",
)

PLATFORM_SURFACE_IDS: tuple[str, ...] = (
    "timeline",
    "documents",
    "communication",
    "forms",
)

MODULE_CONTRIBUTION_IDS: tuple[str, ...] = (
    "recruitment.stage",
    "recruitment.vacancy",
    "recruitment.assignee",
    "recruitment.intake",
    "hr.employment",
    "fleet.assignment",
    "fixture.optional_addon",
)

WORKSPACE_CAPABILITY_CLASS_IDS: tuple[WorkspaceCapabilityClassId, ...] = (
    "shell_primitive",
    "shared_capability",
    "platform_surface",
    "module_contribution",
)
