"""Vacancy defaults stay a proposal until the operator confirms them.

is_current is the latest confirmed agreement. A refused confirmation
does not replace it and does not move Employment.state.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
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
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.services.employment_terms_runtime import (
    TERMS_COMPLETE,
    TERMS_INCOMPLETE,
    EmploymentTermsConfirmation,
    confirm_employment_terms,
    evaluate_employment_terms,
    propose_employment_terms_defaults,
)


def _session() -> Session:
    engine = create_engine("sqlite://")
    Employment.__table__.create(engine)
    HrEmploymentTerms.__table__.create(engine)
    WorkforceEmployment.__table__.create(engine)
    return Session(engine)


def _employment() -> Employment:
    return Employment(
        id="employment-1",
        tenant_id="tenant-1",
        employee_id="employee-1",
        state="preparing",
        vacancy_id="vacancy-1",
    )


def _confirmation(**overrides) -> EmploymentTermsConfirmation:
    values = dict(
        position="Driver CE",
        contract_basis="agreed-basis",
        work_time_value=Decimal("1"),
        work_time_unit="fte",
        workplace="Warsaw yard",
        compensation_amount=Decimal("30"),
        compensation_currency="PLN",
        compensation_unit="hour",
        duration=DURATION_FIXED,
        fixed_term_end=date(2027, 3, 1),
        probation_status=PROBATION_NONE,
        probation_end=None,
        default_vacancy_id="vacancy-1",
    )
    values.update(overrides)
    return EmploymentTermsConfirmation(**values)


def test_defaults_are_a_proposal_and_confirmation_stores_the_snapshot() -> None:
    vacancy = SimpleNamespace(
        id="vacancy-1",
        title="Driver CE",
        location="Warsaw yard",
        salary_from="20",
        salary_to="40",
        currency="PLN",
        employment_type="full_time",
    )
    proposal = propose_employment_terms_defaults(vacancy)
    assert proposal.position == "Driver CE"
    assert proposal.workplace == "Warsaw yard"
    assert proposal.default_vacancy_id == "vacancy-1"
    assert proposal.contract_basis is None
    assert proposal.compensation_amount is None
    assert proposal.compensation_currency is None
    assert proposal.probation_status == PROBATION_UNDETERMINED
    vacancy.title = "Changed offer"
    vacancy.salary_from = "99"
    assert proposal.position == "Driver CE"

    session = _session()
    employment = _employment()
    session.add(employment)
    session.commit()
    assert evaluate_employment_terms(None) == TERMS_INCOMPLETE

    refused = confirm_employment_terms(
        session,
        tenant_id="tenant-1",
        employment=employment,
        confirmation=_confirmation(probation_status=PROBATION_UNDETERMINED, probation_end=None),
    )
    assert refused.accepted is False
    assert refused.reason == "probation_undetermined"
    assert session.scalars(select(HrEmploymentTerms)).all() == []
    assert employment.state == "preparing"

    confirmed = confirm_employment_terms(
        session,
        tenant_id="tenant-1",
        employment=employment,
        confirmation=_confirmation(
            position=proposal.position,
            workplace=proposal.workplace,
            default_vacancy_id=proposal.default_vacancy_id,
            contract_basis="agreed-basis",
            compensation_amount=Decimal("32"),
        ),
    )
    session.commit()
    assert confirmed.accepted is True
    assert confirmed.terms is not None
    assert confirmed.terms.is_current is True
    assert confirmed.terms.contract_basis == "agreed-basis"
    assert confirmed.terms.compensation_amount == Decimal("32.0000")
    assert confirmed.terms.position == "Driver CE"
    assert evaluate_employment_terms(confirmed.terms) == TERMS_COMPLETE
    assert employment.state == "preparing"
    assert session.scalar(select(func.count()).select_from(WorkforceEmployment)) == 0


def test_a_later_confirmation_keeps_the_previous_agreement() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.commit()
    first = confirm_employment_terms(
        session,
        tenant_id="tenant-1",
        employment=employment,
        confirmation=_confirmation(position="Driver CE"),
    )
    session.commit()
    assert first.terms is not None
    first_id = first.terms.id

    second = confirm_employment_terms(
        session,
        tenant_id="tenant-1",
        employment=employment,
        confirmation=_confirmation(
            position="Warehouse",
            duration=DURATION_INDEFINITE,
            fixed_term_end=None,
            probation_status=PROBATION_DATED,
            probation_end=date(2026, 12, 1),
        ),
    )
    session.commit()
    previous = session.get(HrEmploymentTerms, first_id)
    assert previous is not None
    assert previous.is_current is False
    assert previous.position == "Driver CE"
    assert second.terms is not None
    assert second.terms.is_current is True
    assert second.terms.position == "Warehouse"
    assert second.terms.id != first_id
    assert evaluate_employment_terms(previous) == TERMS_INCOMPLETE
    assert evaluate_employment_terms(second.terms) == TERMS_COMPLETE
    assert employment.state == "preparing"

    blocked = confirm_employment_terms(
        session,
        tenant_id="tenant-1",
        employment=employment,
        confirmation=_confirmation(compensation_amount=None),
    )
    assert blocked.accepted is False
    assert session.get(HrEmploymentTerms, second.terms.id).is_current is True
    assert employment.state == "preparing"
