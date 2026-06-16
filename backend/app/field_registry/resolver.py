"""Read-only Field Registry / Card Layout resolver (P1)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.field_registry.registry import FieldRegistry
from backend.app.models.field_registry import (
    PLATFORM_TENANT_SCOPE,
    FrCanonicalField,
    FrCardLayoutField,
    FrCardLayoutProfile,
)


def canonical_field_to_dict(field: FrCanonicalField) -> dict[str, Any]:
    config = dict(field.config or {})
    return {
        "id": field.id,
        "qualified_code": field.qualified_code,
        "module": field.module,
        "entity_type": field.entity_type,
        "field_type": field.field_type,
        "label_key": field.label_key,
        "name": field.name,
        "ownership": field.ownership,
        "reference_domain": field.reference_domain,
        "pii_class": field.pii_class,
        "storage": config.get("storage"),
        "legacy_aliases": config.get("legacy_aliases") or [],
        "registry_version": field.registry_version,
        "status": field.status,
    }


async def resolve_effective_card_layout(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_type: str,
    layout_code: Optional[str] = None,
    module: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve read-only effective card layout — tenant scope first, then platform catalog."""
    tenant_scope = str(tenant_id)
    profile: FrCardLayoutProfile | None = None
    resolution_source = "platform_catalog"

    if layout_code:
        profile = await FieldRegistry.get_layout_profile(
            db, tenant_id=tenant_scope, layout_code=layout_code, module=module
        )
        if profile is not None:
            resolution_source = "tenant_layout"
    if profile is None and layout_code:
        profile = await FieldRegistry.get_layout_profile(
            db, tenant_id=PLATFORM_TENANT_SCOPE, layout_code=layout_code, module=module
        )
        if profile is not None:
            resolution_source = "platform_layout"
    if profile is None:
        profile = await FieldRegistry.get_default_layout_profile(
            db, tenant_id=tenant_scope, entity_type=entity_type, module=module
        )
        if profile is not None:
            resolution_source = "tenant_default"
    if profile is None:
        profile = await FieldRegistry.get_default_layout_profile(
            db, tenant_id=PLATFORM_TENANT_SCOPE, entity_type=entity_type, module=module
        )
        if profile is not None:
            resolution_source = "platform_default"

    if profile is None:
        return {
            "entity_type": entity_type,
            "layout_code": layout_code,
            "resolution_source": "not_found",
            "sections": [],
            "fields": [],
        }

    rows = (
        await db.execute(
            select(FrCardLayoutField, FrCanonicalField)
            .join(FrCanonicalField, FrCanonicalField.id == FrCardLayoutField.canonical_field_id)
            .where(FrCardLayoutField.layout_profile_id == profile.id)
            .order_by(FrCardLayoutField.section_code.asc(), FrCardLayoutField.sort_order.asc())
        )
    ).all()

    sections: dict[str, dict[str, Any]] = {}
    fields_out: list[dict[str, Any]] = []
    for layout_field, canonical in rows:
        section_code = layout_field.section_code
        section = sections.setdefault(
            section_code,
            {"code": section_code, "order": layout_field.sort_order, "fields": []},
        )
        field_payload = {
            **canonical_field_to_dict(canonical),
            "section_code": section_code,
            "sort_order": layout_field.sort_order,
            "visible": layout_field.visible,
            "required": layout_field.required,
            "label_override": layout_field.label_override,
        }
        section["fields"].append(field_payload)
        fields_out.append(field_payload)

    ordered_sections = sorted(sections.values(), key=lambda s: s.get("order") or 0)
    return {
        "entity_type": entity_type,
        "layout_code": profile.code,
        "layout_name": profile.name,
        "module": profile.module,
        "is_default": profile.is_default,
        "resolution_source": resolution_source,
        "registry_version": profile.registry_version,
        "sections": ordered_sections,
        "fields": fields_out,
    }


async def list_canonical_fields_for_scope(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_type: Optional[str] = None,
    module: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List canonical fields — merges tenant overrides over platform catalog by qualified_code."""
    platform_fields = await FieldRegistry.list_canonical_fields(
        db, tenant_id=PLATFORM_TENANT_SCOPE, entity_type=entity_type, module=module
    )
    tenant_fields = await FieldRegistry.list_canonical_fields(
        db, tenant_id=str(tenant_id), entity_type=entity_type, module=module
    )
    merged: dict[str, FrCanonicalField] = {f.qualified_code: f for f in platform_fields}
    for field in tenant_fields:
        merged[field.qualified_code] = field
    return [canonical_field_to_dict(f) for f in sorted(merged.values(), key=lambda x: x.qualified_code)]
