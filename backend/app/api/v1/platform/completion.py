"""Platform completion + handoff resolution API."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user, require_roles
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.platform_completion_service import resolve_platform_completion

router = APIRouter(
    prefix="/platform/completion",
    tags=["platform-completion"],
    redirect_slashes=False,
)


class PlatformCompletionResolveIn(BaseModel):
    event: str = Field(..., min_length=1, max_length=128)
    context: dict[str, Any] = Field(default_factory=dict)


class PlatformCompletionBlockOut(BaseModel):
    title: str
    message: str
    action_label: Optional[str] = None
    client_id: Optional[str] = None


class PlatformHandoffOut(BaseModel):
    action: str
    label: str
    hint: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


class PlatformCompletionResolveOut(BaseModel):
    event: str
    completion: PlatformCompletionBlockOut
    handoff: Optional[PlatformHandoffOut] = None
    handoffs: list[PlatformHandoffOut] = Field(default_factory=list)
    done: Optional[PlatformCompletionBlockOut] = None


@router.post("/resolve", response_model=PlatformCompletionResolveOut)
async def resolve_completion(
    payload: PlatformCompletionResolveIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_roles(*HIRING_CANDIDATE_PROFILE_READ_ROLES)),
    __user: UserCtx = Depends(get_current_user),
) -> PlatformCompletionResolveOut:
    db, tenant_uuid = db_tenant
    result = await resolve_platform_completion(
        db,
        str(tenant_uuid),
        event=payload.event,
        context=payload.context,
    )
    return PlatformCompletionResolveOut.model_validate(result)
