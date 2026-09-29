"""Recruitment emit of ``ready_for_employment.v1`` on internal-HR transfer.

The operator action stays ``create_handoff``. This writer freezes the boundary
manifest from live candidate, vacancy, and document refs. It does not accept
the handoff, mint an employee, or copy files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.vacancy import Vacancy
from backend.app.modules.documents.crud import list_candidate_documents
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    validate_ready_for_employment_package_v1,
)
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_lead_intent,
    get_application_for_handoff,
)

MANIFEST_PAYLOAD_KEY = "ready_for_employment_v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _extra(candidate: Candidate) -> dict[str, Any]:
    raw = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return raw if isinstance(raw, dict) else {}


async def build_ready_for_employment_manifest(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    candidate: Candidate,
    actor_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return ``(package, None)`` or ``(None, error)``. Does not persist."""
    tenant_id = _text(handoff.agency_tenant_id)
    vacancy_id = _text(getattr(candidate, "vacancy_id", None))
    application = await get_application_for_handoff(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        vacancy_id=vacancy_id or None,
        application_id=_text(getattr(handoff, "application_id", None)) or None,
    )
    if application is None and vacancy_id:
        application = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=str(candidate.id),
            vacancy_id=vacancy_id,
            source="candidate",
            recruiter_id=_text(actor_id) or None,
        )
    if application is not None and not _text(getattr(handoff, "application_id", None)):
        handoff.application_id = str(application.id)

    employer_id = _text(getattr(handoff, "client_company_id", None))
    if vacancy_id:
        vacancy = await db.get(Vacancy, vacancy_id)
        company_id = _text(getattr(vacancy, "company_id", None)) if vacancy is not None else ""
        if company_id:
            employer_id = company_id

    documents = await list_candidate_documents(db, tenant_id, str(candidate.id))
    document_refs = [
        {
            "document_id": _text(getattr(doc, "id", None)),
            "doc_type": _text(getattr(doc, "doc_type", None)),
        }
        for doc in documents
        if _text(getattr(doc, "id", None))
    ]

    extra = _extra(candidate)
    identity: dict[str, Any] = {}
    first_name = _text(getattr(candidate, "first_name", None))
    last_name = _text(getattr(candidate, "last_name", None))
    if first_name:
        identity["first_name"] = first_name
    if last_name:
        identity["last_name"] = last_name
    citizenship = _text(extra.get("citizenship"))
    if citizenship:
        identity["citizenship"] = citizenship

    package: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "tenant_id": tenant_id,
        "person": {
            "person_id": str(candidate.id),
            "candidate_id": str(candidate.id),
            "identity_facts": identity,
        },
        "target_work": {
            "vacancy_id": vacancy_id or None,
            "employer_id": employer_id or None,
        },
        "recruitment_facts": {
            "stage": _text(getattr(candidate, "stage", None)),
        },
        "evidence": {
            "document_refs": document_refs,
        },
        "fits_decision": {
            "decision": "fits",
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "actor_id": _text(actor_id),
        },
        "context_refs": {
            "application_id": str(application.id) if application is not None else "",
            "handoff_id": str(handoff.id),
        },
    }
    errors = validate_ready_for_employment_package_v1(package)
    if errors:
        return None, {
            "code": "ready_for_employment_invalid",
            "message": "Transfer did not emit ready_for_employment.v1",
            "errors": errors,
        }
    return package, None
