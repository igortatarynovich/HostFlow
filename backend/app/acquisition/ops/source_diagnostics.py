"""Source Diagnostics — Marketing ops read compose over Lead + Activity.

PR1: tenant-scoped recent Acquisition-stamped leads + case detail.
PR2: list filters — source / flight_id / failed_only.
PR3: duplicate decision surface (decision_result_v1 + duplicate_match_v1).
No parallel submissions store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.candidate_activity import (
    read_acquisition_routing_stamp,
    resolve_unique_submission_id,
)
from backend.app.acquisition.ops.live_intake_monitor import (
    LiveIntakeApplicantRow,
    _applicant_from_lead,
)
from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent
from backend.app.models.lead import Lead

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@dataclass(frozen=True)
class DiagnosticsDuplicateDecision:
    """Read-only compose of duplicate signals already on Lead (no new SoT)."""

    active: bool
    lead_status: str
    disposition: Optional[str]
    match_level: Optional[str]
    suggested_candidate_id: Optional[str]
    attach_candidate_id: Optional[str]
    reasons: tuple[str, ...]
    hr_blockers: tuple[str, ...]
    error_code: Optional[str]
    needs_duplicate_review: bool
    stamped_at: Optional[str]


@dataclass(frozen=True)
class DiagnosticsCaseDetail:
    applicant: LiveIntakeApplicantRow
    submission_id: Optional[str]
    campaign_id: Optional[str]
    flight_id: Optional[str]
    routing: dict[str, Any]
    decision: dict[str, Any]
    payload: dict[str, Any]
    normalized: dict[str, Any]
    timeline: list[AcquisitionActivityEvent]
    lead_error: Optional[str]
    duplicate: DiagnosticsDuplicateDecision


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _str_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(x).strip() for x in value if str(x or "").strip())


def compose_duplicate_decision(
    *,
    lead_status: str,
    decision: Mapping[str, Any],
    normalized: Mapping[str, Any],
) -> DiagnosticsDuplicateDecision:
    """Explain duplicate outcome from decision_result_v1 + duplicate_match_v1."""
    status = str(lead_status or "").strip()
    disposition = str(decision.get("disposition") or "").strip() or None
    decision_dm = decision.get("duplicate_match")
    decision_dm = decision_dm if isinstance(decision_dm, Mapping) else {}
    stamp = normalized.get("duplicate_match_v1")
    stamp = stamp if isinstance(stamp, Mapping) else {}

    match_level = (
        str(stamp.get("level") or decision_dm.get("level") or "").strip() or None
    )
    suggested = (
        str(stamp.get("suggested_candidate_id") or "").strip()
        or str(decision_dm.get("candidate_id") or "").strip()
        or None
    )
    attach = str(decision.get("attach_candidate_id") or "").strip() or None
    reasons = _str_list(stamp.get("reasons")) or _str_list(decision_dm.get("reasons"))
    hr_blockers = _str_list(stamp.get("hr_blockers")) or _str_list(
        decision_dm.get("hr_blockers")
    )
    error_code = str(stamp.get("error_code") or "").strip() or None
    needs_review = bool(decision_dm.get("needs_duplicate_review")) or status in {
        "duplicate_review",
        "duplicated",
    }
    stamped_at = str(stamp.get("stamped_at") or "").strip() or None
    active = bool(
        status in {"duplicate_review", "duplicated"}
        or disposition == "blocked_duplicate"
        or needs_review
        or match_level not in (None, "", "none")
        or suggested
        or error_code
        or reasons
        or hr_blockers
    )
    return DiagnosticsDuplicateDecision(
        active=active,
        lead_status=status,
        disposition=disposition,
        match_level=match_level,
        suggested_candidate_id=suggested,
        attach_candidate_id=attach,
        reasons=reasons,
        hr_blockers=hr_blockers,
        error_code=error_code,
        needs_duplicate_review=needs_review,
        stamped_at=stamped_at,
    )


def _acquisition_stamped_filter(*, tenant_id: str):
    """Leads that carry Acquisition routing stamp (ops casework set)."""
    routing = Lead.normalized[ACQUISITION_ROUTING_V1_KEY]
    return and_(
        Lead.tenant_id == str(tenant_id),
        routing.isnot(None),
    )


def _list_filters(
    *,
    source: str | None,
    flight_id: str | None,
    failed_only: bool,
):
    """Optional list narrowing — still within stamped Acquisition set."""
    clauses = []
    src = str(source or "").strip()
    if src:
        clauses.append(Lead.source == src)
    fid = str(flight_id or "").strip()
    if fid:
        routing = Lead.normalized[ACQUISITION_ROUTING_V1_KEY]
        clauses.append(routing["campaign_run_id"].as_string() == fid)
    if failed_only:
        routing = Lead.normalized[ACQUISITION_ROUTING_V1_KEY]
        clauses.append(
            or_(
                Lead.status == "failed",
                routing["status"].as_string() == "unresolved",
                and_(Lead.error.isnot(None), Lead.error != ""),
            )
        )
    return and_(*clauses) if clauses else None


async def list_diagnostic_submissions(
    db: AsyncSession,
    *,
    tenant_id: str,
    limit: int = _DEFAULT_LIMIT,
    after_created_at: datetime | None = None,
    after_id: str | None = None,
    source: str | None = None,
    flight_id: str | None = None,
    failed_only: bool = False,
) -> tuple[list[LiveIntakeApplicantRow], tuple[datetime, str] | None]:
    if (after_created_at is None) ^ (after_id is None):
        raise ValueError("after_created_at and after_id must be provided together")
    lim = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
    stmt = (
        select(Lead)
        .where(_acquisition_stamped_filter(tenant_id=tenant_id))
        .order_by(Lead.created_at.desc(), Lead.id.desc())
    )
    extra = _list_filters(source=source, flight_id=flight_id, failed_only=failed_only)
    if extra is not None:
        stmt = stmt.where(extra)
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


async def get_diagnostic_case(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> DiagnosticsCaseDetail | None:
    lead = (
        await db.execute(
            select(Lead).where(
                Lead.tenant_id == str(tenant_id),
                Lead.id == str(lead_id),
            )
        )
    ).scalar_one_or_none()
    if lead is None:
        return None

    routing = read_acquisition_routing_stamp(lead)
    normalized = _as_dict(lead.normalized)
    decision = _as_dict(normalized.get("decision_result_v1"))
    submission_id = resolve_unique_submission_id(lead)
    campaign_id = str(routing.get("campaign_id") or "").strip() or None
    flight_id = str(routing.get("campaign_run_id") or "").strip() or None

    timeline: list[AcquisitionActivityEvent] = []
    if submission_id:
        timeline = await list_activity_events(
            db,
            tenant_id=str(tenant_id),
            submission_id=str(submission_id),
            limit=_MAX_LIMIT,
        )

    payload = _as_dict(getattr(lead, "payload", None))
    lead_status = str(getattr(lead, "status", None) or "")
    return DiagnosticsCaseDetail(
        applicant=_applicant_from_lead(lead),
        submission_id=submission_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        routing=routing,
        decision=decision,
        payload=payload,
        normalized=normalized,
        timeline=timeline,
        lead_error=str(getattr(lead, "error", None) or "").strip() or None,
        duplicate=compose_duplicate_decision(
            lead_status=lead_status,
            decision=decision,
            normalized=normalized,
        ),
    )


__all__ = [
    "DiagnosticsCaseDetail",
    "DiagnosticsDuplicateDecision",
    "compose_duplicate_decision",
    "get_diagnostic_case",
    "list_diagnostic_submissions",
]
