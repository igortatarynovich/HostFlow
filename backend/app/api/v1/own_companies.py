from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import OwnCompany, User
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services.audit import log_activity


router = APIRouter(prefix="/own-companies", tags=["own-companies"], redirect_slashes=False)
# Back-compat for older deployments using underscore paths.
legacy_router = APIRouter(prefix="/own_companies", tags=["own-companies"], redirect_slashes=False)


class OwnCompanyOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    country_code: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_archived: bool = False
    contacts: dict = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)
    bank_details: dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OwnCompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    tax_id: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=64)
    email: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=2)
    country: Optional[str] = Field(default=None, max_length=64)
    city: Optional[str] = Field(default=None, max_length=128)
    address: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=2000)
    contacts: dict = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)
    bank_details: dict = Field(default_factory=dict)


class OwnCompanyPatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    tax_id: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=64)
    email: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=2)
    country: Optional[str] = Field(default=None, max_length=64)
    city: Optional[str] = Field(default=None, max_length=128)
    address: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=2000)
    is_archived: Optional[bool] = None
    contacts: Optional[dict] = None
    extra: Optional[dict] = None
    bank_details: Optional[dict] = None


class OwnCompanyListOut(BaseModel):
    items: List[OwnCompanyOut]
    active_own_company_id: Optional[str] = None


class SetActiveOwnCompanyIn(BaseModel):
    own_company_id: UUID


@router.get("", response_model=OwnCompanyListOut)
@router.get("/", response_model=OwnCompanyListOut, include_in_schema=False)
@legacy_router.get("", response_model=OwnCompanyListOut, include_in_schema=False)
@legacy_router.get("/", response_model=OwnCompanyListOut, include_in_schema=False)
async def list_own_companies(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    rows = await db.execute(
        select(OwnCompany)
        .where(OwnCompany.tenant_id == tenant_id)
        .order_by(OwnCompany.created_at.asc())
    )
    items = list(rows.scalars().all())

    active = None
    if current_user and current_user.sub:
        user_row = await db.execute(select(User.preferences).where(User.id == str(current_user.sub)).limit(1))
        prefs = user_row.scalar_one_or_none()
        if isinstance(prefs, dict):
            active = str(prefs.get("active_own_company_id") or "").strip() or None
    return OwnCompanyListOut(items=[OwnCompanyOut.model_validate(x) for x in items], active_own_company_id=active)


@router.post("", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@legacy_router.post("", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@legacy_router.post("/", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_own_company(
    payload: OwnCompanyCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.administrator)),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    # Enforce license max_companies (0 = unlimited, but we treat <=0 as 1 for self-serve).
    license_row = await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    lic = license_row.scalar_one_or_none()
    max_companies = int(getattr(lic, "max_companies", 1) or 0)
    if max_companies <= 0:
        max_companies = 1
    count_row = await db.execute(select(func.count()).select_from(OwnCompany).where(OwnCompany.tenant_id == tenant_id))
    current_count = int(count_row.scalar_one() or 0)
    if current_count >= max_companies:
        raise HTTPException(status_code=402, detail="Company limit reached for current plan")

    obj = OwnCompany(
        tenant_id=tenant_id,
        name=payload.name.strip(),
        legal_name=(payload.legal_name.strip() if isinstance(payload.legal_name, str) else None),
        tax_id=(payload.tax_id.strip() if isinstance(payload.tax_id, str) else None),
        phone=(payload.phone.strip() if isinstance(payload.phone, str) else None),
        email=(payload.email.strip() if isinstance(payload.email, str) else None),
        website=(payload.website.strip() if isinstance(payload.website, str) else None),
        country_code=(payload.country_code.strip().upper() if isinstance(payload.country_code, str) else None),
        country=(payload.country.strip() if isinstance(payload.country, str) else None),
        city=(payload.city.strip() if isinstance(payload.city, str) else None),
        address=(payload.address.strip() if isinstance(payload.address, str) else None),
        notes=(payload.notes.strip() if isinstance(payload.notes, str) else None),
        contacts=payload.contacts or {},
        extra=payload.extra or {},
        bank_details=payload.bank_details or {},
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=str(current_user.sub or "").strip() or None,
            action="own_company.created",
            target_type="own_company",
            target_id=str(obj.id),
            payload={"name": obj.name},
        )
    except Exception:
        pass
    return OwnCompanyOut.model_validate(obj)


@router.patch("/{own_company_id}", response_model=OwnCompanyOut)
@legacy_router.patch("/{own_company_id}", response_model=OwnCompanyOut, include_in_schema=False)
async def patch_own_company(
    own_company_id: UUID,
    payload: OwnCompanyPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.administrator)),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    row = await db.execute(
        select(OwnCompany).where(OwnCompany.id == str(own_company_id), OwnCompany.tenant_id == tenant_id).limit(1)
    )
    obj = row.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="Own company not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=str(current_user.sub or "").strip() or None,
            action="own_company.updated",
            target_type="own_company",
            target_id=str(obj.id),
            payload={"fields": sorted(list(updates.keys()))},
        )
    except Exception:
        pass
    return OwnCompanyOut.model_validate(obj)


@router.post("/active", response_model=OwnCompanyListOut)
@legacy_router.post("/active", response_model=OwnCompanyListOut, include_in_schema=False)
async def set_active_own_company(
    payload: SetActiveOwnCompanyIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if not current_user or not current_user.sub:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validate belongs to tenant
    row = await db.execute(
        select(OwnCompany.id).where(OwnCompany.id == str(payload.own_company_id), OwnCompany.tenant_id == tenant_id).limit(1)
    )
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=422, detail="Invalid own company")

    user = await db.get(User, str(current_user.sub))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    prefs = dict(user.preferences or {})
    prefs["active_own_company_id"] = str(payload.own_company_id)
    user.preferences = prefs
    await db.commit()
    await db.refresh(user)

    rows = await db.execute(select(OwnCompany).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()))
    items = list(rows.scalars().all())
    return OwnCompanyListOut(items=[OwnCompanyOut.model_validate(x) for x in items], active_own_company_id=str(payload.own_company_id))

