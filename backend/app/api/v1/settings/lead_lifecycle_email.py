"""ADR-033 Control Center API — lead lifecycle email policy + resolve-preview."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.company import Company
from backend.app.models.vacancy import Vacancy
from backend.app.schemas.company_module_settings_json import (
    LeadLifecycleEmailPolicyV1,
    normalize_company_module_settings_json,
)
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.audit import log_audit_event
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.lead_lifecycle_email_policy import (
    LIFECYCLE_PURPOSES,
    resolve_lifecycle_email_policy,
    tenant_preset_to_company_policy,
)

router = APIRouter(
    prefix="/communications/lead-lifecycle-email",
    tags=["lead-lifecycle-email-policy"],
)

_WRITE_ROLES = Depends(require_roles(Role.administrator, Role.supervisor))


class LeadLifecycleEmailPolicyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    policy: dict[str, Any]
    source: str  # company | tenant_preset_default


class LeadLifecycleEmailPolicyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: LeadLifecycleEmailPolicyV1


class VacancyLifecycleOverrideOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vacancy_id: str
    company_id: Optional[str] = None
    override: dict[str, Any]


class VacancyLifecycleOverridePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override: dict[str, Any] = Field(default_factory=dict)


async def _require_company(db: AsyncSession, tenant_id: str, company_id: str) -> Company:
    row = await db.get(Company, company_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return row


async def _assert_comms_admin(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
) -> None:
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature="communicationsAdmin",
    )


@router.get("/resolve-preview")
async def resolve_preview(
    company_id: str = Query(...),
    purpose: str = Query(...),
    vacancy_id: Optional[str] = Query(None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tid = db_tenant
    await _assert_comms_admin(db, tenant_id=str(tid), current_user=current_user)
    await _require_company(db, str(tid), company_id)
    if purpose not in LIFECYCLE_PURPOSES:
        raise HTTPException(status_code=422, detail="Unknown purpose")
    decision = await resolve_lifecycle_email_policy(
        db,
        tenant_id=str(tid),
        company_id=company_id,
        vacancy_id=vacancy_id,
        purpose=purpose,
    )
    return decision.to_dict()


@router.get("/companies/{company_id}", response_model=LeadLifecycleEmailPolicyOut)
async def get_company_lifecycle_email_policy(
    company_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeadLifecycleEmailPolicyOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    await _assert_comms_admin(db, tenant_id=tenant_id, current_user=current_user)
    cid = str(company_id)
    await _require_company(db, tenant_id, cid)
    row = await cms_svc.get_row(db, tenant_id, cid, "recruitment")
    if row is not None:
        settings = normalize_company_module_settings_json("recruitment", dict(row.settings_json or {}))
        block = settings.get("lead_lifecycle_email_v1")
        if isinstance(block, dict) and block:
            return LeadLifecycleEmailPolicyOut(company_id=cid, policy=block, source="company")
    from backend.app.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    preset = tenant_preset_to_company_policy(tenant.settings if tenant else None)
    return LeadLifecycleEmailPolicyOut(company_id=cid, policy=preset, source="tenant_preset_default")


@router.put(
    "/companies/{company_id}",
    response_model=LeadLifecycleEmailPolicyOut,
    dependencies=[_WRITE_ROLES],
)
async def put_company_lifecycle_email_policy(
    company_id: UUID,
    payload: LeadLifecycleEmailPolicyPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeadLifecycleEmailPolicyOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    await _assert_comms_admin(db, tenant_id=tenant_id, current_user=current_user)
    cid = str(company_id)
    await _require_company(db, tenant_id, cid)
    row = await cms_svc.get_row(db, tenant_id, cid, "recruitment")
    prev_settings = dict(row.settings_json or {}) if row else {}
    before = dict(prev_settings.get("lead_lifecycle_email_v1") or {})
    merged = dict(prev_settings)
    new_policy = payload.policy.model_dump(mode="json")
    merged["lead_lifecycle_email_v1"] = new_policy
    normalized = normalize_company_module_settings_json("recruitment", merged)
    row = await cms_svc.upsert_settings(
        db,
        tenant_id,
        cid,
        "recruitment",
        settings_json=normalized,
        is_enabled=True if row is None else None,
    )
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type="lead_lifecycle_email_policy_updated",
        entity_type="company",
        entity_id=cid,
        actor_id=str(getattr(current_user, "sub", None) or getattr(current_user, "id", "") or "") or None,
        payload={
            "scope": "company",
            "company_id": cid,
            "before": before,
            "after": new_policy,
            "at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db.commit()
    await db.refresh(row)
    block = dict((row.settings_json or {}).get("lead_lifecycle_email_v1") or new_policy)
    return LeadLifecycleEmailPolicyOut(company_id=cid, policy=block, source="company")


@router.get("/vacancies/{vacancy_id}", response_model=VacancyLifecycleOverrideOut)
async def get_vacancy_lifecycle_override(
    vacancy_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> VacancyLifecycleOverrideOut:
    db, tid = db_tenant
    await _assert_comms_admin(db, tenant_id=str(tid), current_user=current_user)
    vac = await db.get(Vacancy, str(vacancy_id))
    if vac is None or str(vac.tenant_id) != str(tid):
        raise HTTPException(status_code=404, detail="Vacancy not found")
    settings = vac.settings_json if isinstance(vac.settings_json, dict) else {}
    ov = dict(settings.get("lead_lifecycle_email_override_v1") or {})
    return VacancyLifecycleOverrideOut(
        vacancy_id=str(vac.id),
        company_id=str(vac.company_id) if vac.company_id else None,
        override=ov,
    )


@router.put(
    "/vacancies/{vacancy_id}",
    response_model=VacancyLifecycleOverrideOut,
    dependencies=[_WRITE_ROLES],
)
async def put_vacancy_lifecycle_override(
    vacancy_id: UUID,
    payload: VacancyLifecycleOverridePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> VacancyLifecycleOverrideOut:
    db, tid = db_tenant
    await _assert_comms_admin(db, tenant_id=str(tid), current_user=current_user)
    vac = await db.get(Vacancy, str(vacancy_id))
    if vac is None or str(vac.tenant_id) != str(tid):
        raise HTTPException(status_code=404, detail="Vacancy not found")
    settings = dict(vac.settings_json or {}) if isinstance(vac.settings_json, dict) else {}
    before = dict(settings.get("lead_lifecycle_email_override_v1") or {})
    after = dict(payload.override or {})
    settings["lead_lifecycle_email_override_v1"] = after
    vac.settings_json = settings
    await log_audit_event(
        db,
        tenant_id=str(tid),
        event_type="lead_lifecycle_email_policy_updated",
        entity_type="vacancy",
        entity_id=str(vac.id),
        actor_id=str(getattr(current_user, "sub", None) or getattr(current_user, "id", "") or "") or None,
        payload={
            "scope": "vacancy",
            "vacancy_id": str(vac.id),
            "company_id": str(vac.company_id) if vac.company_id else None,
            "before": before,
            "after": after,
            "at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db.commit()
    await db.refresh(vac)
    return VacancyLifecycleOverrideOut(
        vacancy_id=str(vac.id),
        company_id=str(vac.company_id) if vac.company_id else None,
        override=after,
    )
