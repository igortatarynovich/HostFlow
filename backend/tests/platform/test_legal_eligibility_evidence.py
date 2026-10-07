"""Belarus legal eligibility through the shared resolver.

The stay fact selects a requirement and an accepted variant. It does not
write the required set. A later basis does not inherit the previous
satisfaction.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import (
    APPLICABILITY_NOT_APPLICABLE,
    RESOLUTION_BLOCKING,
    RESOLUTION_SATISFIED,
    RESOLUTION_UNRESOLVED,
    HrEmploymentRequirement,
)
from backend.app.reference.legal_eligibility_evidence import stay_accepted_evidence
from backend.app.services.hr_requirement_resolution import (
    apply_hr_requirement_resolution,
    hr_policy_definitions,
    materialize_hr_requirements,
)
from backend.app.services.pre_employment_requirements_runtime import evaluate_pre_employment_requirements


def _session() -> Session:
    engine = create_engine("sqlite://")
    Employment.__table__.create(engine)
    HrEmploymentRequirement.__table__.create(engine)
    CandidateEvidence.__table__.create(engine)
    return Session(engine)


def _employment(employment_id: str = "employment-a") -> Employment:
    return Employment(
        id=employment_id,
        tenant_id="tenant-1",
        employee_id="employee-1",
        state="preparing",
    )


def _stored_evidence(evidence_id: str, requirement_code: str, variant: str) -> CandidateEvidence:
    return CandidateEvidence(
        id=evidence_id,
        tenant_id="tenant-1",
        candidate_id="candidate-1",
        requirement_code=requirement_code,
        evidence_variant_code=variant,
        status="approved",
        created_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )


def _facts(employment_id: str, *, stay: str | None, procedure: str | None = "employer_declaration", valid_no: bool = False) -> dict:
    work = {
        "work_authorization_basis": "separate_required" if procedure else None,
        "procedure_type": procedure,
        "valid_no": valid_no,
    }
    if procedure is None and not valid_no:
        work = {"work_authorization_basis": None, "procedure_type": None, "valid_no": False}
    return {
        "citizenship": "BY",
        "stay_basis": stay,
        "employments": {employment_id: work},
    }


def _legal_definitions():
    wanted = {"legal_stay_confirmation", "labor_market_access"}
    return [row for row in hr_policy_definitions() if row.definition_key in wanted]


def _open(session: Session, employment: Employment) -> None:
    materialize_hr_requirements(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definitions=_legal_definitions(),
    )


def test_karta_pobytu_selects_evidence_and_does_not_write_the_required_set() -> None:
    spec = stay_accepted_evidence("karta_pobytu")
    assert spec["variant"] == "residence_card_and_decision"
    assert spec["document_codes"] == ("residence_card", "temporary_residence_decision")
    assert "required_set" not in spec


def test_by_declaration_asks_card_decision_and_declaration_then_satisfies() -> None:
    session = _session()
    employment = _employment()
    session.add_all(
        [
            employment,
            _stored_evidence("ev-stay", "legal_stay_confirmation", "residence_card_and_decision"),
            _stored_evidence("ev-work", "labor_market_access", "employer_declaration"),
        ]
    )
    session.commit()
    _open(session, employment)
    facts = _facts("employment-a", stay="karta_pobytu")
    missing = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=facts,
        evidence=[],
    )
    assert set(missing.required_set) == {
        "residence_card",
        "temporary_residence_decision",
        "work_permit",
    }
    assert "passport" not in missing.required_set
    assert "tachograph_card" not in missing.required_set

    approved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=facts,
        evidence=[
            {
                "id": "ev-stay",
                "requirement_code": "legal_stay_confirmation",
                "evidence_variant_code": "residence_card_and_decision",
                "status": "approved",
                "document_ids": ["doc-card", "doc-decision"],
                "document_codes": ["residence_card", "temporary_residence_decision"],
            },
            {
                "id": "ev-work",
                "requirement_code": "labor_market_access",
                "evidence_variant_code": "employer_declaration",
                "status": "approved",
                "document_ids": ["doc-declaration"],
                "document_codes": ["work_permit"],
            },
        ],
    )
    by_key = {row.definition_key: row for row in approved.requirements}
    assert by_key["legal_stay_confirmation"].resolution == RESOLUTION_SATISFIED
    assert by_key["legal_stay_confirmation"].satisfaction_evidence_id == "ev-stay"
    assert by_key["labor_market_access"].satisfaction_evidence_id == "ev-work"
    assert approved.required_set == ()
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is True


def test_visa_d_invalidates_the_card_resolution_and_keeps_the_old_evidence() -> None:
    session = _session()
    employment = _employment()
    session.add_all(
        [
            employment,
            _stored_evidence("ev-stay", "legal_stay_confirmation", "residence_card_and_decision"),
            _stored_evidence("ev-work", "labor_market_access", "employer_declaration"),
        ]
    )
    session.commit()
    _open(session, employment)
    evidence = [
        {
            "id": "ev-stay",
            "requirement_code": "legal_stay_confirmation",
            "evidence_variant_code": "residence_card_and_decision",
            "status": "approved",
            "document_ids": ["doc-card", "doc-decision"],
            "document_codes": ["residence_card", "temporary_residence_decision"],
        },
        {
            "id": "ev-work",
            "requirement_code": "labor_market_access",
            "evidence_variant_code": "employer_declaration",
            "status": "approved",
            "document_ids": ["doc-declaration"],
            "document_codes": ["work_permit"],
        },
    ]
    apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts("employment-a", stay="karta_pobytu"),
        evidence=evidence,
    )
    changed = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts("employment-a", stay="visa_d"),
        evidence=evidence,
    )
    by_key = {row.definition_key: row for row in changed.requirements}
    assert by_key["legal_stay_confirmation"].resolution == RESOLUTION_UNRESOLVED
    assert by_key["legal_stay_confirmation"].satisfaction_evidence_id is None
    assert by_key["labor_market_access"].resolution == RESOLUTION_SATISFIED
    assert set(changed.required_set) == {"visa"}
    assert "residence_card" not in changed.required_set
    assert "temporary_residence_decision" not in changed.required_set
    still_there = session.scalars(select(CandidateEvidence).where(CandidateEvidence.id == "ev-stay")).one()
    assert still_there.evidence_variant_code == "residence_card_and_decision"


def test_unknown_stay_asks_for_no_document_and_none_blocks() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.commit()
    _open(session, employment)
    unknown = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts("employment-a", stay=None, procedure=None),
        evidence=[],
    )
    stay = next(row for row in unknown.readings if row["definition_key"] == "legal_stay_confirmation")
    assert stay["progress"] == "needs_input"
    assert unknown.required_set == ()

    blocked = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts("employment-a", stay="none", procedure=None),
        evidence=[],
    )
    stay = next(row for row in blocked.readings if row["definition_key"] == "legal_stay_confirmation")
    assert stay["progress"] == "blocking"
    stored = {row.definition_key: row for row in blocked.requirements}
    assert stored["legal_stay_confirmation"].resolution == RESOLUTION_BLOCKING
    assert "residence_card" not in blocked.required_set
    assert "visa" not in blocked.required_set


def test_included_in_stay_asks_for_no_work_document() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.commit()
    _open(session, employment)
    facts = {
        "citizenship": "BY",
        "stay_basis": "karta_pobytu",
        "employments": {
            "employment-a": {
                "work_authorization_basis": "included_in_stay",
                "procedure_type": None,
                "valid_no": False,
            }
        },
    }
    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=facts,
        evidence=[],
    )
    by_key = {row.definition_key: row for row in resolved.requirements}
    assert by_key["labor_market_access"].applicability == APPLICABILITY_NOT_APPLICABLE
    assert set(resolved.required_set) == {"residence_card", "temporary_residence_decision"}
    assert "work_permit" not in resolved.required_set


def test_no_right_to_work_blocks_without_a_work_file() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.commit()
    _open(session, employment)
    resolved = apply_hr_requirement_resolution(
        session,
        tenant_id="tenant-1",
        employment=employment,
        facts=_facts("employment-a", stay="karta_pobytu", valid_no=True),
        evidence=[],
    )
    by_key = {row.definition_key: row for row in resolved.requirements}
    assert by_key["labor_market_access"].resolution == RESOLUTION_BLOCKING
    assert "work_permit" not in resolved.required_set
