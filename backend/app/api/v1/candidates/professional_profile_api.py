"""Professional profile for one candidate.

The projection stays read-only. Availability is the one recruiter write,
and it uses the same availability row as intake.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_read, require_trust_write
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.professional_profile import (
    ProfessionalProfileNotFound,
    load_professional_profile,
)

router = APIRouter()


@router.get(
    "/{candidate_id}/professional-profile",
    dependencies=[Depends(require_trust_read())],
    summary="Read-only professional profile projection",
)
async def get_professional_profile(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)
    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)
    try:
        return await load_professional_profile(
            db,
            tenant_id=tenant_id_str,
            candidate_id=candidate_id_str,
        )
    except ProfessionalProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc


class AvailabilityUpdate(BaseModel):
    available_from: Optional[date] = None


@router.patch(
    "/{candidate_id}/professional-profile/availability",
    dependencies=[Depends(require_trust_write())],
    summary="Set when the candidate can start",
)
async def patch_professional_availability(
    candidate_id: UUID,
    payload: AvailabilityUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)
    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)
    from backend.app.services.professional_intake_writer import set_candidate_available_from

    await set_candidate_available_from(
        db,
        tenant_id=tenant_id_str,
        candidate_id=candidate_id_str,
        available_from=payload.available_from,
    )
    await db.commit()
    try:
        return await load_professional_profile(
            db,
            tenant_id=tenant_id_str,
            candidate_id=candidate_id_str,
        )
    except ProfessionalProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc
