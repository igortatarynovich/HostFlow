from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.services.handoff import is_client_tenant, can_client_edit
from backend.app.services.recruitment_handoff_write_guard import require_agency_recruitment_write_allowed

router = APIRouter(prefix="/candidate-links", tags=["candidate-links"])


class LinkIn(BaseModel):
    company_id: str | None = None
    vacancy_id: str | None = None


@router.get("/{candidate_id}")
async def get_links(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    row = await db.execute(
        select(Candidate).where(
            Candidate.id == str(candidate_id), Candidate.tenant_id == str(tenant_id)
        )
    )
    c = row.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"company_id": c.company_id, "vacancy_id": c.vacancy_id}


@router.patch(
    "/{candidate_id}", dependencies=[Depends(require_roles(Role.manager, Role.admin))]
)
async def set_links(
    candidate_id: UUID,
    payload: LinkIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    row = await db.execute(
        select(Candidate).where(
            Candidate.id == str(candidate_id), Candidate.tenant_id == tenant_id_str
        )
    )
    c = row.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Vacancy/company links are recruitment dossier mutations — no privileged bypass:
    # re-linking after handoff would break audit / intent of a transferred candidate.
    if await is_client_tenant(db, tenant_id_str):
        if not await can_client_edit(db, str(candidate_id), tenant_id_str):
            raise HTTPException(status_code=403, detail="Cannot edit links: no accepted handoff")
    else:
        await require_agency_recruitment_write_allowed(
            db,
            agency_tenant_id=tenant_id_str,
            candidate_id=str(candidate_id),
            bypass=None,
        )

    vals = {}
    if payload.company_id is not None:
        vals["company_id"] = payload.company_id
    if payload.vacancy_id is not None:
        vals["vacancy_id"] = payload.vacancy_id

    if vals:
        await db.execute(
            update(Candidate)
            .where(
                Candidate.id == str(candidate_id), Candidate.tenant_id == str(tenant_id)
            )
            .values(**vals)
        )
        await db.commit()

    return {
        "ok": True,
        "company_id": vals.get("company_id", c.company_id),
        "vacancy_id": vals.get("vacancy_id", c.vacancy_id),
    }
