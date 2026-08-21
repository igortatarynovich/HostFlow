"""Capability Host Contract — hosts and regions.

Two constitution types implement the same contract.
Host owns placement only. Registry is not this contract.
"""

from __future__ import annotations

from typing import Literal

WorkspaceCapabilityHostId = Literal["entity_workspace", "application_workspace"]
WorkspaceHostRegionId = Literal[
    "header",
    "summary",
    "overview",
    "rail",
    "decision",
    "platform_slot",
]

WORKSPACE_CAPABILITY_HOST_IDS: tuple[WorkspaceCapabilityHostId, ...] = (
    "entity_workspace",
    "application_workspace",
)

WORKSPACE_HOST_REGION_IDS: tuple[WorkspaceHostRegionId, ...] = (
    "header",
    "summary",
    "overview",
    "rail",
    "decision",
    "platform_slot",
)

ENTITY_WORKSPACE_HOST = {
    "host": "entity_workspace",
    "constitution": "§3.3",
    "regions": WORKSPACE_HOST_REGION_IDS,
}

APPLICATION_WORKSPACE_HOST = {
    "host": "application_workspace",
    "constitution": "§3.2",
    "regions": WORKSPACE_HOST_REGION_IDS,
}

WORKSPACE_CAPABILITY_HOSTS = {
    "entity_workspace": ENTITY_WORKSPACE_HOST,
    "application_workspace": APPLICATION_WORKSPACE_HOST,
}
