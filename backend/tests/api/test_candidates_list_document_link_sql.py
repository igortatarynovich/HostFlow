"""GET /candidates must not filter documents via Document.candidate_id column_property.

That attribute is a correlated scalar subquery on document_entity_links. Wrapping it
in EXISTS/aggregates for every list row made the candidates table multi-second.
"""

from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import select

from backend.app.api.v1.candidates import repo as cand_repo
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document


def _compile(clause) -> str:
    return str(clause.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False})).lower()


def test_candidate_document_exists_joins_entity_links() -> None:
    sql = _compile(select(Candidate.id).where(cand_repo._candidate_document_exists()))
    assert "document_entity_links" in sql
    assert "linked_entity_id" in sql
    # Nested scalar projection of candidate_id (the old column_property pattern).
    assert "as candidate_id" not in sql


def test_candidate_document_exists_with_status_still_uses_links() -> None:
    sql = _compile(
        select(Candidate.id).where(
            cand_repo._candidate_document_exists(Document.status.in_(cand_repo.READY_STATUSES))
        )
    )
    assert "document_entity_links" in sql
    assert "as candidate_id" not in sql
    assert "documents.status" in sql
