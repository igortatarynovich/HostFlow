"""Ready to Start appends a decision and activates only a current pass.

The four inputs stay the canonical readings. A stale pass does not move
Employment, and an older decision is not rewritten.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import HrEmploymentRequirement
from backend.app.models.hr_employment_terms import HrEmploymentTerms
from backend.app.models.hr_legal_eligibility_gate import HrLegalEligibilityGateDecision
from backend.app.models.hr_ready_to_start import HrReadyToStartDecision
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.services.employment_terms_runtime import (
    EmploymentTermsConfirmation,
    confirm_employment_terms,
)
from backend.app.services.hr_legal_eligibility_gate import chain_from_reading, reading_fingerprint
from backend.app.services.pre_employment_requirements_runtime import (
    RequirementDefinition,
    materialize_pre_employment_requirements,
    satisfy_pre_employment_requirement,
)
from backend.app.services.ready_to_start_runtime import (
    activate_employment,
    record_ready_to_start,
)

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "alembic"
    / "versions"
    / "202610070001_hr_ready_to_start.py"
)
_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "specs"
    / "architecture"
    / "employee-record-employment-lifecycle-contract.md"
)
_RUNTIME = Path(__file__).resolve().parents[2] / "app" / "services" / "ready_to_start_runtime.py"
_REFERENCE = Path(__file__).resolve().parents[2] / "app" / "reference" / "ready_to_start.py"
_YES = {
    "citizenship_class": "pl",
    "stay_basis": "not_required",
    "work_authorization_basis": "not_required",
    "valid_for_this_employment": "yes",
}
_FACTS = {"first_name": "Ada", "last_name": "Nowak"}


def _session() -> Session:
    engine = create_engine("sqlite://")
    for table in (
        Employment.__table__,
        HrLegalEligibilityGateDecision.__table__,
        HrEmploymentTerms.__table__,
        HrEmploymentRequirement.__table__,
        CandidateEvidence.__table__,
        HrReadyToStartDecision.__table__,
        WorkforceEmployment.__table__,
        WorkforceOnboardingTask.__table__,
    ):
        table.create(engine)
    return Session(engine)


def _employment() -> Employment:
    return Employment(
        id="employment-1",
        tenant_id="tenant-1",
        employee_id="employee-1",
        state="preparing",
        client_company_id="client-1",
        vacancy_id="vac-1",
        started_on=date(2026, 11, 2),
    )


def _legal(employment: Employment, *, outcome: str = "pass", decision_id: str = "legal-1") -> None:
    chain = chain_from_reading(_YES)
    context = {
        "client_company_id": employment.client_company_id,
        "vacancy_id": employment.vacancy_id,
        "planned_start": employment.started_on.isoformat() if employment.started_on else None,
    }
    return HrLegalEligibilityGateDecision(
        id=decision_id,
        tenant_id=employment.tenant_id,
        employment_id=employment.id,
        outcome=outcome,
        policy_id="legal_eligibility.v1",
        citizenship_class="pl",
        stay_basis="not_required",
        work_authorization_basis="not_required",
        valid_for_this_employment="yes" if outcome == "pass" else "no",
        client_company_id=employment.client_company_id,
        vacancy_id=employment.vacancy_id,
        planned_start=employment.started_on,
        fingerprint=reading_fingerprint(chain, context),
        actor_user_id="user-1",
        decided_at=datetime(2026, 10, 4, 8, tzinfo=timezone.utc),
    )


def _terms(session: Session, employment: Employment) -> None:
    confirmed = confirm_employment_terms(
        session,
        tenant_id="tenant-1",
        employment=employment,
        confirmation=EmploymentTermsConfirmation(
            position="Driver CE",
            contract_basis="agreed-basis",
            work_time_value=Decimal("1"),
            work_time_unit="fte",
            workplace="Warsaw yard",
            compensation_amount=Decimal("30"),
            compensation_currency="PLN",
            compensation_unit="hour",
            duration="fixed",
            fixed_term_end=date(2027, 3, 1),
            probation_status="none",
            probation_end=None,
        ),
    )
    assert confirmed.accepted is True


def _requirements(session: Session, employment: Employment, *, satisfied: bool) -> None:
    materialized = materialize_pre_employment_requirements(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definitions=[
            RequirementDefinition(
                definition_key="medical",
                policy_id="policy-a",
                policy_version="1",
                applicability="applicable",
                applicability_basis="this hire",
            )
        ],
    )
    assert materialized.accepted is True
    if not satisfied:
        return
    session.add(
        CandidateEvidence(
            id="evidence-1",
            tenant_id="tenant-1",
            candidate_id="candidate-1",
            requirement_code="passport",
            evidence_variant_code="scan",
            status="approved",
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    )
    session.flush()
    linked = satisfy_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="medical",
        evidence_id="evidence-1",
    )
    assert linked.accepted is True


def _record(session: Session, employment: Employment, *, facts: dict | None = None, complete: bool = True, when: datetime):
    return record_ready_to_start(
        session,
        tenant_id="tenant-1",
        employment=employment,
        actor_user_id="user-1",
        legal_reading=_YES,
        employee_facts=_FACTS if facts is None else facts,
        employee_data_complete=complete,
        decided_at=when,
    )


def test_migration_appends_decisions_without_backfill() -> None:
    text = _MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "202610070001_hr_ready_to_start"' in text
    assert 'down_revision: Union[str, None] = "202610060001_hr_employment_requirements"' in text
    assert "No backfill" in text
    assert "INSERT INTO" not in text
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "## Ready to Start Persistence and Activation" in contract
    assert "Schema Gate **PASS**" not in contract
    assert "Runtime Gate **PASS**" not in contract
    source = _RUNTIME.read_text(encoding="utf-8")
    assert "decision_is_current" in source
    assert "evaluate_employment_terms" in source
    assert "evaluate_pre_employment_requirements" in source
    assert "read_employee_data_set" in source
    assert "citizenship_class" not in source
    assert "pesel" not in source
    assert "commit(" not in source
    assert not _REFERENCE.exists()


def test_current_pass_activates_in_the_same_session_and_keeps_history() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.flush()
    session.add(_legal(employment))
    _terms(session, employment)
    _requirements(session, employment, satisfied=False)
    session.commit()

    blocked = _record(session, employment, when=datetime(2026, 10, 4, 9, tzinfo=timezone.utc))
    session.commit()
    assert blocked.accepted is True
    assert blocked.decision is not None
    assert blocked.decision.outcome == "blocked"
    assert "requirements_unresolved:medical" in json.loads(blocked.decision.blocked_reasons)
    assert employment.state == "preparing"
    blocked_id = blocked.decision.id

    _requirements_satisfy = satisfy_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="medical",
        evidence_id="evidence-1",
    )
    assert _requirements_satisfy.accepted is False
    session.add(
        CandidateEvidence(
            id="evidence-1",
            tenant_id="tenant-1",
            candidate_id="candidate-1",
            requirement_code="passport",
            evidence_variant_code="scan",
            status="approved",
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    )
    session.flush()
    linked = satisfy_pre_employment_requirement(
        session,
        tenant_id="tenant-1",
        employment=employment,
        definition_key="medical",
        evidence_id="evidence-1",
    )
    assert linked.accepted is True

    passed = _record(session, employment, when=datetime(2026, 10, 4, 10, tzinfo=timezone.utc))
    session.commit()
    assert passed.decision is not None
    assert passed.decision.outcome == "pass"
    assert passed.decision.blocked_reasons == "[]"
    earlier = session.get(HrReadyToStartDecision, blocked_id)
    assert earlier is not None
    assert earlier.outcome == "blocked"
    assert earlier.id != passed.decision.id
    assert employment.state == "preparing"

    employment.client_company_id = "client-2"
    session.flush()
    stale = activate_employment(
        session,
        tenant_id="tenant-1",
        employment_id=employment.id,
        legal_reading=_YES,
        employee_facts=_FACTS,
        employee_data_complete=True,
    )
    assert stale.activated is False
    assert stale.reason == "stale"
    assert employment.state == "preparing"
    assert session.get(HrReadyToStartDecision, passed.decision.id).outcome == "pass"

    employment.client_company_id = "client-1"
    session.flush()
    activated = activate_employment(
        session,
        tenant_id="tenant-1",
        employment_id=employment.id,
        legal_reading=_YES,
        employee_facts=_FACTS,
        employee_data_complete=True,
    )
    session.commit()
    assert activated.activated is True
    assert employment.state == "active"
    again = activate_employment(
        session,
        tenant_id="tenant-1",
        employment_id=employment.id,
        legal_reading=_YES,
        employee_facts=_FACTS,
        employee_data_complete=True,
    )
    assert again.activated is False
    assert again.reason == "not_preparing"
    assert session.scalar(select(func.count()).select_from(WorkforceEmployment)) == 0
    assert session.scalar(select(func.count()).select_from(WorkforceOnboardingTask)) == 0
    assert session.scalar(select(func.count()).select_from(CandidateEvidence)) == 1


def test_blocked_fail_and_missing_do_not_activate() -> None:
    session = _session()
    employment = _employment()
    session.add(employment)
    session.flush()
    session.add(_legal(employment, outcome="fail"))
    _terms(session, employment)
    _requirements(session, employment, satisfied=True)
    session.commit()

    recorded = _record(session, employment, when=datetime(2026, 10, 4, 11, tzinfo=timezone.utc))
    session.commit()
    assert recorded.decision is not None
    assert recorded.decision.outcome == "blocked"
    assert json.loads(recorded.decision.blocked_reasons) == ["legal_fail"]
    refused = activate_employment(
        session,
        tenant_id="tenant-1",
        employment_id=employment.id,
        legal_reading=_YES,
        employee_facts=_FACTS,
        employee_data_complete=True,
    )
    assert refused.activated is False
    assert refused.reason == "blocked"
    assert employment.state == "preparing"

    bare = _employment()
    bare.id = "employment-2"
    session.add(bare)
    session.commit()
    missing = activate_employment(
        session,
        tenant_id="tenant-1",
        employment_id=bare.id,
        legal_reading=_YES,
        employee_facts=_FACTS,
        employee_data_complete=True,
    )
    assert missing.activated is False
    assert missing.reason == "missing"
    assert bare.state == "preparing"

    no_actor = record_ready_to_start(
        session,
        tenant_id="tenant-1",
        employment=bare,
        actor_user_id=" ",
        legal_reading=_YES,
        employee_facts=_FACTS,
        employee_data_complete=False,
        decided_at=datetime(2026, 10, 4, 12, tzinfo=timezone.utc),
    )
    assert no_actor.accepted is False
    assert no_actor.reason == "actor"
    assert session.scalar(select(func.count()).select_from(HrReadyToStartDecision)) == 1
