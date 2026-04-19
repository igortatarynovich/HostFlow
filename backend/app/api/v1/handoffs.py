"""API for handoff workflow."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.auth.deps import get_current_user, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.services import billing_restrictions
from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.services.handoff import (
    create_handoff,
    accept_handoff,
    reject_handoff,
    return_handoff,
    change_processor,
    list_pending_for_client,
    list_pending_with_candidates,
    list_handoffs_with_candidates,
    list_available_clients,
    get_pending_handoff,
    get_accepted_handoff,
    get_pending_handoff_for_agency,
    get_accepted_handoff_for_agency,
)

router = APIRouter(prefix="/handoffs", tags=["handoffs"])


class HandoffCreate(BaseModel):
    client_company_id: Optional[UUID] = None
    client_tenant_id: Optional[UUID] = None
    assigned_to_user_id: Optional[UUID] = None


class HandoffBulkCreate(BaseModel):
    candidate_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    client_company_id: UUID
    assigned_to_user_id: Optional[UUID] = None


class HandoffBulkResult(BaseModel):
    created: int
    failed: int
    errors: List[dict] = Field(default_factory=list)


class HandoffOut(BaseModel):
    id: str
    candidate_id: str
    agency_tenant_id: str
    client_company_id: Optional[str] = None
    client_tenant_id: Optional[str] = None
    requested_by_user_id: str
    requested_at: datetime
    assigned_to_user_id: Optional[str] = None
    status: str
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    return_reason: Optional[str] = None
    requested_by_user_name: Optional[str] = None
    assigned_to_user_name: Optional[str] = None

    class Config:
        from_attributes = True


class HandoffReject(BaseModel):
    rejection_reason: str = Field(..., min_length=1)


class HandoffReturn(BaseModel):
    return_reason: str = Field(..., min_length=1)


class HandoffChangeProcessor(BaseModel):
    processor_user_id: str = Field(..., min_length=1)


class AvailableClientOut(BaseModel):
    link_id: str
    client_company_id: Optional[str] = None
    client_tenant_id: Optional[str] = None
    client_name: str


@router.get("/available-clients", response_model=List[AvailableClientOut])
async def get_available_clients(
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """List clients with handoff enabled (for handoff modal)."""
    db, tenant_id = db_tenant
    clients = await list_available_clients(db, str(tenant_id))
    return [AvailableClientOut(**c) for c in clients]


@router.post("/bulk", response_model=HandoffBulkResult)
async def create_handoff_bulk(
    payload: HandoffBulkCreate,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Bulk handoff: create handoffs for multiple candidates to the same client."""
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    cid = str(payload.client_company_id)
    aid = str(payload.assigned_to_user_id) if payload.assigned_to_user_id else None
    created = 0
    errors: List[dict] = []
    for candidate_id in payload.candidate_ids:
        try:
            await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
            handoff, err = await create_handoff(
                db,
                candidate_id=str(candidate_id),
                agency_tenant_id=str(tenant_id),
                client_company_id=cid,
                client_tenant_id=None,
                requested_by_user_id=current_user.sub,
                assigned_to_user_id=aid,
            )
            if err:
                errors.append({"candidate_id": str(candidate_id), "error": err})
            else:
                created += 1
        except HTTPException as e:
            errors.append({"candidate_id": str(candidate_id), "error": str(e.detail)})
        except Exception as e:
            errors.append({"candidate_id": str(candidate_id), "error": str(e)})
    await db.commit()
    return HandoffBulkResult(created=created, failed=len(errors), errors=errors)


@router.post("/candidates/{candidate_id}", response_model=HandoffOut, status_code=201)
async def create_handoff_route(
    candidate_id: UUID,
    payload: HandoffCreate,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Create handoff (Przekaż do klienta). Agency only."""
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    cid = str(payload.client_company_id) if payload.client_company_id else None
    tid = str(payload.client_tenant_id) if payload.client_tenant_id else None
    aid = str(payload.assigned_to_user_id) if payload.assigned_to_user_id else None
    handoff, err = await create_handoff(
        db,
        candidate_id=str(candidate_id),
        agency_tenant_id=str(tenant_id),
        client_company_id=cid,
        client_tenant_id=tid,
        requested_by_user_id=current_user.sub,
        assigned_to_user_id=aid,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.commit()
    await db.refresh(handoff)
    return HandoffOut.model_validate(handoff)


class PendingHandoffWithCandidateOut(BaseModel):
    handoff: HandoffOut
    candidate: dict


class HandoffWithCandidatesListOut(BaseModel):
    total: int
    items: List[PendingHandoffWithCandidateOut]


@router.get("/pending", response_model=List[HandoffOut])
async def list_pending(
    client_company_id: Optional[UUID] = Query(None),
    client_tenant_id: Optional[UUID] = Query(None),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """List pending handoffs for client (Do procesowania)."""
    db, tenant_id = db_tenant
    cid = str(client_company_id) if client_company_id else None
    tid = str(client_tenant_id) if client_tenant_id else None
    if not cid and not tid:
        raise HTTPException(
            status_code=400,
            detail="Provide client_company_id or client_tenant_id",
        )
    handoffs = await list_pending_for_client(
        db, client_company_id=cid, client_tenant_id=tid
    )
    return [HandoffOut.model_validate(h) for h in handoffs]


@router.get("/pending-with-candidates", response_model=List[dict])
async def list_pending_with_candidates_route(
    client_company_id: Optional[UUID] = Query(None),
    client_tenant_id: Optional[UUID] = Query(None),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """List pending handoffs with candidate summary (Do procesowania inbox)."""
    db, tenant_id = db_tenant
    cid = str(client_company_id) if client_company_id else None
    tid = str(client_tenant_id) if client_tenant_id else None
    if not cid and not tid:
        raise HTTPException(
            status_code=400,
            detail="Provide client_company_id or client_tenant_id",
        )
    items = await list_pending_with_candidates(
        db, client_company_id=cid, client_tenant_id=tid
    )
    return [
        {
            "handoff": HandoffOut.model_validate(item["handoff"]),
            "candidate": item["candidate"],
        }
        for item in items
    ]


@router.get("/with-candidates", response_model=HandoffWithCandidatesListOut)
async def list_handoffs_with_candidates_route(
    client_company_id: Optional[UUID] = Query(None),
    client_tenant_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(
        None,
        description="Comma-separated handoff statuses: pending, accepted, rejected, returned. "
        "pending maps to internal status pending_review.",
    ),
    from_days: int = Query(
        30,
        ge=0,
        le=365,
        description="Look back this many days for history (0 = all time). "
        "Applied to reviewed_at/requested_at.",
    ),
    date_from: Optional[date] = Query(
        None,
        description="Requested date range start (YYYY-MM-DD). Overrides from_days when provided.",
    ),
    date_to: Optional[date] = Query(
        None,
        description="Requested date range end (YYYY-MM-DD, inclusive). Overrides from_days when provided.",
    ),
    stage_codes: Optional[str] = Query(
        None,
        description="Comma-separated candidate stage codes filter.",
    ),
    q: Optional[str] = Query(
        None,
        description="Search by first_name, last_name, email, short_id (min 2 chars).",
    ),
    order_by: str = Query(
        "requested_at",
        description="Sort by: requested_at, reviewed_at, candidate_name, status.",
    ),
    desc: bool = Query(True, description="Sort descending."),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """
    List handoffs with candidate summary (history for Do procesowania).

    The same endpoint is used by clients (client_tenant_id) and agencies (client_company_id).
    """
    db, tenant_id = db_tenant
    cid = str(client_company_id) if client_company_id else None
    tid = str(client_tenant_id) if client_tenant_id else None
    if not cid and not tid:
        raise HTTPException(
            status_code=400,
            detail="Provide client_company_id or client_tenant_id",
        )

    # Parse and normalize status filter from UI values
    db_statuses: list[str] = []
    if status:
        raw = [s.strip().lower() for s in status.split(",") if s.strip()]
        for s in raw:
            if s == "pending":
                db_statuses.append("pending_review")
            elif s in {"accepted", "rejected", "returned"}:
                db_statuses.append(s)

    from_dt: datetime | None = None
    requested_from_dt: datetime | None = None
    requested_to_dt: datetime | None = None
    if date_from or date_to:
        if date_from:
            requested_from_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        if date_to:
            requested_to_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
    elif from_days > 0:
        now = datetime.now(timezone.utc)
        from_dt = now - timedelta(days=from_days)

    stage_filter: list[str] | None = None
    if stage_codes:
        stage_filter = [s.strip() for s in stage_codes.split(",") if s.strip()]

    items_raw, total = await list_handoffs_with_candidates(
        db,
        client_company_id=cid,
        client_tenant_id=tid,
        statuses=db_statuses or None,
        from_dt=from_dt,
        requested_from_dt=requested_from_dt,
        requested_to_dt=requested_to_dt,
        candidate_stage_codes=stage_filter,
        q=q,
        order_by=order_by or "requested_at",
        desc=desc,
        limit=limit,
        offset=offset,
    )

    items: List[PendingHandoffWithCandidateOut] = []
    for item in items_raw:
        handoff = item.get("handoff")
        candidate = item.get("candidate") or {}
        items.append(
            PendingHandoffWithCandidateOut(
                handoff=HandoffOut.model_validate(handoff),
                candidate=candidate,
            )
        )

    return HandoffWithCandidatesListOut(total=total, items=items)


@router.post("/{handoff_id}/accept", response_model=HandoffOut)
async def accept_handoff_route(
    handoff_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Accept handoff (Przyjmij)."""
    from backend.app.models import CandidateHandoff

    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    handoff = await db.get(CandidateHandoff, str(handoff_id))
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    handoff, err = await accept_handoff(
        db,
        handoff_id=str(handoff_id),
        reviewed_by_user_id=current_user.sub,
        tenant_id=str(tenant_id),
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.commit()
    await db.refresh(handoff)
    return HandoffOut.model_validate(handoff)


@router.post("/{handoff_id}/reject", response_model=HandoffOut)
async def reject_handoff_route(
    handoff_id: UUID,
    payload: HandoffReject,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Reject handoff (Odrzuć)."""
    from backend.app.models import CandidateHandoff

    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    handoff = await db.get(CandidateHandoff, str(handoff_id))
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    handoff, err = await reject_handoff(
        db,
        handoff_id=str(handoff_id),
        reviewed_by_user_id=current_user.sub,
        rejection_reason=payload.rejection_reason,
        tenant_id=str(tenant_id),
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.commit()
    await db.refresh(handoff)
    return HandoffOut.model_validate(handoff)


@router.patch("/{handoff_id}/processor", response_model=HandoffOut)
async def change_processor_route(
    handoff_id: UUID,
    payload: HandoffChangeProcessor,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Change processor for accepted handoff."""
    from backend.app.models import CandidateHandoff

    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    handoff = await db.get(CandidateHandoff, str(handoff_id))
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    handoff, err = await change_processor(
        db,
        handoff_id=str(handoff_id),
        new_processor_user_id=payload.processor_user_id,
        actor_id=current_user.sub,
        tenant_id=str(tenant_id),
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.commit()
    await db.refresh(handoff)
    return HandoffOut.model_validate(handoff)


@router.post("/{handoff_id}/return", response_model=HandoffOut)
async def return_handoff_route(
    handoff_id: UUID,
    payload: HandoffReturn,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Return handoff to agency (Zwróć do agencji)."""
    from backend.app.models import CandidateHandoff

    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    handoff = await db.get(CandidateHandoff, str(handoff_id))
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    handoff, err = await return_handoff(
        db,
        handoff_id=str(handoff_id),
        reviewed_by_user_id=current_user.sub,
        return_reason=payload.return_reason,
        tenant_id=str(tenant_id),
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.commit()
    await db.refresh(handoff)
    return HandoffOut.model_validate(handoff)


@router.get("/candidates/{candidate_id}/handoff-status")
async def get_handoff_status(
    candidate_id: UUID,
    client_company_id: Optional[UUID] = Query(None),
    client_tenant_id: Optional[UUID] = Query(None),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Get handoff status for candidate (for UI). client_owns=True when current user's tenant can accept/reject."""
    from backend.app.models import Candidate

    db, tenant_id = db_tenant
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    cand = await db.get(Candidate, str(candidate_id))
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    from backend.app.models.tenant import TenantLink
    from sqlalchemy import select

    str_tenant_id = str(tenant_id)
    pending = None
    accepted = None
    client_owns = False

    if cand.tenant_id == str_tenant_id:
        pending = await get_pending_handoff_for_agency(db, str(candidate_id), str_tenant_id)
        accepted = await get_accepted_handoff_for_agency(db, str(candidate_id), str_tenant_id)
    if pending is None and accepted is None:
        tid = str(client_tenant_id) if client_tenant_id is not None else str_tenant_id
        cid = str(client_company_id) if client_company_id is not None else (str(cand.company_id) if cand.company_id else None)
        include_company_id: str | None = None
        if tid:
            row = await db.execute(
                select(TenantLink.handoff_include_company_id).where(
                    TenantLink.client_tenant_id == tid,
                    TenantLink.handoff_include_company_id.isnot(None),
                ).limit(1)
            )
            inc = row.scalar_one_or_none()
            include_company_id = str(inc) if inc else None
        if tid:
            pending = await get_pending_handoff(db, str(candidate_id), client_tenant_id=tid)
            accepted = await get_accepted_handoff(db, str(candidate_id), client_tenant_id=tid)
        if pending is None and accepted is None and include_company_id:
            pending = await get_pending_handoff(db, str(candidate_id), client_company_id=include_company_id)
            accepted = await get_accepted_handoff(db, str(candidate_id), client_company_id=include_company_id)
        if pending is None and accepted is None and cid:
            pending = await get_pending_handoff(db, str(candidate_id), client_company_id=cid)
            accepted = await get_accepted_handoff(db, str(candidate_id), client_company_id=cid)
        client_owns = pending is not None or accepted is not None

    async def handoff_with_names(h):
        if h is None:
            return None
        from backend.app.models import User
        req_user = await db.get(User, h.requested_by_user_id)
        ass_user = await db.get(User, h.assigned_to_user_id) if h.assigned_to_user_id else None
        def name(u):
            return (getattr(u, "full_name", None) or getattr(u, "short_id", None) or getattr(u, "email", None) or getattr(u, "id", None)) if u else None
        return HandoffOut(
            id=h.id, candidate_id=h.candidate_id, agency_tenant_id=h.agency_tenant_id,
            client_company_id=getattr(h, "client_company_id", None), client_tenant_id=getattr(h, "client_tenant_id", None),
            requested_by_user_id=h.requested_by_user_id, requested_at=h.requested_at,
            assigned_to_user_id=h.assigned_to_user_id, status=h.status,
            reviewed_by_user_id=getattr(h, "reviewed_by_user_id", None), reviewed_at=getattr(h, "reviewed_at", None),
            rejection_reason=getattr(h, "rejection_reason", None), return_reason=getattr(h, "return_reason", None),
            requested_by_user_name=name(req_user), assigned_to_user_name=name(ass_user),
        )

    return {
        "pending": await handoff_with_names(pending),
        "accepted": await handoff_with_names(accepted),
        "client_owns": client_owns,
    }
