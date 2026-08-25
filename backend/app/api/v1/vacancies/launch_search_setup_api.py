from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
from backend.app.services.launch_search_vacancy_setup import (
    LaunchSearchSetupError,
    ensure_launch_search_vacancy_defaults,
)

router = APIRouter(tags=["vacancies-launch-search"])

LaunchSearchRoleIn = Literal["driver", "warehouse", "office", "other"]


class LaunchSearchSetupIn(BaseModel):
    role: LaunchSearchRoleIn = Field(default="driver")


class LaunchSearchSetupOut(BaseModel):
    vacancy_id: str
    company_id: str
    funnel_id: Optional[str] = None
    funnel_name: Optional[str] = None
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    lead_funnel_id: Optional[str] = None


@router.post(
    "/{vacancy_id}/launch-search/setup",
    response_model=LaunchSearchSetupOut,
    dependencies=[Depends(require_trust_write())],
)
async def setup_launch_search_vacancy(
    vacancy_id: UUID,
    payload: LaunchSearchSetupIn,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    try:
        result = await ensure_launch_search_vacancy_defaults(
            db,
            tenant_id=str(tenant_id),
            vacancy_id=str(vacancy_id),
            role=payload.role,
        )
    except LaunchSearchSetupError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await db.commit()
    return LaunchSearchSetupOut.model_validate(result)
