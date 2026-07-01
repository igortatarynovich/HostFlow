"""Legacy mapping between Process Engine registry and pre-P1 recruitment artifacts."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.process_engine import PeProcessProfile
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.pipeline_mapping import (
    ensure_recruitment_funnel_stages_mapped,
    sync_funnel_stages_from_pipeline_config,
)

__all__ = [
    "backfill_candidate_profile_links",
    "ensure_recruitment_funnel_stages_mapped",
    "link_process_profile_to_candidate_profile",
    "resolve_process_profile_for_candidate_profile",
    "sync_funnel_stages_from_pipeline_config",
]


async def link_process_profile_to_candidate_profile(
    db: AsyncSession,
    *,
    entity: PeProcessProfile,
    tenant_id: str,
) -> None:
    legacy_code = str((entity.config or {}).get("legacy_candidate_profile_code") or "").strip()
    if not legacy_code:
        return
    row = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.code == legacy_code,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return
    entity.legacy_candidate_profile_id = row.id
    if getattr(row, "pe_process_profile_id", None) != entity.id:
        row.pe_process_profile_id = entity.id


async def resolve_process_profile_for_candidate_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_profile_id: str,
) -> Optional[PeProcessProfile]:
    profile = (
        await db.execute(
            select(PeProcessProfile).where(
                PeProcessProfile.tenant_id == tenant_id,
                PeProcessProfile.legacy_candidate_profile_id == candidate_profile_id,
                PeProcessProfile.module == RECRUITMENT_MODULE,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if profile is not None:
        return profile
    cp = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == candidate_profile_id,
                CandidateProfile.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if cp is None or not getattr(cp, "pe_process_profile_id", None):
        return None
    return (
        await db.execute(
            select(PeProcessProfile).where(PeProcessProfile.id == cp.pe_process_profile_id)
        )
    ).scalar_one_or_none()


async def backfill_candidate_profile_links(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
    legacy_candidate_profile_id: str,
) -> None:
    await db.execute(
        update(CandidateProfile)
        .where(
            CandidateProfile.id == legacy_candidate_profile_id,
            CandidateProfile.tenant_id == tenant_id,
        )
        .values(pe_process_profile_id=process_profile_id)
    )
