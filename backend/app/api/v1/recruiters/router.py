from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.recruiter_assignment import assign_recruiter as assign_recruiter_service


class AssignRecruiterRequest(BaseModel):
    vacancy_id: Optional[UUID] = None
    company_id: Optional[UUID] = None


class AssignRecruiterResponse(BaseModel):
    recruiter_id: Optional[UUID]
    strategy: str
    context: dict = Field(default_factory=dict)


router = APIRouter(
    prefix="/recruiters",
    tags=["recruiters"],
)


@router.post(
    "/assign",
    response_model=AssignRecruiterResponse,
    dependencies=[Depends(require_trust_write())],
)
async def assign_recruiter_endpoint(
    payload: AssignRecruiterRequest,
    db_tenant = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    decision = await assign_recruiter_service(
        db=db,
        tenant_id=str(tenant_id),
        vacancy_id=str(payload.vacancy_id) if payload.vacancy_id else None,
        company_id=str(payload.company_id) if payload.company_id else None,
    )
    recruiter_uuid: Optional[UUID] = None
    if decision.recruiter_id:
        recruiter_uuid = UUID(str(decision.recruiter_id))
    return AssignRecruiterResponse(
        recruiter_id=recruiter_uuid,
        strategy=decision.strategy,
        context=jsonable_encoder(decision.context, custom_encoder={UUID: str}),
    )
