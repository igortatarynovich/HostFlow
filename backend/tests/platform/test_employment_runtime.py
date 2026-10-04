"""Accepted internal_hr handoff opens Employment(preparing) on the existing Employee."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.app.models.hr_employment import Employment
from backend.app.services.employment_runtime import open_preparing_employment_for_accepted_handoff


def _handoff(**overrides):
    base = dict(
        id="h-1",
        client_company_id="client-1",
        accepted_at=datetime(2026, 10, 3, tzinfo=timezone.utc),
        accepted_by_user_id="actor-1",
        reviewed_by_user_id="actor-1",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _candidate(**overrides):
    base = dict(
        id="c-1",
        company_id="candidate-client",
        vacancy_id="vac-1",
        recruiter_id="rec-1",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _employee(**overrides):
    base = dict(id="e-1", tenant_id="t1", candidate_id="c-1", status="onboarding")
    base.update(overrides)
    return SimpleNamespace(**base)


def _db(*results):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _missing():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    return result


def _found(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_accepted_handoff_opens_preparing_on_the_existing_employee() -> None:
    employee = _employee(status="terminated")
    candidate = _candidate()
    snapshot = {"handoff_id": "h-1", "candidate_id": "c-1"}
    db = _db(_missing(), _found(snapshot))

    row = await open_preparing_employment_for_accepted_handoff(
        db,
        tenant_id="t1",
        handoff=_handoff(),
        candidate=candidate,
        employee=employee,
    )

    assert isinstance(row, Employment)
    assert row.state == "preparing"
    assert row.employee_id == "e-1"
    assert row.client_company_id == "client-1"
    assert row.vacancy_id == "vac-1"
    assert row.recruiter_user_id == "rec-1"
    assert row.handoff_id == "h-1"
    assert row.handoff_by_user_id == "actor-1"
    assert row.candidate_snapshot == snapshot
    assert row.started_on is None
    assert row.ended_on is None
    assert employee.status == "terminated"
    assert candidate.id == "c-1"
    added = db.add.call_args.args[0]
    assert isinstance(added, Employment)
    assert added.__class__.__name__ != "WorkforceEmployment"


@pytest.mark.asyncio
async def test_repeat_handoff_adds_another_employment_without_rewriting_the_first() -> None:
    first = Employment(
        id="rel-1",
        tenant_id="t1",
        employee_id="e-1",
        state="preparing",
        client_company_id="client-1",
        vacancy_id="vac-1",
        recruiter_user_id="rec-1",
        handoff_id="h-1",
        handoff_by_user_id="actor-1",
        candidate_snapshot={"handoff_id": "h-1"},
    )
    before = (
        first.state,
        first.client_company_id,
        first.vacancy_id,
        first.handoff_id,
        dict(first.candidate_snapshot),
    )
    db = _db(_missing(), _found({"handoff_id": "h-2"}))

    second = await open_preparing_employment_for_accepted_handoff(
        db,
        tenant_id="t1",
        handoff=_handoff(id="h-2", client_company_id="client-2"),
        candidate=_candidate(vacancy_id="vac-2", recruiter_id="rec-2"),
        employee=_employee(),
    )

    assert second is not None
    assert second.id != first.id
    assert second.handoff_id == "h-2"
    assert second.state == "preparing"
    assert second.employee_id == "e-1"
    assert second.client_company_id == "client-2"
    assert (first.state, first.client_company_id, first.vacancy_id, first.handoff_id, first.candidate_snapshot) == before


@pytest.mark.asyncio
async def test_same_handoff_returns_the_existing_employment_unchanged() -> None:
    existing = Employment(
        id="rel-1",
        tenant_id="t1",
        employee_id="e-1",
        state="preparing",
        client_company_id="client-1",
        handoff_id="h-1",
    )
    db = _db(_found(existing))

    again = await open_preparing_employment_for_accepted_handoff(
        db,
        tenant_id="t1",
        handoff=_handoff(client_company_id="other-client"),
        candidate=_candidate(),
        employee=_employee(status="active"),
    )

    assert again is existing
    assert existing.client_company_id == "client-1"
    assert existing.state == "preparing"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_missing_employee_context_does_not_create_one() -> None:
    db = _db(_missing())
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "backend.app.services.employment_runtime.find_employee_by_candidate",
            AsyncMock(return_value=None),
        )
        row = await open_preparing_employment_for_accepted_handoff(
            db,
            tenant_id="t1",
            handoff=_handoff(),
            candidate=_candidate(),
            employee=None,
        )

    assert row is None
    db.add.assert_not_called()


def test_runtime_does_not_read_legacy_employee_facts_or_move_state() -> None:
    text = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "app/services/employment_runtime.py"
    ).read_text(encoding="utf-8")
    assert "WorkforceEmployee.status" not in text
    assert ".hire_date" not in text
    assert "WorkforceEmployment(" not in text
    assert "legal_eligibility" not in text
    assert 'state="active"' not in text
