"""Materialize a candidate document request from the outstanding required set.

Outstanding membership is the RPM required set minus requirements already
satisfied for this candidate. A required request may be created only for a
member of that set. A recruiter may still ask for something else through the
manual document create; that row is an ad-hoc request and does not enter the
required set. Direct operator upload does not need a request row.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.modules.documents import crud as documents_crud
from backend.app.services import candidate_notifications
from backend.app.services import reminders as reminders_service
from backend.app.services.candidate_evidence_service import build_requirements_checklist
from backend.app.services.document_catalog import get_doc_type_defaults
from backend.app.services.own_company_doc_scope import resolved_document_own_company_id

REQUEST_KIND_REQUIRED = "required"
REQUEST_KIND_AD_HOC = "ad_hoc"


class NotOutstandingRequirement(Exception):
    """The vacancy-driven request path was asked for a type that is not outstanding."""

    def __init__(self, requirement_code: str, outstanding_codes: list[str]) -> None:
        self.requirement_code = requirement_code
        self.outstanding_codes = list(outstanding_codes)
        super().__init__(requirement_code)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


async def outstanding_requirement_view(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> dict[str, Any]:
    """RPM required set split into outstanding and already satisfied codes."""
    checklist = await build_requirements_checklist(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
    )
    required: list[str] = []
    outstanding: list[str] = []
    satisfied: list[str] = []
    for item in checklist.get("requirements") or []:
        if not isinstance(item, dict):
            continue
        code = _norm(item.get("requirement_code"))
        if not code:
            continue
        required.append(code)
        if item.get("fulfilled"):
            satisfied.append(code)
        else:
            outstanding.append(code)
    return {
        "candidate_id": str(candidate.id),
        "required_codes": required,
        "outstanding_codes": outstanding,
        "satisfied_codes": satisfied,
    }


async def create_required_document_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    requirement_code: str,
    own_company_id: str | None = None,
) -> dict[str, Any]:
    """Persist a requested document for one outstanding requirement and return the candidate link.

    Refuses a code outside the outstanding set. Does not add that code to RPM.
    """
    code = _norm(requirement_code)
    view = await outstanding_requirement_view(db, tenant_id=tenant_id, candidate=candidate)
    outstanding = [str(item) for item in view["outstanding_codes"]]
    if code not in outstanding:
        raise NotOutstandingRequirement(code, outstanding)

    defaults = get_doc_type_defaults(code)
    meta = {
        "doc_type": defaults.doc_type,
        "title": code,
        "request_kind": REQUEST_KIND_REQUIRED,
        "requirement_code": code,
    }
    await documents_crud.ensure_document_type(db, str(candidate.tenant_id), defaults.doc_type)
    document = Document(
        id=str(uuid4()),
        tenant_id=str(candidate.tenant_id),
        own_company_id=resolved_document_own_company_id(candidate, own_company_id),
        owner_type="candidate",
        owner_id=str(candidate.id),
        candidate_id=str(candidate.id),
        doc_type=defaults.doc_type,
        kind=defaults.kind,
        requested_from=defaults.requested_from,
        process_type=defaults.process_type,
        reminder_days_before=30,
        meta=meta,
        status=DocumentStatus.requested,
    )
    db.add(document)
    await db.flush()
    await reminders_service.schedule_document_expiry_reminders(
        db,
        tenant_id=str(candidate.tenant_id),
        document=document,
    )

    from backend.app.api.public.intake import _ensure_status_share_token

    _ensure_status_share_token(candidate)
    await db.commit()
    await db.refresh(document)

    token = getattr(candidate, "status_share_token", None) or getattr(candidate, "intake_token", None)
    candidate_link = f"/public/status/{token}" if token else None
    base_url = (settings.frontend_url or "").strip().rstrip("/") or "https://hostflow.cc"
    status_url = f"{base_url}{candidate_link}" if candidate_link else None
    await candidate_notifications.send_document_requested_email_to_candidate(
        db,
        tenant_id=str(candidate.tenant_id),
        candidate=candidate,
        doc_type=defaults.doc_type,
        status_url=status_url,
    )
    await db.commit()

    from backend.app.api.v1.candidate_documents import _recalc_docs_progress

    await _recalc_docs_progress(
        db,
        str(candidate.tenant_id),
        str(candidate.id),
        own_company_id=own_company_id,
    )
    return {
        "document_id": str(document.id),
        "requirement_code": code,
        "doc_type": defaults.doc_type,
        "status": DocumentStatus.requested.value,
        "request_kind": REQUEST_KIND_REQUIRED,
        "candidate_link": candidate_link,
    }
