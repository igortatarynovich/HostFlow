"""ADR-033 Control Center API — lead lifecycle email policy + resolve-preview.

Own-company SoT (slice A): policy blob on ``OwnCompany.extra.lead_lifecycle_email_v1``.
Client-company routes remain as optional overlay editors until Control Center IA (slice B).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany
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
    set_own_company_lifecycle_policy,
    tenant_preset_to_company_policy,
)

router = APIRouter(
    prefix="/communications/lead-lifecycle-email",
    tags=["lead-lifecycle-email-policy"],
)

_WRITE_ROLES = Depends(require_trust_write())


class LeadLifecycleEmailPolicyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: Optional[str] = None
    own_company_id: Optional[str] = None
    policy: dict[str, Any]
    source: str  # own_company | company | tenant_preset_default


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


async def _require_own_company(db: AsyncSession, tenant_id: str, own_company_id: str) -> OwnCompany:
    row = await db.get(OwnCompany, own_company_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Own company not found")
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
    purpose: str = Query(...),
    own_company_id: Optional[str] = Query(
        None,
        description="Operating firm SoT (preferred).",
    ),
    company_id: Optional[str] = Query(
        None,
        description="Optional client overlay. Legacy callers may pass only this; "
        "preview then requires own_company_id as well.",
    ),
    vacancy_id: Optional[str] = Query(None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tid = db_tenant
    await _assert_comms_admin(db, tenant_id=str(tid), current_user=current_user)
    if purpose not in LIFECYCLE_PURPOSES:
        raise HTTPException(status_code=422, detail="Unknown purpose")

    oid = (own_company_id or "").strip() or None
    cid = (company_id or "").strip() or None
    if not oid:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "own_company_id_required",
                "message": "resolve-preview requires own_company_id (firm SoT).",
            },
        )
    await _require_own_company(db, str(tid), oid)
    if cid:
        await _require_company(db, str(tid), cid)

    decision = await resolve_lifecycle_email_policy(
        db,
        tenant_id=str(tid),
        own_company_id=oid,
        company_id=cid,
        vacancy_id=vacancy_id,
        purpose=purpose,
    )
    return decision.to_dict()


@router.get("/own-companies/{own_company_id}", response_model=LeadLifecycleEmailPolicyOut)
async def get_own_company_lifecycle_email_policy(
    own_company_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeadLifecycleEmailPolicyOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    await _assert_comms_admin(db, tenant_id=tenant_id, current_user=current_user)
    oid = str(own_company_id)
    own = await _require_own_company(db, tenant_id, oid)
    extra = own.extra if isinstance(own.extra, dict) else {}
    block = extra.get("lead_lifecycle_email_v1")
    if isinstance(block, dict) and block:
        return LeadLifecycleEmailPolicyOut(
            own_company_id=oid,
            policy=block,
            source="own_company",
        )
    from backend.app.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    preset = tenant_preset_to_company_policy(tenant.settings if tenant else None)
    return LeadLifecycleEmailPolicyOut(
        own_company_id=oid,
        policy=preset,
        source="tenant_preset_default",
    )


@router.put(
    "/own-companies/{own_company_id}",
    response_model=LeadLifecycleEmailPolicyOut,
    dependencies=[_WRITE_ROLES],
)
async def put_own_company_lifecycle_email_policy(
    own_company_id: UUID,
    payload: LeadLifecycleEmailPolicyPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeadLifecycleEmailPolicyOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    await _assert_comms_admin(db, tenant_id=tenant_id, current_user=current_user)
    oid = str(own_company_id)
    own = await _require_own_company(db, tenant_id, oid)
    extra = dict(own.extra or {}) if isinstance(own.extra, dict) else {}
    before = dict(extra.get("lead_lifecycle_email_v1") or {})
    new_policy = payload.policy.model_dump(mode="json")
    set_own_company_lifecycle_policy(own, new_policy)
    flag_modified(own, "extra")
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type="lead_lifecycle_email_policy_updated",
        entity_type="own_company",
        entity_id=oid,
        actor_id=str(getattr(current_user, "sub", None) or getattr(current_user, "id", "") or "") or None,
        payload={
            "scope": "own_company",
            "own_company_id": oid,
            "before": before,
            "after": new_policy,
            "at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db.commit()
    await db.refresh(own)
    block = dict((own.extra or {}).get("lead_lifecycle_email_v1") or new_policy)
    return LeadLifecycleEmailPolicyOut(own_company_id=oid, policy=block, source="own_company")


@router.get("/companies/{company_id}", response_model=LeadLifecycleEmailPolicyOut)
async def get_company_lifecycle_email_policy(
    company_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeadLifecycleEmailPolicyOut:
    """Client-company overlay (optional). Prefer own-companies SoT endpoints for firm policy."""
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
    """Write client-company overlay (optional white-label). Firm SoT = own-companies PUT."""
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
    new_policy.pop("rodo_send_mode", None)
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
            "scope": "client_overlay",
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
    gdpr = after.get("gdpr_notice") if isinstance(after.get("gdpr_notice"), dict) else None
    if gdpr is not None:
        cleaned = dict(gdpr)
        cleaned.pop("enabled", None)
        cleaned.pop("send_mode", None)
        if cleaned.get("template_ref"):
            after["gdpr_notice"] = cleaned
        else:
            after.pop("gdpr_notice", None)
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
