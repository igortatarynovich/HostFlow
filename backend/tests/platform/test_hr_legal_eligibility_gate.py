"""HR Legal Eligibility Gate on one Employment(preparing).

The gate reads legal_eligibility.v1. It does not derive the chain and it
does not move Employment.state.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from backend.app.services.hr_legal_eligibility_gate import (
    decision_is_current,
    evaluate_hr_legal_eligibility_gate,
    record_hr_legal_eligibility_gate,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_GATE = _REPO_ROOT / "backend" / "app" / "services" / "hr_legal_eligibility_gate.py"
_YES = {
    "citizenship_class": "pl",
    "stay_basis": "not_required",
    "work_authorization_basis": "not_required",
    "valid_for_this_employment": "yes",
}


def _employment(**overrides):
    values = {
        "id": "emp-rel-1",
        "state": "preparing",
        "client_company_id": "client-1",
        "vacancy_id": "vac-1",
        "started_on": date(2026, 11, 2),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_pass_stays_preparing_for_this_employment() -> None:
    employment = _employment()
    result = evaluate_hr_legal_eligibility_gate(
        employment_state=employment.state,
        reading=_YES,
        client_company_id=employment.client_company_id,
        vacancy_id=employment.vacancy_id,
        planned_start=employment.started_on,
    )
    assert result.outcome == "pass"
    assert result.policy_id == "legal_eligibility.v1"
    assert result.continues_existing_workflow is False
    assert result.employment_context["client_company_id"] == "client-1"
    assert result.employment_context["vacancy_id"] == "vac-1"
    assert result.employment_context["planned_start"] == "2026-11-02"
    assert employment.state == "preparing"


def test_fail_and_blocked_do_not_invent_an_employment_state() -> None:
    fail = evaluate_hr_legal_eligibility_gate(
        employment_state="preparing",
        reading={**_YES, "valid_for_this_employment": "no"},
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    blocked = evaluate_hr_legal_eligibility_gate(
        employment_state="preparing",
        reading={**_YES, "stay_basis": ""},
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    held = evaluate_hr_legal_eligibility_gate(
        employment_state="preparing",
        reading={**_YES, "valid_for_this_employment": "operator_verification"},
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    assert fail.outcome == "fail"
    assert fail.continues_existing_workflow is False
    assert blocked.outcome == "blocked"
    assert blocked.continues_existing_workflow is True
    assert held.outcome == "blocked"
    assert held.continues_existing_workflow is True


def test_missing_employment_context_blocks_a_yes() -> None:
    result = evaluate_hr_legal_eligibility_gate(
        employment_state="preparing",
        reading=_YES,
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=None,
    )
    assert result.outcome == "blocked"
    assert result.continues_existing_workflow is True


def test_unknown_token_is_not_derived_into_the_chain() -> None:
    result = evaluate_hr_legal_eligibility_gate(
        employment_state="preparing",
        reading={**_YES, "stay_basis": "visa", "citizenship_class": "Poland"},
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    assert result.outcome == "blocked"


def test_active_employment_is_outside_the_gate() -> None:
    result = evaluate_hr_legal_eligibility_gate(
        employment_state="active",
        reading=_YES,
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    assert result.applies is False
    assert result.outcome == "not_preparing"


def test_changed_legal_fact_makes_the_recorded_pass_stale() -> None:
    employment = _employment()
    first = evaluate_hr_legal_eligibility_gate(
        employment_state="preparing",
        reading=_YES,
        client_company_id=employment.client_company_id,
        vacancy_id=employment.vacancy_id,
        planned_start=employment.started_on,
    )
    decision = SimpleNamespace(fingerprint=first.fingerprint, outcome="pass")
    assert decision_is_current(
        decision,
        reading=_YES,
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    assert not decision_is_current(
        decision,
        reading={**_YES, "citizenship_class": "third_country"},
        client_company_id="client-1",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )
    assert not decision_is_current(
        decision,
        reading=_YES,
        client_company_id="client-2",
        vacancy_id="vac-1",
        planned_start=date(2026, 11, 2),
    )


class _TermsLookup:
    def one_or_none(self):
        return None


class _Db:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def scalars(self, _statement):
        return _TermsLookup()


def test_record_keeps_provenance_and_leaves_state() -> None:
    employment = _employment()
    when = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    db = _Db()
    result = asyncio.run(
        record_hr_legal_eligibility_gate(
            db,
            tenant_id="tenant-1",
            employment=employment,
            reading=_YES,
            actor_user_id="hr-user-1",
            decided_at=when,
        )
    )
    assert result.outcome == "pass"
    assert employment.state == "preparing"
    row = db.added[0]
    assert row.outcome == "pass"
    assert row.policy_id == "legal_eligibility.v1"
    assert row.actor_user_id == "hr-user-1"
    assert row.decided_at == when
    assert row.citizenship_class == "pl"
    assert row.valid_for_this_employment == "yes"
    assert row.client_company_id == "client-1"
    assert row.vacancy_id == "vac-1"
    assert row.planned_start == date(2026, 11, 2)
    assert not hasattr(row, "evidence")


def test_gate_source_does_not_move_employment_or_ship_the_engine() -> None:
    text = _GATE.read_text(encoding="utf-8")
    assert "state = \"active\"" not in text
    assert ".state =" not in text
    assert "eu_member" not in text
    assert "WorkforceEmployment(" not in text
    assert not (_REPO_ROOT / "backend" / "app" / "reference" / "legal_eligibility.py").exists()
