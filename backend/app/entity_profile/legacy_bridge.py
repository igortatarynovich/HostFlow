"""Legacy CandidateProfile → Entity Profile facade view (P2 bridge)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.field_registry.intake_mapping import qualified_code_from_legacy_target
from backend.app.field_registry.registry import FieldRegistry
from backend.app.field_registry.resolver import canonical_field_to_dict
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.field_registry import PLATFORM_TENANT_SCOPE, FrCanonicalField


def _legacy_level(required: bool, visible: bool) -> str:
    if visible is False:
        return "hidden"
    if required:
        return "required"
    return "optional"


def _match_canonical_for_legacy_key(
    field_key: str,
    canonical_index: dict[str, FrCanonicalField],
) -> Optional[FrCanonicalField]:
    key = str(field_key or "").strip()
    if not key:
        return None
    qualified = qualified_code_from_legacy_target(key)
    if qualified and qualified in canonical_index:
        return canonical_index[qualified]
    if key in canonical_index:
        return canonical_index[key]
    for canonical in canonical_index.values():
        config = dict(canonical.config or {})
        aliases = [str(a) for a in (config.get("legacy_aliases") or []) if str(a).strip()]
        storage = config.get("storage") or {}
        path = str(storage.get("path") or "").strip()
        tail = path.split(".")[-1] if path else ""
        if key in aliases or key == tail or key == canonical.code:
            return canonical
    return None


async def _canonical_index_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_type: str = "candidate",
) -> dict[str, FrCanonicalField]:
    platform_fields = await FieldRegistry.list_canonical_fields(
        db, tenant_id=PLATFORM_TENANT_SCOPE, entity_type=entity_type
    )
    tenant_fields = await FieldRegistry.list_canonical_fields(
        db, tenant_id=str(tenant_id), entity_type=entity_type
    )
    merged: dict[str, FrCanonicalField] = {f.qualified_code: f for f in platform_fields}
    for field in tenant_fields:
        merged[field.qualified_code] = field
    return merged


async def build_legacy_profile_view_from_candidate_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: CandidateProfile,
) -> dict[str, Any]:
    """Translate CandidateProfile.config into unified Entity Profile facade shape."""
    configs = (profile.config or {}).get("field_configs") or []
    if not isinstance(configs, list):
        configs = []

    canonical_index = await _canonical_index_for_tenant(db, tenant_id=tenant_id)
    fields_out: list[dict[str, Any]] = []
    warnings: list[str] = []
    sort_order = 10

    for row in configs:
        if not isinstance(row, dict):
            continue
        field_key = str(row.get("field_key") or "").strip()
        if not field_key:
            continue
        canonical = _match_canonical_for_legacy_key(field_key, canonical_index)
        required = row.get("required") is True
        visible = row.get("visible") is not False
        level = _legacy_level(required, visible)
        if canonical is None:
            warnings.append(f"legacy_unknown_field:{field_key}")
            fields_out.append(
                {
                    "qualified_code": None,
                    "legacy_field_key": field_key,
                    "sort_order": int(row.get("order") or sort_order),
                    "intake_level": level,
                    "card_save_level": level,
                    "transition_level": "optional",
                    "is_active": visible,
                    "canonical_field_id": None,
                    "field": None,
                    "label_override": str(row.get("label") or "").strip() or None,
                }
            )
        else:
            fields_out.append(
                {
                    "qualified_code": canonical.qualified_code,
                    "legacy_field_key": field_key,
                    "sort_order": int(row.get("order") or sort_order),
                    "intake_level": level,
                    "card_save_level": level,
                    "transition_level": "optional",
                    "is_active": visible,
                    "canonical_field_id": canonical.id,
                    "field": canonical_field_to_dict(canonical),
                    "label_override": str(row.get("label") or "").strip() or None,
                }
            )
        sort_order += 10

    if warnings:
        warnings.insert(0, "legacy_candidate_profile_fallback")

    document_configs = (profile.config or {}).get("document_configs") or []
    return {
        "profile_code": None,
        "entity_profile_code": None,
        "resolution_source": "legacy_candidate_profile",
        "bridge_source": "legacy_candidate_profile",
        "profile": {
            "id": profile.id,
            "profile_code": None,
            "entity_type": "candidate",
            "module_owner": "recruitment",
            "name": profile.name,
            "description": profile.description,
            "default_layout_code": None,
            "document_pack_code": None,
            "process_profile_code": None,
            "registry_version": "legacy_candidate_profile_v1",
            "status": "active" if profile.is_active else "archived",
            "version": 1,
            "config": {
                "legacy_candidate_profile_code": profile.code,
                "document_configs": document_configs,
                "legacy_config": dict(profile.config or {}),
            },
        },
        "fields": fields_out,
        "presentations": [],
        "warnings": warnings,
        "candidate_profile_id": profile.id,
        "candidate_profile_code": profile.code,
    }


async def list_legacy_unknown_field_warnings(
    db: AsyncSession,
    *,
    tenant_id: str,
    field_keys: list[str],
) -> list[str]:
    """Return warning tokens for legacy keys that do not map to Field Registry."""
    canonical_index = await _canonical_index_for_tenant(db, tenant_id=tenant_id)
    warnings: list[str] = []
    for key in field_keys:
        if not _match_canonical_for_legacy_key(key, canonical_index):
            warnings.append(f"legacy_unknown_field:{key}")
    return warnings
