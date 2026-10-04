"""Policy becomes Employment instances. A later policy does not rewrite them.

Resolution is the id the caller names. Employee history does not satisfy
a row. Completeness does not move Employment.state.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.document import Document
from backend.app.models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
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
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.services.pre_employment_requirements_runtime import (
    RequirementDefinition,
    block_pre_employment_requirement,
    evaluate_pre_employment_requirements,
    materialize_pre_employment_requirements,
    satisfy_pre_employment_requirement,
    waive_pre_employment_requirement,
)


def _session() -> Session:
    engine = create_engine("sqlite://")
    Employment.__table__.create(engine)
    HrEmploymentRequirement.__table__.create(engine)
    CandidateEvidence.__table__.create(engine)
    Document.__table__.create(engine)
    WorkforceEmployment.__table__.create(engine)
    WorkforceOnboardingTask.__table__.create(engine)
    return Session(engine)


def _employment(employment_id: str = "employment-1", employee_id: str = "employee-1") -> Employment:
    return Employment(
        id=employment_id,
        tenant_id="tenant-1",
        employee_id=employee_id,
        state="preparing",
    )


def _definition(key: str = "medical", **overrides) -> RequirementDefinition:
    values = dict(
        definition_key=key,
        policy_id="policy-a",
        policy_version="1",
        applicability=APPLICABILITY_APPLICABLE,
        applicability_basis="hire context v1",
    )
    values.update(overrides)
    return RequirementDefinition(**values)


def _evidence(evidence_id: str = "evidence-1") -> CandidateEvidence:
    return CandidateEvidence(
        id=evidence_id,
        tenant_id="tenant-1",
        candidate_id="candidate-1",
        requirement_code="passport",
        evidence_variant_code="scan",
        status="approved",
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )


def _document(document_id: str = "document-1") -> Document:
    return Document(
        id=document_id,
        tenant_id="tenant-1",
        doc_type="passport",
        kind=DocumentKind.driver,
        status=DocumentStatus.missing,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.none,
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )


def test_materialize_is_stable_and_resolution_is_explicit() -> None:
    session = _session()
    employment = _employment()
    other = _employment(employment_id="employment-2", employee_id="employee-1")
    session.add_all([employment, other, _evidence(), _document()])
    session.commit()
    state = employment.state
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is False

    empty = materialize_pre_employment_requirements(
        session, tenant_id="tenant-1", employment=employment, definitions=[]
    )
    assert empty.accepted is False
    assert empty.reason == "undefined"
    assert session.scalars(select(HrEmploymentRequirement)).all() == []

    first = materialize_pre_employment_requirements(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definitions=[
            _definition("medical"),
            _definition("outside", applicability=APPLICABILITY_NOT_APPLICABLE, applicability_basis="not this hire"),
        ],
    )
    session.commit()
    assert first.accepted is True
    by_key = {row.definition_key: row for row in first.requirements}
    assert by_key["medical"].resolution == RESOLUTION_UNRESOLVED
    assert by_key["medical"].satisfaction_evidence_id is None
    assert by_key["outside"].applicability == APPLICABILITY_NOT_APPLICABLE
    assert by_key["outside"].resolution is None
    assert by_key["medical"].policy_version == "1"
    assert employment.state == state
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is False

    drifted = materialize_pre_employment_requirements(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definitions=[
            _definition("medical", policy_version="2", applicability=APPLICABILITY_NOT_APPLICABLE),
            _definition("new-key", policy_version="2"),
        ],
    )
    session.commit()
    assert drifted.accepted is True
    assert {row.definition_key for row in drifted.requirements} == {"medical", "outside"}
    medical = session.scalars(
        select(HrEmploymentRequirement).where(
            HrEmploymentRequirement.employment_id == "employment-1",
            HrEmploymentRequirement.definition_key == "medical",
        )
    ).one()
    assert medical.policy_version == "1"
    assert medical.applicability == APPLICABILITY_APPLICABLE
    assert medical.resolution == RESOLUTION_UNRESOLVED
    assert medical.applicability_basis == "hire context v1"
    assert session.scalar(select(func.count()).select_from(HrEmploymentRequirement)) == 2

    other_set = materialize_pre_employment_requirements(
        session,
        tenant_id="tenant-1",
        employment=other,
        definitions=[_definition("medical")],
    )
    session.commit()
    assert other_set.accepted is True
    assert other_set.requirements[0].employment_id == "employment-2"
    assert other_set.requirements[0].id != medical.id
    assert medical.resolution == RESOLUTION_UNRESOLVED

    refused = satisfy_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="outside",
        evidence_id="evidence-1",
    )
    assert refused.accepted is False
    assert refused.reason == "not_applicable"
    outside = session.scalars(
        select(HrEmploymentRequirement).where(HrEmploymentRequirement.definition_key == "outside")
    ).one()
    assert outside.resolution is None

    missing = satisfy_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="medical",
        evidence_id="missing-evidence",
    )
    assert missing.accepted is False
    assert missing.reason == "missing_evidence"
    assert medical.resolution == RESOLUTION_UNRESOLVED

    blocked = block_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="medical",
        blocking_reason="exam refused",
    )
    session.commit()
    assert blocked.accepted is True
    assert blocked.requirement is not None
    assert blocked.requirement.resolution == RESOLUTION_BLOCKING
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is False
    assert other_set.requirements[0].resolution == RESOLUTION_UNRESOLVED

    satisfied = satisfy_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="medical",
        evidence_id="evidence-1",
        document_id="document-1",
    )
    session.commit()
    assert satisfied.accepted is True
    assert satisfied.requirement is not None
    assert satisfied.requirement.resolution == RESOLUTION_SATISFIED
    assert satisfied.requirement.satisfaction_evidence_id == "evidence-1"
    assert satisfied.requirement.satisfaction_document_id == "document-1"
    assert satisfied.requirement.blocking_reason is None
    assert session.scalar(select(func.count()).select_from(CandidateEvidence)) == 1
    assert other_set.requirements[0].resolution == RESOLUTION_UNRESOLVED
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is True
    assert employment.state == "preparing"
    assert session.scalar(select(func.count()).select_from(WorkforceEmployment)) == 0
    assert session.scalar(select(func.count()).select_from(WorkforceOnboardingTask)) == 0


def test_blocking_can_be_waived_and_a_closed_row_stays() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.commit()
    materialize_pre_employment_requirements(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definitions=[_definition("ack"), _definition("quiet", applicability=APPLICABILITY_NOT_APPLICABLE)],
    )
    session.commit()
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is False

    blank = waive_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="ack",
        actor_id="user-1",
        waiver_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
        reason="  ",
    )
    assert blank.accepted is False
    assert blank.reason == "waiver"

    blocked = block_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="ack",
        blocking_reason="form rejected",
    )
    session.commit()
    assert blocked.requirement is not None
    assert blocked.requirement.resolution == RESOLUTION_BLOCKING

    waived = waive_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="ack",
        actor_id="user-1",
        waiver_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
        reason="operator lifted it",
    )
    session.commit()
    assert waived.accepted is True
    assert waived.requirement is not None
    assert waived.requirement.resolution == RESOLUTION_WAIVED
    assert waived.requirement.waiver_actor_id == "user-1"
    assert waived.requirement.blocking_reason is None
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is True

    other_waiver = waive_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="ack",
        actor_id="user-2",
        waiver_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        reason="a different reason",
    )
    assert other_waiver.accepted is False
    assert other_waiver.reason == "closed"
    assert waived.requirement.waiver_actor_id == "user-1"
    assert waived.requirement.waiver_reason == "operator lifted it"

    again = block_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="ack",
        blocking_reason="form rejected",
    )
    assert again.accepted is False
    assert again.reason == "closed"
    assert waived.requirement.resolution == RESOLUTION_WAIVED
    assert employment.state == "preparing"


def test_active_employment_is_not_materialized() -> None:
    session = _session()
    employment = _employment()
    employment.state = "active"
    session.add(employment)
    session.commit()
    result = materialize_pre_employment_requirements(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definitions=[_definition()],
    )
    assert result.accepted is False
    assert result.reason == "not_preparing"
    assert session.scalars(select(HrEmploymentRequirement)).all() == []
    assert evaluate_pre_employment_requirements(session, tenant_id="tenant-1", employment=employment) is False
    assert employment.state == "active"
