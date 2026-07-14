from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
from backend.app.services.search_workspace_service import get_search_workspace_pulse

router = APIRouter(tags=["vacancies-workspace"])


class SearchWorkspacePulseOut(BaseModel):
    search_id: str
    mode: str = "operate"
    mode_label: str = "Работаем"
    next_action: Optional[dict[str, Any]] = None
    after_that: list[dict[str, Any]] = Field(default_factory=list)
    today: list[dict[str, Any]] = Field(default_factory=list)
    later: list[dict[str, Any]] = Field(default_factory=list)
    attention: list[dict[str, Any]] = Field(default_factory=list)
    status: dict[str, Any] = Field(default_factory=dict)


@router.get("/{vacancy_id}/workspace", response_model=SearchWorkspacePulseOut)
async def get_search_workspace(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    try:
        pulse = await get_search_workspace_pulse(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return SearchWorkspacePulseOut.model_validate(pulse)
