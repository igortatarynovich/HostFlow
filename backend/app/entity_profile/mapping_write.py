"""Intake source field mapping write path (P9).

Mapping selects qualified_code targets from Entity Profile only — never creates fields.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import ENTITY_CANDIDATE
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import resolve_entity_profile_facade
from backend.app.entity_profile.mapping_validation import (
    MappingValidationResult,
    allowed_qualified_codes_from_profile_view,
    rule_qualified_code,
    validate_mapping_rules_for_profile,
)
from backend.app.field_registry.intake_mapping import enrich_mapping_rules_for_storage


class MappingWriteError(ValueError):
    def __init__(self, code: str, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _entity_type_mismatch(qualified_code: str, profile_entity_type: str) -> bool:
    code = str(qualified_code or "").strip().lower()
    entity = str(profile_entity_type or "").strip().lower()
    if not code or not entity:
        return False
    if entity == ENTITY_CANDIDATE:
        if code.startswith("recruitment.client.") or code.startswith("sales.client."):
            return True
        return False
    if entity in {"client", "company", "client_lead"}:
        if code.startswith("recruitment.candidate.") and not code.startswith("recruitment.lead."):
            return True
    return False


async def validate_intake_mapping_rules_write(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    rules: list[dict[str, Any]],
    reject_on_any_invalid: bool = True,
) -> tuple[list[dict[str, Any]], MappingValidationResult]:
    profile_code = str(entity_profile_code or "").strip()
    if not profile_code:
        raise MappingWriteError(code="entity_profile_code_required", message="entity_profile_code is required")

    try:
        profile_view = await resolve_entity_profile_facade(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=profile_code,
            include_presentations=False,
        )
    except EntityProfileNotFoundError as exc:
        raise MappingWriteError(
            code="entity_profile_not_found",
            message=str(exc),
            details={"entity_profile_code": profile_code},
        ) from exc

    if profile_view.get("resolution_source") == "not_found" or not profile_view.get("profile"):
        raise MappingWriteError(
            code="entity_profile_not_found",
            message=f"Entity profile not found: {profile_code}",
            details={"entity_profile_code": profile_code},
        )

    profile_meta = profile_view.get("profile") or {}
    profile_entity_type = str(profile_meta.get("entity_type") or "").strip()
    allowed = allowed_qualified_codes_from_profile_view(profile_view)

    normalized_rules = enrich_mapping_rules_for_storage([dict(r) for r in rules if isinstance(r, dict)])
    entity_mismatches: list[str] = []
    for rule in normalized_rules:
        qualified = rule_qualified_code(rule)
        if qualified and _entity_type_mismatch(qualified, profile_entity_type):
            entity_mismatches.append(qualified)

    if entity_mismatches:
        raise MappingWriteError(
            code="mapping_entity_type_mismatch",
            message="Mapping target qualified_code does not match Entity Profile entity type",
            details={"qualified_codes": entity_mismatches, "entity_type": profile_entity_type},
        )

    validation = validate_mapping_rules_for_profile(
        normalized_rules,
        allowed_qualified_codes=allowed,
        entity_profile_code=profile_code,
        resolution_source=str(profile_view.get("resolution_source") or "entity_profile"),
    )

    if reject_on_any_invalid and validation.rejected_rules:
        raise MappingWriteError(
            code="mapping_target_not_in_profile",
            message="Mapping targets must belong to the selected Entity Profile",
            details={
                "rejected_rules": validation.rejected_rules,
                "entity_profile_code": profile_code,
            },
        )

    return validation.accepted_rules, validation
