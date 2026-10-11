"""ESO-5: Employment physical start (Employment-owned).

Employee created ≠ Started. Formalize complete ≠ Started.
Confirm first day at work (date + context); audit once; idempotent replay.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.reference.employment_formalize import evaluate_employment_formalize_v1
from backend.app.reference.employment_started import (
    AUDIT_EVENT_PHYSICAL_START,
    DECISION_STARTED,
    PHYSICAL_START_META_KEY,
    POLICY_ID,
    apply_employment_started_v1,
)
from backend.app.services.audit import log_audit_event
from backend.app.services.employment_accept_orchestrator import (
    read_employment_spine,
    resolve_ready_for_employment_package,
    write_employment_spine,
)
from backend.app.services import workforce_employees as we_svc


class EmploymentStartedError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prior_from_employee_meta(meta: Mapping[str, Any] | None) -> dict[str, Any]:
    return _record(_record(meta).get(PHYSICAL_START_META_KEY))


async def confirm_employment_started_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    actor_id: str | None,
    package: Mapping[str, Any] | None = None,
    employment_context: Mapping[str, Any] | None = None,
    start_confirmation: Mapping[str, Any] | bool | str | None = None,
    known_start_date: str | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    require_confirm_when_not_started: bool = False,
    ensure_employee: bool = False,
) -> dict[str, Any]:
    """Employment-owned physical start. Does not auto-start from Employee or formalize."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EmploymentStartedError("handoff_not_found", "Handoff not found")

    agency = str(getattr(handoff, "agency_tenant_id", "") or "")
    client = str(getattr(handoff, "client_tenant_id", "") or "")
    if str(tenant_id) not in {agency, client} and agency != str(tenant_id):
        raise EmploymentStartedError("handoff_tenant_mismatch", "Handoff does not belong to tenant")

    resolved = await resolve_ready_for_employment_package(db, handoff=handoff, package=package)

    ctx: dict[str, Any] = dict(employment_context or {})
    if isinstance(resolved, Mapping):
        target = resolved.get("target_work")
        if isinstance(target, Mapping):
            if not _text(ctx.get("employer_id")) and target.get("employer_id"):
                ctx.setdefault("employer_id", target.get("employer_id"))
            if not _text(ctx.get("vacancy_id")) and target.get("vacancy_id"):
                ctx.setdefault("vacancy_id", target.get("vacancy_id"))
            if not _text(ctx.get("employment_country")) and (
                target.get("employment_country") or target.get("country")
            ):
                ctx.setdefault(
                    "employment_country",
                    target.get("employment_country") or target.get("country"),
                )

    candidate_id = _text(getattr(handoff, "candidate_id", None))
    employee = None
    if candidate_id:
        employee = await we_svc.find_employee_by_candidate(db, str(tenant_id), candidate_id)
        if employee is None and agency and agency != str(tenant_id):
            employee = await we_svc.find_employee_by_candidate(db, agency, candidate_id)

    prior = _prior_from_employee_meta(getattr(employee, "meta", None) if employee is not None else None)
    known = _text(known_start_date) or None
    if not known and employee is not None and getattr(employee, "hire_date", None) is not None:
        known = str(employee.hire_date)

    formalize = evaluate_employment_formalize_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_context=ctx,
        confirmed_actions=read_employment_spine(handoff).get("confirmed_actions"),
        employment_missing=employment_missing,
    )

    result = apply_employment_started_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_context=ctx,
        employee_id=_text(getattr(employee, "id", None)) or None,
        ready_to_create_employee=bool(formalize.get("ready_to_create_employee")),
        known_start_date=known,
        prior_start=prior,
        start_confirmation=start_confirmation,
        employment_missing=employment_missing,
        require_confirm_when_not_started=require_confirm_when_not_started,
    )

    mint = bool(result.get("mint_employee")) and (
        result.get("decision") == DECISION_STARTED or ensure_employee
    )
    if mint and employee is None and candidate_id:
        cand = await db.get(Candidate, candidate_id)
        if cand is None:
            raise EmploymentStartedError("candidate_not_found", "Candidate not found for Employee mint")
        actor = _text(actor_id) or _text(getattr(handoff, "requested_by_user_id", None)) or "system"
        employee = await we_svc.handoff_from_candidate(
            db,
            str(tenant_id),
            cand,
            hire_date=None,
            actor_user_id=actor,
        )
        md = dict(employee.meta or {})
        md["internal_hr_handoff_id"] = str(handoff.id)
        employee.meta = md
        await db.flush()
        result["employee_id"] = str(employee.id)
        result["employee_created"] = True
        if result.get("decision") != DECISION_STARTED:
            result["started"] = False
            result["start_event_emitted"] = False

    if employee is not None:
        result["employee_id"] = str(employee.id)
        result["employee_created"] = True

    if result.get("decision") == DECISION_STARTED and employee is not None:
        record = _record((_record(result.get("start_record"))).get(PHYSICAL_START_META_KEY))
        md = dict(employee.meta or {})
        md[PHYSICAL_START_META_KEY] = {
            **record,
            "event_id": AUDIT_EVENT_PHYSICAL_START,
            "confirmed_at": _now_iso(),
            "handoff_id": str(handoff.id),
            "actor_id": _text(actor_id) or None,
        }
        employee.meta = md
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=str(tenant_id),
            event_type=AuditEventType.employee_physical_start,
            entity_type=AuditEntityType.handoff,
            entity_id=str(handoff.id),
            actor_id=_text(actor_id) or None,
            payload={
                "message": "Employee physical start confirmed",
                "handoff_id": str(handoff.id),
                "candidate_id": candidate_id or None,
                "employee_id": str(employee.id),
                "start_date": result.get("start_date"),
                "employment_context": result.get("employment_context"),
                "policy_id": POLICY_ID,
                "event": AUDIT_EVENT_PHYSICAL_START,
            },
        )
        result["start_event_emitted"] = True
        result["started"] = True
        result["spine"] = "employee_to_started"
    else:
        result["start_event_emitted"] = bool(result.get("start_event_emitted")) and (
            result.get("decision") == DECISION_STARTED
        )

    if result.get("started") or result.get("decision") in {DECISION_STARTED, "already_started"}:
        write_employment_spine(
            handoff,
            {
                "next_action": "started",
                "started": True,
                "ready_to_create_employee": True,
                "start_date": result.get("start_date"),
                "employment_context": result.get("employment_context"),
            },
        )
    elif result.get("ready_to_create_employee"):
        write_employment_spine(
            handoff,
            {
                "next_action": "confirm_physical_start",
                "ready_to_create_employee": True,
                "started": False,
            },
        )

    result["policy_id"] = POLICY_ID
    result["handoff_id"] = str(handoff.id)
    result["hr_employee_card"] = False
    return result


__all__ = [
    "EmploymentStartedError",
    "confirm_employment_started_for_handoff",
]
