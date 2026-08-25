"""Capability definitions — semantic owner + state owner + placement.

Discriminated by ``class``. ``status`` is an owner projection, not a global enum.
"""

from __future__ import annotations

from typing import Any

from backend.app.platform.workspace_capability.catalogs import (
    MODULE_CONTRIBUTION_IDS,
    PLATFORM_SURFACE_IDS,
    SHARED_CAPABILITY_IDS,
    SHELL_PRIMITIVE_IDS,
)

_BOTH_HOSTS = ("entity_workspace", "application_workspace")

SHELL_PRIMITIVE_CAPABILITIES: dict[str, dict[str, Any]] = {
    "identity": {
        "class": "shell_primitive",
        "capability_id": "identity",
        "owner": "entity_or_application_type",
        "state_owner": "entity_or_application_type",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("header",),
    },
    "status": {
        "class": "shell_primitive",
        "capability_id": "status",
        "owner": "entity_or_application_type",
        "state_owner": "entity_or_application_type",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("header",),
        "projection": "owner_status",
    },
    "ownership": {
        "class": "shell_primitive",
        "capability_id": "ownership",
        "owner": "host_region",
        "state_owner": "entity_or_application_type",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("header", "rail"),
    },
    "actions": {
        "class": "shell_primitive",
        "capability_id": "actions",
        "owner": "action_canon",
        "state_owner": "action_canon",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("header", "decision"),
    },
    "audit": {
        "class": "shell_primitive",
        "capability_id": "audit",
        "owner": "activity",
        "state_owner": "activity",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("rail",),
    },
}

SHARED_CAPABILITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "contacts": {
        "class": "shared_capability",
        "capability_id": "contacts",
        "owner": "contacts",
        "state_owner": "contacts",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("overview", "rail"),
    },
    "notes": {
        "class": "shared_capability",
        "capability_id": "notes",
        "owner": "notes",
        "state_owner": "notes",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("overview", "rail"),
    },
    "consent": {
        "class": "shared_capability",
        "capability_id": "consent",
        "owner": "compliance",
        "state_owner": "compliance",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("overview", "rail"),
    },
    "tasks": {
        "class": "shared_capability",
        "capability_id": "tasks",
        "owner": "activity",
        "state_owner": "activity",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("rail",),
    },
    "relations": {
        "class": "shared_capability",
        "capability_id": "relations",
        "owner": "entity_model",
        "state_owner": "entity_model",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("overview",),
    },
}

PLATFORM_SURFACE_CAPABILITIES: dict[str, dict[str, Any]] = {
    "timeline": {
        "class": "platform_surface",
        "capability_id": "timeline",
        "owner": "activity",
        "state_owner": "activity",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("platform_slot",),
        "d2_slot": "timeline",
    },
    "documents": {
        "class": "platform_surface",
        "capability_id": "documents",
        "owner": "documents",
        "state_owner": "documents",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("platform_slot",),
        "d2_slot": "documents",
    },
    "communication": {
        "class": "platform_surface",
        "capability_id": "communication",
        "owner": "communication",
        "state_owner": "communication",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("platform_slot",),
        "d2_slot": "communication",
    },
    "forms": {
        "class": "platform_surface",
        "capability_id": "forms",
        "owner": "forms",
        "state_owner": "forms",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("platform_slot",),
        "d2_slot": "forms",
    },
}

MODULE_CAPABILITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "recruitment.stage": {
        "class": "module_contribution",
        "capability_id": "recruitment.stage",
        "owner": "recruitment",
        "state_owner": "recruitment",
        "contributor": "recruitment",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("decision", "rail"),
    },
    "recruitment.vacancy": {
        "class": "module_contribution",
        "capability_id": "recruitment.vacancy",
        "owner": "recruitment",
        "state_owner": "recruitment",
        "contributor": "recruitment",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("rail", "overview"),
    },
    "recruitment.assignee": {
        "class": "module_contribution",
        "capability_id": "recruitment.assignee",
        "owner": "recruitment",
        "state_owner": "recruitment",
        "contributor": "recruitment",
        "allowed_hosts": _BOTH_HOSTS,
        "allowed_regions": ("rail", "header"),
    },
    "hr.employment": {
        "class": "module_contribution",
        "capability_id": "hr.employment",
        "owner": "hr",
        "state_owner": "hr",
        "contributor": "hr",
        "allowed_hosts": ("entity_workspace",),
        "allowed_regions": ("overview", "rail"),
    },
    "fleet.assignment": {
        "class": "module_contribution",
        "capability_id": "fleet.assignment",
        "owner": "fleet",
        "state_owner": "fleet",
        "contributor": "fleet",
        "allowed_hosts": ("entity_workspace",),
        "allowed_regions": ("overview", "rail"),
    },
    "fixture.optional_addon": {
        "class": "module_contribution",
        "capability_id": "fixture.optional_addon",
        "owner": "fixture",
        "state_owner": "fixture",
        "contributor": "fixture",
        "allowed_hosts": ("application_workspace",),
        "allowed_regions": ("rail",),
    },
}

WORKSPACE_CAPABILITY_DEFINITIONS = {
    "shell_primitive": SHELL_PRIMITIVE_CAPABILITIES,
    "shared_capability": SHARED_CAPABILITY_DEFINITIONS,
    "platform_surface": PLATFORM_SURFACE_CAPABILITIES,
    "module_contribution": MODULE_CAPABILITY_DEFINITIONS,
}


def all_capability_ids() -> tuple[str, ...]:
    return (
        SHELL_PRIMITIVE_IDS
        + SHARED_CAPABILITY_IDS
        + PLATFORM_SURFACE_IDS
        + MODULE_CONTRIBUTION_IDS
    )


def assert_no_rodo_capability_id() -> None:
    for capability_id in all_capability_ids():
        if capability_id == "rodo" or capability_id.endswith(".rodo"):
            raise AssertionError("capability_id must not be named rodo")
