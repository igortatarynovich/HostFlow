"""hr_employment_terms stores one current employment_terms.v1 snapshot.

The table is the store. It does not copy a vacancy or a contract card,
and it does not move Employment.state.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
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

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "alembic"
    / "versions"
    / "202610050001_hr_employment_terms.py"
)


def _terms(**overrides) -> HrEmploymentTerms:
    values = dict(
        id="terms-1",
        tenant_id="tenant-1",
        employment_id="employment-1",
        is_current=True,
        position="Driver CE",
        contract_basis="agreed-basis",
        work_time_value=Decimal("1.0000"),
        work_time_unit="fte",
        workplace="Warsaw yard",
        compensation_amount=Decimal("30.0000"),
        compensation_currency="PLN",
        compensation_unit="hour",
        duration=DURATION_FIXED,
        fixed_term_end=date(2027, 3, 1),
        probation_status=PROBATION_DATED,
        probation_end=date(2026, 12, 1),
        default_vacancy_id="vacancy-1",
    )
    values.update(overrides)
    return HrEmploymentTerms(**values)


def _session() -> Session:
    engine = create_engine("sqlite://")
    Employment.__table__.create(engine)
    HrEmploymentTerms.__table__.create(engine)
    return Session(engine)


def test_migration_creates_the_table_without_backfill() -> None:
    text = _MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "202610050001_hr_employment_terms"' in text
    assert 'down_revision: Union[str, None] = "202610040001_hr_legal_eligibility_gate"' in text
    assert '"hr_employment_terms"' in text
    assert "No backfill" in text
    assert "INSERT INTO" not in text
    assert "vacancies" not in text
    assert "workforce_employments" not in text
    assert "workforce_payroll_profiles" not in text


def test_snapshot_belongs_to_one_employment_and_not_to_the_card() -> None:
    fks = {fk.parent.name: fk for fk in HrEmploymentTerms.__table__.foreign_keys}
    assert fks["employment_id"].column.table.name == "hr_employments"
    assert fks["tenant_id"].column.table.name == "tenants"
    assert "default_vacancy_id" not in fks
    assert "vacancy_id" not in HrEmploymentTerms.__table__.c
    card_columns = set(WorkforceEmployment.__table__.c.keys())
    assert "position" not in card_columns
    assert "contract_basis" not in card_columns
    assert "work_time_value" not in card_columns
    assert "compensation_amount" not in card_columns
    employment_columns = set(Employment.__table__.c.keys())
    assert "position" not in employment_columns
    assert "duration" not in employment_columns
    assert "ended_on" in employment_columns
    assert "started_on" in employment_columns
    assert "intended_start_date" in HrEmploymentTerms.__table__.c
    assert "work_system" in HrEmploymentTerms.__table__.c
    assert "intended_start_date" not in employment_columns
    assert "work_system" not in employment_columns
    checks = " ".join(str(c.sqltext) for c in HrEmploymentTerms.__table__.constraints if c.name)
    assert "full_time" not in checks


def test_one_current_snapshot_and_a_later_history_row() -> None:
    session = _session()
    session.add(_terms())
    session.commit()
    session.add(_terms(id="terms-2", is_current=True))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(_terms(id="terms-3", is_current=False, probation_status=PROBATION_NONE, probation_end=None))
    session.commit()
    current = session.query(HrEmploymentTerms).filter_by(is_current=True).one()
    assert current.id == "terms-1"
    assert session.query(HrEmploymentTerms).filter_by(employment_id="employment-1").count() == 2


def test_duration_and_probation_are_explicit() -> None:
    session = _session()
    session.add(_terms(id="indef", duration=DURATION_INDEFINITE, fixed_term_end=None, probation_status=PROBATION_NONE, probation_end=None))
    session.commit()
    stored = session.get(HrEmploymentTerms, "indef")
    assert stored is not None
    assert stored.duration == DURATION_INDEFINITE
    assert stored.fixed_term_end is None
    assert stored.probation_status == PROBATION_NONE

    session.add(_terms(id="bad-end", employment_id="employment-2", duration=DURATION_INDEFINITE, fixed_term_end=date(2027, 1, 1)))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(_terms(id="bad-fixed", employment_id="employment-3", duration=DURATION_FIXED, fixed_term_end=None))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(
        _terms(
            id="unset",
            employment_id="employment-4",
            probation_status=PROBATION_UNDETERMINED,
            probation_end=None,
        )
    )
    session.commit()
    unset = session.get(HrEmploymentTerms, "unset")
    assert unset is not None
    assert unset.probation_status == PROBATION_UNDETERMINED
    assert unset.probation_end is None

    session.add(
        _terms(
            id="none-with-date",
            employment_id="employment-5",
            probation_status=PROBATION_NONE,
            probation_end=date(2026, 12, 1),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(
        _terms(
            id="dated-without-date",
            employment_id="employment-6",
            probation_status=PROBATION_DATED,
            probation_end=None,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_employment_state_change_does_not_rewrite_the_snapshot() -> None:
    session = _session()
    session.add(
        Employment(
            id="employment-1",
            tenant_id="tenant-1",
            employee_id="employee-1",
            state="preparing",
        )
    )
    session.add(_terms(probation_status=PROBATION_NONE, probation_end=None))
    session.commit()
    employment = session.get(Employment, "employment-1")
    assert employment is not None
    employment.state = "active"
    session.commit()
    terms = session.get(HrEmploymentTerms, "terms-1")
    assert terms is not None
    assert terms.position == "Driver CE"
    assert terms.compensation_amount == Decimal("30.0000")
    assert terms.default_vacancy_id == "vacancy-1"
    assert employment.state == "active"
    assert inspect(session.get_bind()).has_table("hr_employment_terms")
