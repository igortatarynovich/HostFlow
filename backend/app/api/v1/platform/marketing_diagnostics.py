"""Marketing Source Diagnostics API — list + case detail (+ PR2 filters)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.ops.source_diagnostics import (
    get_diagnostic_case,
    list_diagnostic_submissions,
)
from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant

router = APIRouter(
    prefix="/platform/marketing/diagnostics",
    tags=["marketing-diagnostics"],
    redirect_slashes=False,
)

_READ = [
    Depends(
        require_roles(
            Role.administrator,
            Role.supervisor,
            Role.recruiter,
            Role.client_manager,
            Role.viewer,
            Role.hr_officer,
            Role.superadmin,
        )
    )
]

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


class DiagnosticsCursorOut(BaseModel):
    created_at: datetime
    id: str


class DiagnosticsSubmissionOut(BaseModel):
    lead_id: str
    created_at: Optional[datetime] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    lead_status: str = ""
    disposition: Optional[str] = None
    status_label: str = ""
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    route_intent: Optional[str] = None
    routing_status: Optional[str] = None
    source: Optional[str] = None


class DiagnosticsListOut(BaseModel):
    items: list[DiagnosticsSubmissionOut]
    next_cursor: Optional[DiagnosticsCursorOut] = None


class DiagnosticsTimelineEventOut(BaseModel):
    id: str
    event_type: str
    occurred_at: datetime
    campaign_id: str
    flight_id: Optional[str] = None
    submission_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsCaseOut(BaseModel):
    lead_id: str
    created_at: Optional[datetime] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    lead_status: str = ""
    disposition: Optional[str] = None
    status_label: str = ""
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    route_intent: Optional[str] = None
    routing_status: Optional[str] = None
    source: Optional[str] = None
    submission_id: Optional[str] = None
    campaign_id: Optional[str] = None
    flight_id: Optional[str] = None
    routing: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    normalized: dict[str, Any] = Field(default_factory=dict)
    lead_error: Optional[str] = None
    timeline: list[DiagnosticsTimelineEventOut] = Field(default_factory=list)


def _require_uuid(value: str, *, field: str) -> str:
    raw = str(value or "").strip()
    try:
        return str(UUID(raw))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid {field}") from exc


@router.get("/submissions", response_model=DiagnosticsListOut, dependencies=_READ)
async def list_submissions(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    after_created_at: Optional[datetime] = Query(default=None),
    after_id: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None, max_length=64),
    flight_id: Optional[str] = Query(default=None),
    failed_only: bool = Query(default=False),
) -> DiagnosticsListOut:
    db, tenant_id = db_tenant
    cursor_id = _require_uuid(after_id, field="after_id") if after_id is not None else None
    flight = (
        _require_uuid(flight_id, field="flight_id") if flight_id is not None and str(flight_id).strip() else None
    )
    try:
        rows, cursor = await list_diagnostic_submissions(
            db,
            tenant_id=str(tenant_id),
            limit=limit,
            after_created_at=after_created_at,
            after_id=cursor_id,
            source=source,
            flight_id=flight,
            failed_only=bool(failed_only),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DiagnosticsListOut(
        items=[
            DiagnosticsSubmissionOut(
                lead_id=row.lead_id,
                created_at=row.created_at,
                full_name=row.full_name,
                phone=row.phone,
                email=row.email,
                lead_status=row.lead_status,
                disposition=row.disposition,
                status_label=row.status_label,
                candidate_id=row.candidate_id,
                vacancy_id=row.vacancy_id,
                route_intent=row.route_intent,
                routing_status=row.routing_status,
                source=row.source,
            )
            for row in rows
        ],
        next_cursor=(
            DiagnosticsCursorOut(created_at=cursor[0], id=cursor[1]) if cursor else None
        ),
    )


@router.get(
    "/submissions/{lead_id}",
    response_model=DiagnosticsCaseOut,
    dependencies=_READ,
)
async def get_submission_case(
    lead_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> DiagnosticsCaseOut:
    db, tenant_id = db_tenant
    lid = _require_uuid(lead_id, field="lead_id")
    detail = await get_diagnostic_case(db, tenant_id=str(tenant_id), lead_id=lid)
    if detail is None:
        raise HTTPException(status_code=404, detail="submission_not_found")
    app = detail.applicant
    return DiagnosticsCaseOut(
        lead_id=app.lead_id,
        created_at=app.created_at,
        full_name=app.full_name,
        phone=app.phone,
        email=app.email,
        lead_status=app.lead_status,
        disposition=app.disposition,
        status_label=app.status_label,
        candidate_id=app.candidate_id,
        vacancy_id=app.vacancy_id,
        route_intent=app.route_intent,
        routing_status=app.routing_status,
        source=app.source,
        submission_id=detail.submission_id,
        campaign_id=detail.campaign_id,
        flight_id=detail.flight_id,
        routing=detail.routing,
        decision=detail.decision,
        payload=detail.payload,
        normalized=detail.normalized,
        lead_error=detail.lead_error,
        timeline=[
            DiagnosticsTimelineEventOut(
                id=str(ev.id),
                event_type=str(ev.event_type),
                occurred_at=ev.occurred_at,
                campaign_id=str(ev.campaign_id),
                flight_id=str(ev.flight_id) if ev.flight_id else None,
                submission_id=str(ev.submission_id) if ev.submission_id else None,
                payload=dict(ev.payload or {}),
            )
            for ev in detail.timeline
        ],
    )
