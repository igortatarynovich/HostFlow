"""Resolve Recruitment-owned funnels per company (module-owned pipelines P0).

Runtime wiring (candidate create, /meta/stages, analytics, UI) is a follow-up;
this module defines the canonical resolution chain only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module

logger = logging.getLogger(__name__)

RECRUITMENT_MODULE_KEY = "recruitment"
RecruitmentPipelineType = Literal["candidate", "lead"]
RecruitmentFunnelSource = Literal[
    "explicit",
    "cms",
    "company_default",
    "legacy_tenant",
    "platform_seed",
]

PLATFORM_SEED_TENANT_ID = "default"


class RecruitmentFunnelResolveError(Exception):
    """Base error for funnel resolution failures."""


class RecruitmentModuleNotEnabledError(RecruitmentFunnelResolveError):
    """Recruitment is not enabled for the company on this tenant."""


class RecruitmentFunnelNotFoundError(RecruitmentFunnelResolveError):
    """No funnel could be resolved for the requested scope."""


@dataclass(frozen=True)
class RecruitmentFunnelResolveResult:
    funnel: Funnel
    source: RecruitmentFunnelSource
    used_legacy_strangler: bool


async def resolve_recruitment_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    pipeline_type: RecruitmentPipelineType = "candidate",
    explicit_funnel_id: Optional[str] = None,
    tenant: Optional[Tenant] = None,
    company: Optional[Company] = None,
) -> RecruitmentFunnelResolveResult:
    """Resolve a Recruitment funnel for ``company_id`` using the P0 chain.

    Order:
    1. ``explicit_funnel_id`` when company-scoped and type matches
    2. ``company_module_settings.recruitment.default_candidate_funnel_id`` (candidate only)
    3. company default funnel (`is_default=true`)
    4. legacy tenant-scoped funnel (`company_id IS NULL`) — strangler
    5. platform seed funnel (`tenant_id='default'`)
    """
    tid = str(tenant_id).strip()
    cid = str(company_id).strip()
    if not tid or not cid:
        raise RecruitmentFunnelNotFoundError("tenant_id and company_id are required")

    tenant_obj = tenant
    if tenant_obj is None:
        tenant_obj = await db.get(Tenant, tid)
    if tenant_obj is None:
        raise RecruitmentFunnelNotFoundError(f"tenant not found: {tid}")

    company_obj = company
    if company_obj is None:
        company_obj = await cms_svc.get_company_for_tenant(db, tid, cid)
    if company_obj is None:
        raise RecruitmentFunnelNotFoundError(f"company not found: {cid}")

    if not company_allows_module(tenant_obj, company_obj, RECRUITMENT_MODULE_KEY):
        raise RecruitmentModuleNotEnabledError(
            f"recruitment module is not enabled for company {cid}"
        )

    if explicit_funnel_id:
        explicit = await _load_company_scoped_funnel(
            db,
            funnel_id=str(explicit_funnel_id).strip(),
            tenant_id=tid,
            company_id=cid,
            pipeline_type=pipeline_type,
        )
        if explicit is not None:
            return RecruitmentFunnelResolveResult(
                funnel=explicit,
                source="explicit",
                used_legacy_strangler=False,
            )

    if pipeline_type == "candidate":
        cms_funnel = await _resolve_cms_default_candidate_funnel(
            db, tenant_id=tid, company_id=cid
        )
        if cms_funnel is not None:
            return RecruitmentFunnelResolveResult(
                funnel=cms_funnel,
                source="cms",
                used_legacy_strangler=False,
            )

    company_default = await _load_default_funnel(
        db,
        tenant_id=tid,
        company_id=cid,
        pipeline_type=pipeline_type,
        legacy_tenant_scope=False,
    )
    if company_default is not None:
        return RecruitmentFunnelResolveResult(
            funnel=company_default,
            source="company_default",
            used_legacy_strangler=False,
        )

    legacy = await _load_default_funnel(
        db,
        tenant_id=tid,
        company_id=None,
        pipeline_type=pipeline_type,
        legacy_tenant_scope=True,
    )
    if legacy is not None:
        logger.info(
            "recruitment_funnel_resolver legacy tenant fallback tenant=%s company=%s type=%s funnel=%s",
            tid,
            cid,
            pipeline_type,
            legacy.id,
        )
        return RecruitmentFunnelResolveResult(
            funnel=legacy,
            source="legacy_tenant",
            used_legacy_strangler=True,
        )

    platform = await _load_default_funnel(
        db,
        tenant_id=PLATFORM_SEED_TENANT_ID,
        company_id=None,
        pipeline_type=pipeline_type,
        legacy_tenant_scope=True,
    )
    if platform is not None:
        logger.info(
            "recruitment_funnel_resolver platform seed fallback tenant=%s company=%s type=%s funnel=%s",
            tid,
            cid,
            pipeline_type,
            platform.id,
        )
        return RecruitmentFunnelResolveResult(
            funnel=platform,
            source="platform_seed",
            used_legacy_strangler=True,
        )

    raise RecruitmentFunnelNotFoundError(
        f"no recruitment funnel for tenant={tid} company={cid} type={pipeline_type}"
    )


async def _resolve_cms_default_candidate_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> Optional[Funnel]:
    row = await cms_svc.get_row(db, tenant_id, company_id, RECRUITMENT_MODULE_KEY)
    if row is None:
        return None
    settings = row.settings_json if isinstance(row.settings_json, dict) else {}
    raw_fid = settings.get("default_candidate_funnel_id")
    if not raw_fid or not str(raw_fid).strip():
        return None
    return await _load_company_scoped_funnel(
        db,
        funnel_id=str(raw_fid).strip(),
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )


async def _load_company_scoped_funnel(
    db: AsyncSession,
    *,
    funnel_id: str,
    tenant_id: str,
    company_id: str,
    pipeline_type: RecruitmentPipelineType,
) -> Optional[Funnel]:
    stmt = (
        select(Funnel)
        .options(selectinload(Funnel.stages))
        .where(
            Funnel.id == funnel_id,
            Funnel.tenant_id == tenant_id,
            Funnel.company_id == company_id,
            Funnel.module_key == RECRUITMENT_MODULE_KEY,
            Funnel.type == pipeline_type,
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def _load_default_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    pipeline_type: RecruitmentPipelineType,
    legacy_tenant_scope: bool,
) -> Optional[Funnel]:
    stmt = (
        select(Funnel)
        .options(selectinload(Funnel.stages))
        .where(
            Funnel.tenant_id == tenant_id,
            Funnel.module_key == RECRUITMENT_MODULE_KEY,
            Funnel.type == pipeline_type,
            Funnel.is_default.is_(True),
        )
        .order_by(Funnel.name.asc(), Funnel.id.asc())
        .limit(1)
    )
    if legacy_tenant_scope:
        stmt = stmt.where(Funnel.company_id.is_(None))
    else:
        if not company_id:
            return None
        stmt = stmt.where(Funnel.company_id == company_id)

    res = await db.execute(stmt)
    return res.scalar_one_or_none()
