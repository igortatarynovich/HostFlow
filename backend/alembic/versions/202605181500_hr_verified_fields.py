"""workforce_hr_verified_fields — HR verified fields SoT (PR4).

Revision ID: 202605181500_hr_verified
Revises: 202605181400_hr_doc_verify
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605181500_hr_verified"
down_revision: Union[str, None] = "202605181400_hr_doc_verify"
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
        "workforce_hr_verified_fields",
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
            "document_verification_id",
            uid,
            sa.ForeignKey("workforce_hr_document_verifications.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("field_code", sa.String(64), nullable=False),
        sa.Column("field_label", sa.String(256), nullable=False),
        sa.Column("downstream_use_json", jtype, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("verified_value", sa.Text(), nullable=True),
        sa.Column(
            "source_document_id",
            uid,
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_document_key", sa.String(128), nullable=True),
        sa.Column("profile_values_json", jtype, nullable=True),
        sa.Column("verified_by_user_id", uid, nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "hr_review_id",
            "field_code",
            name="uq_hr_verified_field_review_code",
        ),
    )
    _rls_tenant("workforce_hr_verified_fields")


def downgrade() -> None:
    op.drop_table("workforce_hr_verified_fields")
