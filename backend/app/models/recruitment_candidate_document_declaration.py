
"""Candidate-specific declaration state for Recruitment document requirements.

ADR-043 keeps candidate declaration state separate from immutable Recruitment

Profile policy and from Candidate Evidence lifecycle.

"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

from .mixins import TimestampMixin

DECLARATION_UNKNOWN = "unknown"

DECLARATION_DOES_NOT_HAVE = "does_not_have"

DECLARATION_HAS_DOCUMENT = "has_document"

DECLARATION_UPLOAD_REQUESTED = "upload_requested"

CANDIDATE_DOCUMENT_DECLARATION_STATES = frozenset(

    {

        DECLARATION_UNKNOWN,

        DECLARATION_DOES_NOT_HAVE,

        DECLARATION_HAS_DOCUMENT,

        DECLARATION_UPLOAD_REQUESTED,

    }

)

class RecruitmentCandidateDocumentDeclaration(Base, TimestampMixin):

    """Declaration for one candidate and one immutable Recruitment document requirement."""

    __tablename__ = "recruitment_candidate_document_declarations"

    __table_args__ = (

        UniqueConstraint(

            "tenant_id",

            "candidate_id",

            "entity_profile_version_id",

            "document_type_version_id",

            name="uq_recruitment_candidate_doc_declaration_scope",

        ),

        CheckConstraint(

            "state IN ('unknown', 'does_not_have', 'has_document', 'upload_requested')",

            name="ck_recruitment_candidate_doc_declaration_state",

        ),

    )

    id: Mapped[str] = mapped_column(

        String(36),

        primary_key=True,

        default=lambda: str(uuid4()),

    )

    tenant_id: Mapped[str] = mapped_column(

        String(36),

        ForeignKey("tenants.id", ondelete="CASCADE"),

        nullable=False,

        index=True,

    )

    candidate_id: Mapped[str] = mapped_column(

        String(36),

        ForeignKey("candidates.id", ondelete="CASCADE"),

        nullable=False,

        index=True,

    )

    entity_profile_version_id: Mapped[str] = mapped_column(

        String(36),

        ForeignKey("ep_entity_profile_versions.id", ondelete="RESTRICT"),

        nullable=False,

        index=True,

    )

    document_type_version_id: Mapped[str] = mapped_column(

        String(36),

        ForeignKey("ref_document_type_versions.id", ondelete="RESTRICT"),

        nullable=False,

        index=True,

    )

    state: Mapped[str] = mapped_column(

        String(32),

        nullable=False,

        default=DECLARATION_UNKNOWN,

    )

    updated_by: Mapped[str | None] = mapped_column(

        String(36),

        ForeignKey("users.id", ondelete="SET NULL"),

        nullable=True,

    )

__all__ = [

    "CANDIDATE_DOCUMENT_DECLARATION_STATES",

    "DECLARATION_DOES_NOT_HAVE",

    "DECLARATION_HAS_DOCUMENT",

    "DECLARATION_UNKNOWN",

    "DECLARATION_UPLOAD_REQUESTED",

    "RecruitmentCandidateDocumentDeclaration",

]
