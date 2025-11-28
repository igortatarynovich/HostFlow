from __future__ import annotations

import json
import uuid
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select, update, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate_children import CandidatePermit
from backend.app.api.v1.candidates.acl import ensure_candidate_access


router = APIRouter(prefix="/candidates", tags=["candidate-permits"], redirect_slashes=False)

RESTRICTED_ROLES = {
    Role.recruiter.value,
    Role.supervisor.value,
    Role.manager.value,
}


class PermitCreate(BaseModel):
    permit_type: str
    number: Optional[str] = None
    status: str
    issued_on: Optional[str] = None
    expires_on: Optional[str] = None
    meta: Dict[str, object] = {}


class PermitUpdate(BaseModel):
    number: Optional[str] = None
    status: Optional[str] = None
    issued_on: Optional[str] = None
    expires_on: Optional[str] = None
    meta: Optional[Dict[str, object]] = None


class PermitOut(BaseModel):
    id: str
    candidate_id: str
    permit_type: str
    number: Optional[str]
    status: str
    issued_on: Optional[str]
    expires_on: Optional[str]
    meta: Dict[str, object]


def _to_out(row: CandidatePermit) -> PermitOut:
    meta = {}
    if row.meta:
        try:
            meta = json.loads(row.meta)
        except Exception:
            meta = {}
    return PermitOut(
        id=row.id,
        candidate_id=row.candidate_id,
        permit_type=row.permit_type,
        number=row.number,
        status=row.status,
        issued_on=row.issued_on,
        expires_on=row.expires_on,
        meta=meta,
    )


@router.post(
    "/{candidate_id}/permits",
    response_model=PermitOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.manager, Role.admin, Role.recruiter))],
)
async def create_permit(
    candidate_id: uuid.UUID,
    payload: PermitCreate,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    permit_id = str(uuid.uuid4())
    await db.execute(
        insert(CandidatePermit).values(
            id=permit_id,
            tenant_id=tenant_str,
            candidate_id=str(candidate_id),
            permit_type=payload.permit_type,
            number=payload.number,
            status=payload.status,
            issued_on=payload.issued_on,
            expires_on=payload.expires_on,
            meta=json.dumps(payload.meta or {}, ensure_ascii=False),
        )
    )
    await db.commit()
    row = await db.execute(
        select(CandidatePermit).where(
            CandidatePermit.id == permit_id, CandidatePermit.tenant_id == tenant_str
        )
    )
    permit = row.scalar_one()
    return _to_out(permit)


@router.get(
    "/{candidate_id}/permits",
    response_model=list[PermitOut],
    dependencies=[Depends(require_roles(Role.manager, Role.viewer, Role.admin, Role.recruiter))],
)
async def list_permits(
    candidate_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    result = await db.execute(
        select(CandidatePermit).where(
            CandidatePermit.candidate_id == str(candidate_id),
            CandidatePermit.tenant_id == tenant_str,
        )
    )
    rows = result.scalars().all()
    return [_to_out(r) for r in rows]


@router.patch(
    "/{candidate_id}/permits/{permit_id}",
    response_model=PermitOut,
    dependencies=[Depends(require_roles(Role.manager, Role.admin, Role.recruiter))],
)
async def update_permit(
    candidate_id: uuid.UUID,
    permit_id: uuid.UUID,
    payload: PermitUpdate,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    result = await db.execute(
        select(CandidatePermit).where(
            CandidatePermit.id == str(permit_id),
            CandidatePermit.candidate_id == str(candidate_id),
            CandidatePermit.tenant_id == tenant_str,
        )
    )
    permit = result.scalar_one_or_none()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    changes = {}
    if payload.number is not None:
        changes["number"] = payload.number
    if payload.status is not None:
        changes["status"] = payload.status
    if payload.issued_on is not None:
        changes["issued_on"] = payload.issued_on
    if payload.expires_on is not None:
        changes["expires_on"] = payload.expires_on
    if payload.meta is not None:
        changes["meta"] = json.dumps(payload.meta, ensure_ascii=False)

    if changes:
        changes["updated_at"] = text("CURRENT_TIMESTAMP")
        await db.execute(
            update(CandidatePermit)
            .where(
                CandidatePermit.id == str(permit_id),
                CandidatePermit.tenant_id == tenant_str,
            )
            .values(**changes)
        )
        await db.commit()

    result = await db.execute(
        select(CandidatePermit).where(
            CandidatePermit.id == str(permit_id),
            CandidatePermit.tenant_id == tenant_str,
        )
    )
    permit = result.scalar_one()
    return _to_out(permit)


@router.delete(
    "/{candidate_id}/permits/{permit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.manager, Role.admin, Role.recruiter))],
)
async def delete_permit(
    candidate_id: uuid.UUID,
    permit_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    result = await db.execute(
        delete(CandidatePermit).where(
            CandidatePermit.id == str(permit_id),
            CandidatePermit.candidate_id == str(candidate_id),
            CandidatePermit.tenant_id == tenant_str,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Permit not found")
    await db.commit()
