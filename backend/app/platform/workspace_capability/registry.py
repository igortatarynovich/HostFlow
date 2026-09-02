"""Renderer Registry — technical ``component_id`` → module path only.

Not the platform. No owner / placement / host / class semantics.
"""

from __future__ import annotations

WORKSPACE_RENDERER_REGISTRATION_KEYS: tuple[str, ...] = (
    "component_id",
    "renderer_module",
)

WORKSPACE_RENDERER_REGISTRY: dict[str, dict[str, str]] = {
    "workspace.shell.identity": {
        "component_id": "workspace.shell.identity",
        "renderer_module": "platform/capabilities/shell/identity",
    },
    "workspace.shell.status": {
        "component_id": "workspace.shell.status",
        "renderer_module": "platform/capabilities/shell/status",
    },
    "workspace.shell.ownership": {
        "component_id": "workspace.shell.ownership",
        "renderer_module": "platform/capabilities/shell/ownership",
    },
    "workspace.shell.actions": {
        "component_id": "workspace.shell.actions",
        "renderer_module": "platform/capabilities/shell/actions",
    },
    "workspace.shell.audit": {
        "component_id": "workspace.shell.audit",
        "renderer_module": "platform/capabilities/shell/audit",
    },
    "workspace.shared.contacts": {
        "component_id": "workspace.shared.contacts",
        "renderer_module": "platform/capabilities/contacts",
    },
    "workspace.shared.notes": {
        "component_id": "workspace.shared.notes",
        "renderer_module": "platform/capabilities/notes",
    },
    "workspace.shared.consent": {
        "component_id": "workspace.shared.consent",
        "renderer_module": "platform/capabilities/consent",
    },
    "workspace.shared.tasks": {
        "component_id": "workspace.shared.tasks",
        "renderer_module": "platform/capabilities/tasks",
    },
    "workspace.shared.relations": {
        "component_id": "workspace.shared.relations",
        "renderer_module": "platform/capabilities/relations",
    },
    "workspace.surface.timeline": {
        "component_id": "workspace.surface.timeline",
        "renderer_module": "platform/capabilities/timeline",
    },
    "workspace.surface.documents": {
        "component_id": "workspace.surface.documents",
        "renderer_module": "platform/capabilities/documents",
    },
    "workspace.surface.communication": {
        "component_id": "workspace.surface.communication",
        "renderer_module": "platform/capabilities/communication",
    },
    "workspace.surface.forms": {
        "component_id": "workspace.surface.forms",
        "renderer_module": "platform/capabilities/forms",
    },
    "workspace.module.recruitment.stage": {
        "component_id": "workspace.module.recruitment.stage",
        "renderer_module": "modules/recruitment/contributions/stage",
    },
    "workspace.module.recruitment.vacancy": {
        "component_id": "workspace.module.recruitment.vacancy",
        "renderer_module": "modules/recruitment/contributions/vacancy",
    },
    "workspace.module.recruitment.assignee": {
        "component_id": "workspace.module.recruitment.assignee",
        "renderer_module": "modules/recruitment/contributions/assignee",
    },
    "workspace.module.recruitment.intake": {
        "component_id": "workspace.module.recruitment.intake",
        "renderer_module": "modules/recruitment/contributions/intake",
    },
    "workspace.module.hr.employment": {
        "component_id": "workspace.module.hr.employment",
        "renderer_module": "modules/hr/contributions/employment",
    },
    "workspace.module.fleet.assignment": {
        "component_id": "workspace.module.fleet.assignment",
        "renderer_module": "modules/fleet/contributions/assignment",
    },
    "workspace.fixture.optional_addon": {
        "component_id": "workspace.fixture.optional_addon",
        "renderer_module": "platform/workspace-capability/fixtures/optional-addon",
    },
}
