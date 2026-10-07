"""Employment Persistence Schema storage proofs.

Accepted handoff does not create an Employment. These tests cover the
backfill, the cardinality, and the fact that relationship columns no
longer live on WorkforceEmployee.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import create_engine

from backend.app.models.hr_employment import Employment
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.reference.employment_persistence import (
    LEGACY_EMPLOYEE_COLUMNS,
    apply_employment_backfill,
    backfill_state,
)

_APP = Path(__file__).resolve().parents[2] / "app"
_READ_RE = re.compile(
    r"(?<![\w])(?:employee|emp)\.(?:hire_date|termination_date|company_id|"
    r"vacancy_id|recruiter_user_id|handoff_at|handoff_by_user_id|candidate_snapshot|"
    r"probation_end)\b"
)
_META_RE = re.compile(r"""meta(?:\.get\(|\[)\s*["']internal_hr_handoff_id["']""")


def test_backfill_state_is_deterministic() -> None:
    assert "hire_date" not in backfill_state.__code__.co_varnames
    assert backfill_state("onboarding", None) == "preparing"
    assert backfill_state("", None) == "preparing"
    for status in (
        "active",
        "on_sick_leave",
        "on_vacation",
        "on_leave",
        "suspended",
        "contract_ending",
    ):
        assert backfill_state(status, None) == "active"
    for status in ("terminated", "returned", "returned_to_recruitment"):
        assert backfill_state(status, None) == "ended"
    assert backfill_state("active", date(2026, 2, 1)) == "ended"


def test_existing_employee_backfills_one_employment_and_attaches_cards() -> None:
    engine = create_engine("sqlite://")
    meta = sa.MetaData()
    employees = sa.Table(
        "workforce_employees",
        meta,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32)),
        sa.Column("company_id", sa.String(36)),
        sa.Column("vacancy_id", sa.String(36)),
        sa.Column("recruiter_user_id", sa.String(36)),
        sa.Column("hire_date", sa.Date()),
        sa.Column("termination_date", sa.Date()),
        sa.Column("probation_end", sa.Date()),
        sa.Column("handoff_at", sa.DateTime()),
        sa.Column("handoff_by_user_id", sa.String(36)),
        sa.Column("candidate_snapshot", sa.JSON()),
        sa.Column("meta", sa.JSON()),
    )
    hr = sa.Table(
        "hr_employments",
        meta,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("client_company_id", sa.String(36)),
        sa.Column("started_on", sa.Date()),
        sa.Column("ended_on", sa.Date()),
        sa.Column("vacancy_id", sa.String(36)),
        sa.Column("recruiter_user_id", sa.String(36)),
        sa.Column("handoff_at", sa.DateTime()),
        sa.Column("handoff_by_user_id", sa.String(36)),
        sa.Column("handoff_id", sa.String(36)),
        sa.Column("candidate_snapshot", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    cards = sa.Table(
        "workforce_employments",
        meta,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("employment_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("probation_end", sa.Date()),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("meta", sa.JSON()),
    )
    meta.create_all(engine)

    hired = date(2026, 3, 1)
    snapshot = {"first_name": "Jan", "citizenship": "UA"}
    with engine.begin() as bind:
        bind.execute(
            employees.insert(),
            [
                {
                    "id": "e-active",
                    "tenant_id": "t1",
                    "status": "active",
                    "company_id": "client-1",
                    "vacancy_id": "vac-1",
                    "recruiter_user_id": "user-1",
                    "hire_date": hired,
                    "termination_date": None,
                    "probation_end": date(2026, 6, 1),
                    "handoff_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
                    "handoff_by_user_id": "user-2",
                    "candidate_snapshot": snapshot,
                    "meta": {"internal_hr_handoff_id": "h-1", "keep": "yes"},
                },
                {
                    "id": "e-prep",
                    "tenant_id": "t1",
                    "status": "onboarding",
                    "company_id": None,
                    "vacancy_id": None,
                    "recruiter_user_id": None,
                    "hire_date": hired,
                    "termination_date": None,
                    "probation_end": None,
                    "handoff_at": None,
                    "handoff_by_user_id": None,
                    "candidate_snapshot": None,
                    "meta": {},
                },
                {
                    "id": "e-ended",
                    "tenant_id": "t1",
                    "status": "active",
                    "company_id": None,
                    "vacancy_id": None,
                    "recruiter_user_id": None,
                    "hire_date": None,
                    "termination_date": date(2026, 4, 1),
                    "probation_end": None,
                    "handoff_at": None,
                    "handoff_by_user_id": None,
                    "candidate_snapshot": None,
                    "meta": None,
                },
            ],
        )
        bind.execute(
            cards.insert(),
            [
                {
                    "id": "card-old",
                    "employee_id": "e-active",
                    "employment_id": None,
                    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "probation_end": None,
                    "lifecycle_status": "terminated",
                    "meta": {"source": "manual"},
                },
                {
                    "id": "card-new",
                    "employee_id": "e-active",
                    "employment_id": None,
                    "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                    "probation_end": None,
                    "lifecycle_status": "issued",
                    "meta": {"source": "auto_bundle"},
                },
            ],
        )
        apply_employment_backfill(bind)

        rows = list(bind.execute(sa.select(hr).where(hr.c.employee_id == "e-active")).mappings())
        assert len(rows) == 1
        employment = rows[0]
        assert employment["state"] == "active"
        assert employment["client_company_id"] == "client-1"
        assert employment["started_on"] == hired
        assert employment["ended_on"] is None
        assert employment["vacancy_id"] == "vac-1"
        assert employment["recruiter_user_id"] == "user-1"
        assert employment["handoff_id"] == "h-1"
        stored = employment["candidate_snapshot"]
        if isinstance(stored, str):
            stored = json.loads(stored)
        assert stored["first_name"] == "Jan"

        attached = list(
            bind.execute(sa.select(cards).where(cards.c.employee_id == "e-active")).mappings()
        )
        assert {row["employment_id"] for row in attached} == {employment["id"]}
        newest = next(row for row in attached if row["id"] == "card-new")
        assert newest["probation_end"] == date(2026, 6, 1)
        assert newest["lifecycle_status"] == "issued"

        preparing = list(bind.execute(sa.select(hr).where(hr.c.employee_id == "e-prep")).mappings())
        assert len(preparing) == 1
        assert preparing[0]["state"] == "preparing"
        ended = list(bind.execute(sa.select(hr).where(hr.c.employee_id == "e-ended")).mappings())
        assert len(ended) == 1
        assert ended[0]["state"] == "ended"

        kept = bind.execute(sa.select(employees.c.meta).where(employees.c.id == "e-active")).scalar_one()
        if isinstance(kept, str):
            kept = json.loads(kept)
        assert "internal_hr_handoff_id" not in (kept or {})
        assert kept["keep"] == "yes"

        bind.execute(
            hr.insert(),
            [
                {
                    "id": "rel-1",
                    "tenant_id": "t1",
                    "employee_id": "e-new",
                    "state": "preparing",
                    "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
                    "updated_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
                },
                {
                    "id": "rel-2",
                    "tenant_id": "t1",
                    "employee_id": "e-new",
                    "state": "active",
                    "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
                    "updated_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
                },
            ],
        )
        several = list(bind.execute(sa.select(hr.c.id).where(hr.c.employee_id == "e-new")).scalars())
        assert set(several) == {"rel-1", "rel-2"}
        bind.execute(
            cards.update().where(cards.c.id == "card-new").values(lifecycle_status="signed")
        )
        state_after = bind.execute(sa.select(hr.c.state).where(hr.c.id == employment["id"])).scalar_one()
        assert state_after == "active"


def test_model_drops_legacy_employee_facts_and_allows_many_employments() -> None:
    names = {column.name for column in WorkforceEmployee.__table__.columns}
    assert set(LEGACY_EMPLOYEE_COLUMNS).isdisjoint(names)
    assert WorkforceEmployment.__table__.c.employment_id.nullable is False
    unique_on_employee = [
        constraint
        for constraint in Employment.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
        and {column.name for column in constraint.columns} == {"employee_id"}
    ]
    assert unique_on_employee == []
    for index in Employment.__table__.indexes:
        column_names = [column.name for column in index.columns]
        assert not (index.unique and column_names == ["employee_id"])

    employment = Employment(id="rel", tenant_id="t", employee_id="e", state="active")
    card = WorkforceEmployment(
        id="card",
        tenant_id="t",
        employee_id="e",
        employment_id=employment.id,
        lifecycle_status="issued",
    )
    card.lifecycle_status = "terminated"
    assert employment.state == "active"


def test_runtime_does_not_read_employment_facts_from_the_employee() -> None:
    offenders: list[str] = []
    for path in _APP.rglob("*.py"):
        if path.name == "employment_persistence.py":
            continue
        text = path.read_text(encoding="utf-8")
        for match in _READ_RE.finditer(text):
            offenders.append(f"{path}:{match.group(0)}")
        for match in _META_RE.finditer(text):
            offenders.append(f"{path}:{match.group(0)}")
    assert offenders == []
