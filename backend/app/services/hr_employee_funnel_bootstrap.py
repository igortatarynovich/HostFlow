"""Bootstrap company-scoped HR employee funnels (hr-employee-pipeline-p0 H3)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.funnel_types import HR_EMPLOYEE_FUNNEL_TYPE, HR_MODULE_KEY
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant
from backend.app.process_engine.constants import HR_MODULE
from backend.app.process_engine.manifests.hr import hr_module_manifest
from backend.app.process_engine.pipeline_mapping import apply_pe_mapping_to_funnel_stage
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module

logger = logging.getLogger(__name__)

StageRow = tuple[str, str, str, bool]

HR_EMPLOYEE_FUNNEL_NAME = "HR Employee Pipeline"

# P0 happy-path chain — every code must exist in hr_module_manifest().system_stages.
HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES: tuple[str, ...] = (
    "handoff_pending",
    "accepted_by_hr",
    "hr_review_in_progress",
    "verification",
    "approved_for_employment",
    "employment_pending",
    "active",
)


def hr_employee_bootstrap_stages() -> list[StageRow]:
    """Build bootstrap stage rows from the HR PE manifest only."""
    manifest = hr_module_manifest()
    by_code = {
        str(row.get("code") or "").strip(): row
        for row in manifest.get("system_stages") or []
        if str(row.get("code") or "").strip()
    }
    rows: list[StageRow] = []
    for code in HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES:
        stage = by_code.get(code)
        if stage is None:
            raise ValueError(f"HR bootstrap stage {code!r} missing from hr PE manifest")
        label = str(stage.get("name") or code.replace("_", " ").title())
        bucket = str(stage.get("analytics_bucket") or code)
        is_terminal = bool(stage.get("terminal"))
        rows.append((code, label, bucket, is_terminal))
    return rows


async def _load_company_hr_employee_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> Funnel | None:
    rows = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            )
        )
    ).scalars().all()
    for funnel in rows:
        if funnel.is_default:
            return funnel
    for funnel in rows:
        return funnel
    return None


async def _ensure_company_hr_employee_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    name: str,
    stages: list[StageRow],
) -> Funnel:
    existing = await _load_company_hr_employee_funnel(
        db, tenant_id=tenant_id, company_id=company_id
    )
    target = existing
    created = False
    if target is None:
        target = Funnel(
            tenant_id=tenant_id,
            company_id=company_id,
            module_key=HR_MODULE_KEY,
            type=HR_EMPLOYEE_FUNNEL_TYPE,
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
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
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
            stage = FunnelStage(
                funnel_id=target.id,
                code=code,
                label=label,
                system_stage=system_stage,
                order=order,
                is_terminal=bool(is_terminal),
            )
            db.add(stage)
        await db.flush()

        stage_rows = (
            await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == target.id))
        ).scalars().all()
        for stage in stage_rows:
            pe_code = str(stage.code or "").strip()
            if pe_code:
                await apply_pe_mapping_to_funnel_stage(
                    db,
                    stage,
                    tenant_id=tenant_id,
                    module=HR_MODULE,
                    code=pe_code,
                    source="pipeline_template",
                )

    return target


async def _maybe_set_employee_pipeline_funnel_cms(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_id: str,
) -> None:
    row = await cms_svc.get_row(db, tenant_id, company_id, HR_MODULE_KEY)
    settings = dict(row.settings_json or {}) if row and isinstance(row.settings_json, dict) else {}
    if settings.get("employee_pipeline_funnel_id"):
        return
    settings.setdefault("version", 1)
    settings["employee_pipeline_funnel_id"] = funnel_id
    await cms_svc.upsert_settings(
        db,
        tenant_id,
        company_id,
        HR_MODULE_KEY,
        settings_json=settings,
        is_enabled=True,
    )


async def bootstrap_hr_employee_funnel_for_company(
    db: AsyncSession,
    *,
    tenant: Tenant,
    company: Company,
) -> dict[str, str]:
    """Idempotently ensure company-scoped HR employee funnel. Returns created funnel ids by type."""
    company_id = str(company.id)
    tenant_id = str(tenant.id)

    if not company_allows_module(tenant, company, HR_MODULE_KEY):
        logger.info(
            "hr_employee_funnel_bootstrap skipped tenant=%s company=%s (hr disabled)",
            tenant_id,
            company_id,
        )
        return {}

    stages = hr_employee_bootstrap_stages()
    funnel = await _ensure_company_hr_employee_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        name=HR_EMPLOYEE_FUNNEL_NAME,
        stages=stages,
    )
    await _maybe_set_employee_pipeline_funnel_cms(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        funnel_id=funnel.id,
    )
    await db.flush()
    return {HR_EMPLOYEE_FUNNEL_TYPE: funnel.id}
