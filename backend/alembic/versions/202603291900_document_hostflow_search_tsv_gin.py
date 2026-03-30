"""Stored tsvector on documents for global search GIN (§2.6)

Revision ID: 202603291900_doc_tsv_gin
Revises: 202603291800_hostflow_tsv_gin
Create Date: 2026-03-29

Document FTS in global_search also joins Candidate (name/email). That part stays as
expression in the query; this column indexes document-row text only (same tokens as
the first segment of the concat), so PG15+ can use GIN on the physical column.

"""
from typing import Sequence, Union

from alembic import op

revision: str = "202603291900_doc_tsv_gin"
down_revision: Union[str, None] = "202603291800_hostflow_tsv_gin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS hostflow_document_search_tsv tsvector
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_document_search_tsv()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $f$
        BEGIN
          NEW.hostflow_document_search_tsv := to_tsvector(
            'pg_catalog.simple'::regconfig,
            concat_ws(
              ' ',
              COALESCE(NEW.doc_type, ''),
              COALESCE(NEW.custom_name, ''),
              COALESCE(NEW.filename, ''),
              COALESCE(NEW.number, ''),
              COALESCE(NEW.external_id, ''),
              COALESCE(NEW.user_comment, ''),
              COALESCE(NEW.source, ''),
              COALESCE(NEW.id::text, ''),
              COALESCE(NEW.candidate_id::text, ''),
              COALESCE(NEW.status::text, '')
            )
          );
          RETURN NEW;
        END;
        $f$
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_documents_hostflow_search_tsv ON documents")
    op.execute(
        """
        CREATE TRIGGER trg_documents_hostflow_search_tsv
        BEFORE INSERT OR UPDATE OF
          doc_type, custom_name, filename, number, external_id, user_comment, source,
          id, candidate_id, status
        ON documents
        FOR EACH ROW
        EXECUTE PROCEDURE trg_refresh_document_search_tsv()
        """
    )
    op.execute(
        """
        UPDATE documents SET doc_type = doc_type
        WHERE hostflow_document_search_tsv IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_documents_hostflow_document_search_tsv_gin
        ON documents
        USING gin (hostflow_document_search_tsv)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_hostflow_document_search_tsv_gin")
    op.execute("DROP TRIGGER IF EXISTS trg_documents_hostflow_search_tsv ON documents")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_document_search_tsv()")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS hostflow_document_search_tsv")
