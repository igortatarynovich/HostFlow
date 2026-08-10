from __future__ import annotations

import json
import uuid
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate_children import CandidateVisa


router = APIRouter(prefix="/candidates", tags=["candidate-visas"], redirect_slashes=False)


class VisaCreate(BaseModel):
    visa_type: str
    status: str
    checkpoints: Dict[str, str] = {}
    issued_on: Optional[str] = None
    meta: Dict[str, object] = {}


class VisaUpdate(BaseModel):
    status: Optional[str] = None
    checkpoints: Optional[Dict[str, str]] = None
    issued_on: Optional[str] = None
    meta: Optional[Dict[str, object]] = None


class VisaOut(BaseModel):
    id: str
    candidate_id: str
    visa_type: str
    status: str
    checkpoints: Dict[str, str]
    issued_on: Optional[str]
    meta: Dict[str, object]


def _visa_to_out(row: CandidateVisa) -> VisaOut:
    checkpoints = {}
    meta = {}
    if row.checkpoints:
        try:
            checkpoints = json.loads(row.checkpoints)
        except Exception:
            checkpoints = {}
    if row.meta:
        try:
            meta = json.loads(row.meta)
        except Exception:
            meta = {}
    return VisaOut(
        id=row.id,
        candidate_id=row.candidate_id,
        visa_type=row.visa_type,
        status=row.status,
        checkpoints=checkpoints,
        issued_on=row.issued_on,
        meta=meta,
    )


@router.post(
    "/{candidate_id}/visas",
    response_model=VisaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trust_write())],
)
async def create_visa(
    candidate_id: uuid.UUID,
    payload: VisaCreate,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    visa_id = str(uuid.uuid4())
    await db.execute(
        insert(CandidateVisa).values(
            id=visa_id,
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            visa_type=payload.visa_type,
            status=payload.status,
            checkpoints=json.dumps(payload.checkpoints or {}, ensure_ascii=False),
            issued_on=payload.issued_on,
            meta=json.dumps(payload.meta or {}, ensure_ascii=False),
        )
    )
    await db.commit()
    row = await db.execute(
        select(CandidateVisa).where(
            CandidateVisa.id == visa_id, CandidateVisa.tenant_id == str(tenant_id)
        )
    )
    visa = row.scalar_one()
    return _visa_to_out(visa)


@router.get(
    "/{candidate_id}/visas",
    response_model=list[VisaOut],
    dependencies=[Depends(require_trust_read())],
)
async def list_visas(
    candidate_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    result = await db.execute(
        select(CandidateVisa).where(
            CandidateVisa.candidate_id == str(candidate_id),
            CandidateVisa.tenant_id == str(tenant_id),
        )
    )
    return [_visa_to_out(r) for r in result.scalars().all()]


@router.patch(
    "/{candidate_id}/visas/{visa_id}",
    response_model=VisaOut,
    dependencies=[Depends(require_trust_write())],
)
async def update_visa(
    candidate_id: uuid.UUID,
    visa_id: uuid.UUID,
    payload: VisaUpdate,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    result = await db.execute(
        select(CandidateVisa).where(
            CandidateVisa.id == str(visa_id),
            CandidateVisa.candidate_id == str(candidate_id),
            CandidateVisa.tenant_id == str(tenant_id),
        )
    )
    visa = result.scalar_one_or_none()
    if not visa:
        raise HTTPException(status_code=404, detail="Visa not found")

    changes = {}
    if payload.status is not None:
        changes["status"] = payload.status
    if payload.checkpoints is not None:
        changes["checkpoints"] = json.dumps(payload.checkpoints, ensure_ascii=False)
    if payload.issued_on is not None:
        changes["issued_on"] = payload.issued_on
    if payload.meta is not None:
        changes["meta"] = json.dumps(payload.meta, ensure_ascii=False)

    if changes:
        changes["updated_at"] = text("CURRENT_TIMESTAMP")
        await db.execute(
            update(CandidateVisa)
            .where(
                CandidateVisa.id == str(visa_id),
                CandidateVisa.tenant_id == str(tenant_id),
            )
            .values(**changes)
        )
        await db.commit()

    result = await db.execute(
        select(CandidateVisa).where(
            CandidateVisa.id == str(visa_id),
            CandidateVisa.tenant_id == str(tenant_id),
        )
    )
    visa = result.scalar_one()
    return _visa_to_out(visa)


@router.delete(
    "/{candidate_id}/visas/{visa_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
    dependencies=[Depends(require_trust_write())],
)
async def delete_visa(
    candidate_id: uuid.UUID,
    visa_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    result = await db.execute(
        delete(CandidateVisa).where(
            CandidateVisa.id == str(visa_id),
            CandidateVisa.candidate_id == str(candidate_id),
            CandidateVisa.tenant_id == str(tenant_id),
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Visa not found")
    await db.commit()
