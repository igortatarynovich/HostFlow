"""Candidate declaration state for immutable Recruitment document requirements."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.recruitment_policy import (
    RecruitmentProfilePolicyResolutionError,
    load_recruitment_profile_policy,
)
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion
from backend.app.models.recruitment_candidate_document_declaration import (
    CANDIDATE_DOCUMENT_DECLARATION_STATES,
    DECLARATION_UNKNOWN,
    DECLARATION_UPLOAD_REQUESTED,
    RecruitmentCandidateDocumentDeclaration,
)
from backend.app.services.document_catalog import get_doc_type_defaults
from backend.app.services.own_company_doc_scope import resolved_document_own_company_id


UPLOAD_SLOT_REQUEST_KIND = "profile_declaration"


class CandidateDocumentDeclarationError(ValueError):
    """Base declaration contract error."""


class CandidateDocumentDeclarationNotFound(CandidateDocumentDeclarationError):
    """Candidate or canonical Recruitment document requirement was not found."""


class InvalidCandidateDocumentDeclarationState(CandidateDocumentDeclarationError):
    """Requested declaration state is outside ADR-043 declaration states."""


@dataclass(frozen=True)
class CandidateDocumentDeclarationView:
    candidate_id: str
    entity_profile_version_id: str
    document_type_version_id: str
    state: str
    upload_document_id: str | None
    updated_by: str | None
    created_at: str | None
    updated_at: str | None


async def _validate_scope(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    entity_profile_version_id: str,
    document_type_version_id: str,
) -> Candidate:
    candidate = await db.get(Candidate, str(candidate_id))
    if candidate is None or str(candidate.tenant_id) != str(tenant_id):
        raise CandidateDocumentDeclarationNotFound("Candidate not found")

    try:
        policy = await load_recruitment_profile_policy(
            db,
            tenant_id=str(tenant_id),
            profile_version_id=str(entity_profile_version_id),
        )
    except RecruitmentProfilePolicyResolutionError as exc:
        raise CandidateDocumentDeclarationNotFound(
            "Recruitment Profile Version not found"
        ) from exc

    if not any(
        item.document_type_version_id == str(document_type_version_id)
        for item in policy.documents
    ):
        raise CandidateDocumentDeclarationNotFound(
            "Document requirement does not belong to Recruitment Profile Version"
        )

    return candidate


async def _canonical_document_type(
    db: AsyncSession,
    *,
    document_type_version_id: str,
) -> tuple[RefDocumentTypeVersion, RefDocumentType]:
    row = (
        await db.execute(
            select(RefDocumentTypeVersion, RefDocumentType)
            .join(
                RefDocumentType,
                RefDocumentType.id == RefDocumentTypeVersion.document_type_id,
            )
            .where(RefDocumentTypeVersion.id == str(document_type_version_id))
        )
    ).first()

    if row is None:
        raise CandidateDocumentDeclarationNotFound(
            "Canonical Document Type Version not found"
        )

    version, document_type = row
    return version, document_type


async def _find_upload_slot(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    entity_profile_version_id: str,
    document_type_version_id: str,
) -> Document | None:
    documents = (
        await db.execute(
            select(Document).where(
                Document.tenant_id == str(tenant_id),
                Document.candidate_id == str(candidate_id),
                Document.document_type_version_id == str(document_type_version_id),
                Document.status == DocumentStatus.requested,
                Document.deleted_at.is_(None),
            )
        )
    ).scalars()

    for document in documents:
        meta = document.meta if isinstance(document.meta, dict) else {}
        if (
            meta.get("request_kind") == UPLOAD_SLOT_REQUEST_KIND
            and str(meta.get("entity_profile_version_id") or "")
            == str(entity_profile_version_id)
        ):
            return document

    return None


async def _ensure_upload_slot(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    entity_profile_version_id: str,
    document_type_version_id: str,
) -> Document:
    existing = await _find_upload_slot(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        entity_profile_version_id=entity_profile_version_id,
        document_type_version_id=document_type_version_id,
    )
    if existing is not None:
        return existing

    version, document_type = await _canonical_document_type(
        db,
        document_type_version_id=document_type_version_id,
    )

    canonical_code = str(document_type.code)
    defaults = get_doc_type_defaults(canonical_code)

    document = Document(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        own_company_id=resolved_document_own_company_id(candidate, None),
        owner_type="candidate",
        owner_id=str(candidate.id),
        candidate_id=str(candidate.id),
        doc_type=canonical_code,
        document_type_id=str(document_type.id),
        document_type_version_id=str(version.id),
        kind=defaults.kind,
        requested_from=defaults.requested_from,
        process_type=defaults.process_type,
        reminder_days_before=30,
        files=[],
        meta={
            "doc_type": canonical_code,
            "request_kind": UPLOAD_SLOT_REQUEST_KIND,
            "entity_profile_version_id": str(entity_profile_version_id),
            "document_type_version_id": str(document_type_version_id),
        },
        status=DocumentStatus.requested,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


async def get_candidate_document_declaration(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    entity_profile_version_id: str,
    document_type_version_id: str,
) -> CandidateDocumentDeclarationView:
    await _validate_scope(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        entity_profile_version_id=entity_profile_version_id,
        document_type_version_id=document_type_version_id,
    )

    row = (
        await db.execute(
            select(RecruitmentCandidateDocumentDeclaration).where(
                RecruitmentCandidateDocumentDeclaration.tenant_id == str(tenant_id),
                RecruitmentCandidateDocumentDeclaration.candidate_id == str(candidate_id),
                RecruitmentCandidateDocumentDeclaration.entity_profile_version_id
                == str(entity_profile_version_id),
                RecruitmentCandidateDocumentDeclaration.document_type_version_id
                == str(document_type_version_id),
            )
        )
    ).scalar_one_or_none()

    upload_slot = await _find_upload_slot(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        entity_profile_version_id=entity_profile_version_id,
        document_type_version_id=document_type_version_id,
    )

    if row is None:
        return CandidateDocumentDeclarationView(
            candidate_id=str(candidate_id),
            entity_profile_version_id=str(entity_profile_version_id),
            document_type_version_id=str(document_type_version_id),
            state=DECLARATION_UNKNOWN,
            upload_document_id=str(upload_slot.id) if upload_slot else None,
            updated_by=None,
            created_at=None,
            updated_at=None,
        )

    return _view(
        row,
        upload_document_id=str(upload_slot.id) if upload_slot else None,
    )


async def set_candidate_document_declaration(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    entity_profile_version_id: str,
    document_type_version_id: str,
    state: str,
    actor_id: str | None,
) -> CandidateDocumentDeclarationView:
    normalized_state = str(state or "").strip().lower()
    if normalized_state not in CANDIDATE_DOCUMENT_DECLARATION_STATES:
        raise InvalidCandidateDocumentDeclarationState(
            f"Invalid candidate document declaration state: {state}"
        )

    candidate = await _validate_scope(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        entity_profile_version_id=entity_profile_version_id,
        document_type_version_id=document_type_version_id,
    )

    row = (
        await db.execute(
            select(RecruitmentCandidateDocumentDeclaration).where(
                RecruitmentCandidateDocumentDeclaration.tenant_id == str(tenant_id),
                RecruitmentCandidateDocumentDeclaration.candidate_id == str(candidate_id),
                RecruitmentCandidateDocumentDeclaration.entity_profile_version_id
                == str(entity_profile_version_id),
                RecruitmentCandidateDocumentDeclaration.document_type_version_id
                == str(document_type_version_id),
            )
        )
    ).scalar_one_or_none()

    if row is None:
        row = RecruitmentCandidateDocumentDeclaration(
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            entity_profile_version_id=str(entity_profile_version_id),
            document_type_version_id=str(document_type_version_id),
            state=normalized_state,
            updated_by=str(actor_id) if actor_id else None,
        )
        db.add(row)
    else:
        row.state = normalized_state
        row.updated_by = str(actor_id) if actor_id else None

    upload_slot: Document | None
    if normalized_state == DECLARATION_UPLOAD_REQUESTED:
        upload_slot = await _ensure_upload_slot(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
            entity_profile_version_id=entity_profile_version_id,
            document_type_version_id=document_type_version_id,
        )
    else:
        upload_slot = await _find_upload_slot(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            entity_profile_version_id=entity_profile_version_id,
            document_type_version_id=document_type_version_id,
        )

    await db.flush()
    await db.refresh(row)

    return _view(
        row,
        upload_document_id=str(upload_slot.id) if upload_slot else None,
    )


def _view(
    row: RecruitmentCandidateDocumentDeclaration,
    *,
    upload_document_id: str | None = None,
) -> CandidateDocumentDeclarationView:
    return CandidateDocumentDeclarationView(
        candidate_id=str(row.candidate_id),
        entity_profile_version_id=str(row.entity_profile_version_id),
        document_type_version_id=str(row.document_type_version_id),
        state=str(row.state),
        upload_document_id=upload_document_id,
        updated_by=str(row.updated_by) if row.updated_by else None,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


__all__ = [
    "CandidateDocumentDeclarationError",
    "CandidateDocumentDeclarationNotFound",
    "CandidateDocumentDeclarationView",
    "InvalidCandidateDocumentDeclarationState",
    "get_candidate_document_declaration",
    "set_candidate_document_declaration",
]
