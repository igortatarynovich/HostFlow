"""Stage 4 PR-3 — Live Intake Monitor projection over Activity Timeline + KPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity import ACTIVITY_LIST_ORDER, list_activity_events
from backend.app.acquisition.flights.runtime_commands import (
    FlightRuntimeError,
    get_flight,
)
from backend.app.acquisition.kpi_aggregates import (
    FlightKpiAggregate,
    KpiAggregateError,
    aggregate_flight_kpi,
)
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent

# Ops feed allowlist — Timeline remains SoT; this is a convenience filter.
LIVE_INTAKE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "SubmissionReceived",
        "SubmissionNormalized",
        "SubmissionRejected",
        "RoutingCompleted",
        "RoutingFailed",
        "ResultAttributed",
        "LeadCreated",
        "CandidateCreated",
        "DuplicateDetected",
        "DeliveryErrorOccurred",
        "ProviderSubmissionAccepted",
        "ProviderSubmissionRejected",
    }
)

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@dataclass(frozen=True)
class LiveIntakeCounters:
    submissions: int
    leads_activity: int
    candidates: int
    routing_completed: int
    routing_failed: int
    rejected: int
    # KPI strip (3D) — distinct from activity lead counts
    kpi_leads: int
    spend: str
    cost_per_lead: str | None
    currency: str | None

    def to_dict(self) -> dict:
        return {
            "submissions": self.submissions,
            "leads_activity": self.leads_activity,
            "candidates": self.candidates,
            "routing_completed": self.routing_completed,
            "routing_failed": self.routing_failed,
            "rejected": self.rejected,
            "kpi_leads": self.kpi_leads,
            "spend": self.spend,
            "cost_per_lead": self.cost_per_lead,
            "currency": self.currency,
        }


@dataclass(frozen=True)
class LiveIntakeMonitorPage:
    tenant_id: str
    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    counters: LiveIntakeCounters
    items: list[AcquisitionActivityEvent]
    next_cursor: tuple[datetime, str] | None
    order: tuple[str, str]
    event_types: tuple[str, ...]


async def _count_by_type(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
) -> dict[str, int]:
    stmt = (
        select(AcquisitionActivityEvent.event_type, func.count())
        .where(
            AcquisitionActivityEvent.tenant_id == str(tenant_id),
            AcquisitionActivityEvent.campaign_id == str(campaign_id),
            AcquisitionActivityEvent.flight_id == str(flight_id),
            AcquisitionActivityEvent.event_type.in_(sorted(LIVE_INTAKE_EVENT_TYPES)),
        )
        .group_by(AcquisitionActivityEvent.event_type)
    )
    rows = await db.execute(stmt)
    return {str(et): int(n) for et, n in rows.all()}


def _counters_from(
    counts: dict[str, int], kpi: FlightKpiAggregate
) -> LiveIntakeCounters:
    return LiveIntakeCounters(
        submissions=counts.get("SubmissionReceived", 0),
        leads_activity=counts.get("LeadCreated", 0),
        candidates=counts.get("CandidateCreated", 0),
        routing_completed=counts.get("RoutingCompleted", 0),
        routing_failed=counts.get("RoutingFailed", 0),
        rejected=counts.get("SubmissionRejected", 0),
        kpi_leads=int(kpi.leads),
        spend=str(kpi.spend),
        cost_per_lead=None if kpi.cost_per_lead is None else str(kpi.cost_per_lead),
        currency=kpi.currency,
    )


async def get_live_intake_monitor(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    own_company_id: str | None = None,
    occurred_after: datetime | None = None,
    after_occurred_at: datetime | None = None,
    after_id: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    event_types: Sequence[str] | None = None,
) -> LiveIntakeMonitorPage:
    """Flight-scoped Live Intake Monitor page (Activity projection + counters + KPI)."""
    if (after_occurred_at is None) ^ (after_id is None):
        raise FlightRuntimeError(
            "after_occurred_at and after_id must be provided together",
            status_code=422,
        )
    lim = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))

    try:
        campaign, flight = await get_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
        )
    except FlightRuntimeError:
        raise

    allowlist = sorted(LIVE_INTAKE_EVENT_TYPES)
    if event_types:
        requested = [str(t).strip() for t in event_types if str(t).strip()]
        unknown = [t for t in requested if t not in LIVE_INTAKE_EVENT_TYPES]
        if unknown:
            raise FlightRuntimeError(
                f"event_types not allowed on live intake monitor: {unknown}",
                status_code=422,
            )
        filter_types = requested
    else:
        filter_types = allowlist

    try:
        kpi = await aggregate_flight_kpi(
            db, tenant_id=str(tenant_id), flight_id=str(flight.id)
        )
    except KpiAggregateError as exc:
        raise FlightRuntimeError(str(exc), status_code=422) from exc

    counts = await _count_by_type(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign.id),
        flight_id=str(flight.id),
    )
    # Fetch limit+1 for next_cursor detection (same pattern as 3E read API).
    rows = await list_activity_events(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign.id),
        flight_id=str(flight.id),
        event_types=filter_types,
        occurred_after=occurred_after,
        after_occurred_at=after_occurred_at,
        after_id=after_id,
        limit=lim + 1,
    )
    has_more = len(rows) > lim
    page = rows[:lim]
    next_cursor: tuple[datetime, str] | None = None
    if has_more and page:
        last = page[-1]
        next_cursor = (last.occurred_at, str(last.id))

    return LiveIntakeMonitorPage(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign.id),
        flight_id=str(flight.id),
        campaign_status=str(campaign.status or ""),
        flight_status=str(flight.status or ""),
        counters=_counters_from(counts, kpi),
        items=page,
        next_cursor=next_cursor,
        order=ACTIVITY_LIST_ORDER,
        event_types=tuple(filter_types),
    )


__all__ = [
    "LIVE_INTAKE_EVENT_TYPES",
    "LiveIntakeCounters",
    "LiveIntakeMonitorPage",
    "get_live_intake_monitor",
]
