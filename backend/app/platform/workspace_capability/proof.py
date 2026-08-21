"""Frozen G4 proof composition. Bound by ApplicationWorkspaceCapabilityHost."""

from __future__ import annotations

PROOF_CONSUMER_ID = "recruitment_application"
PROOF_HOST_ID = "application_workspace"

RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS: tuple[dict[str, object], ...] = (
    {
        "class": "shell_primitive",
        "capability_id": "identity",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.shell.identity",
        "license": "default",
    },
    {
        "class": "shell_primitive",
        "capability_id": "status",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.shell.status",
        "license": "default",
    },
    {
        "class": "shared_capability",
        "capability_id": "notes",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.shared.notes",
        "license": "default",
    },
    {
        "class": "shared_capability",
        "capability_id": "consent",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.shared.consent",
        "license": "default",
    },
    {
        "class": "module_contribution",
        "capability_id": "recruitment.stage",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.module.recruitment.stage",
        "license": "default",
    },
    {
        "class": "module_contribution",
        "capability_id": "recruitment.vacancy",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.module.recruitment.vacancy",
        "license": "default",
    },
    {
        "class": "module_contribution",
        "capability_id": "recruitment.assignee",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.module.recruitment.assignee",
        "license": "default",
    },
    {
        "class": "module_contribution",
        "capability_id": "fixture.optional_addon",
        "host": PROOF_HOST_ID,
        "consumer": PROOF_CONSUMER_ID,
        "component_id": "workspace.fixture.optional_addon",
        "license": "optional",
    },
)
