"""Operator surface for one Employment.

Reads the existing owners into one screen. Confirmations and activation call
those owners. This module does not store a second driver card.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import (
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_NOT_APPLICABLE,
    RESOLUTION_BLOCKING,
    RESOLUTION_SATISFIED,
    RESOLUTION_UNRESOLVED,
    RESOLUTION_WAIVED,
    HrEmploymentRequirement,
)
from backend.app.models.hr_employment_terms import HrEmploymentTerms
from backend.app.models.hr_legal_eligibility_gate import HrLegalEligibilityGateDecision
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask
from backend.app.services.employment_terms_runtime import (
    TERMS_COMPLETE,
    EmploymentTermsConfirmation,
    confirm_employment_terms,
    evaluate_employment_terms,
)
from backend.app.services.hr_legal_eligibility_gate import (
    checkpoint_planned_start,
    decision_is_current,
    record_hr_legal_eligibility_gate,
)
from backend.app.services.ready_to_start_runtime import (
    activate_employment,
    latest_ready_to_start_decision,
    read_ready_to_start_inputs,
    ready_to_start_is_current,
    record_ready_to_start,
)

_PROFESSIONAL_ORDER = (
    "passport",
    "driving_licence",
    "code_95",
    "tachograph_card",
    "medical",
    "psychological",
    "occupational_medicine",
)
_KEY_ALIASES = {
    "driver_license": "driving_licence",
    "driver_licence": "driving_licence",
    "code95": "code_95",
    "driver_qualification_card": "code_95",
    "qualification_code95": "code_95",
    "tachograph": "tachograph_card",
    "psych": "psychological",
    "psychological_certificate": "psychological",
    "medycyna_pracy": "occupational_medicine",
    "occupational_health": "occupational_medicine",
}
_LABELS = {
    "passport": "Passport",
    "driving_licence": "Driving licence",
    "code_95": "Code 95",
    "tachograph_card": "Tachograph card",
    "medical": "Medical",
    "psychological": "Psychological",
    "occupational_medicine": "Occupational medicine",
}
_ZUS_CLOSED = frozenset({"done", "completed", "cancelled", "canceled"})


@dataclass(frozen=True)
class SurfaceFact:
    key: str
    label: str
    applicability: str
    resolution: str | None
    blocking_reason: str | None
    evidence_linked: bool


@dataclass(frozen=True)
class SurfaceCase:
    state: str
    terms_complete: bool
    work_yes: bool
    legal_pass: bool
    zus_open: bool
    ready_pass: bool
    facts: tuple[SurfaceFact, ...]
    live_ready: bool = False


def canonical_fact_key(definition_key: str) -> str:
    raw = str(definition_key or "").strip()
    return _KEY_ALIASES.get(raw, raw)


def fact_label(definition_key: str) -> str:
    key = canonical_fact_key(definition_key)
    return _LABELS.get(key, definition_key)


def _order_index(key: str) -> tuple[int, str]:
    canonical = canonical_fact_key(key)
    try:
        return (_PROFESSIONAL_ORDER.index(canonical), canonical)
    except ValueError:
        return (len(_PROFESSIONAL_ORDER), canonical)


def ordered_facts(facts: tuple[SurfaceFact, ...] | list[SurfaceFact]) -> tuple[SurfaceFact, ...]:
    return tuple(sorted(facts, key=lambda fact: _order_index(fact.key)))


def choose_next_action(case: SurfaceCase) -> dict[str, str] | None:
    """One action whose prerequisites hold. Display order is not this order."""

    if case.state != "preparing":
        return None
    facts = ordered_facts(case.facts)
    blocking = next(
        (
            fact
            for fact in facts
            if fact.applicability == APPLICABILITY_APPLICABLE and fact.resolution == RESOLUTION_BLOCKING
        ),
        None,
    )
    if blocking is not None:
        return {
            "code": "resolve_requirement",
            "focus": "professional",
            "fact_key": blocking.key,
            "title": f"Resolve {blocking.label}",
            "reason": blocking.blocking_reason or "A professional fact is blocking.",
        }
    if not case.work_yes and not case.terms_complete:
        return {
            "code": "confirm_terms",
            "focus": "terms",
            "fact_key": "",
            "title": "Confirm employment terms",
            "reason": "The work-authorization procedure needs the agreed terms.",
        }
    if not case.work_yes and case.terms_complete and case.zus_open:
        return {
            "code": "register_zus",
            "focus": "next",
            "fact_key": "",
            "title": "Register in ZUS",
            "reason": "Required for the current work-authorization procedure.",
        }
    if not case.work_yes and case.terms_complete:
        return {
            "code": "start_work_authorization",
            "focus": "work_eligibility",
            "fact_key": "",
            "title": "Start work authorization",
            "reason": "Stay can be known while the permit for this Employment is still open.",
        }
    unresolved = next(
        (
            fact
            for fact in facts
            if fact.applicability == APPLICABILITY_APPLICABLE and fact.resolution == RESOLUTION_UNRESOLVED
        ),
        None,
    )
    if unresolved is not None:
        return {
            "code": "confirm_fact",
            "focus": "professional",
            "fact_key": unresolved.key,
            "title": f"Confirm {unresolved.label}",
            "reason": "Confirm the fact. The document is the evidence beside it.",
        }
    if not case.terms_complete:
        return {
            "code": "confirm_terms",
            "focus": "terms",
            "fact_key": "",
            "title": "Confirm employment terms",
            "reason": "The agreed terms of this Employment are not confirmed.",
        }
    if not case.legal_pass:
        return {
            "code": "confirm_legal",
            "focus": "work_eligibility",
            "fact_key": "",
            "title": "Confirm legal eligibility",
            "reason": "The chain for this Employment is not a current pass.",
        }
    if case.ready_pass:
        return {
            "code": "start_employment",
            "focus": "ready",
            "fact_key": "",
            "title": "Start employment",
            "reason": "Ready to Start is a current pass.",
        }
    if case.live_ready:
        return {
            "code": "record_ready",
            "focus": "ready",
            "fact_key": "",
            "title": "Record Ready to Start",
            "reason": "The four readings pass. There is no current Ready to Start pass.",
        }
    return None


def _iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _personal(candidate: Candidate | None) -> dict[str, Any]:
    if candidate is None:
        return {}
    data = candidate.personal_data if isinstance(candidate.personal_data, dict) else {}
    return data


def _operator_reasons(readings: Any, facts: tuple[SurfaceFact, ...]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        if label not in seen:
            seen.add(label)
            labels.append(label)

    for code in readings.legal.reasons:
        if str(code).startswith("legal"):
            add("Work eligibility")
    for code in readings.employee_data.reasons:
        if code == "employee_data_incomplete":
            add("Identity")
    for code in readings.terms.reasons:
        if str(code).startswith("terms"):
            add("Employment terms")
    for code in readings.requirements.reasons:
        text = str(code)
        if text == "requirements_undefined":
            add("Professional requirements")
        elif text.startswith("requirements_unresolved:") or text.startswith("requirements_blocking:"):
            add(fact_label(text.split(":", 1)[1]))
        elif text == "requirements_not_ready":
            for fact in ordered_facts(facts):
                if fact.applicability != APPLICABILITY_APPLICABLE:
                    continue
                if fact.resolution in {RESOLUTION_UNRESOLVED, RESOLUTION_BLOCKING}:
                    add(fact.label)
            if not any(
                fact.applicability == APPLICABILITY_APPLICABLE
                and fact.resolution in {RESOLUTION_UNRESOLVED, RESOLUTION_BLOCKING}
                for fact in facts
            ):
                add("Professional requirements")
    return labels


async def _latest_employment(db: AsyncSession, tenant_id: str, employee_id: str) -> Employment | None:
    rows = (
        await db.scalars(
            select(Employment)
            .where(Employment.tenant_id == tenant_id, Employment.employee_id == employee_id)
            .order_by(Employment.created_at.desc())
        )
    ).all()
    preparing = [row for row in rows if row.state == "preparing"]
    if preparing:
        return preparing[0]
    return rows[0] if rows else None


async def build_hr_driver_operator_surface(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee: WorkforceEmployee,
) -> dict[str, Any]:
    tenant = str(tenant_id).strip()
    employment = await _latest_employment(db, tenant, str(employee.id))
    candidate = None
    if employee.candidate_id:
        candidate = await db.get(Candidate, str(employee.candidate_id))
    personal = _personal(candidate)
    employer = None
    if employee.own_company_id:
        company = await db.get(Company, str(employee.own_company_id))
        employer = company.name if company is not None else None

    if employment is None:
        return {
            "employee_id": str(employee.id),
            "employment_id": None,
            "state": None,
            "header": {
                "name": employee.display_name,
                "position": None,
                "employer": employer,
                "planned_start": None,
            },
            "identity": _identity(candidate, personal),
            "legal_stay": {"basis": None, "status": "unknown"},
            "work_eligibility": {"basis": None, "valid_for_this_employment": None, "status": "unknown"},
            "professional": {"defined": False, "satisfied": 0, "applicable": 0, "facts": []},
            "terms": None,
            "next_action": None,
            "ready_to_start": {"status": "blocked", "reasons": ["Employment"], "can_start": False},
        }

    decision = (
        await db.scalars(
            select(HrLegalEligibilityGateDecision)
            .where(
                HrLegalEligibilityGateDecision.tenant_id == tenant,
                HrLegalEligibilityGateDecision.employment_id == str(employment.id),
            )
            .order_by(HrLegalEligibilityGateDecision.decided_at.desc())
        )
    ).first()
    terms = (
        await db.scalars(
            select(HrEmploymentTerms).where(
                HrEmploymentTerms.tenant_id == tenant,
                HrEmploymentTerms.employment_id == str(employment.id),
                HrEmploymentTerms.is_current.is_(True),
            )
        )
    ).one_or_none()
    requirement_rows = (
        await db.scalars(
            select(HrEmploymentRequirement)
            .where(
                HrEmploymentRequirement.tenant_id == tenant,
                HrEmploymentRequirement.employment_id == str(employment.id),
            )
            .order_by(HrEmploymentRequirement.definition_key)
        )
    ).all()
    zus_tasks = (
        await db.scalars(
            select(WorkforceZusWorkspaceTask).where(
                WorkforceZusWorkspaceTask.tenant_id == tenant,
                WorkforceZusWorkspaceTask.employee_id == str(employee.id),
                WorkforceZusWorkspaceTask.task_kind == "registration",
            )
        )
    ).all()

    legal_pass = False
    if decision is not None and decision.outcome == "pass":
        legal_pass = decision_is_current(
            decision,
            reading={
                "citizenship_class": decision.citizenship_class,
                "stay_basis": decision.stay_basis,
                "work_authorization_basis": decision.work_authorization_basis,
                "valid_for_this_employment": decision.valid_for_this_employment,
            },
            client_company_id=employment.client_company_id,
            vacancy_id=employment.vacancy_id,
            planned_start=checkpoint_planned_start(
                employment,
                terms.intended_start_date if terms is not None else None,
            ),
        )
    work_yes = bool(
        decision is not None and decision.valid_for_this_employment == "yes" and legal_pass
    )
    terms_complete = evaluate_employment_terms(terms) == TERMS_COMPLETE
    facts = ordered_facts(
        tuple(
            SurfaceFact(
                key=row.definition_key,
                label=fact_label(row.definition_key),
                applicability=row.applicability,
                resolution=row.resolution,
                blocking_reason=row.blocking_reason,
                evidence_linked=bool(row.satisfaction_document_id or row.satisfaction_evidence_id),
            )
            for row in requirement_rows
        )
    )
    applicable = [fact for fact in facts if fact.applicability == APPLICABILITY_APPLICABLE]
    satisfied = [
        fact
        for fact in applicable
        if fact.resolution in {RESOLUTION_SATISFIED, RESOLUTION_WAIVED}
    ]
    requirements_defined = len(requirement_rows) > 0
    identity = _identity(candidate, personal)
    zus_open = any((task.status or "").lower() not in _ZUS_CLOSED for task in zus_tasks)
    legal_reading = {
        "citizenship_class": decision.citizenship_class if decision is not None else None,
        "stay_basis": decision.stay_basis if decision is not None else None,
        "work_authorization_basis": decision.work_authorization_basis if decision is not None else None,
        "valid_for_this_employment": decision.valid_for_this_employment if decision is not None else None,
    }
    employment_id = str(employment.id)

    def _ready(sync: Session):
        row = sync.get(Employment, employment_id)
        if row is None:
            raise LookupError(employment_id)
        fresh = read_ready_to_start_inputs(
            sync,
            tenant_id=tenant,
            employment=row,
            legal_reading=legal_reading,
            employee_facts={
                "first_name": identity["first_name"],
                "last_name": identity["last_name"],
                "birth_date": identity["birth_date"],
                "citizenship": identity["citizenship"],
            },
            employee_data_complete=bool(identity["complete"]),
        )
        stored = latest_ready_to_start_decision(sync, tenant_id=tenant, employment_id=employment_id)
        current = bool(stored is not None and ready_to_start_is_current(stored, fresh))
        return fresh, current

    readings, ready_current = await db.run_sync(_ready)
    live_ready = employment.state == "preparing" and all(
        reading.result == "pass"
        for reading in (
            readings.legal,
            readings.employee_data,
            readings.terms,
            readings.requirements,
        )
    )
    case = SurfaceCase(
        state=employment.state,
        terms_complete=terms_complete,
        work_yes=work_yes,
        legal_pass=legal_pass,
        zus_open=zus_open,
        ready_pass=ready_current,
        facts=facts,
        live_ready=live_ready and not ready_current,
    )
    if employment.state == "active":
        ready_status = "active"
        reasons: list[str] = []
    elif ready_current:
        ready_status = "pass"
        reasons = []
    else:
        ready_status = "blocked"
        reasons = _operator_reasons(readings, facts)
        if live_ready:
            reasons.append("Ready to Start is not a current pass")

    stay_basis = decision.stay_basis if decision is not None else None
    work_basis = decision.work_authorization_basis if decision is not None else None
    valid_for = decision.valid_for_this_employment if decision is not None else None
    return {
        "employee_id": str(employee.id),
        "employment_id": str(employment.id),
        "state": employment.state,
        "header": {
            "name": _person_name(candidate, employee.display_name),
            "position": terms.position if terms is not None else None,
            "employer": employer,
            "planned_start": _iso(terms.intended_start_date) if terms is not None else None,
        },
        "identity": identity,
        "legal_stay": {
            "basis": stay_basis,
            "status": "valid" if stay_basis and stay_basis != "none" else "unknown",
        },
        "work_eligibility": {
            "basis": work_basis,
            "valid_for_this_employment": valid_for,
            "citizenship_class": decision.citizenship_class if decision is not None else None,
            "checkpoint_context_complete": bool(
                employment.client_company_id
                and employment.vacancy_id
                and checkpoint_planned_start(
                    employment,
                    terms.intended_start_date if terms is not None else None,
                )
            ),
            "status": "eligible" if work_yes else "pending",
        },
        "professional": {
            "defined": requirements_defined,
            "satisfied": len(satisfied),
            "applicable": len(applicable),
            "facts": [
                {
                    "key": fact.key,
                    "label": fact.label,
                    "applicability": fact.applicability,
                    "resolution": fact.resolution,
                    "blocking_reason": fact.blocking_reason,
                    "evidence_linked": fact.evidence_linked,
                    "not_applicable": fact.applicability == APPLICABILITY_NOT_APPLICABLE,
                }
                for fact in facts
            ],
        },
        "terms": None
        if terms is None
        else {
            "complete": terms_complete,
            "position": terms.position,
            "contract_basis": terms.contract_basis,
            "work_time_value": _decimal(terms.work_time_value),
            "work_time_unit": terms.work_time_unit,
            "work_system": terms.work_system,
            "workplace": terms.workplace,
            "compensation_amount": _decimal(terms.compensation_amount),
            "compensation_currency": terms.compensation_currency,
            "compensation_unit": terms.compensation_unit,
            "duration": terms.duration,
            "fixed_term_end": _iso(terms.fixed_term_end),
            "probation_status": terms.probation_status,
            "probation_end": _iso(terms.probation_end),
            "intended_start_date": _iso(terms.intended_start_date),
        },
        "next_action": choose_next_action(case),
        "ready_to_start": {
            "status": ready_status,
            "reasons": reasons,
            "can_start": ready_status == "pass",
        },
    }


def _person_name(candidate: Candidate | None, fallback: str) -> str:
    if candidate is None:
        return fallback
    name = f"{candidate.first_name} {candidate.last_name}".strip()
    return name or fallback


def _identity(candidate: Candidate | None, personal: dict[str, Any]) -> dict[str, Any]:
    birth = personal.get("birth_date")
    citizenship = personal.get("citizenship")
    first = candidate.first_name if candidate is not None else None
    last = candidate.last_name if candidate is not None else None
    complete = bool(first and last and birth and citizenship)
    return {
        "first_name": first,
        "last_name": last,
        "birth_date": str(birth) if birth else None,
        "citizenship": str(citizenship) if citizenship else None,
        "complete": complete,
        "status": "complete" if complete else "incomplete",
    }


def _identity_facts(candidate: Candidate | None) -> tuple[dict[str, Any], bool]:
    personal = _personal(candidate)
    identity = _identity(candidate, personal)
    return (
        {
            "first_name": identity["first_name"],
            "last_name": identity["last_name"],
            "birth_date": identity["birth_date"],
            "citizenship": identity["citizenship"],
        },
        bool(identity["complete"]),
    )


def _legal_reading_from_decision(decision: HrLegalEligibilityGateDecision | None) -> dict[str, Any]:
    if decision is None:
        return {}
    return {
        "citizenship_class": decision.citizenship_class,
        "stay_basis": decision.stay_basis,
        "work_authorization_basis": decision.work_authorization_basis,
        "valid_for_this_employment": decision.valid_for_this_employment,
    }


async def confirm_surface_terms(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    confirmation: EmploymentTermsConfirmation,
) -> dict[str, Any]:
    employment = await _latest_employment(db, tenant_id, employee_id)
    if employment is None or employment.state != "preparing":
        return {"accepted": False, "reason": "not_preparing"}
    employment_id = str(employment.id)

    def _confirm(sync: Session) -> dict[str, Any]:
        row = sync.get(Employment, employment_id)
        if row is None or row.state != "preparing":
            return {"accepted": False, "reason": "not_preparing"}
        result = confirm_employment_terms(
            sync,
            tenant_id=tenant_id,
            employment=row,
            confirmation=confirmation,
        )
        return {"accepted": result.accepted, "reason": result.reason}

    return await db.run_sync(_confirm)


async def confirm_surface_legal(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    reading: dict[str, Any],
    actor_user_id: str,
) -> dict[str, Any]:
    employment = await _latest_employment(db, tenant_id, employee_id)
    if employment is None or employment.state != "preparing":
        return {"accepted": False, "outcome": "not_preparing", "reason": "not_preparing"}
    result = await record_hr_legal_eligibility_gate(
        db,
        tenant_id=tenant_id,
        employment=employment,
        reading=reading,
        actor_user_id=actor_user_id,
    )
    context_complete = bool(result.employment_context.get("planned_start")) and bool(
        result.employment_context.get("client_company_id")
    ) and bool(result.employment_context.get("vacancy_id"))
    return {
        "accepted": result.applies,
        "outcome": result.outcome,
        "reason": None if result.outcome == "pass" else result.outcome,
        "checkpoint_context_complete": context_complete,
    }


async def start_surface_employment(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    actor_user_id: str,
) -> dict[str, Any]:
    employment = await _latest_employment(db, tenant_id, employee_id)
    if employment is None or employment.state != "preparing":
        return {"activated": False, "reason": "not_preparing", "blocked_reasons": [], "state": None}
    employment_id = str(employment.id)
    candidate = None
    employee = await db.get(WorkforceEmployee, employee_id)
    if employee is not None and employee.candidate_id:
        candidate = await db.get(Candidate, str(employee.candidate_id))
    facts, complete = _identity_facts(candidate)
    decision = (
        await db.scalars(
            select(HrLegalEligibilityGateDecision)
            .where(
                HrLegalEligibilityGateDecision.tenant_id == tenant_id,
                HrLegalEligibilityGateDecision.employment_id == employment_id,
            )
            .order_by(HrLegalEligibilityGateDecision.decided_at.desc())
        )
    ).first()
    legal_reading = _legal_reading_from_decision(decision)

    def _start(sync: Session) -> dict[str, Any]:
        row = sync.get(Employment, employment_id)
        if row is None or row.state != "preparing":
            return {"activated": False, "reason": "not_preparing", "blocked_reasons": [], "state": None}
        activated = activate_employment(
            sync,
            tenant_id=tenant_id,
            employment_id=employment_id,
            legal_reading=legal_reading,
            employee_facts=facts,
            employee_data_complete=complete,
        )
        return {
            "activated": activated.activated,
            "reason": activated.reason,
            "blocked_reasons": [],
            "state": "active" if activated.activated else row.state,
        }

    return await db.run_sync(_start)


async def record_surface_ready(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    actor_user_id: str,
) -> dict[str, Any]:
    """Append a Ready to Start decision. Does not move Employment.state."""

    employment = await _latest_employment(db, tenant_id, employee_id)
    if employment is None or employment.state != "preparing":
        return {"accepted": False, "outcome": None, "reason": "not_preparing", "blocked_reasons": []}
    employment_id = str(employment.id)
    employee = await db.get(WorkforceEmployee, employee_id)
    candidate = None
    if employee is not None and employee.candidate_id:
        candidate = await db.get(Candidate, str(employee.candidate_id))
    facts, complete = _identity_facts(candidate)
    decision = (
        await db.scalars(
            select(HrLegalEligibilityGateDecision)
            .where(
                HrLegalEligibilityGateDecision.tenant_id == tenant_id,
                HrLegalEligibilityGateDecision.employment_id == employment_id,
            )
            .order_by(HrLegalEligibilityGateDecision.decided_at.desc())
        )
    ).first()
    legal_reading = _legal_reading_from_decision(decision)

    def _record(sync: Session) -> dict[str, Any]:
        row = sync.get(Employment, employment_id)
        if row is None or row.state != "preparing":
            return {"accepted": False, "outcome": None, "reason": "not_preparing", "blocked_reasons": []}
        recorded = record_ready_to_start(
            sync,
            tenant_id=tenant_id,
            employment=row,
            actor_user_id=actor_user_id,
            legal_reading=legal_reading,
            employee_facts=facts,
            employee_data_complete=complete,
        )
        blocked: list[str] = []
        outcome = None
        if recorded.decision is not None:
            outcome = recorded.decision.outcome
            if recorded.decision.blocked_reasons:
                parsed = json.loads(recorded.decision.blocked_reasons)
                if isinstance(parsed, list):
                    blocked = [str(item) for item in parsed]
        return {
            "accepted": bool(recorded.accepted and outcome == "pass"),
            "outcome": outcome,
            "reason": None if outcome == "pass" else (recorded.reason or "blocked"),
            "blocked_reasons": blocked,
        }

    return await db.run_sync(_record)
