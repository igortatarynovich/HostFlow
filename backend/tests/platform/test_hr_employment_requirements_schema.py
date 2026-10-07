"""hr_employment_requirements stores one instance per Employment and definition.

Applicability and resolution are separate. The migration does not
backfill, and it does not move Employment.state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "alembic"
    / "versions"
    / "202610060001_hr_employment_requirements.py"
)
_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "specs"
    / "architecture"
    / "employee-record-employment-lifecycle-contract.md"
)


def _requirement(**overrides) -> HrEmploymentRequirement:
    values = dict(
        id="req-1",
        tenant_id="tenant-1",
        employment_id="employment-1",
        definition_key="def-a",
        policy_id="policy-a",
        policy_version="1",
        applicability=APPLICABILITY_APPLICABLE,
        applicability_basis=None,
        resolution=RESOLUTION_UNRESOLVED,
        satisfaction_evidence_id=None,
        satisfaction_document_id=None,
        waiver_actor_id=None,
        waiver_at=None,
        waiver_reason=None,
        blocking_reason=None,
    )
    values.update(overrides)
    return HrEmploymentRequirement(**values)


def _session() -> Session:
    engine = create_engine("sqlite://")
    Employment.__table__.create(engine)
    HrEmploymentRequirement.__table__.create(engine)
    return Session(engine)


def test_migration_creates_the_table_without_backfill() -> None:
    text = _MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "202610060001_hr_employment_requirements"' in text
    assert 'down_revision: Union[str, None] = "202610050001_hr_employment_terms"' in text
    assert '"hr_employment_requirements"' in text
    assert "No backfill" in text
    assert "INSERT INTO" not in text
    assert "RequirementEvaluationStatus" not in text
    assert "workforce_onboarding_tasks" not in text
    assert "workforce_employments" not in text
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "## Pre-employment Requirements Schema" in contract
    assert "Schema Gate **PASS**" not in contract
    assert "Runtime Gate **PASS**" not in contract


def test_instance_belongs_to_employment_and_definition_not_to_the_employee() -> None:
    columns = set(HrEmploymentRequirement.__table__.c.keys())
    assert "employee_id" not in columns
    assert "definition_key" in columns
    fks = {fk.parent.name: fk for fk in HrEmploymentRequirement.__table__.foreign_keys}
    assert fks["employment_id"].column.table.name == "hr_employments"
    assert fks["tenant_id"].column.table.name == "tenants"
    assert fks["satisfaction_evidence_id"].column.table.name == "candidate_evidence"
    assert fks["satisfaction_document_id"].column.table.name == "documents"
    assert fks["waiver_actor_id"].column.table.name == "users"
    assert "policy_id" not in fks
    assert "definition_key" not in fks
    employment_columns = set(Employment.__table__.c.keys())
    assert "definition_key" not in employment_columns
    assert "resolution" not in employment_columns
    unique = [
        constraint
        for constraint in HrEmploymentRequirement.__table__.constraints
        if constraint.name == "uq_hr_employment_requirements_employment_definition"
    ]
    assert len(unique) == 1
    assert {column.name for column in unique[0].columns} == {"employment_id", "definition_key"}


def test_two_employments_keep_independent_instances() -> None:
    session = _session()
    session.add(_requirement())
    session.add(_requirement(id="req-2", employment_id="employment-2"))
    session.commit()
    assert session.query(HrEmploymentRequirement).count() == 2
    session.add(_requirement(id="req-3"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_axes_stay_independent() -> None:
    session = _session()
    session.add(
        _requirement(
            id="na",
            applicability=APPLICABILITY_NOT_APPLICABLE,
            applicability_basis="outside this hire",
            resolution=None,
        )
    )
    session.commit()
    stored = session.get(HrEmploymentRequirement, "na")
    assert stored is not None
    assert stored.resolution is None

    session.add(
        _requirement(
            id="na-resolved",
            definition_key="def-b",
            applicability=APPLICABILITY_NOT_APPLICABLE,
            resolution=RESOLUTION_UNRESOLVED,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(_requirement(id="open", definition_key="def-c"))
    session.commit()
    open_row = session.get(HrEmploymentRequirement, "open")
    assert open_row is not None
    assert open_row.resolution == RESOLUTION_UNRESOLVED
    assert open_row.blocking_reason is None

    session.add(
        _requirement(
            id="open-with-block",
            definition_key="def-d",
            blocking_reason="found a problem",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(
        _requirement(
            id="done",
            definition_key="def-e",
            resolution=RESOLUTION_SATISFIED,
            satisfaction_document_id="document-1",
        )
    )
    session.commit()

    session.add(
        _requirement(
            id="done-empty",
            definition_key="def-f",
            resolution=RESOLUTION_SATISFIED,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(
        _requirement(
            id="waived",
            definition_key="def-g",
            resolution=RESOLUTION_WAIVED,
            waiver_actor_id="user-1",
            waiver_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            waiver_reason="operator lifted it",
        )
    )
    session.commit()

    session.add(
        _requirement(
            id="waived-blank",
            definition_key="def-h",
            resolution=RESOLUTION_WAIVED,
            waiver_actor_id="user-1",
            waiver_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            waiver_reason="",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(
        _requirement(
            id="blocked",
            definition_key="def-i",
            resolution=RESOLUTION_BLOCKING,
            blocking_reason="exam refused",
        )
    )
    session.commit()
    blocked = session.get(HrEmploymentRequirement, "blocked")
    assert blocked is not None
    assert blocked.resolution == RESOLUTION_BLOCKING
    assert blocked.satisfaction_document_id is None


def test_employment_state_change_does_not_rewrite_the_instance() -> None:
    session = _session()
    session.add(
        Employment(
            id="employment-1",
            tenant_id="tenant-1",
            employee_id="employee-1",
            state="preparing",
        )
    )
    session.add(_requirement(satisfaction_evidence_id=None))
    session.commit()
    employment = session.get(Employment, "employment-1")
    assert employment is not None
    employment.state = "active"
    session.commit()
    row = session.get(HrEmploymentRequirement, "req-1")
    assert row is not None
    assert row.resolution == RESOLUTION_UNRESOLVED
    assert row.definition_key == "def-a"
    assert employment.state == "active"
