"""Seed Process Engine registry defaults for tenants."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.funnel import Funnel
from backend.app.models.process_engine import (
    PLATFORM_TENANT_SCOPE,
    PePipelineTemplate,
    PeProcessProfile,
    PeSystemStage,
)
from backend.app.models.vacancy import Vacancy
from backend.app.process_engine.legacy_mapping import (
    ensure_recruitment_funnel_stages_mapped,
    sync_funnel_stages_from_pipeline_config,
)
from backend.app.process_engine.manifests.hr import HR_MODULE, hr_module_manifest
from backend.app.process_engine.manifests.recruitment import (
    DEFAULT_PIPELINE_CODE,
    DEFAULT_PROFILE_CODE,
    RECRUITMENT_MODULE,
    recruitment_module_manifest,
)
from backend.app.process_engine.registry import ProcessEngineRegistry


async def _platform_module_registered(
    db: AsyncSession,
    *,
    module: str,
) -> bool:
    existing = (
        await db.execute(
            select(PeProcessProfile)
            .where(
                PeProcessProfile.module == module,
                PeProcessProfile.tenant_id == PLATFORM_TENANT_SCOPE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return True
    stage = (
        await db.execute(
            select(PeSystemStage)
            .where(
                PeSystemStage.module == module,
                PeSystemStage.tenant_id == PLATFORM_TENANT_SCOPE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return stage is not None


async def ensure_platform_process_engine_catalog(db: AsyncSession) -> None:
    """Register platform-global module manifests (tenant scope = empty string)."""
    if not await _platform_module_registered(db, module=RECRUITMENT_MODULE):
        await ProcessEngineRegistry.register_module(
            db,
            recruitment_module_manifest(),
            tenant_id=PLATFORM_TENANT_SCOPE,
        )
    if not await _platform_module_registered(db, module=HR_MODULE):
        await ProcessEngineRegistry.register_module(
            db,
            hr_module_manifest(),
            tenant_id=PLATFORM_TENANT_SCOPE,
        )


async def ensure_hr_process_engine_stages(db: AsyncSession, tenant_id: str) -> dict[str, Any]:
    """Register HR system stages for a tenant when HR module is enabled.

    Stages-only — no pipeline template, process profile, or funnel runtime (HR P0).
    """
    from backend.app.api.v1.tenants import service as tenant_service

    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        return {}
    modules = tenant_service.get_module_settings_snapshot(tenant)
    if not modules.get("hr"):
        return {}

    existing = (
        await db.execute(
            select(PeSystemStage)
            .where(
                PeSystemStage.module == HR_MODULE,
                PeSystemStage.tenant_id == str(tenant_id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"module": HR_MODULE, "tenant_id": str(tenant_id), "skipped": True}

    return await ProcessEngineRegistry.register_module(
        db,
        hr_module_manifest(),
        tenant_id=str(tenant_id),
        link_legacy=False,
    )


async def ensure_recruitment_process_engine_defaults(db: AsyncSession, tenant_id: str) -> dict:
    """Register recruitment module rows for a tenant and link legacy CandidateProfile / Funnel."""
    manifest = recruitment_module_manifest()
    result = await ProcessEngineRegistry.register_module(
        db,
        manifest,
        tenant_id=str(tenant_id),
        link_legacy=True,
    )

    profile = await ProcessEngineRegistry.get_default_process_profile(
        db, module=RECRUITMENT_MODULE, tenant_id=str(tenant_id)
    )
    if profile is None or str(profile.code or "") != DEFAULT_PROFILE_CODE:
        raise RuntimeError(
            f"Process Engine seed invariant failed: tenant {tenant_id} missing "
            f"recruitment default profile code {DEFAULT_PROFILE_CODE!r}"
        )
    pipeline = None
    if profile and profile.pipeline_template_id:
        pipeline = (
            await db.execute(
                select(PePipelineTemplate).where(PePipelineTemplate.id == profile.pipeline_template_id)
            )
        ).scalar_one_or_none()

    legacy_funnel_id = None
    if profile and profile.legacy_candidate_profile_id:
        from backend.app.models.candidate_profile import CandidateProfile

        cp = (
            await db.execute(
                select(CandidateProfile).where(CandidateProfile.id == profile.legacy_candidate_profile_id)
            )
        ).scalar_one_or_none()
        legacy_funnel_id = getattr(cp, "funnel_id", None) if cp else None

    if pipeline is None:
        pipeline = (
            await db.execute(
                select(PePipelineTemplate).where(
                    PePipelineTemplate.tenant_id == str(tenant_id),
                    PePipelineTemplate.module == RECRUITMENT_MODULE,
                    PePipelineTemplate.code == DEFAULT_PIPELINE_CODE,
                )
            )
        ).scalar_one_or_none()

    if legacy_funnel_id is None:
        funnel = (
            await db.execute(
                select(Funnel)
                .where(
                    Funnel.tenant_id == str(tenant_id),
                    Funnel.type == "candidate",
                    Funnel.is_default.is_(True),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        legacy_funnel_id = funnel.id if funnel else None

    if pipeline:
        if legacy_funnel_id and not pipeline.legacy_funnel_id:
            pipeline.legacy_funnel_id = legacy_funnel_id
        await sync_funnel_stages_from_pipeline_config(
            db,
            tenant_id=str(tenant_id),
            pipeline_config=pipeline.config or {},
            legacy_funnel_id=legacy_funnel_id or pipeline.legacy_funnel_id,
        )

    await ensure_recruitment_funnel_stages_mapped(db, tenant_id=str(tenant_id))

    await _backfill_vacancy_process_profile_links(db, tenant_id=str(tenant_id), default_profile=profile)

    from backend.app.process_engine.transition_rules_adapter import (
        sync_tenant_hiring_gates_to_default_profile_rule,
    )

    await sync_tenant_hiring_gates_to_default_profile_rule(db, tenant_id=str(tenant_id))

    return result


async def _backfill_vacancy_process_profile_links(
    db: AsyncSession,
    *,
    tenant_id: str,
    default_profile: PeProcessProfile | None,
) -> None:
    """P3 compat: bind vacancies without explicit PE profile to tenant recruitment default."""
    if default_profile is None:
        return
    await db.execute(
        update(Vacancy)
        .where(
            Vacancy.tenant_id == str(tenant_id),
            Vacancy.pe_process_profile_id.is_(None),
        )
        .values(pe_process_profile_id=default_profile.id)
    )
