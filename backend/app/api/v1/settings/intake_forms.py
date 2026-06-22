"""Intake Source / Form Builder admin read API (P6 foundation)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.intake_form_admin_context import (
    build_intake_form_admin_context,
    run_intake_form_smoke_test,
)

router = APIRouter(prefix="/intake-forms", tags=["settings-intake-forms"])


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


class IntakeFormSummaryOut(BaseModel):
    id: str
    title: str
    public_slug: Optional[str] = None
    is_active: bool
    entity_profile_code: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IntakeFormDetailOut(BaseModel):
    form: dict[str, Any]
    intake_source_profile: Optional[dict[str, Any]] = None
    intake_source_profile_id: Optional[str] = None
    entity_profile: dict[str, Any]
    presentation: dict[str, Any]
    presentations_available: List[dict[str, Any]] = Field(default_factory=list)
    submit_destination: dict[str, Any]


class IntakeFormSmokeTestOut(BaseModel):
    lead_id: str
    candidate_id: Optional[str] = None
    token: str
    expires_at: datetime
    contacts: dict[str, Any]
    stage: Optional[str] = None
    message: str


@router.get(
    "/{form_id}",
    response_model=IntakeFormDetailOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_intake_form_detail(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormDetailOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    payload = await build_intake_form_admin_context(db, tenant_id=tenant_id, form_id=form_id)
    return IntakeFormDetailOut.model_validate(payload)


@router.post(
    "/{form_id}/smoke-test",
    response_model=IntakeFormSmokeTestOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def smoke_test_intake_form(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormSmokeTestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    payload = await run_intake_form_smoke_test(db, tenant_id=tenant_id, form_id=form_id)
    return IntakeFormSmokeTestOut.model_validate(payload)
