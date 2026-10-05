"""HR is the second consumer of requirement_resolution.v1.

The Employment row is resolved again. It does not inherit another
Employment's satisfied, and it does not open a second resolver.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import (
    RESOLUTION_BLOCKING,
    RESOLUTION_SATISFIED,
    RESOLUTION_UNRESOLVED,
    HrEmploymentRequirement,
)
from backend.app.reference.requirement_resolution import resolve_requirements
from backend.app.services.hr_requirement_resolution import (
    apply_hr_requirement_resolution,
    hr_policy_definitions,
    materialize_hr_requirements,
)
from backend.app.services.pre_employment_requirements_runtime import evaluate_pre_employment_requirements
from backend.app.services.ready_to_start_runtime import _requirements_reading


def _session() -> Session:
    engine = create_engine("sqlite://")
    Employment.__table__.create(engine)
    HrEmploymentRequirement.__table__.create(engine)
    CandidateEvidence.__table__.create(engine)
    return Session(engine)


def _employment(employment_id: str) -> Employment:
    return Employment(
        id=employment_id,
        tenant_id="tenant-1",
        employee_id="employee-1",
        state="preparing",
    )


def _evidence(
    evidence_id: str,
    requirement_code: str,
    variant: str,
    *,
    status: str = "approved",
) -> CandidateEvidence:
    return CandidateEvidence(
        id=evidence_id,
        tenant_id="tenant-1",
        candidate_id="candidate-1",
        requirement_code=requirement_code,
        evidence_variant_code=variant,
        status=status,
        created_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )


def _shared_evidence() -> list[dict]:
    return [
        {
            "id": "ev-ce",
            "requirement_code": "ce",
            "evidence_variant_code": "combined_eu_license",
            "status": "approved",
            "document_ids": ["doc-1"],
        },
        {
            "id": "ev-code95",
            "requirement_code": "code95",
            "evidence_variant_code": "combined_eu_license",
            "status": "approved",
            "document_ids": ["doc-1"],
        },
    ]


def _facts(**patch: object) -> dict:
    facts = {
        "licence_issuing_country": "PL",
        "licence_categories": ["CE"],
        "adr_presence": True,
        "tachograph_presence": True,
    }
    facts.update(patch)
    return facts


def _by_key(result) -> dict:
    return {row.definition_key: row for row in result.requirements}


def test_hr_policy_names_ce_and_code95_and_not_a_fact() -> None:
    keys = [row.definition_key for row in hr_policy_definitions()]
    assert keys == [
        "driver_entitlement",
        "professional_qualification",
        "legal_stay_confirmation",
        "labor_market_access",
    ]


def test_handoff_reuses_approved_evidence_on_the_employment_row() -> None:
    recruitment = resolve_requirements(
        [
            {"requirement_code": "ce", "level": "REQUIRED"},
            {"requirement_code": "code95", "level": "REQUIRED"},
        ],
        _facts(),
        _shared_evidence(),
    )
    assert [row["progress"] for row in recruitment] == ["satisfied", "satisfied"]

    session = _session()
    employment = _employment("employment-a")
    session.add_all([employment, _evidence("ev-ce", "ce", "combined_eu_license"), _evidence("ev-code95", "code95", "combined_eu_license")])
    session.commit()

    opened = materialize_hr_requirements(session, tenant_id="tenant-1", employment=employment)
    assert opened.accepted is True
    assert {row.definition_key for row in opened.requirements} == {
        "driver_entitlement",
        "professional_qualification",
        "legal_stay_confirmation",
        "labor_market_access",
    }
    assert {row.resolution for row in opened.requirements} == {RESOLUTION_UNRESOLVED}
    assert employment.state == "preparing"

    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts(),
        evidence=_shared_evidence(),
    )
    assert resolved.accepted is True
    assert resolved.required_set == ()
    rows = _by_key(resolved)
    assert rows["driver_entitlement"].resolution == RESOLUTION_SATISFIED
    assert rows["driver_entitlement"].satisfaction_evidence_id == "ev-ce"
    assert rows["professional_qualification"].satisfaction_evidence_id == "ev-code95"
    assert "passport" not in resolved.required_set
    assert "tachograph_card" not in resolved.required_set
    assert employment.state == "preparing"


def test_new_employment_resolves_again_and_does_not_inherit_satisfied() -> None:
    session = _session()
    first = _employment("employment-a")
    second = _employment("employment-b")
    session.add_all(
        [
            first,
            second,
            _evidence("ev-ce", "ce", "combined_eu_license"),
            _evidence("ev-code95", "code95", "combined_eu_license"),
        ]
    )
    session.commit()
    materialize_hr_requirements(session, tenant_id="tenant-1", employment=first)
    apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=first,
        facts=_facts(),
        evidence=_shared_evidence(),
    )

    opened = materialize_hr_requirements(session, tenant_id="tenant-1", employment=second)
    assert {row.resolution for row in opened.requirements} == {RESOLUTION_UNRESOLVED}
    first_ids = {
        row.id
        for row in session.scalars(
            select(HrEmploymentRequirement).where(HrEmploymentRequirement.employment_id == "employment-a")
        )
    }
    assert {row.id for row in opened.requirements}.isdisjoint(first_ids)

    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=second,
        facts=_facts(),
        evidence=_shared_evidence(),
    )
    rows = _by_key(resolved)
    assert rows["driver_entitlement"].resolution == RESOLUTION_SATISFIED
    assert rows["driver_entitlement"].id not in first_ids
    assert rows["driver_entitlement"].satisfaction_evidence_id == "ev-ce"
    assert resolved.required_set == ()


def test_evidence_that_does_not_fit_the_employment_is_not_satisfied() -> None:
    session = _session()
    employment = _employment("employment-c")
    session.add_all(
        [
            employment,
            _evidence("ev-ce", "ce", "combined_eu_license"),
            _evidence("ev-code95", "code95", "combined_eu_license"),
        ]
    )
    session.commit()
    materialize_hr_requirements(session, tenant_id="tenant-1", employment=employment)
    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts(licence_issuing_country="BY", code95_presence=True),
        evidence=_shared_evidence(),
    )
    rows = _by_key(resolved)
    assert rows["driver_entitlement"].resolution == RESOLUTION_UNRESOLVED
    assert rows["driver_entitlement"].satisfaction_evidence_id is None
    assert rows["professional_qualification"].resolution == RESOLUTION_UNRESOLVED
    assert set(resolved.required_set) == {"driver_license", "driver_qualification_card"}
    assert "passport" not in resolved.required_set
    assert "tachograph_card" not in resolved.required_set
    assert "adr_certificate" not in resolved.required_set


def test_separate_evidence_satisfies_its_own_employment_rows() -> None:
    evidence = [
        {
            "id": "ev-ce",
            "requirement_code": "ce",
            "evidence_variant_code": "separate_license_and_code95",
            "status": "approved",
            "document_ids": ["doc-licence"],
        },
        {
            "id": "ev-code95",
            "requirement_code": "code95",
            "evidence_variant_code": "separate_license_and_code95",
            "status": "approved",
            "document_ids": ["doc-card"],
        },
    ]
    session = _session()
    employment = _employment("employment-separate")
    session.add_all(
        [
            employment,
            _evidence("ev-ce", "ce", "separate_license_and_code95"),
            _evidence("ev-code95", "code95", "separate_license_and_code95"),
        ]
    )
    session.commit()
    materialize_hr_requirements(session, tenant_id="tenant-1", employment=employment)
    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts(licence_issuing_country="BY", code95_presence=True),
        evidence=evidence,
    )
    rows = _by_key(resolved)
    assert rows["driver_entitlement"].resolution == RESOLUTION_SATISFIED
    assert rows["professional_qualification"].resolution == RESOLUTION_SATISFIED
    assert resolved.required_set == ()


def test_under_review_asks_for_no_second_file() -> None:
    evidence = [
        {
            "id": "ev-ce",
            "requirement_code": "ce",
            "evidence_variant_code": "combined_eu_license",
            "status": "pending_review",
            "document_ids": ["doc-1"],
        },
        {
            "id": "ev-code95",
            "requirement_code": "code95",
            "evidence_variant_code": "combined_eu_license",
            "status": "pending_review",
            "document_ids": ["doc-1"],
        },
    ]
    session = _session()
    employment = _employment("employment-review")
    session.add_all([employment, _evidence("ev-ce", "ce", "combined_eu_license", status="pending_review")])
    session.commit()
    materialize_hr_requirements(session, tenant_id="tenant-1", employment=employment)
    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts(),
        evidence=evidence,
    )
    assert resolved.required_set == ()
    assert {row["progress"] for row in resolved.readings if row["definition_key"] in {"driver_entitlement", "professional_qualification"}} == {"under_review"}
    assert {row.resolution for row in resolved.requirements} == {RESOLUTION_UNRESOLVED}


def test_blocking_entitlement_is_stored_on_the_employment_row() -> None:
    session = _session()
    employment = _employment("employment-block")
    session.add(employment)
    session.commit()
    materialize_hr_requirements(session, tenant_id="tenant-1", employment=employment)
    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts(licence_categories=["B"]),
        evidence=[],
    )
    rows = _by_key(resolved)
    assert rows["driver_entitlement"].resolution == RESOLUTION_BLOCKING
    assert rows["driver_entitlement"].blocking_reason == "requirement_resolution.v1"
    entitlement = next(row for row in resolved.readings if row["definition_key"] == "driver_entitlement")
    assert entitlement["document_codes"] == []
    assert rows["professional_qualification"].resolution == RESOLUTION_UNRESOLVED


def test_ready_to_start_reads_the_stored_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    employment = _employment("employment-a")
    session.add_all(
        [
            employment,
            _evidence("ev-ce", "ce", "combined_eu_license"),
            _evidence("ev-code95", "code95", "combined_eu_license"),
        ]
    )
    session.commit()
    materialize_hr_requirements(session, tenant_id="tenant-1", employment=employment)
    apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts(citizenship="PL"),
        evidence=_shared_evidence(),
    )

    def _refuse(*_args, **_kwargs):
        raise AssertionError("resolver")

    monkeypatch.setattr(
        "backend.app.reference.requirement_resolution.resolve_requirement",
        _refuse,
    )
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is True
    reading = _requirements_reading(session, "tenant-1", employment)
    assert reading.result == "pass"
    assert reading.reasons == ()
