"""API for contact attempts (Zarejestruj próbę kontaktu)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.deps import get_current_user, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.services.contact_attempts import (
    create_attempt,
    get_effective_contact_policy,
    list_attempts,
)

router = APIRouter(prefix="/candidates", tags=["contact-attempts"])

CHANNELS = ("call", "sms", "email", "whatsapp", "messenger")
RESULTS = ("no_answer", "answered", "wrong_number", "unavailable")


class ContactAttemptOut(BaseModel):
    id: str
    candidate_id: str
    attempt_number: int
    attempted_at: datetime
    attempted_by_user_id: Optional[str]
    channel: str
    result: str
    note: Optional[str]

    class Config:
        from_attributes = True


class ContactAttemptCreate(BaseModel):
    channel: str = Field(..., pattern="^(call|sms|email|whatsapp|messenger)$")
    result: str = Field(..., pattern="^(no_answer|answered|wrong_number|unavailable)$")
    note: Optional[str] = Field(None, max_length=2000)


class ContactPolicyOut(BaseModel):
    enabled: bool
    max_attempts: int
    post_action: str
    stage_code: Optional[str] = None
    rodo_sent: bool = False


@router.get("/{candidate_id}/contact-attempts", response_model=List[ContactAttemptOut])
async def list_contact_attempts(
    candidate_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """List contact attempts for candidate."""
    db, tenant_id = db_tenant
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    attempts = await list_attempts(db, str(candidate_id))
    return [ContactAttemptOut.model_validate(a) for a in attempts]


@router.get("/{candidate_id}/contact-attempts/policy", response_model=ContactPolicyOut)
async def get_contact_policy(
    candidate_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Get effective contact policy for candidate."""
    from backend.app.models.candidate import Candidate

    from backend.app.models import Candidate as CandidateModel

    db, tenant_id = db_tenant
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    cand = await db.get(CandidateModel, str(candidate_id))
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    policy = await get_effective_contact_policy(db, str(tenant_id), cand)
    return ContactPolicyOut(**policy)


@router.post("/{candidate_id}/contact-attempts", response_model=ContactAttemptOut, status_code=201)
async def create_contact_attempt(
    candidate_id: UUID,
    payload: ContactAttemptCreate,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Register contact attempt (Zarejestruj próbę kontaktu)."""
    db, tenant_id = db_tenant
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    attempt, err = await create_attempt(
        db,
        candidate_id=str(candidate_id),
        tenant_id=str(tenant_id),
        channel=payload.channel,
        result=payload.result,
        note=payload.note,
        actor_id=current_user.sub,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.commit()
    await db.refresh(attempt)
    return ContactAttemptOut.model_validate(attempt)
