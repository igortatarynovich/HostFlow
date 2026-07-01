"""Read-only Entity Profile resolver (P1)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.registry import EntityProfileRegistry
from backend.app.field_registry.resolver import canonical_field_to_dict
from backend.app.models.entity_profile import (
    PLATFORM_TENANT_SCOPE,
    EpEntityProfile,
    EpEntityProfileField,
    EpIntakePresentation,
)
from backend.app.models.field_registry import FrCanonicalField


def entity_profile_to_dict(profile: EpEntityProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "profile_code": profile.profile_code,
        "entity_type": profile.entity_type,
        "module_owner": profile.module_owner,
        "name": profile.name,
        "description": profile.description,
        "default_layout_code": profile.default_layout_code,
        "document_pack_code": profile.document_pack_code,
        "process_profile_code": profile.process_profile_code,
        "registry_version": profile.registry_version,
        "status": profile.status,
        "version": profile.version,
        "config": dict(profile.config or {}),
    }


def profile_field_to_dict(
    profile_field: EpEntityProfileField,
    canonical: Optional[FrCanonicalField],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "qualified_code": profile_field.qualified_code,
        "sort_order": profile_field.sort_order,
        "intake_level": profile_field.intake_level,
        "card_save_level": profile_field.card_save_level,
        "transition_level": profile_field.transition_level,
        "is_active": profile_field.is_active,
        "canonical_field_id": profile_field.canonical_field_id,
    }
    if canonical is not None:
        payload["field"] = canonical_field_to_dict(canonical)
    else:
        payload["field"] = None
    return payload


async def resolve_effective_entity_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_code: str,
    include_presentations: bool = False,
) -> dict[str, Any]:
    """Resolve Entity Profile with Field Registry-backed field definitions."""
    tenant_scope = str(tenant_id)
    profile = await EntityProfileRegistry.get_entity_profile(
        db,
        tenant_id=tenant_scope,
        profile_code=profile_code,
    )
    if profile is None:
        return {
            "profile_code": profile_code,
            "resolution_source": "not_found",
            "profile": None,
            "fields": [],
            "presentations": [],
        }

    resolution_source = "tenant_profile" if profile.tenant_id == tenant_scope else "platform_catalog"

    rows = (
        await db.execute(
            select(EpEntityProfileField, FrCanonicalField)
            .outerjoin(
                FrCanonicalField,
                FrCanonicalField.id == EpEntityProfileField.canonical_field_id,
            )
            .where(
                EpEntityProfileField.entity_profile_id == profile.id,
                EpEntityProfileField.is_active.is_(True),
            )
            .order_by(EpEntityProfileField.sort_order.asc())
        )
    ).all()

    fields_out: list[dict[str, Any]] = []
    for profile_field, canonical in rows:
        if canonical is None:
            canonical = (
                await db.execute(
                    select(FrCanonicalField).where(
                        FrCanonicalField.qualified_code == profile_field.qualified_code,
                    ).limit(1)
                )
            ).scalar_one_or_none()
        fields_out.append(profile_field_to_dict(profile_field, canonical))

    presentations_out: list[dict[str, Any]] = []
    if include_presentations:
        presentation_rows = (
            await db.execute(
                select(EpIntakePresentation).where(
                    EpIntakePresentation.entity_profile_id == profile.id,
                    EpIntakePresentation.is_active.is_(True),
                    EpIntakePresentation.tenant_id.in_([tenant_scope, PLATFORM_TENANT_SCOPE]),
                )
            )
        ).scalars().all()
        for presentation in presentation_rows:
            presentations_out.append(
                {
                    "presentation_code": presentation.presentation_code,
                    "field_subset": list(presentation.field_subset or []),
                    "presentation_overrides": dict(presentation.presentation_overrides or {}),
                    "intake_source_binding_id": presentation.intake_source_binding_id,
                }
            )

    return {
        "profile_code": profile.profile_code,
        "resolution_source": resolution_source,
        "profile": entity_profile_to_dict(profile),
        "fields": fields_out,
        "presentations": presentations_out,
    }
