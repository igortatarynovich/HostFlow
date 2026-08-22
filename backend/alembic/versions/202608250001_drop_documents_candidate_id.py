"""E5: backfill Hub candidate/primary links; drop documents.candidate_id.

Revision ID: 202608250001_drop_documents_candidate_id
Revises: 202608240001_document_expiry_notification_events_p2
Create Date: 2026-08-22 16:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608250001_drop_documents_candidate_id"
down_revision: RevisionType = "202608240001_document_expiry_notification_events_p2"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("documents"):
        return
    columns = {c["name"] for c in insp.get_columns("documents")}
    if "candidate_id" not in columns:
        return

    if insp.has_table("document_entity_links"):
        op.execute(
            sa.text(
                """
                INSERT INTO document_entity_links (
                    id,
                    tenant_id,
                    document_id,
                    linked_entity_type,
                    linked_entity_id,
                    relation_type,
                    module_key,
                    created_at
                )
                SELECT
                    gen_random_uuid()::text,
                    d.tenant_id,
                    d.id,
                    'candidate',
                    d.candidate_id,
                    'primary',
                    'recruitment',
                    NOW()
                FROM documents d
                WHERE d.candidate_id IS NOT NULL
                  AND btrim(d.candidate_id) <> ''
                  AND NOT EXISTS (
                    SELECT 1
                    FROM document_entity_links l
                    WHERE l.tenant_id = d.tenant_id
                      AND l.document_id = d.id
                      AND l.linked_entity_type = 'candidate'
                      AND l.linked_entity_id = d.candidate_id
                      AND l.relation_type = 'primary'
                  )
                """
            )
        )

    indexes = {idx["name"] for idx in insp.get_indexes("documents")}
    if "ix_documents_candidate_id" in indexes:
        op.drop_index("ix_documents_candidate_id", table_name="documents")
    op.drop_column("documents", "candidate_id")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("documents"):
        return
    columns = {c["name"] for c in insp.get_columns("documents")}
    if "candidate_id" in columns:
        return
    op.add_column(
        "documents",
        sa.Column("candidate_id", sa.String(length=36), nullable=True),
    )
    if insp.has_table("document_entity_links"):
        op.execute(
            sa.text(
                """
                UPDATE documents d
                SET candidate_id = l.linked_entity_id
                FROM document_entity_links l
                WHERE l.document_id = d.id
                  AND l.tenant_id = d.tenant_id
                  AND l.linked_entity_type = 'candidate'
                  AND l.relation_type = 'primary'
                  AND (d.candidate_id IS NULL OR btrim(d.candidate_id) = '')
                """
            )
        )
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET candidate_id = '00000000-0000-0000-0000-000000000000'
            WHERE candidate_id IS NULL OR btrim(candidate_id) = ''
            """
        )
    )
    op.alter_column("documents", "candidate_id", nullable=False)
    op.create_index("ix_documents_candidate_id", "documents", ["candidate_id"], unique=False)
