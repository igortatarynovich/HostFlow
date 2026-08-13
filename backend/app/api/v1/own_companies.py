from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import OwnCompany, User
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.api.v1.utils.own_company_acl import (
    allowed_own_company_ids_from_prefs,
    is_own_company_id_allowed_for_user,
    role_bypasses_own_company_acl,
)
from backend.app.modules.companies import crud as companies_crud
from backend.app.services.audit import log_activity
from backend.app.services import billing_restrictions
from backend.app.services.onboarding_demo_seed import seed_onboarding_demo_if_needed


router = APIRouter(prefix="/own-companies", tags=["own-companies"], redirect_slashes=False)
# Back-compat for older deployments using underscore paths.
legacy_router = APIRouter(prefix="/own_companies", tags=["own-companies"], redirect_slashes=False)


async def _load_own_company_acl_context(
    db: AsyncSession,
    current_user: UserCtx | None,
) -> tuple[bool, Optional[set[str]], dict[str, Any]]:
    prefs: dict[str, Any] = {}
    if current_user and current_user.sub:
        user_row = await db.execute(select(User.preferences).where(User.id == str(current_user.sub)).limit(1))
        raw = user_row.scalar_one_or_none()
        if isinstance(raw, dict):
            prefs = dict(raw)
    bypass = role_bypasses_own_company_acl(current_user.role if current_user else None)
    allowed = allowed_own_company_ids_from_prefs(prefs)
    return bypass, allowed, prefs


def _filter_own_companies_by_acl(
    items: List[OwnCompany],
    *,
    bypass: bool,
    allowed: Optional[set[str]],
) -> List[OwnCompany]:
    if allowed is None or bypass:
        return items
    allow = allowed
    return [x for x in items if str(x.id) in allow]


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
    onboarding_demo: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


_ONBOARDING_CREATE_KEYS = frozenset(
    {
        "business_type",
        "industry",
        "team_size",
        "workspace_name",
        "workspace_count",
        "working_hours_preset",
    }
)


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
    # Onboarding v2 (merged into `extra` + first-own-company tenant bootstrap)
    business_type: Optional[str] = Field(default=None, max_length=32)
    industry: Optional[str] = Field(default=None, max_length=64)
    team_size: Optional[str] = Field(default=None, max_length=32)
    workspace_name: Optional[str] = Field(default=None, max_length=255)
    workspace_count: Optional[int] = Field(default=None, ge=1, le=999)
    working_hours_preset: Optional[str] = Field(default=None, max_length=64)


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

    bypass, allowed, prefs = await _load_own_company_acl_context(db, current_user)
    items = _filter_own_companies_by_acl(items, bypass=bypass, allowed=allowed)

    active = str(prefs.get("active_own_company_id") or "").strip() or None
    if active and allowed is not None and not bypass and active not in allowed:
        active = None
    return OwnCompanyListOut(items=[OwnCompanyOut.model_validate(x) for x in items], active_own_company_id=active)


@router.post("", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@legacy_router.post("", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@legacy_router.post("/", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_own_company(
    payload: OwnCompanyCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id)

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

    dumped = payload.model_dump()
    ob_fields = {k: dumped.pop(k, None) for k in _ONBOARDING_CREATE_KEYS}
    extra = dict(dumped.pop("extra") or {})
    bt_raw = ob_fields.get("business_type") or extra.get("business_type")
    bt_norm = str(bt_raw or "").strip().lower()
    if bt_norm not in ("agency", "employer", "services"):
        bt_norm = "agency"
    extra["business_type"] = bt_norm
    if ob_fields.get("industry") is not None:
        _ind = str(ob_fields["industry"]).strip()
        if _ind:
            extra["industry"] = _ind
    if ob_fields.get("team_size") is not None:
        _ts = str(ob_fields["team_size"]).strip()
        if _ts:
            extra["team_size"] = _ts
    if ob_fields.get("workspace_name") is not None:
        _wn = str(ob_fields["workspace_name"]).strip()
        if _wn:
            extra["workspace_name"] = _wn
    if ob_fields.get("workspace_count") is not None:
        try:
            _wc = int(ob_fields["workspace_count"])
            if _wc >= 1:
                extra["workspace_count"] = _wc
        except (TypeError, ValueError):
            pass
    if ob_fields.get("working_hours_preset") is not None:
        _wh = str(ob_fields["working_hours_preset"]).strip()
        if _wh:
            extra["working_hours_preset"] = _wh

    obj = OwnCompany(
        tenant_id=tenant_id,
        name=dumped["name"].strip(),
        legal_name=(dumped["legal_name"].strip() if isinstance(dumped.get("legal_name"), str) else None),
        tax_id=(dumped["tax_id"].strip() if isinstance(dumped.get("tax_id"), str) else None),
        phone=(dumped["phone"].strip() if isinstance(dumped.get("phone"), str) else None),
        email=(dumped["email"].strip() if isinstance(dumped.get("email"), str) else None),
        website=(dumped["website"].strip() if isinstance(dumped.get("website"), str) else None),
        country_code=(
            dumped["country_code"].strip().upper() if isinstance(dumped.get("country_code"), str) else None
        ),
        country=(dumped["country"].strip() if isinstance(dumped.get("country"), str) else None),
        city=(dumped["city"].strip() if isinstance(dumped.get("city"), str) else None),
        address=(dumped["address"].strip() if isinstance(dumped.get("address"), str) else None),
        notes=(dumped["notes"].strip() if isinstance(dumped.get("notes"), str) else None),
        contacts=dumped.get("contacts") or {},
        extra=extra,
        bank_details=dumped.get("bank_details") or {},
    )
    db.add(obj)
    await db.flush()
    demo_summary: Dict[str, Any] | None = None
    if current_count == 0:
        await companies_crud.bootstrap_tenant_for_own_company_onboarding(
            db,
            tenant_id=tenant_id,
            company_type=bt_norm,
            industry=extra.get("industry"),
            team_size=extra.get("team_size"),
            workspace_name=extra.get("workspace_name"),
            workspace_count=extra.get("workspace_count"),
            working_hours_preset=extra.get("working_hours_preset"),
            actor_user_id=str(current_user.sub).strip() if getattr(current_user, "sub", None) else None,
        )
        try:
            demo_summary = await seed_onboarding_demo_if_needed(
                db,
                tenant_id=tenant_id,
                own_company_id=str(obj.id),
                business_type=bt_norm,
                assignee_user_id=str(current_user.sub).strip() if current_user and current_user.sub else None,
            )
        except Exception:
            demo_summary = None
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
    out = OwnCompanyOut.model_validate(obj)
    if demo_summary:
        return out.model_copy(update={"onboarding_demo": demo_summary})
    return out


@router.patch("/{own_company_id}", response_model=OwnCompanyOut)
@legacy_router.patch("/{own_company_id}", response_model=OwnCompanyOut, include_in_schema=False)
async def patch_own_company(
    own_company_id: UUID,
    payload: OwnCompanyPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
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
    request: Request,
    payload: SetActiveOwnCompanyIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if not current_user or not current_user.sub:
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_id = str(payload.own_company_id)
    row = await db.execute(
        select(OwnCompany.id).where(
            OwnCompany.id == new_id,
            OwnCompany.tenant_id == tenant_id,
            OwnCompany.is_archived.is_(False),
        ).limit(1)
    )
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=422, detail="Invalid own company")

    user = await db.get(User, str(current_user.sub))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    prefs = dict(user.preferences or {})
    bypass = role_bypasses_own_company_acl(current_user.role)
    allowed = allowed_own_company_ids_from_prefs(prefs)
    if not is_own_company_id_allowed_for_user(new_id, allowed=allowed, bypass=bypass):
        raise HTTPException(status_code=403, detail="Own company not permitted for this user")

    old_active = str(prefs.get("active_own_company_id") or "").strip() or None
    prefs["active_own_company_id"] = new_id
    user.preferences = prefs
    await db.flush()
    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=str(current_user.sub or "").strip() or None,
            action="own_company.active_changed",
            target_type="user",
            target_id=str(current_user.sub),
            payload={"from_own_company_id": old_active, "to_own_company_id": new_id},
            ip=request.client.host if request.client else None,
            ua=(request.headers.get("user-agent") if request else None),
        )
    except Exception:
        pass
    await db.commit()
    await db.refresh(user)

    rows = await db.execute(select(OwnCompany).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()))
    items = _filter_own_companies_by_acl(list(rows.scalars().all()), bypass=bypass, allowed=allowed_own_company_ids_from_prefs(prefs))
    return OwnCompanyListOut(items=[OwnCompanyOut.model_validate(x) for x in items], active_own_company_id=new_id)

