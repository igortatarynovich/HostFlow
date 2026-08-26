"""Company-scoped module settings (ADR-005)."""

from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.schemas.company_module_settings_json import (
    MODULE_SETTINGS_MODEL_V1,
    normalize_company_module_settings_json,
)
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.company import Company
from backend.app.models.company_module_settings import CompanyModuleSettings
from backend.app.models.tenant import Tenant
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module
from backend.app.services.recruitment_funnel_resolver import (
    RecruitmentFunnelForbiddenError,
    validate_recruitment_module_settings_for_company,
)
from backend.app.services.hr_employee_funnel_resolver import (
    HrEmployeeFunnelForbiddenError,
    validate_hr_module_settings_for_company,
)

router = APIRouter(prefix="/companies", tags=["company-module-settings"])


def _settings_json_for_response(module_key: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    """Typed modules return schema-shaped JSON; invalid legacy rows coerce to v1 defaults."""
    model = MODULE_SETTINGS_MODEL_V1.get(module_key)
    if model is None:
        return dict(raw or {})
    try:
        return model.model_validate(raw or {}).model_dump(mode="json")
    except ValidationError:
        return model().model_dump(mode="json")


def _default_out(
    *,
    tenant_id: str,
    company_id: str,
    module_key: str,
    row: Optional[CompanyModuleSettings] = None,
) -> "CompanyModuleSettingsOut":
    if row is None:
        return CompanyModuleSettingsOut(
            id="",
            tenant_id=tenant_id,
            company_id=company_id,
            module_key=module_key,
            settings_json={},
            is_enabled=False,
            configured_at=None,
            created_at="",
            updated_at="",
        )
    return CompanyModuleSettingsOut(
        id=row.id,
        tenant_id=row.tenant_id,
        company_id=row.company_id,
        module_key=row.module_key,
        settings_json=_settings_json_for_response(row.module_key, dict(row.settings_json or {})),
        is_enabled=bool(row.is_enabled),
        configured_at=row.configured_at.isoformat() if row.configured_at else None,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


class CompanyModuleSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    company_id: str
    module_key: str
    settings_json: dict[str, Any]
    is_enabled: bool
    configured_at: Optional[str] = None
    created_at: str
    updated_at: str


class CompanyModuleSettingsPatch(BaseModel):
    settings_json: Optional[dict[str, Any]] = Field(default=None)
    is_enabled: Optional[bool] = Field(default=None)


async def _load_tenant_company_and_enforce(
    db: AsyncSession,
    tenant_id: str,
    company_id: str,
    module_key: str,
    current_user: UserCtx,
) -> tuple[Tenant, Company]:
    """Return (tenant_orm, company_orm). Raises HTTPException on errors."""
    company = await cms_svc.get_company_for_tenant(db, tenant_id, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    acl = await resolve_restricted_acl(db, tenant_id, current_user)
    if acl is not None and acl.company_ids and company_id not in acl.company_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if not company_allows_module(tenant, company, module_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Module is not enabled for this company",
        )
    return tenant, company


@router.get(
    "/{company_id}/module-settings/{module_key}",
    response_model=CompanyModuleSettingsOut,
    dependencies=[
        Depends(require_trust_write()),
    ],
)
async def get_company_module_settings(
    company_id: UUID,
    module_key: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CompanyModuleSettingsOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    cid = str(company_id)
    try:
        mk = cms_svc.normalize_module_key(module_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    await _load_tenant_company_and_enforce(db, tenant_id, cid, mk, current_user)

    row = await cms_svc.get_row(db, tenant_id, cid, mk)
    return _default_out(tenant_id=tenant_id, company_id=cid, module_key=mk, row=row)


@router.get(
    "/{company_id}/module-settings",
    response_model=List[CompanyModuleSettingsOut],
    dependencies=[
        Depends(require_trust_write()),
    ],
)
async def list_company_module_settings(
    company_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> List[CompanyModuleSettingsOut]:
    db, tid = db_tenant
    tenant_id = str(tid)
    cid = str(company_id)
    company = await cms_svc.get_company_for_tenant(db, tenant_id, cid)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    acl = await resolve_restricted_acl(db, tenant_id, current_user)
    if acl is not None and acl.company_ids and cid not in acl.company_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    rows = await cms_svc.list_rows_for_company(db, tenant_id, cid)
    out: list[CompanyModuleSettingsOut] = []
    for r in rows:
        if not company_allows_module(tenant, company, r.module_key):
            continue
        out.append(_default_out(tenant_id=tenant_id, company_id=cid, module_key=r.module_key, row=r))
    return out


@router.patch(
    "/{company_id}/module-settings/{module_key}",
    response_model=CompanyModuleSettingsOut,
    dependencies=[
        Depends(require_trust_write()),
    ],
)
async def patch_company_module_settings(
    company_id: UUID,
    module_key: str,
    payload: CompanyModuleSettingsPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CompanyModuleSettingsOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    cid = str(company_id)
    try:
        mk = cms_svc.normalize_module_key(module_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    await _load_tenant_company_and_enforce(db, tenant_id, cid, mk, current_user)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        row = await cms_svc.get_row(db, tenant_id, cid, mk)
        return _default_out(tenant_id=tenant_id, company_id=cid, module_key=mk, row=row)

    if "settings_json" in data and data["settings_json"] is not None:
        if not isinstance(data["settings_json"], dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="settings_json must be an object",
            )
        try:
            data["settings_json"] = normalize_company_module_settings_json(mk, data["settings_json"])
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=exc.errors(),
            ) from exc
        if mk == "recruitment":
            try:
                data["settings_json"] = await validate_recruitment_module_settings_for_company(
                    db,
                    tenant_id=tenant_id,
                    company_id=cid,
                    settings_json=data["settings_json"],
                )
            except RecruitmentFunnelForbiddenError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc
            from backend.app.services.recruitment_handoff_funnel_gate import (
                HandoffFunnelGateError,
                ensure_candidate_funnel_allows_company_handoff,
            )

            try:
                await ensure_candidate_funnel_allows_company_handoff(
                    db,
                    tenant_id=tenant_id,
                    company_id=cid,
                    funnel_id=(data["settings_json"] or {}).get("default_candidate_funnel_id"),
                )
            except HandoffFunnelGateError as exc:
                raise exc.as_http_exception() from exc
        if mk == "hr":
            try:
                data["settings_json"] = await validate_hr_module_settings_for_company(
                    db,
                    tenant_id=tenant_id,
                    company_id=cid,
                    settings_json=data["settings_json"],
                )
            except HrEmployeeFunnelForbiddenError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc

    row = await cms_svc.upsert_settings(
        db,
        tenant_id,
        cid,
        mk,
        settings_json=data.get("settings_json"),
        is_enabled=data.get("is_enabled"),
    )
    await db.commit()
    await db.refresh(row)
    return _default_out(tenant_id=tenant_id, company_id=cid, module_key=mk, row=row)
