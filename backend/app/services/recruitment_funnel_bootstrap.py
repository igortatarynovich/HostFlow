"""Bootstrap company-scoped recruitment funnels (M6)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant
from backend.app.modules.companies.funnel_presets import business_funnel_presets
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import get_effective_company_modules
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY

logger = logging.getLogger(__name__)

StageRow = tuple[str, str, str, bool]


def _recruitment_product_enabled(tenant: Tenant, company: Company) -> bool:
    mods = get_effective_company_modules(tenant, company)
    if mods.get("recruitment"):
        return True
    return bool(mods.get("candidates") or mods.get("leads"))


def _bootstrap_pipeline_flags(
    tenant: Tenant,
    company: Company,
    tenant_modules: dict[str, bool] | None,
) -> tuple[bool, bool]:
    """Return (create_candidate_funnel, create_lead_funnel)."""
    if not _recruitment_product_enabled(tenant, company):
        return False, False
    effective = get_effective_company_modules(tenant, company)
    tm = tenant_modules or {}
    create_candidate = bool(effective.get("candidates", tm.get("candidates", True)))
    create_lead = bool(effective.get("leads", tm.get("leads", True)))
    return create_candidate, create_lead


async def _load_company_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_type: str,
) -> Funnel | None:
    rows = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.module_key == RECRUITMENT_MODULE_KEY,
                Funnel.type == funnel_type,
            )
        )
    ).scalars().all()
    for funnel in rows:
        if funnel.is_default:
            return funnel
    for funnel in rows:
        return funnel
    return None


async def _ensure_company_recruitment_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_type: str,
    name: str,
    stages: list[StageRow],
) -> Funnel:
    existing = await _load_company_funnel(
        db, tenant_id=tenant_id, company_id=company_id, funnel_type=funnel_type
    )
    target = existing
    created = False
    if target is None:
        target = Funnel(
            tenant_id=tenant_id,
            company_id=company_id,
            module_key=RECRUITMENT_MODULE_KEY,
            type=funnel_type,
            name=name,
            is_default=True,
        )
        db.add(target)
        await db.flush()
        created = True

    siblings = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.module_key == RECRUITMENT_MODULE_KEY,
                Funnel.type == funnel_type,
            )
        )
    ).scalars().all()
    for funnel in siblings:
        funnel.is_default = funnel.id == target.id
    target.is_default = True
    if created or not (target.name or "").strip():
        target.name = name

    existing_stages = (
        await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == target.id))
    ).scalars().all()
    if not existing_stages:
        for order, (code, label, system_stage, is_terminal) in enumerate(stages):
            db.add(
                FunnelStage(
                    funnel_id=target.id,
                    code=code,
                    label=label,
                    system_stage=system_stage,
                    order=order,
                    is_terminal=bool(is_terminal),
                )
            )
        await db.flush()

        if funnel_type == "candidate":
            from backend.app.process_engine.pipeline_mapping import (
                ensure_funnel_stage_pe_mapping,
            )

            stage_rows = (
                await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == target.id))
            ).scalars().all()
            for stage in stage_rows:
                await ensure_funnel_stage_pe_mapping(
                    db, stage, tenant_id=tenant_id, module=RECRUITMENT_MODULE_KEY
                )

    return target


async def _maybe_set_default_candidate_funnel_cms(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_id: str,
) -> None:
    row = await cms_svc.get_row(db, tenant_id, company_id, RECRUITMENT_MODULE_KEY)
    settings = dict(row.settings_json or {}) if row and isinstance(row.settings_json, dict) else {}
    if settings.get("default_candidate_funnel_id"):
        return
    settings["default_candidate_funnel_id"] = funnel_id
    await cms_svc.upsert_settings(
        db,
        tenant_id,
        company_id,
        RECRUITMENT_MODULE_KEY,
        settings_json=settings,
        is_enabled=True,
    )


async def bootstrap_recruitment_funnels_for_company(
    db: AsyncSession,
    *,
    tenant: Tenant,
    company: Company,
    company_type: str | None,
    tenant_modules: dict[str, bool] | None = None,
    industry: str | None = None,
) -> dict[str, str]:
    """Idempotently ensure company-scoped recruitment funnels. Returns created funnel ids by type."""
    company_id = str(company.id)
    tenant_id = str(tenant.id)
    create_candidate, create_lead = _bootstrap_pipeline_flags(tenant, company, tenant_modules)
    if not create_candidate and not create_lead:
        logger.info(
            "recruitment_funnel_bootstrap skipped tenant=%s company=%s (recruitment disabled)",
            tenant_id,
            company_id,
        )
        return {}

    presets = business_funnel_presets(company_type, industry)
    out: dict[str, str] = {}

    if create_candidate:
        candidate = presets["candidate"]
        funnel = await _ensure_company_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            funnel_type="candidate",
            name=str(candidate["name"]),
            stages=list(candidate["stages"]),
        )
        out["candidate"] = funnel.id
        await _maybe_set_default_candidate_funnel_cms(
            db, tenant_id=tenant_id, company_id=company_id, funnel_id=funnel.id
        )

    if create_lead:
        lead = presets["lead"]
        funnel = await _ensure_company_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            funnel_type="lead",
            name=str(lead["name"]),
            stages=list(lead["stages"]),
        )
        out["lead"] = funnel.id

    await db.flush()
    return out


async def resolve_company_default_funnel_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_type: str,
) -> str | None:
    funnel = await _load_company_funnel(
        db,
        tenant_id=str(tenant_id),
        company_id=str(company_id),
        funnel_type=funnel_type,
    )
    return str(funnel.id) if funnel else None


async def resolve_first_operating_company_id(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> str | None:
    rows = (
        await db.execute(
            select(Company.id, Company.extra).where(Company.tenant_id == tenant_id)
        )
    ).all()
    for cid, extra in rows:
        role = ""
        if isinstance(extra, dict):
            role = str(extra.get("company_role") or "").strip().lower()
        if role in ("", "operating"):
            return str(cid)
    return None
