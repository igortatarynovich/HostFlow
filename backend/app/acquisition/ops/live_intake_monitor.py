"""Stage 4 PR-3 — Live Intake Monitor: Activity counters + person-facing applicants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from sqlalchemy import and_, func, or_, select
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
from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent
from backend.app.models.lead import Lead

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
class LiveIntakeApplicantRow:
    """Person-facing row for Marketing Live Intake (not raw Activity)."""

    lead_id: str
    created_at: datetime | None
    full_name: str | None
    phone: str | None
    email: str | None
    lead_status: str
    disposition: str | None
    status_label: str
    candidate_id: str | None
    vacancy_id: str | None
    route_intent: str | None
    routing_status: str | None
    source: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "lead_status": self.lead_status,
            "disposition": self.disposition,
            "status_label": self.status_label,
            "candidate_id": self.candidate_id,
            "vacancy_id": self.vacancy_id,
            "route_intent": self.route_intent,
            "routing_status": self.routing_status,
            "source": self.source,
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
    applicants: list[LiveIntakeApplicantRow]
    next_cursor: tuple[datetime, str] | None
    applicants_next_cursor: tuple[datetime, str] | None
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


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _person_name(normalized: Mapping[str, Any]) -> str | None:
    full = _clean_text(normalized.get("full_name"))
    if full:
        return full
    first = _clean_text(normalized.get("first_name"))
    last = _clean_text(normalized.get("last_name"))
    joined = " ".join(p for p in (first, last) if p)
    return joined or None


def _status_label(
    *,
    lead_status: str,
    disposition: str | None,
    routing_status: str | None,
    unresolved_reason: str | None,
    blocking_reasons: Sequence[str],
    candidate_id: str | None,
) -> str:
    if candidate_id:
        return "Кандидат"
    status = str(lead_status or "").strip().lower()
    if status == "duplicated":
        return "Дубликат"
    if status == "failed":
        return "Ошибка"
    if status == "processed":
        return "Обработана"
    if unresolved_reason == "missing_campaign_flight":
        return "Нет маршрута на Flight"
    if "auto_convert_gated" in blocking_reasons:
        return "Ожидает конвертации"
    if "duplicate_review" in blocking_reasons or unresolved_reason == "DUPLICATE_REVIEW_PENDING":
        return "Проверка дубликата"
    if disposition == "needs_routing" or status == "needs_routing":
        return "Нужна обработка"
    if routing_status == "routed":
        return "Направлена"
    if routing_status == "unresolved":
        return "Не направлена"
    return status.replace("_", " ").capitalize() if status else "Заявка"


def _applicant_from_lead(lead: Lead) -> LiveIntakeApplicantRow:
    normalized = _as_dict(lead.normalized)
    routing = _as_dict(normalized.get(ACQUISITION_ROUTING_V1_KEY))
    decision = _as_dict(normalized.get("decision_result_v1"))
    blocking = decision.get("blocking_reasons") or []
    if not isinstance(blocking, list):
        blocking = []
    blocking_reasons = [str(x) for x in blocking if str(x or "").strip()]
    candidate_id = _clean_text(getattr(lead, "candidate_id", None))
    disposition = _clean_text(decision.get("disposition"))
    routing_status = _clean_text(routing.get("status"))
    unresolved = _clean_text(routing.get("unresolved_reason")) or _clean_text(
        getattr(lead, "error", None)
    )
    return LiveIntakeApplicantRow(
        lead_id=str(lead.id),
        created_at=getattr(lead, "created_at", None),
        full_name=_person_name(normalized),
        phone=_clean_text(normalized.get("phone")),
        email=_clean_text(normalized.get("email")),
        lead_status=str(lead.status or ""),
        disposition=disposition,
        status_label=_status_label(
            lead_status=str(lead.status or ""),
            disposition=disposition,
            routing_status=routing_status,
            unresolved_reason=unresolved,
            blocking_reasons=blocking_reasons,
            candidate_id=candidate_id,
        ),
        candidate_id=candidate_id,
        vacancy_id=_clean_text(getattr(lead, "vacancy_id", None))
        or _clean_text(normalized.get("vacancy_id")),
        route_intent=_clean_text(routing.get("route_intent")),
        routing_status=routing_status,
        source=_clean_text(getattr(lead, "source", None)),
    )


def _flight_attributed_lead_filter(*, tenant_id: str, flight_id: str):
    """Leads stamped to this Flight via acquisition_routing_v1.campaign_run_id."""
    routing = Lead.normalized[ACQUISITION_ROUTING_V1_KEY]
    return and_(
        Lead.tenant_id == str(tenant_id),
        routing["campaign_run_id"].as_string() == str(flight_id),
    )


async def list_flight_applicants(
    db: AsyncSession,
    *,
    tenant_id: str,
    flight_id: str,
    limit: int = _DEFAULT_LIMIT,
    after_created_at: datetime | None = None,
    after_id: str | None = None,
) -> tuple[list[LiveIntakeApplicantRow], tuple[datetime, str] | None]:
    """Recent person-facing applicants attributed to a Flight."""
    if (after_created_at is None) ^ (after_id is None):
        raise FlightRuntimeError(
            "after_created_at and after_id must be provided together",
            status_code=422,
        )
    lim = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
    stmt = (
        select(Lead)
        .where(_flight_attributed_lead_filter(tenant_id=tenant_id, flight_id=flight_id))
        .order_by(Lead.created_at.desc(), Lead.id.desc())
    )
    if after_created_at is not None and after_id is not None:
        stmt = stmt.where(
            or_(
                Lead.created_at < after_created_at,
                and_(Lead.created_at == after_created_at, Lead.id < str(after_id)),
            )
        )
    stmt = stmt.limit(lim + 1)
    leads = list((await db.execute(stmt)).scalars().all())
    has_more = len(leads) > lim
    page = leads[:lim]
    next_cursor: tuple[datetime, str] | None = None
    if has_more and page:
        last = page[-1]
        created = getattr(last, "created_at", None)
        if created is not None:
            next_cursor = (created, str(last.id))
    return [_applicant_from_lead(lead) for lead in page], next_cursor


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
    applicants_after_created_at: datetime | None = None,
    applicants_after_id: str | None = None,
) -> LiveIntakeMonitorPage:
    """Flight-scoped Live Intake: person applicants + Activity projection + KPI."""
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

    applicants, applicants_next = await list_flight_applicants(
        db,
        tenant_id=str(tenant_id),
        flight_id=str(flight.id),
        limit=lim,
        after_created_at=applicants_after_created_at,
        after_id=applicants_after_id,
    )

    return LiveIntakeMonitorPage(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign.id),
        flight_id=str(flight.id),
        campaign_status=str(campaign.status or ""),
        flight_status=str(flight.status or ""),
        counters=_counters_from(counts, kpi),
        items=page,
        applicants=applicants,
        next_cursor=next_cursor,
        applicants_next_cursor=applicants_next,
        order=ACTIVITY_LIST_ORDER,
        event_types=tuple(filter_types),
    )


__all__ = [
    "LIVE_INTAKE_EVENT_TYPES",
    "LiveIntakeApplicantRow",
    "LiveIntakeCounters",
    "LiveIntakeMonitorPage",
    "get_live_intake_monitor",
    "list_flight_applicants",
]
