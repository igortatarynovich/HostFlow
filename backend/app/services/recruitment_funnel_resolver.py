"""Resolve Recruitment-owned funnels per company (module-owned pipelines P0).

Runtime wiring (candidate create, /meta/stages, analytics, UI) is incremental;
this module defines the canonical resolution chain and ownership validation.

Funnel identity (canon): ``(company_id, module_key, type)`` + ``name`` for human label.
There is no company default funnel without ``module_key``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module
from backend.app.services.recruitment_funnel_metrics import record_recruitment_funnel_resolve

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


class RecruitmentFunnelForbiddenError(RecruitmentFunnelResolveError):
    """Explicit funnel_id violates company/module/type ownership — no fallback."""


@dataclass(frozen=True)
class RecruitmentFunnelResolveResult:
    funnel: Funnel
    source: RecruitmentFunnelSource
    used_legacy_strangler: bool


def _return_resolve_result(result: RecruitmentFunnelResolveResult) -> RecruitmentFunnelResolveResult:
    record_recruitment_funnel_resolve(
        source=result.source,
        used_legacy_strangler=result.used_legacy_strangler,
    )
    return result


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

    Order (when ``explicit_funnel_id`` is omitted):
    1. ``company_module_settings.recruitment.default_candidate_funnel_id`` (candidate only)
    2. company default funnel (`is_default=true`, scoped by company_id + module_key + type)
    3. legacy tenant-scoped funnel (`company_id IS NULL`) — strangler
    4. platform seed funnel (`tenant_id='default'`)

    When ``explicit_funnel_id`` is provided: load by id; on company mismatch →
    ``RecruitmentFunnelForbiddenError`` (never fallback). When id missing →
    ``RecruitmentFunnelNotFoundError``.
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
        explicit = await _resolve_explicit_funnel(
            db,
            funnel_id=str(explicit_funnel_id).strip(),
            tenant_id=tid,
            company_id=cid,
            pipeline_type=pipeline_type,
        )
        return _return_resolve_result(
            RecruitmentFunnelResolveResult(
                funnel=explicit,
                source="explicit",
                used_legacy_strangler=explicit.company_id is None,
            )
        )

    if pipeline_type == "candidate":
        cms_funnel = await _resolve_cms_default_candidate_funnel(
            db, tenant_id=tid, company_id=cid
        )
        if cms_funnel is not None:
            return _return_resolve_result(
                RecruitmentFunnelResolveResult(
                    funnel=cms_funnel,
                    source="cms",
                    used_legacy_strangler=False,
                )
            )

    company_default = await _load_default_funnel(
        db,
        tenant_id=tid,
        company_id=cid,
        pipeline_type=pipeline_type,
        legacy_tenant_scope=False,
    )
    if company_default is not None:
        return _return_resolve_result(
            RecruitmentFunnelResolveResult(
                funnel=company_default,
                source="company_default",
                used_legacy_strangler=False,
            )
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
        return _return_resolve_result(
            RecruitmentFunnelResolveResult(
                funnel=legacy,
                source="legacy_tenant",
                used_legacy_strangler=True,
            )
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
        return _return_resolve_result(
            RecruitmentFunnelResolveResult(
                funnel=platform,
                source="platform_seed",
                used_legacy_strangler=True,
            )
        )

    raise RecruitmentFunnelNotFoundError(
        f"no recruitment funnel for tenant={tid} company={cid} type={pipeline_type}"
    )


async def resolve_legacy_tenant_recruitment_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    pipeline_type: RecruitmentPipelineType = "candidate",
) -> RecruitmentFunnelResolveResult:
    """Legacy tenant-scoped funnel for strangler analytics (read-only path)."""
    tid = str(tenant_id).strip()
    if not tid:
        raise RecruitmentFunnelNotFoundError("tenant_id is required")

    legacy = await _load_default_funnel(
        db,
        tenant_id=tid,
        company_id=None,
        pipeline_type=pipeline_type,
        legacy_tenant_scope=True,
    )
    if legacy is not None:
        logger.info(
            "recruitment_funnel_resolver legacy tenant analytics fallback tenant=%s type=%s funnel=%s",
            tid,
            pipeline_type,
            legacy.id,
        )
        return _return_resolve_result(
            RecruitmentFunnelResolveResult(
                funnel=legacy,
                source="legacy_tenant",
                used_legacy_strangler=True,
            )
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
            "recruitment_funnel_resolver platform seed analytics fallback tenant=%s type=%s funnel=%s",
            tid,
            pipeline_type,
            platform.id,
        )
        return _return_resolve_result(
            RecruitmentFunnelResolveResult(
                funnel=platform,
                source="platform_seed",
                used_legacy_strangler=True,
            )
        )

    raise RecruitmentFunnelNotFoundError(
        f"no legacy recruitment funnel for tenant={tid} type={pipeline_type}"
    )


async def validate_recruitment_funnel_id_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_id: str,
    pipeline_type: RecruitmentPipelineType = "candidate",
) -> Funnel:
    """Validate an explicit funnel binding (profiles, vacancy config). Raises on violation."""
    return await _resolve_explicit_funnel(
        db,
        funnel_id=funnel_id,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type=pipeline_type,
    )


async def _resolve_explicit_funnel(
    db: AsyncSession,
    *,
    funnel_id: str,
    tenant_id: str,
    company_id: str,
    pipeline_type: RecruitmentPipelineType,
) -> Funnel:
    if not funnel_id:
        raise RecruitmentFunnelNotFoundError("explicit funnel_id is empty")

    funnel = await _load_funnel_by_id(
        db,
        funnel_id=funnel_id,
        tenant_id=tenant_id,
        pipeline_type=pipeline_type,
    )
    if funnel is None:
        raise RecruitmentFunnelNotFoundError(f"explicit funnel not found: {funnel_id}")

    # ADR-035 §12: Vacancy.funnel_id is SoT. Funnel.company_id is library metadata only —
    # do not block assigning a tenant recruitment pipeline to a vacancy of another client.
    _ = company_id

    f_module = str(funnel.module_key or "").strip() or None
    if f_module and f_module != RECRUITMENT_MODULE_KEY:
        raise RecruitmentFunnelForbiddenError(
            f"funnel {funnel_id} module_key={f_module} is not recruitment"
        )

    if str(funnel.type or "") != pipeline_type:
        raise RecruitmentFunnelForbiddenError(
            f"funnel {funnel_id} type={funnel.type} does not match {pipeline_type}"
        )

    return funnel


async def validate_recruitment_module_settings_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    settings_json: dict[str, Any],
) -> dict[str, Any]:
    """Validate recruitment CMS JSON; enforce company-owned candidate funnel pointer."""
    from backend.app.schemas.company_module_settings_json import RecruitmentModuleSettingsV1

    normalized = RecruitmentModuleSettingsV1.model_validate(settings_json).model_dump(mode="json")
    raw_fid = normalized.get("default_candidate_funnel_id")
    if not raw_fid or not str(raw_fid).strip():
        return normalized

    funnel = await validate_recruitment_funnel_id_for_company(
        db,
        tenant_id=str(tenant_id),
        company_id=str(company_id),
        funnel_id=str(raw_fid).strip(),
        pipeline_type="candidate",
    )
    if not funnel.company_id or str(funnel.company_id) != str(company_id).strip():
        raise RecruitmentFunnelForbiddenError(
            "default_candidate_funnel_id must be a company-scoped recruitment candidate funnel"
        )
    if str(funnel.module_key or "") != RECRUITMENT_MODULE_KEY:
        raise RecruitmentFunnelForbiddenError(
            "default_candidate_funnel_id must use module_key=recruitment"
        )
    return normalized


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
    try:
        return await validate_recruitment_funnel_id_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            funnel_id=str(raw_fid).strip(),
            pipeline_type="candidate",
        )
    except RecruitmentFunnelForbiddenError:
        logger.warning(
            "recruitment_funnel_resolver cms funnel forbidden tenant=%s company=%s funnel=%s",
            tenant_id,
            company_id,
            raw_fid,
        )
        return None
    except RecruitmentFunnelNotFoundError:
        return None


async def _load_funnel_by_id(
    db: AsyncSession,
    *,
    funnel_id: str,
    tenant_id: str,
    pipeline_type: RecruitmentPipelineType,
) -> Optional[Funnel]:
    stmt = (
        select(Funnel)
        .options(selectinload(Funnel.stages))
        .where(
            Funnel.id == funnel_id,
            Funnel.tenant_id.in_([tenant_id, PLATFORM_SEED_TENANT_ID]),
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


def first_funnel_stage_code(funnel: Funnel) -> Optional[str]:
    """First stage code by order (for default candidate/lead stage on create)."""
    stages = list(getattr(funnel, "stages", None) or [])
    if not stages:
        return None
    ordered = sorted(stages, key=lambda s: (int(getattr(s, "order", 0) or 0), str(s.code)))
    if not ordered:
        return None
    code = str(getattr(ordered[0], "code", "") or "").strip()
    return code or None
