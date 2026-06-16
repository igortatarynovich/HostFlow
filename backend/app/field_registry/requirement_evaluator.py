"""Process Engine field requirement evaluation via Field Registry (P4)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.field_registry.populated_check import (
    candidate_field_is_populated,
    legacy_field_code_from_qualified,
    qualified_code_from_field_spec,
)
from backend.app.field_registry.registry import FieldRegistry
from backend.app.field_registry.resolver import canonical_field_to_dict
from backend.app.models.candidate import Candidate
from backend.app.models.field_registry import PLATFORM_TENANT_SCOPE, REGISTRY_STATUS_ACTIVE
from backend.app.models.process_engine import PeFieldRequirement
from backend.app.process_engine.constants import RECRUITMENT_MODULE

READY_FOR_HANDOFF_STAGE = "ready_for_handoff"


def _requirement_level(field_spec: dict[str, Any]) -> str:
    level = str(field_spec.get("level") or field_spec.get("requirement") or "optional").strip().lower()
    return level


def _matches_requirement_context(
    requirement_config: dict[str, Any],
    *,
    context: str,
    system_stage: Optional[str],
) -> bool:
    req_context = str(requirement_config.get("context") or "transition").strip().lower()
    if req_context != str(context or "").strip().lower():
        return False
    configured_stage = str(requirement_config.get("system_stage") or "").strip().lower()
    if configured_stage and system_stage:
        return configured_stage == str(system_stage).strip().lower()
    return True


async def _load_field_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    module: str,
    entity_type: str,
) -> list[PeFieldRequirement]:
    tenant_scope = str(tenant_id).strip()
    platform_rows = list(
        (
            await db.execute(
                select(PeFieldRequirement).where(
                    PeFieldRequirement.tenant_id == PLATFORM_TENANT_SCOPE,
                    PeFieldRequirement.module == module,
                    PeFieldRequirement.entity_type == entity_type,
                    PeFieldRequirement.status == REGISTRY_STATUS_ACTIVE,
                )
            )
        ).scalars()
    )
    tenant_rows = list(
        (
            await db.execute(
                select(PeFieldRequirement).where(
                    PeFieldRequirement.tenant_id == tenant_scope,
                    PeFieldRequirement.module == module,
                    PeFieldRequirement.entity_type == entity_type,
                    PeFieldRequirement.status == REGISTRY_STATUS_ACTIVE,
                )
            )
        ).scalars()
    )
    merged: dict[str, PeFieldRequirement] = {row.code: row for row in platform_rows}
    for row in tenant_rows:
        merged[row.code] = row
    return list(merged.values())


async def _resolve_canonical_field(
    db: AsyncSession,
    *,
    tenant_id: str,
    qualified_code: str,
) -> dict[str, Any] | None:
    field = await FieldRegistry.get_canonical_field(
        db,
        tenant_id=str(tenant_id),
        qualified_code=qualified_code,
    )
    if field is None:
        return None
    payload = canonical_field_to_dict(field)
    payload["storage"] = dict((field.config or {}).get("storage") or payload.get("storage") or {})
    return payload


async def evaluate_field_requirements_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    module: str = RECRUITMENT_MODULE,
    entity_type: str = "candidate",
    context: str = "transition",
    system_stage: Optional[str] = READY_FOR_HANDOFF_STAGE,
) -> dict[str, Any]:
    """Evaluate PE field requirements against candidate data using registry storage paths."""
    requirements = await _load_field_requirements(
        db,
        tenant_id=tenant_id,
        module=module,
        entity_type=entity_type,
    )

    missing_fields: list[dict[str, str]] = []
    blocking_reasons: list[dict[str, Any]] = []
    evaluated_codes: set[str] = set()

    for requirement in requirements:
        config = dict(requirement.config or {})
        if not _matches_requirement_context(config, context=context, system_stage=system_stage):
            continue

        for field_spec in config.get("fields") or []:
            if not isinstance(field_spec, dict):
                continue
            if _requirement_level(field_spec) != "required":
                continue

            qualified_code = qualified_code_from_field_spec(field_spec)
            if not qualified_code or qualified_code in evaluated_codes:
                continue
            evaluated_codes.add(qualified_code)

            canonical = await _resolve_canonical_field(
                db,
                tenant_id=tenant_id,
                qualified_code=qualified_code,
            )
            storage = (canonical or {}).get("storage")
            label = str(
                (canonical or {}).get("name")
                or field_spec.get("label")
                or legacy_field_code_from_qualified(qualified_code)
                or qualified_code
            )
            field_code = legacy_field_code_from_qualified(qualified_code)

            if candidate_field_is_populated(candidate, storage):
                continue

            missing_fields.append(
                {
                    "qualified_code": qualified_code,
                    "field_code": field_code,
                    "label": label,
                    "requirement_code": requirement.code,
                }
            )
            blocking_reasons.append(
                {
                    "code": "missing_data_field",
                    "message": f"Missing required data: {label}",
                    "source_layer": "field_requirements",
                    "qualified_code": qualified_code,
                    "field_code": field_code,
                    "label": label,
                    "requirement_code": requirement.code,
                }
            )

    return {
        "missing_fields": missing_fields,
        "blocking_reasons": blocking_reasons,
        "context": context,
        "system_stage": system_stage,
        "requirement_count": len(requirements),
    }
