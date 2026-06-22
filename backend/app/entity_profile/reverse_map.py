"""Reverse map legacy CandidateProfile.code → Entity Profile registry code (P3)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.entity_profile import PLATFORM_TENANT_SCOPE, EpEntityProfile


from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE

# Transitional static map — expanded in P4; registry manifest is canonical when seeded.
STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY: dict[str, str] = {
    "driver_ce_default": DRIVER_CE_PROFILE_CODE,
    "poltrakt_drivers": DRIVER_CE_PROFILE_CODE,
    "base": DRIVER_CE_PROFILE_CODE,
}


async def find_entity_profile_code_by_legacy_candidate_code(
    db: AsyncSession,
    *,
    tenant_id: str,
    legacy_candidate_profile_code: str,
) -> Optional[str]:
    """Transitional lookup: CandidateProfile.code → ep_entity_profiles.profile_code."""
    legacy_code = str(legacy_candidate_profile_code or "").strip()
    if not legacy_code:
        return None

    static = STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY.get(legacy_code)
    if static:
        return static

    tenant_scope = str(tenant_id).strip()

    profiles = (
        await db.execute(
            select(EpEntityProfile.profile_code, EpEntityProfile.config, EpEntityProfile.tenant_id).where(
                EpEntityProfile.tenant_id.in_([tenant_scope, PLATFORM_TENANT_SCOPE]),
                EpEntityProfile.status == "active",
            )
        )
    ).all()
    for profile_code, config, scope in profiles:
        cfg = config if isinstance(config, dict) else {}
        if str(cfg.get("legacy_candidate_profile_code") or "").strip() != legacy_code:
            continue
        if scope == tenant_scope:
            return str(profile_code).strip() or None
    for profile_code, config, scope in profiles:
        cfg = config if isinstance(config, dict) else {}
        if scope == PLATFORM_TENANT_SCOPE and str(cfg.get("legacy_candidate_profile_code") or "").strip() == legacy_code:
            return str(profile_code).strip() or None
    return None
