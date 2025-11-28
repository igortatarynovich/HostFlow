from __future__ import annotations

from sqlalchemy import Column, String, Date, ForeignKey, Text, JSON

from backend.app.db.base import Base  # adjust only if your Base lives elsewhere


class CandidateDocument(Base):
    __tablename__ = "candidate_documents"

    # Using String for IDs to be compatible with SQLite and UUID strings
    id = Column(String, primary_key=True, index=True)

    tenant_id = Column(String, nullable=False, index=True)
    candidate_id = Column(String, nullable=False, index=True)

    # Reference to document type
    doc_type_id = Column(String, ForeignKey("document_types.id"), nullable=False, index=True)

    status = Column(String, nullable=True)
    number = Column(String, nullable=True)
    issued_at = Column(Date, nullable=True)
    expires_at = Column(Date, nullable=True)

    file_url = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    # Optional relationship to DocumentType (uncomment if DocumentType model exists)
    # document_type = relationship("DocumentType", back_populates="candidate_documents", lazy="joined")
