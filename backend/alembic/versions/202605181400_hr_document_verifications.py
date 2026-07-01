"""workforce_hr_document_verifications — HR review document verification cards (PR3).

Revision ID: 202605181400_hr_doc_verify
Revises: 202605181200_hr_review_handoff
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605181400_hr_doc_verify"
down_revision: Union[str, None] = "202605181200_hr_review_handoff"
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
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    uid = sa.String(36)

    op.create_table(
        "workforce_hr_document_verifications",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "hr_review_id",
            uid,
            sa.ForeignKey("workforce_hr_reviews.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "employee_id",
            uid,
            sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "handoff_id",
            uid,
            sa.ForeignKey("candidate_handoffs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("document_key", sa.String(128), nullable=False),
        sa.Column("document_id", uid, sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", sa.String(100), nullable=True),
        sa.Column("checklist_item_code", sa.String(64), nullable=False, server_default="documents_uploaded"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("verified_by_user_id", uid, nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("opened_by_user_id", uid, nullable=True),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("correction_note", sa.Text(), nullable=True),
        sa.Column("reviewed_fields_json", jtype, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "hr_review_id",
            "document_key",
            name="uq_hr_doc_verify_review_key",
        ),
    )
    _rls_tenant("workforce_hr_document_verifications")


def downgrade() -> None:
    op.drop_table("workforce_hr_document_verifications")
