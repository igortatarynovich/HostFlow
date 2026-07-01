"""Effective process profile resolution (Process Engine P3).

Resolution order for recruitment:
1. vacancy.pe_process_profile_id (explicit binding)
2. legacy bridge: vacancy.candidate_profile_id → PeProcessProfile / CandidateProfile.pe_process_profile_id
3. tenant default recruitment profile (is_default on tenant scope)
4. system recruitment default (platform scope, code recruitment_default)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.process_engine import (
    PLATFORM_TENANT_SCOPE,
    REGISTRY_STATUS_ACTIVE,
    PeProcessProfile,
)
from backend.app.models.vacancy import Vacancy
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.legacy_mapping import resolve_process_profile_for_candidate_profile
from backend.app.process_engine.manifests.recruitment import DEFAULT_PROFILE_CODE
from backend.app.process_engine.registry import ProcessEngineRegistry

ProcessProfileSource = Literal[
    "vacancy",
    "legacy_candidate_profile",
    "tenant_default",
    "system_default",
]


@dataclass(frozen=True)
class EffectiveProcessProfile:
    profile: PeProcessProfile
    source: ProcessProfileSource

    @property
    def profile_id(self) -> str:
        return str(self.profile.id)

    @property
    def profile_code(self) -> str:
        return str(self.profile.code or "")


def effective_process_profile_to_dict(resolved: EffectiveProcessProfile) -> dict[str, Any]:
    return {
        "process_profile_id": resolved.profile_id,
        "process_profile_code": resolved.profile_code,
        "process_profile_source": resolved.source,
        "module": str(resolved.profile.module or RECRUITMENT_MODULE),
    }


async def _load_active_process_profile(
    db: AsyncSession,
    *,
    profile_id: str,
    module: str,
    tenant_id: str | None = None,
) -> Optional[PeProcessProfile]:
    stmt = select(PeProcessProfile).where(
        PeProcessProfile.id == profile_id,
        PeProcessProfile.module == module,
        PeProcessProfile.status == REGISTRY_STATUS_ACTIVE,
    )
    if tenant_id is not None:
        stmt = stmt.where(
            PeProcessProfile.tenant_id.in_([tenant_id, PLATFORM_TENANT_SCOPE])
        )
    return (await db.execute(stmt.limit(1))).scalar_one_or_none()


async def _resolve_system_default_process_profile(
    db: AsyncSession,
    *,
    module: str,
) -> Optional[PeProcessProfile]:
    by_code = (
        await db.execute(
            select(PeProcessProfile)
            .where(
                PeProcessProfile.module == module,
                PeProcessProfile.tenant_id == PLATFORM_TENANT_SCOPE,
                PeProcessProfile.code == DEFAULT_PROFILE_CODE,
                PeProcessProfile.status == REGISTRY_STATUS_ACTIVE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if by_code is not None:
        return by_code
    return (
        await db.execute(
            select(PeProcessProfile)
            .where(
                PeProcessProfile.module == module,
                PeProcessProfile.tenant_id == PLATFORM_TENANT_SCOPE,
                PeProcessProfile.is_default.is_(True),
                PeProcessProfile.status == REGISTRY_STATUS_ACTIVE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def resolve_effective_process_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy: Vacancy | None = None,
    module: str = RECRUITMENT_MODULE,
) -> Optional[EffectiveProcessProfile]:
    """Resolve effective process profile for a vacancy (or tenant/system defaults when vacancy is None)."""
    tenant_scope = str(tenant_id or "").strip()

    explicit_id = str(getattr(vacancy, "pe_process_profile_id", None) or "").strip() if vacancy else ""
    if explicit_id:
        profile = await _load_active_process_profile(
            db,
            profile_id=explicit_id,
            module=module,
            tenant_id=tenant_scope,
        )
        if profile is not None:
            return EffectiveProcessProfile(profile=profile, source="vacancy")

    legacy_candidate_profile_id = (
        str(getattr(vacancy, "candidate_profile_id", None) or "").strip() if vacancy else ""
    )
    if legacy_candidate_profile_id and tenant_scope:
        legacy_profile = await resolve_process_profile_for_candidate_profile(
            db,
            tenant_id=tenant_scope,
            candidate_profile_id=legacy_candidate_profile_id,
        )
        if legacy_profile is not None and str(legacy_profile.module or "") == module:
            return EffectiveProcessProfile(profile=legacy_profile, source="legacy_candidate_profile")

    if tenant_scope:
        tenant_default = await ProcessEngineRegistry.get_default_process_profile(
            db,
            module=module,
            tenant_id=tenant_scope,
        )
        if tenant_default is not None:
            return EffectiveProcessProfile(profile=tenant_default, source="tenant_default")

    system_default = await _resolve_system_default_process_profile(db, module=module)
    if system_default is not None:
        return EffectiveProcessProfile(profile=system_default, source="system_default")

    return None


async def resolve_effective_process_profile_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    module: str = RECRUITMENT_MODULE,
) -> Optional[EffectiveProcessProfile]:
    """Candidate inherits process profile from its vacancy, then tenant/system defaults."""
    vacancy: Vacancy | None = None
    vacancy_id = str(getattr(candidate, "vacancy_id", None) or "").strip()
    if vacancy_id:
        vacancy = (
            await db.execute(
                select(Vacancy).where(
                    Vacancy.id == vacancy_id,
                    Vacancy.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
    return await resolve_effective_process_profile(
        db,
        tenant_id=str(tenant_id),
        vacancy=vacancy,
        module=module,
    )


async def resolve_effective_process_profile_for_candidate_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    module: str = RECRUITMENT_MODULE,
) -> Optional[EffectiveProcessProfile]:
    candidate = (
        await db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if candidate is None:
        return None
    return await resolve_effective_process_profile_for_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
        module=module,
    )
