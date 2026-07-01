"""Vacancy → Entity Profile bridge (P4)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.reverse_map import find_entity_profile_code_by_legacy_candidate_code
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy


async def resolve_entity_profile_hints_from_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve ``entity_profile_code`` + legacy profile hints from vacancy.candidate_profile_id."""
    vid = str(vacancy_id or "").strip()
    if not vid:
        return None, None, None

    vacancy = await db.get(Vacancy, vid)
    if vacancy is None or str(vacancy.tenant_id) != str(tenant_id):
        return None, None, None

    profile_id = str(getattr(vacancy, "candidate_profile_id", None) or "").strip()
    if not profile_id:
        return None, None, None

    profile = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == profile_id,
                CandidateProfile.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        return None, profile_id, None

    legacy_code = str(profile.code or "").strip() or None
    entity_code = None
    if legacy_code:
        entity_code = await find_entity_profile_code_by_legacy_candidate_code(
            db,
            tenant_id=str(tenant_id),
            legacy_candidate_profile_code=legacy_code,
        )
    return entity_code, profile_id, legacy_code
