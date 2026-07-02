"""C2 — deprecate CandidateProfile.config semantic writes (field/document matrix)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.reverse_map import (
    STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY,
    find_entity_profile_code_by_legacy_candidate_code,
)

DEPRECATED_CONFIG_KEYS = frozenset({"field_configs", "document_configs"})
DEPRECATION_WARNING_PREFIX = "candidate_profile_config_deprecated"


def _config_dict(config: dict[str, Any] | None) -> dict[str, Any]:
    return dict(config) if isinstance(config, dict) else {}


def deprecated_config_fragments_changed(
    previous_config: dict[str, Any] | None,
    next_config: dict[str, Any] | None,
) -> list[str]:
    """Return deprecated config keys whose values changed between writes."""
    previous = _config_dict(previous_config)
    updated = _config_dict(next_config)
    return [key for key in DEPRECATED_CONFIG_KEYS if previous.get(key) != updated.get(key)]


async def is_legacy_candidate_profile_mapped(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_code: str,
) -> bool:
    code = str(profile_code or "").strip()
    if not code:
        return False
    if code in STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY:
        return True
    mapped = await find_entity_profile_code_by_legacy_candidate_code(
        db,
        tenant_id=str(tenant_id),
        legacy_candidate_profile_code=code,
    )
    return bool(mapped)


async def enforce_candidate_profile_config_write(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_code: str,
    previous_config: dict[str, Any] | None,
    next_config: dict[str, Any] | None,
) -> list[str]:
    """Block semantic config writes for mapped profiles; warn on unmapped legacy writes."""
    changed_keys = deprecated_config_fragments_changed(previous_config, next_config)
    if not changed_keys:
        return []

    if await is_legacy_candidate_profile_mapped(
        db,
        tenant_id=str(tenant_id),
        profile_code=str(profile_code),
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": DEPRECATION_WARNING_PREFIX,
                "message": (
                    "CandidateProfile.config field_configs/document_configs are deprecated for "
                    "profiles mapped to Entity Profile. Edit Entity Profile fields, intake forms, "
                    "or card layout registry instead."
                ),
                "changed_keys": changed_keys,
                "profile_code": str(profile_code),
            },
        )

    return [f"{DEPRECATION_WARNING_PREFIX}:{key}" for key in changed_keys]
