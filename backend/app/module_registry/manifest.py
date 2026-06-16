"""Baseline Module Registry manifest (P1)."""

from __future__ import annotations

from typing import Any

from backend.app.models.module_registry import MODULE_KIND_BUSINESS, MODULE_KIND_PLATFORM

BASELINE_MODULE_CODES = (
    "recruitment",
    "hr",
    "fleet",
    "documents",
    "process_engine",
    "field_registry",
)


def _capability(
    capability_code: str,
    *,
    kind: str,
    display_name: str,
    default_enabled: bool = True,
    description: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "capability_code": capability_code,
        "kind": kind,
        "display_name": display_name,
        "description": description,
        "default_enabled": default_enabled,
        "config": config or {},
    }


def _module(
    module_code: str,
    *,
    kind: str,
    display_name: str,
    owner: str,
    capabilities: list[dict[str, Any]],
    dependencies: list[dict[str, Any]] | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "module_code": module_code,
        "kind": kind,
        "display_name": display_name,
        "owner": owner,
        "capabilities": capabilities,
        "dependencies": dependencies or [],
        "manifest": manifest or {},
    }


def module_registry_manifest() -> list[dict[str, Any]]:
    return [
        _module(
            "recruitment",
            kind=MODULE_KIND_BUSINESS,
            display_name="Recruitment",
            owner="recruitment",
            capabilities=[
                _capability("recruitment.candidate.view", kind="route_access", display_name="View candidates"),
                _capability("recruitment.candidate.manage", kind="write_access", display_name="Manage candidates"),
                _capability("recruitment.vacancy.view", kind="route_access", display_name="View vacancies"),
                _capability("recruitment.vacancy.manage", kind="write_access", display_name="Manage vacancies"),
                _capability("recruitment.handoff.submit", kind="process_transition", display_name="Submit handoff"),
            ],
            dependencies=[
                {
                    "dependency_module_code": "hr",
                    "dependency_kind": "optional",
                    "capability_code": "recruitment.handoff.internal_hr",
                    "config": {"activates": ["handoff.internal_hr"]},
                }
            ],
            manifest={
                "legacy_keys": ["candidates", "leads", "vacancies"],
                "process_engine": {"module": "recruitment"},
                "field_registry": {"namespace": "recruitment.*"},
            },
        ),
        _module(
            "hr",
            kind=MODULE_KIND_BUSINESS,
            display_name="HR / Workforce",
            owner="hr",
            capabilities=[
                _capability("hr.workspace.view", kind="route_access", display_name="View HR workspace"),
                _capability("hr.employee.manage", kind="write_access", display_name="Manage employees"),
                _capability("hr.handoff.accept", kind="process_transition", display_name="Accept HR handoff"),
            ],
            dependencies=[
                {
                    "dependency_module_code": "recruitment",
                    "dependency_kind": "optional",
                    "capability_code": "hr.handoff.accept",
                    "config": {"activates": ["handoff.accept_from_recruitment"]},
                }
            ],
            manifest={"field_registry": {"namespace": "hr.employee.*"}},
        ),
        _module(
            "fleet",
            kind=MODULE_KIND_BUSINESS,
            display_name="Fleet",
            owner="fleet",
            capabilities=[
                _capability("fleet.workspace.view", kind="route_access", display_name="View fleet workspace"),
                _capability("fleet.vehicle.manage", kind="write_access", display_name="Manage vehicles"),
                _capability("fleet.assignment.manage", kind="write_access", display_name="Manage fleet assignments"),
            ],
            manifest={"field_registry": {"namespace": "fleet.vehicle.*"}},
        ),
        _module(
            "documents",
            kind=MODULE_KIND_PLATFORM,
            display_name="Document Hub",
            owner="document-hub",
            capabilities=[
                _capability("documents.view", kind="route_access", display_name="View documents"),
                _capability("documents.manage", kind="write_access", display_name="Manage documents"),
            ],
            manifest={"platform_layer": "document_hub"},
        ),
        _module(
            "process_engine",
            kind=MODULE_KIND_PLATFORM,
            display_name="Process Engine",
            owner="platform",
            capabilities=[
                _capability("process_engine.registry.read", kind="registry_access", display_name="Read process registry"),
                _capability("process_engine.evaluate", kind="runtime_evaluator", display_name="Evaluate process rules"),
            ],
            manifest={"platform_layer": "process_engine"},
        ),
        _module(
            "field_registry",
            kind=MODULE_KIND_PLATFORM,
            display_name="Field Registry / Card Configuration",
            owner="platform",
            capabilities=[
                _capability("field_registry.fields.read", kind="registry_access", display_name="Read fields"),
                _capability("field_registry.layouts.read", kind="registry_access", display_name="Read layouts"),
            ],
            manifest={"platform_layer": "field_registry"},
        ),
    ]
