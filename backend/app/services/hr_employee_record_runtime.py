"""Load and write the HR employee record through the owners that already exist."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.candidate_evidence import CandidateEvidence, CandidateEvidenceDocument
from backend.app.models.document import Document
from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import HrEmploymentRequirement
from backend.app.models.hr_employment_terms import HrEmploymentTerms
from backend.app.models.hr_legal_eligibility_gate import HrLegalEligibilityGateDecision
from backend.app.models.hr_ready_to_start import HrReadyToStartDecision
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_insurance_profile import WorkforceInsuranceProfile
from backend.app.models.workforce_zus_profile import WorkforceZusProfile
from backend.app.services.candidate_evidence_service import approve_evidence, reject_evidence
from backend.app.services.employment_terms_runtime import (
    EmploymentTermsConfirmation,
    confirm_employment_terms,
)
from backend.app.services.hr_employee_record_projection import (
    RecordWriteRejected,
    apply_column_write,
    apply_employment_write,
    apply_person_write,
    operator_facts_patch,
    project_employee_record,
    write_plan,
)
from backend.app.services.operator_facts_persistence import save_operator_facts
from backend.app.services.workforce_employees import get_employee


def _iso(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _employment_payload(row: Employment) -> dict[str, Any]:
    return {
        "id": row.id,
        "state": row.state,
        "client_company_id": row.client_company_id,
        "vacancy_id": row.vacancy_id,
        "started_on": _iso(row.started_on),
        "ended_on": _iso(row.ended_on),
        "handoff_at": _iso(row.handoff_at),
        "handoff_by_user_id": row.handoff_by_user_id,
        "handoff_id": row.handoff_id,
        "candidate_snapshot": row.candidate_snapshot,
    }


async def _employments(db: AsyncSession, tenant_id: str, employee_id: str) -> list[Employment]:
    res = await db.execute(
        select(Employment)
        .where(Employment.tenant_id == tenant_id, Employment.employee_id == employee_id)
        .order_by(Employment.created_at.desc())
    )
    return list(res.scalars().all())


async def load_hr_employee_record(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    employment_id: str | None = None,
) -> dict[str, Any] | None:
    employee = await get_employee(db, tenant_id, employee_id)
    if employee is None or not employee.candidate_id:
        return None
    employments = await _employments(db, tenant_id, employee_id)
    if not employments:
        return None
    chosen = next((row for row in employments if row.id == employment_id), None) if employment_id else employments[0]
    if chosen is None:
        return None
    candidate = await db.get(Candidate, employee.candidate_id)
    if candidate is None or str(candidate.tenant_id) != tenant_id:
        return None
    personal = candidate.personal_data if isinstance(candidate.personal_data, dict) else {}
    requirements = list(
        (
            await db.execute(
                select(HrEmploymentRequirement)
                .where(
                    HrEmploymentRequirement.tenant_id == tenant_id,
                    HrEmploymentRequirement.employment_id == chosen.id,
                )
                .order_by(HrEmploymentRequirement.definition_key)
            )
        ).scalars().all()
    )
    legal_rows = list(
        (
            await db.execute(
                select(HrLegalEligibilityGateDecision)
                .where(
                    HrLegalEligibilityGateDecision.tenant_id == tenant_id,
                    HrLegalEligibilityGateDecision.employment_id == chosen.id,
                )
                .order_by(HrLegalEligibilityGateDecision.decided_at.desc())
            )
        ).scalars().all()
    )
    ready_rows = list(
        (
            await db.execute(
                select(HrReadyToStartDecision)
                .where(
                    HrReadyToStartDecision.tenant_id == tenant_id,
                    HrReadyToStartDecision.employment_id == chosen.id,
                )
                .order_by(HrReadyToStartDecision.decided_at.desc())
            )
        ).scalars().all()
    )
    terms = (
        await db.execute(
            select(HrEmploymentTerms).where(
                HrEmploymentTerms.tenant_id == tenant_id,
                HrEmploymentTerms.employment_id == chosen.id,
                HrEmploymentTerms.is_current.is_(True),
            )
        )
    ).scalars().first()
    cards = list(
        (
            await db.execute(
                select(WorkforceEmployment).where(
                    WorkforceEmployment.tenant_id == tenant_id,
                    WorkforceEmployment.employment_id == chosen.id,
                )
            )
        ).scalars().all()
    )
    prior = list(
        (
            await db.execute(
                select(CandidateEmployment).where(
                    CandidateEmployment.tenant_id == tenant_id,
                    CandidateEmployment.candidate_id == candidate.id,
                )
            )
        ).scalars().all()
    )
    documents = list(
        (
            await db.execute(
                select(Document.id, Document.doc_type)
                .join(DocumentEntityLink, DocumentEntityLink.document_id == Document.id)
                .where(
                    DocumentEntityLink.tenant_id == tenant_id,
                    DocumentEntityLink.linked_entity_type == "candidate",
                    DocumentEntityLink.linked_entity_id == candidate.id,
                    DocumentEntityLink.relation_type == "primary",
                )
            )
        ).all()
    )
    evidence_rows = list(
        (
            await db.execute(
                select(CandidateEvidence).where(
                    CandidateEvidence.tenant_id == tenant_id,
                    CandidateEvidence.candidate_id == candidate.id,
                )
            )
        ).scalars().all()
    )
    evidence_ids = [row.id for row in evidence_rows]
    links: list[CandidateEvidenceDocument] = []
    if evidence_ids:
        links = list(
            (
                await db.execute(
                    select(CandidateEvidenceDocument).where(
                        CandidateEvidenceDocument.candidate_evidence_id.in_(evidence_ids)
                    )
                )
            ).scalars().all()
        )
    doc_types = {str(row.id): row.doc_type for row in documents}
    if links:
        missing = [link.document_id for link in links if link.document_id not in doc_types]
        if missing:
            extra = (
                await db.execute(select(Document.id, Document.doc_type).where(Document.id.in_(missing)))
            ).all()
            doc_types.update({str(row.id): row.doc_type for row in extra})
    codes_by_evidence: dict[str, list[str]] = {}
    for link in links:
        codes_by_evidence.setdefault(link.candidate_evidence_id, [])
        code = doc_types.get(link.document_id)
        if code:
            codes_by_evidence[link.candidate_evidence_id].append(code)
    insurance = (
        await db.execute(
            select(WorkforceInsuranceProfile).where(
                WorkforceInsuranceProfile.tenant_id == tenant_id,
                WorkforceInsuranceProfile.employee_id == employee.id,
            )
        )
    ).scalars().first()
    zus = (
        await db.execute(
            select(WorkforceZusProfile).where(
                WorkforceZusProfile.tenant_id == tenant_id,
                WorkforceZusProfile.employee_id == employee.id,
            )
        )
    ).scalars().first()
    latest_legal = legal_rows[0] if legal_rows else None
    latest_ready = ready_rows[0] if ready_rows else None
    return project_employee_record(
        {
            "employment_id": chosen.id,
            "candidate_id": candidate.id,
            "employee_id": employee.id,
            "employments": [{"id": row.id, "state": row.state} for row in employments],
            "person": {
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "first_name_latin": candidate.first_name_latin,
                "last_name_latin": candidate.last_name_latin,
                "phone": candidate.phone,
                "phone_country_code": candidate.phone_country_code,
                "email": candidate.email,
                "languages": candidate.languages or [],
                "display_name": employee.display_name,
            },
            "personal_data": personal,
            "employment": _employment_payload(chosen),
            "requirements": [
                {
                    "definition_key": row.definition_key,
                    "applicability": row.applicability,
                    "resolution": row.resolution,
                }
                for row in requirements
            ],
            "legal_decision": None
            if latest_legal is None
            else {
                "id": latest_legal.id,
                "outcome": latest_legal.outcome,
                "valid_for_this_employment": latest_legal.valid_for_this_employment,
                "decided_at": _iso(latest_legal.decided_at),
            },
            "legal_decisions": [
                {
                    "id": row.id,
                    "outcome": row.outcome,
                    "valid_for_this_employment": row.valid_for_this_employment,
                    "decided_at": _iso(row.decided_at),
                }
                for row in legal_rows
            ],
            "ready_to_start": None
            if latest_ready is None
            else {"id": latest_ready.id, "outcome": latest_ready.outcome, "decided_at": _iso(latest_ready.decided_at)},
            "ready_decisions": [
                {"id": row.id, "outcome": row.outcome, "decided_at": _iso(row.decided_at)}
                for row in ready_rows
            ],
            "terms": None
            if terms is None
            else {"id": terms.id, "position": terms.position, "contract_basis": terms.contract_basis},
            "contract_cards": [
                {"id": row.id, "contract_type": row.contract_type, "lifecycle_status": row.lifecycle_status}
                for row in cards
            ],
            "prior_jobs": [
                {"id": row.id, "employer_name": row.employer_name, "position": row.position}
                for row in prior
            ],
            "documents": [{"id": row.id, "doc_type": row.doc_type} for row in documents],
            "evidence": [
                {
                    "id": row.id,
                    "requirement_code": row.requirement_code,
                    "evidence_variant_code": row.evidence_variant_code,
                    "status": row.status,
                    "document_codes": codes_by_evidence.get(row.id, []),
                }
                for row in evidence_rows
            ],
            "insurance": None
            if insurance is None
            else {"id": insurance.id, "status": insurance.status},
            "zus": None if zus is None else {"id": zus.id, "registration_status": zus.registration_status},
        }
    )


async def write_hr_employee_record(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    employment_id: str,
    address: str,
    value: Any,
    actor_user_id: str,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    plan = write_plan(address)
    employee = await get_employee(db, tenant_id, employee_id)
    if employee is None or not employee.candidate_id:
        raise RecordWriteRejected("employee")
    employment = await db.get(Employment, employment_id)
    if employment is None or str(employment.tenant_id) != tenant_id or employment.employee_id != employee.id:
        raise RecordWriteRejected("employment")
    candidate = await db.get(Candidate, employee.candidate_id)
    if candidate is None:
        raise RecordWriteRejected("candidate")
    if plan["kind"] == "operator_facts":
        await save_operator_facts(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
            patch=operator_facts_patch(address, value),
            actor_user_id=actor_user_id,
            employment_id=employment_id,
        )
    elif plan["kind"] == "personal_data":
        personal = candidate.personal_data if isinstance(candidate.personal_data, dict) else {}
        candidate.personal_data = apply_person_write(
            personal,
            address=address,
            value=value,
            employment_id=employment_id,
        )
        flag_modified(candidate, "personal_data")
        await db.commit()
    elif plan["kind"] == "candidate_columns":
        for column, column_value in apply_column_write(address, value).items():
            setattr(candidate, column, column_value)
        await db.commit()
    elif plan["kind"] == "employment":
        apply_employment_write(employment, address=address, value=value)
        await db.commit()
    elif plan["kind"] == "employment_terms":
        if not isinstance(value, dict):
            raise RecordWriteRejected("employment.terms")

        def _confirm(sync_session: Any) -> Any:
            row = sync_session.get(Employment, employment_id)
            if row is None:
                return None
            confirmation = EmploymentTermsConfirmation(
                position=value.get("position"),
                contract_basis=value.get("contract_basis"),
                work_time_value=_decimal(value.get("work_time_value")),
                work_time_unit=value.get("work_time_unit"),
                workplace=value.get("workplace"),
                compensation_amount=_decimal(value.get("compensation_amount")),
                compensation_currency=value.get("compensation_currency"),
                compensation_unit=value.get("compensation_unit"),
                duration=value.get("duration"),
                fixed_term_end=_date(value.get("fixed_term_end")),
                probation_status=value.get("probation_status"),
                probation_end=_date(value.get("probation_end")),
                default_vacancy_id=value.get("default_vacancy_id"),
            )
            return confirm_employment_terms(
                sync_session,
                tenant_id=tenant_id,
                employment=row,
                confirmation=confirmation,
            )

        result = await db.run_sync(_confirm)
        if result is None or not result.accepted:
            raise RecordWriteRejected(getattr(result, "reason", None) or "employment.terms")
        await db.commit()
    elif plan["kind"] == "candidate_evidence":
        if not evidence_id:
            raise RecordWriteRejected("evidence_id")
        if value == "approved":
            await approve_evidence(db, tenant_id=tenant_id, evidence_id=evidence_id, user_id=actor_user_id)
        elif value == "rejected":
            await reject_evidence(
                db,
                tenant_id=tenant_id,
                evidence_id=evidence_id,
                user_id=actor_user_id,
                reason=None,
            )
        else:
            raise RecordWriteRejected("evidence.status")
        await db.commit()
    else:
        raise RecordWriteRejected(address)
    loaded = await load_hr_employee_record(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        employment_id=employment_id,
    )
    if loaded is None:
        raise RecordWriteRejected("employee")
    return loaded
