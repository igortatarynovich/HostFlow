"""Acquisition Activity Timeline Read API — Stage 3E PR-3.

Read-only. All writes remain behind ``append_activity_event`` (PR-1/PR-2).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity import ACTIVITY_LIST_ORDER, list_activity_events
from backend.app.acquisition.activity.catalog import ACTIVITY_EVENT_TYPES
from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent

router = APIRouter(
    prefix="/platform/acquisition-activity",
    tags=["acquisition-activity"],
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

_TIME_AFTER_DESC = (
    "Exclusive lower bound on occurred_at (events with occurred_at > this value)."
)
_TIME_BEFORE_DESC = (
    "Exclusive upper bound on occurred_at (events with occurred_at < this value)."
)
_CURSOR_AT_DESC = (
    "Cursor: occurred_at of the last item from the previous page. "
    "Must be paired with after_id. Selects rows strictly after (occurred_at, id)."
)
_CURSOR_ID_DESC = (
    "Cursor: id of the last item from the previous page. Must be paired with after_occurred_at."
)


class ActivityEventOut(BaseModel):
    id: str
    tenant_id: str
    campaign_id: str
    flight_id: Optional[str] = None
    endpoint_id: Optional[str] = None
    submission_id: Optional[str] = None
    result_id: Optional[str] = None
    outcome_id: Optional[str] = None
    event_type: str
    event_version: str
    occurred_at: datetime
    recorded_at: datetime
    actor_type: str
    actor_id: Optional[str] = None
    provider: Optional[str] = None
    source_event_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ActivityCursorOut(BaseModel):
    """Cursor: last row's (occurred_at, id) for stable keyset pagination."""

    occurred_at: datetime
    id: str


class ActivityListOut(BaseModel):
    items: list[ActivityEventOut]
    next_cursor: Optional[ActivityCursorOut] = None
    order: tuple[str, str] = ACTIVITY_LIST_ORDER


def _require_uuid(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return str(UUID(raw))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{field} must be a valid UUID",
        ) from exc


def _to_out(row: AcquisitionActivityEvent) -> ActivityEventOut:
    return ActivityEventOut(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        campaign_id=str(row.campaign_id),
        flight_id=str(row.flight_id) if row.flight_id else None,
        endpoint_id=str(row.endpoint_id) if row.endpoint_id else None,
        submission_id=str(row.submission_id) if row.submission_id else None,
        result_id=str(row.result_id) if row.result_id else None,
        outcome_id=str(row.outcome_id) if row.outcome_id else None,
        event_type=str(row.event_type),
        event_version=str(row.event_version),
        occurred_at=row.occurred_at,
        recorded_at=row.recorded_at,
        actor_type=str(row.actor_type),
        actor_id=str(row.actor_id) if row.actor_id else None,
        provider=str(row.provider) if row.provider else None,
        source_event_id=str(row.source_event_id) if row.source_event_id else None,
        correlation_id=str(row.correlation_id) if row.correlation_id else None,
        causation_id=str(row.causation_id) if row.causation_id else None,
        payload=dict(row.payload or {}),
    )


@router.get("", response_model=ActivityListOut, dependencies=_READ)
async def list_acquisition_activity(
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
    campaign_id: Optional[str] = Query(default=None),
    flight_id: Optional[str] = Query(default=None),
    endpoint_id: Optional[str] = Query(
        default=None,
        description="Opaque endpoint id (e.g. form:{uuid} / intake_source:{uuid}).",
    ),
    submission_id: Optional[str] = Query(default=None),
    result_id: Optional[str] = Query(
        default=None,
        description="Opaque Result id (not necessarily a UUID).",
    ),
    outcome_id: Optional[str] = Query(default=None),
    event_type: Optional[list[str]] = Query(
        default=None,
        description="Filter by catalog event_type (repeatable). Unknown types → 422.",
    ),
    occurred_after: Optional[datetime] = Query(default=None, description=_TIME_AFTER_DESC),
    occurred_before: Optional[datetime] = Query(default=None, description=_TIME_BEFORE_DESC),
    after_occurred_at: Optional[datetime] = Query(default=None, description=_CURSOR_AT_DESC),
    after_id: Optional[str] = Query(default=None, description=_CURSOR_ID_DESC),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
) -> ActivityListOut:
    """Tenant-scoped Activity Timeline list with cursor pagination.

    Order is fixed to ``(occurred_at ASC, id ASC)``. Pass the last item's
    ``occurred_at`` + ``id`` as ``after_*`` for the next page (strictly greater).
    """
    db, tenant_id = db_tenant
    if (after_occurred_at is None) ^ (after_id is None or not str(after_id or "").strip()):
        raise HTTPException(
            status_code=422,
            detail="after_occurred_at and after_id must be provided together",
        )

    types: list[str] | None = None
    if event_type:
        types = [str(t).strip() for t in event_type if str(t).strip()]
        if not types:
            types = None
        else:
            unknown = sorted({t for t in types if t not in ACTIVITY_EVENT_TYPES})
            if unknown:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown event_type(s): {', '.join(unknown)}",
                )

    campaign_f = _require_uuid(campaign_id, field="campaign_id")
    flight_f = _require_uuid(flight_id, field="flight_id")
    submission_f = _require_uuid(submission_id, field="submission_id")
    outcome_f = _require_uuid(outcome_id, field="outcome_id")
    after_id_f = _require_uuid(after_id, field="after_id") if after_id else None
    endpoint_f = str(endpoint_id).strip() if endpoint_id and str(endpoint_id).strip() else None
    result_f = str(result_id).strip() if result_id and str(result_id).strip() else None

    # Fetch one extra row to decide whether a next cursor exists.
    fetch_limit = min(limit + 1, 500)
    try:
        rows = await list_activity_events(
            db,
            tenant_id=str(tenant_id),
            campaign_id=campaign_f,
            flight_id=flight_f,
            endpoint_id=endpoint_f,
            submission_id=submission_f,
            result_id=result_f,
            outcome_id=outcome_f,
            event_types=types,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            after_occurred_at=after_occurred_at,
            after_id=after_id_f,
            limit=fetch_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    page = rows[:limit]
    next_cursor: ActivityCursorOut | None = None
    if len(rows) > limit and page:
        last = page[-1]
        next_cursor = ActivityCursorOut(occurred_at=last.occurred_at, id=str(last.id))

    return ActivityListOut(
        items=[_to_out(r) for r in page],
        next_cursor=next_cursor,
        order=ACTIVITY_LIST_ORDER,
    )


__all__ = ["router"]
