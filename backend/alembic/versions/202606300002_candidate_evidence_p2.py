"""candidate_evidence + candidate_evidence_documents (Recruitment Phase 2).

Revision ID: 202606300002_candidate_evidence_p2
Revises: 202606300001_funnels_company_module_scope_p0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202606300002_candidate_evidence_p2"
down_revision: Union[str, None] = "202606300001_funnels_company_module_scope_p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _rls_tenant(table: str) -> None:
    if not _is_postgres():
        return
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = '{table}'
                AND policyname = 'rls_{table}_tenant'
            ) THEN
                CREATE POLICY rls_{table}_tenant ON {table}
                USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
            END IF;
        END $$;
    """
    )


def upgrade() -> None:
    uid = sa.String(36)
    ts = sa.TIMESTAMP(timezone=True)

    op.create_table(
        "candidate_evidence",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            uid,
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_code", sa.String(128), nullable=False),
        sa.Column("evidence_variant_code", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("selected_by", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("selected_at", ts, nullable=True),
        sa.Column("approved_by", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", ts, nullable=True),
        sa.Column("rejected_by", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", ts, nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("superseded_by", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("superseded_at", ts, nullable=True),
        sa.Column(
            "superseded_by_evidence_id",
            uid,
            sa.ForeignKey("candidate_evidence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", ts, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", ts, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_candidate_evidence_tenant_candidate",
        "candidate_evidence",
        ["tenant_id", "candidate_id"],
    )
    op.create_index(
        "ix_candidate_evidence_tenant_candidate_requirement",
        "candidate_evidence",
        ["tenant_id", "candidate_id", "requirement_code"],
    )
    op.create_index(
        "ix_candidate_evidence_tenant_status",
        "candidate_evidence",
        ["tenant_id", "status"],
    )

    op.create_table(
        "candidate_evidence_documents",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_evidence_id",
            uid,
            sa.ForeignKey("candidate_evidence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            uid,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("linked_by", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linked_at", ts, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "candidate_evidence_id",
            "document_id",
            name="uq_candidate_evidence_documents_evidence_document",
        ),
    )
    op.create_index(
        "ix_candidate_evidence_documents_tenant",
        "candidate_evidence_documents",
        ["tenant_id"],
    )

    _rls_tenant("candidate_evidence")
    _rls_tenant("candidate_evidence_documents")


def downgrade() -> None:
    op.drop_table("candidate_evidence_documents")
    op.drop_table("candidate_evidence")
