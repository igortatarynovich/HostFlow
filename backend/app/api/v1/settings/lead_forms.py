from __future__ import annotations

from datetime import datetime
from typing import Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.mixins import now_utc
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.services.lead_forms_quota import (
    ensure_public_slug_unique_for_tenant,
    ensure_tenant_lead_form_active_count_allows_transition,
    normalize_and_validate_public_slug,
)
from backend.app.services.plan_feature_gates import count_tenant_lead_sources, ensure_lead_source_limit


router = APIRouter(prefix="/lead-forms", tags=["settings-lead-forms"])


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


class TenantLeadFormOut(BaseModel):
    id: str
    title: str
    public_slug: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TenantLeadFormCreateIn(BaseModel):
    title: str = Field(default="", max_length=256)


class TenantLeadFormPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    is_active: bool | None = None
    public_slug: str | None = Field(default=None, max_length=64)


def _out(row: TenantLeadForm) -> TenantLeadFormOut:
    return TenantLeadFormOut(
        id=row.id,
        title=row.title or "",
        public_slug=getattr(row, "public_slug", None),
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "",
    response_model=list[TenantLeadFormOut],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_lead_forms(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> list[TenantLeadFormOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rows = (
        await db.execute(
            select(TenantLeadForm)
            .where(TenantLeadForm.tenant_id == tenant_id)
            .order_by(TenantLeadForm.created_at.asc())
        )
    ).scalars().all()
    return [_out(r) for r in rows]


@router.post(
    "",
    response_model=TenantLeadFormOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_lead_form(
    payload: TenantLeadFormCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantLeadFormOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    current_sources = await count_tenant_lead_sources(db, tenant_id)
    await ensure_lead_source_limit(db, tenant_id, current_count=current_sources, extra_sources=1)
    await ensure_tenant_lead_form_active_count_allows_transition(
        db,
        tenant_id,
        was_active=False,
        will_be_active=True,
    )
    row = TenantLeadForm(
        id=str(uuid4()),
        tenant_id=tenant_id,
        title=(payload.title or "").strip() or "Lead form",
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out(row)


@router.patch(
    "/{form_id}",
    response_model=TenantLeadFormOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def patch_lead_form(
    form_id: str,
    payload: TenantLeadFormPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantLeadFormOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    row = (
        await db.execute(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.id == form_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Lead form not found")
    patch_data = payload.model_dump(exclude_unset=True)
    was_active = bool(row.is_active)
    if payload.title is not None:
        row.title = payload.title.strip() or row.title
    if "public_slug" in patch_data:
        raw_slug = patch_data.get("public_slug")
        try:
            norm = normalize_and_validate_public_slug(raw_slug if isinstance(raw_slug, str) else None)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "lead_form_public_slug_invalid", "message": str(exc)},
            ) from exc
        if norm is None:
            row.public_slug = None
        else:
            await ensure_public_slug_unique_for_tenant(
                db,
                tenant_id,
                slug=norm,
                exclude_form_id=row.id,
            )
            row.public_slug = norm
    will_active = was_active if payload.is_active is None else bool(payload.is_active)
    if not was_active and will_active:
        current_sources = await count_tenant_lead_sources(db, tenant_id)
        await ensure_lead_source_limit(db, tenant_id, current_count=current_sources, extra_sources=1)
    await ensure_tenant_lead_form_active_count_allows_transition(
        db,
        tenant_id,
        was_active=was_active,
        will_be_active=will_active,
    )
    if payload.is_active is not None:
        row.is_active = will_active
    row.updated_at = now_utc()
    await db.commit()
    await db.refresh(row)
    return _out(row)
