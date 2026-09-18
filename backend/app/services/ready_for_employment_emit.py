"""Assemble ready_for_employment.v1 at Transfer (RSO-2B).

Emit only REQUIRED_AT_TRANSFER + authoritative PASS_IF_KNOWN.
Does not call Accept / Employment init. Does not invent new Recruitment prompts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.recruitment.public.models import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.modules.recruitment.public.models import RecruitmentApplication
from backend.app.modules.recruitment.public.models import Vacancy
from backend.app.modules.documents.public.crud import list_candidate_documents
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    validate_ready_for_employment_package_v1,
)
from backend.app.modules.documents.public.types import DocumentTypeRuntimeResolver
from backend.app.modules.employment.public.transfer import flatten_recruitment_candidate_fields
from backend.app.modules.recruitment.public.application import (
    InvalidRecruitmentApplicationTransition,
    normalize_application_status,
    set_recruitment_application_status,
)
from backend.app.modules.recruitment.public.application import get_application_for_handoff


class HandoffManifestValidationError(Exception):
    """Raised when Transfer cannot emit a valid ready_for_employment.v1 package."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors) if errors else "invalid package")
        self.errors = list(errors or [])


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


async def ensure_application_for_transfer_manifest(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    handoff: CandidateHandoff,
) -> RecruitmentApplication:
    """Resolve or create a minimal application so context_refs.application_id is valid."""
    app = await get_application_for_handoff(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        vacancy_id=_text(getattr(candidate, "vacancy_id", None)),
        application_id=_text(getattr(handoff, "application_id", None)),
    )
    if app is not None:
        return app

    vac_id = _text(getattr(candidate, "vacancy_id", None))
    app = RecruitmentApplication(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        candidate_id=str(candidate.id),
        vacancy_id=vac_id,
        source="handoff_transfer",
        recruiter_id=_text(getattr(candidate, "recruiter_id", None))
        or _text(getattr(handoff, "requested_by_user_id", None)),
        status="ready_for_handoff",
        meta={"created_for": "ready_for_employment.v1_emit"},
    )
    db.add(app)
    await db.flush()
    handoff.application_id = str(app.id)
    await db.flush()
    return app


async def build_ready_for_employment_package_v1(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    candidate: Candidate,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build canonical Transfer manifest (not legacy snapshot)."""
    snap_time = now or datetime.now(timezone.utc)
    agency_tid = str(handoff.agency_tenant_id)
    app = await ensure_application_for_transfer_manifest(
        db, tenant_id=agency_tid, candidate=candidate, handoff=handoff
    )
    cur = normalize_application_status(app.status)
    if cur in ("applied", "in_review", "shortlisted"):
        try:
            set_recruitment_application_status(app, "ready_for_handoff")
        except InvalidRecruitmentApplicationTransition:
            pass

    flat = flatten_recruitment_candidate_fields(candidate)
    identity_facts: dict[str, Any] = {
        "first_name": flat.get("first_name") or str(candidate.first_name or "").strip() or None,
        "last_name": flat.get("last_name") or str(candidate.last_name or "").strip() or None,
    }
    # PASS_IF_KNOWN — authoritative only (already on candidate)
    for key in ("citizenship", "birth_date", "work_country", "country_code"):
        if flat.get(key) not in (None, ""):
            identity_facts[key] = flat.get(key)

    contacts: dict[str, Any] = {}
    for key in ("email", "phone", "phone_country_code"):
        if flat.get(key) not in (None, ""):
            contacts[key] = flat.get(key)

    vac_id = _text(getattr(app, "vacancy_id", None)) or _text(getattr(candidate, "vacancy_id", None))
    employer_id = (
        _text(getattr(handoff, "client_company_id", None))
        or _text(getattr(handoff, "to_company_id", None))
        or _text(getattr(candidate, "company_id", None))
        or _text(getattr(candidate, "own_company_id", None))
    )
    vacancy_title: str | None = None
    if vac_id:
        vac = await db.get(Vacancy, vac_id)
        if vac:
            vacancy_title = _text(getattr(vac, "title", None))
            if not employer_id:
                employer_id = _text(getattr(vac, "company_id", None))

    target_work: dict[str, Any] = {}
    if vac_id:
        target_work["vacancy_id"] = vac_id
    if employer_id:
        target_work["employer_id"] = employer_id
    if vacancy_title:
        target_work["vacancy_title_as_of"] = vacancy_title

    docs = await list_candidate_documents(db, agency_tid, str(candidate.id))
    document_refs: list[dict[str, Any]] = []
    for d in docs:
        did = _text(getattr(d, "id", None))
        if not did:
            continue
        runtime_ref = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)
        document_refs.append(
            {
                "document_id": did,
                "doc_type": _text(getattr(d, "doc_type", None)) or "",
                "canonical_code": runtime_ref.canonical_code,
                "status": str(getattr(getattr(d, "status", None), "value", getattr(d, "status", "")) or ""),
            }
        )

    from backend.app.modules.recruitment.public.evidence import (
        build_requirement_fulfillments_for_candidate,
    )

    fulfillments = await build_requirement_fulfillments_for_candidate(
        db,
        tenant_id=agency_tid,
        candidate_id=str(candidate.id),
    )
    fulfillment_refs: list[dict[str, Any]] = []
    for row in fulfillments or []:
        if not isinstance(row, dict):
            continue
        fulfillment_refs.append(
            {
                "requirement_code": row.get("requirement_code"),
                "chosen_evidence_variant_code": row.get("chosen_evidence_variant_code"),
                "status": row.get("status"),
                "document_ids": [
                    str(doc.get("document_id"))
                    for doc in (row.get("documents") or [])
                    if isinstance(doc, dict) and doc.get("document_id")
                ],
            }
        )

    actor_id = _text(getattr(handoff, "requested_by_user_id", None)) or "system"
    decided_at = _iso(getattr(handoff, "requested_at", None)) or _iso(snap_time)

    package: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "tenant_id": agency_tid,
        "person": {
            "candidate_id": str(candidate.id),
            "person_id": str(candidate.id),
            "identity_facts": {k: v for k, v in identity_facts.items() if v not in (None, "")},
            "contacts": contacts,
        },
        "target_work": target_work,
        "recruitment_facts": {
            "requirement_verdicts_as_of": fulfillment_refs,
            "candidate_stage_as_of": _text(getattr(candidate, "stage", None)),
        },
        "evidence": {
            "document_refs": document_refs,
            "source": "recruitment_transfer",
        },
        "fits_decision": {
            "decision": "fits",
            "decided_at": decided_at,
            "actor_id": actor_id,
            "reason": "transfer_ready_for_handoff",
        },
        "context_refs": {
            "application_id": str(app.id),
            "handoff_id": str(handoff.id),
            "recruiter_id": _text(getattr(app, "recruiter_id", None)),
            "emitted_at": _iso(snap_time),
        },
    }
    return package


async def build_and_validate_ready_for_employment_package_v1(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    candidate: Candidate,
    now: datetime | None = None,
) -> dict[str, Any]:
    package = await build_ready_for_employment_package_v1(
        db, handoff=handoff, candidate=candidate, now=now
    )
    errors = validate_ready_for_employment_package_v1(package)
    if errors:
        raise HandoffManifestValidationError(errors)
    return package


async def vacancy_is_handoff_target_for_hr_lane(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    vacancy_id: str,
) -> bool:
    """True when vacancy is target of an active internal_hr handoff (pre- or post-accept)."""
    from backend.app.modules.recruitment.public.write_guard import LOCK_HANDOFF_STATUSES

    vac = str(vacancy_id).strip()
    tid = str(agency_tenant_id).strip()
    if not vac or not tid:
        return False

    # Via application.vacancy_id
    stmt = (
        select(CandidateHandoff.id)
        .join(
            RecruitmentApplication,
            RecruitmentApplication.id == CandidateHandoff.application_id,
        )
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status.in_(tuple(LOCK_HANDOFF_STATUSES)),
            RecruitmentApplication.vacancy_id == vac,
        )
        .limit(1)
    )
    if (await db.execute(stmt)).scalar_one_or_none():
        return True

    # Via candidate.vacancy_id
    stmt2 = (
        select(CandidateHandoff.id)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status.in_(tuple(LOCK_HANDOFF_STATUSES)),
            Candidate.vacancy_id == vac,
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    return (await db.execute(stmt2)).scalar_one_or_none() is not None


async def employer_is_handoff_target_for_hr_lane(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    company_id: str,
) -> bool:
    """True when company is client/employer on an active internal_hr handoff."""
    from backend.app.modules.recruitment.public.write_guard import LOCK_HANDOFF_STATUSES

    cid = str(company_id).strip()
    tid = str(agency_tenant_id).strip()
    if not cid or not tid:
        return False
    stmt = (
        select(CandidateHandoff.id)
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status.in_(tuple(LOCK_HANDOFF_STATUSES)),
            (
                (CandidateHandoff.client_company_id == cid)
                | (CandidateHandoff.to_company_id == cid)
                | (CandidateHandoff.from_company_id == cid)
            ),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None
