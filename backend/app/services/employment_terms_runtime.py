"""Confirm an employment_terms.v1 snapshot. A draft is not stored.

``is_current`` is the latest confirmed agreement, not the latest edit.
An unresolved proposal stays with the caller. It does not replace the
current row. This module does not move ``hr_employments.state``, does not
insert a contract card, and does not open requirements or Ready to Start.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_terms import (
    DURATION_FIXED,
    DURATION_INDEFINITE,
    PROBATION_DATED,
    PROBATION_NONE,
    PROBATION_UNDETERMINED,
    HrEmploymentTerms,
)

TERMS_COMPLETE = "complete"
TERMS_INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class EmploymentTermsProposal:
    """One reading of compatible vacancy defaults. Not a stored snapshot."""

    position: str | None
    workplace: str | None
    default_vacancy_id: str | None
    contract_basis: None = None
    work_time_value: None = None
    work_time_unit: None = None
    compensation_amount: None = None
    compensation_currency: None = None
    compensation_unit: None = None
    duration: None = None
    fixed_term_end: None = None
    probation_status: str = PROBATION_UNDETERMINED
    probation_end: None = None


@dataclass(frozen=True)
class EmploymentTermsConfirmation:
    position: str | None
    contract_basis: str | None
    work_time_value: Decimal | None
    work_time_unit: str | None
    workplace: str | None
    compensation_amount: Decimal | None
    compensation_currency: str | None
    compensation_unit: str | None
    duration: str | None
    fixed_term_end: date | None
    probation_status: str | None
    probation_end: date | None
    default_vacancy_id: str | None = None


@dataclass(frozen=True)
class EmploymentTermsConfirmationResult:
    accepted: bool
    terms: HrEmploymentTerms | None
    reason: str | None


def _text(value: Any) -> str | None:
    raw = str(value or "").strip()
    return raw or None


def propose_employment_terms_defaults(vacancy: Any) -> EmploymentTermsProposal:
    """Copy title and location once. Leave pay and contract basis unset.

    ``salary_from`` / ``salary_to`` are a range, not one agreed amount.
    ``employment_type`` is the offer vocabulary, not the contract basis.
    """

    return EmploymentTermsProposal(
        position=_text(getattr(vacancy, "title", None)),
        workplace=_text(getattr(vacancy, "location", None)),
        default_vacancy_id=_text(getattr(vacancy, "id", None)),
    )


def _refusal(confirmation: EmploymentTermsConfirmation) -> str | None:
    required = (
        _text(confirmation.position),
        _text(confirmation.contract_basis),
        _text(confirmation.work_time_unit),
        _text(confirmation.workplace),
        _text(confirmation.compensation_currency),
        _text(confirmation.compensation_unit),
    )
    if any(item is None for item in required):
        return "unresolved"
    if confirmation.work_time_value is None or confirmation.compensation_amount is None:
        return "unresolved"
    if confirmation.duration not in {DURATION_FIXED, DURATION_INDEFINITE}:
        return "unresolved"
    if confirmation.duration == DURATION_FIXED and confirmation.fixed_term_end is None:
        return "fixed_term_end"
    if confirmation.duration == DURATION_INDEFINITE and confirmation.fixed_term_end is not None:
        return "fixed_term_end"
    if confirmation.probation_status == PROBATION_UNDETERMINED or not _text(confirmation.probation_status):
        return "probation_undetermined"
    if confirmation.probation_status == PROBATION_NONE and confirmation.probation_end is not None:
        return "probation"
    if confirmation.probation_status == PROBATION_DATED and confirmation.probation_end is None:
        return "probation"
    if confirmation.probation_status not in {PROBATION_NONE, PROBATION_DATED}:
        return "probation"
    return None


def _current_terms(db: Session, tenant_id: str, employment_id: str) -> HrEmploymentTerms | None:
    return db.scalars(
        select(HrEmploymentTerms).where(
            HrEmploymentTerms.tenant_id == tenant_id,
            HrEmploymentTerms.employment_id == employment_id,
            HrEmploymentTerms.is_current.is_(True),
        )
    ).one_or_none()


def confirm_employment_terms(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    confirmation: EmploymentTermsConfirmation,
) -> EmploymentTermsConfirmationResult:
    """Store a confirmed snapshot. Refuse without changing the current row."""

    reason = _refusal(confirmation)
    if reason is not None:
        return EmploymentTermsConfirmationResult(accepted=False, terms=None, reason=reason)

    position = _text(confirmation.position)
    contract_basis = _text(confirmation.contract_basis)
    work_time_unit = _text(confirmation.work_time_unit)
    workplace = _text(confirmation.workplace)
    compensation_currency = _text(confirmation.compensation_currency)
    compensation_unit = _text(confirmation.compensation_unit)
    work_time_value = confirmation.work_time_value
    compensation_amount = confirmation.compensation_amount
    if (
        position is None
        or contract_basis is None
        or work_time_unit is None
        or workplace is None
        or compensation_currency is None
        or compensation_unit is None
        or work_time_value is None
        or compensation_amount is None
        or confirmation.duration is None
        or confirmation.probation_status is None
    ):
        return EmploymentTermsConfirmationResult(accepted=False, terms=None, reason="unresolved")

    previous = _current_terms(db, str(tenant_id).strip(), str(employment.id))
    if previous is not None:
        previous.is_current = False
        db.flush()

    row = HrEmploymentTerms(
        id=str(uuid4()),
        tenant_id=str(tenant_id).strip(),
        employment_id=str(employment.id),
        is_current=True,
        position=position,
        contract_basis=contract_basis,
        work_time_value=work_time_value,
        work_time_unit=work_time_unit,
        workplace=workplace,
        compensation_amount=compensation_amount,
        compensation_currency=compensation_currency,
        compensation_unit=compensation_unit,
        duration=confirmation.duration,
        fixed_term_end=confirmation.fixed_term_end,
        probation_status=confirmation.probation_status,
        probation_end=confirmation.probation_end,
        default_vacancy_id=_text(confirmation.default_vacancy_id),
    )
    db.add(row)
    db.flush()
    return EmploymentTermsConfirmationResult(accepted=True, terms=row, reason=None)


def evaluate_employment_terms(current: HrEmploymentTerms | None) -> str:
    """Read the current snapshot only. No vacancy, card, or payroll input."""

    if current is None or not current.is_current:
        return TERMS_INCOMPLETE
    if not all(
        _text(item)
        for item in (
            current.position,
            current.contract_basis,
            current.work_time_unit,
            current.workplace,
            current.compensation_currency,
            current.compensation_unit,
        )
    ):
        return TERMS_INCOMPLETE
    if current.work_time_value is None or current.compensation_amount is None:
        return TERMS_INCOMPLETE
    if current.duration == DURATION_FIXED and current.fixed_term_end is None:
        return TERMS_INCOMPLETE
    if current.duration == DURATION_INDEFINITE and current.fixed_term_end is not None:
        return TERMS_INCOMPLETE
    if current.duration not in {DURATION_FIXED, DURATION_INDEFINITE}:
        return TERMS_INCOMPLETE
    if current.probation_status == PROBATION_UNDETERMINED:
        return TERMS_INCOMPLETE
    if current.probation_status == PROBATION_NONE and current.probation_end is not None:
        return TERMS_INCOMPLETE
    if current.probation_status == PROBATION_DATED and current.probation_end is None:
        return TERMS_INCOMPLETE
    if current.probation_status not in {PROBATION_NONE, PROBATION_DATED}:
        return TERMS_INCOMPLETE
    return TERMS_COMPLETE
