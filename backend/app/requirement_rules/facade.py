"""Requirement Rules facade — resolves Entity Profile then compiles/evaluates rules (P1)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import resolve_entity_profile_facade
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.registry import (
    RequirementRulesNotFoundError,
    build_requirement_rule_set,
)


async def resolve_requirement_rule_set(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    context: str = "readiness",
    stage_code: str | None = None,
    transition_code: str | None = None,
) -> dict[str, Any]:
    profile_code = str(entity_profile_code or "").strip()
    if not profile_code:
        raise RequirementRulesNotFoundError(entity_profile_code="")

    try:
        profile_view = await resolve_entity_profile_facade(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=profile_code,
            include_presentations=False,
        )
    except EntityProfileNotFoundError as exc:
        raise RequirementRulesNotFoundError(entity_profile_code=profile_code) from exc

    if profile_view.get("resolution_source") == "not_found" or not profile_view.get("profile"):
        raise RequirementRulesNotFoundError(entity_profile_code=profile_code)

    return build_requirement_rule_set(
        profile_view,
        context=context,
        stage_code=stage_code,
        transition_code=transition_code,
    )


async def evaluate_entity_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    context: str,
    normalized_payload: Optional[dict[str, Any]] = None,
    documents: Optional[list[Any]] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    stage_code: str | None = None,
    transition_code: str | None = None,
) -> dict[str, Any]:
    profile_code = str(entity_profile_code or "").strip()
    if not profile_code:
        raise RequirementRulesNotFoundError(entity_profile_code="")

    try:
        profile_view = await resolve_entity_profile_facade(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=profile_code,
            include_presentations=False,
        )
    except EntityProfileNotFoundError as exc:
        raise RequirementRulesNotFoundError(entity_profile_code=profile_code) from exc

    if profile_view.get("resolution_source") == "not_found" or not profile_view.get("profile"):
        raise RequirementRulesNotFoundError(entity_profile_code=profile_code)

    return evaluate_requirement_rules(
        profile_view,
        context=context,
        normalized_payload=normalized_payload,
        documents=documents,
        entity_type=entity_type,
        entity_id=entity_id,
        stage_code=stage_code,
        transition_code=transition_code,
    )
