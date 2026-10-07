"""Pre-employment requirement instances for one Employment.

Revision ID: 202610060001_hr_employment_requirements
Revises: 202610050001_hr_employment_terms

hr_employment_requirements stores pre_employment_requirements.v1.
No backfill. Instances are not generated from policy. Candidate evidence
is not copied. Onboarding tasks and contract cards are not created.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610060001_hr_employment_requirements"
down_revision: Union[str, None] = "202610050001_hr_employment_terms"
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
    op.create_table(
        "hr_employment_requirements",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "employment_id",
            uid,
            sa.ForeignKey("hr_employments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("definition_key", sa.String(191), nullable=False),
        sa.Column("policy_id", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("applicability", sa.String(16), nullable=False),
        sa.Column("applicability_basis", sa.Text(), nullable=True),
        sa.Column("resolution", sa.String(16), nullable=True),
        sa.Column(
            "satisfaction_evidence_id",
            uid,
            sa.ForeignKey("candidate_evidence.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "satisfaction_document_id",
            uid,
            sa.ForeignKey("documents.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "waiver_actor_id",
            uid,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("waiver_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "employment_id",
            "definition_key",
            name="uq_hr_employment_requirements_employment_definition",
        ),
        sa.CheckConstraint(
            "applicability IN ('applicable', 'not_applicable')",
            name="ck_hr_employment_requirements_applicability",
        ),
        sa.CheckConstraint(
            "(applicability = 'not_applicable' AND resolution IS NULL) "
            "OR (applicability = 'applicable' AND resolution IN "
            "('unresolved', 'satisfied', 'waived', 'blocking'))",
            name="ck_hr_employment_requirements_resolution",
        ),
        sa.CheckConstraint(
            "(resolution = 'satisfied' AND ("
            "satisfaction_evidence_id IS NOT NULL OR satisfaction_document_id IS NOT NULL)) "
            "OR ((resolution IS NULL OR resolution <> 'satisfied') AND "
            "satisfaction_evidence_id IS NULL AND satisfaction_document_id IS NULL)",
            name="ck_hr_employment_requirements_satisfaction",
        ),
        sa.CheckConstraint(
            "(resolution = 'waived' AND waiver_actor_id IS NOT NULL AND waiver_at IS NOT NULL "
            "AND waiver_reason IS NOT NULL AND length(waiver_reason) > 0) "
            "OR ((resolution IS NULL OR resolution <> 'waived') AND waiver_actor_id IS NULL "
            "AND waiver_at IS NULL AND waiver_reason IS NULL)",
            name="ck_hr_employment_requirements_waiver",
        ),
        sa.CheckConstraint(
            "(resolution = 'blocking' AND blocking_reason IS NOT NULL AND length(blocking_reason) > 0) "
            "OR ((resolution IS NULL OR resolution <> 'blocking') AND blocking_reason IS NULL)",
            name="ck_hr_employment_requirements_blocking",
        ),
    )
    op.create_index(
        "ix_hr_employment_requirements_tenant_id",
        "hr_employment_requirements",
        ["tenant_id"],
    )
    op.create_index(
        "ix_hr_employment_requirements_employment_id",
        "hr_employment_requirements",
        ["employment_id"],
    )
    _rls_tenant("hr_employment_requirements")


def downgrade() -> None:
    op.drop_index("ix_hr_employment_requirements_employment_id", table_name="hr_employment_requirements")
    op.drop_index("ix_hr_employment_requirements_tenant_id", table_name="hr_employment_requirements")
    op.drop_table("hr_employment_requirements")
