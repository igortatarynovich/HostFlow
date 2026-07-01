"""recruitment_applications MVP (intent layer).

Revision ID: 202605110001_ram
Revises: 202607150001_cal
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605110001_ram"
down_revision: Union[str, None] = "202607150001_cal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()

    op.create_table(
        "recruitment_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("vacancy_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=64), server_default=sa.text("'meta'"), nullable=False),
        sa.Column("recruiter_id", sa.String(length=36), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column("application_cycle", sa.String(length=64), nullable=True),
        sa.Column("meta", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recruitment_applications_tenant_id", "recruitment_applications", ["tenant_id"])
    op.create_index("ix_recruitment_applications_candidate_id", "recruitment_applications", ["candidate_id"])
    op.create_index("ix_recruitment_applications_lead_id", "recruitment_applications", ["lead_id"])
    op.create_index("ix_recruitment_applications_vacancy_id", "recruitment_applications", ["vacancy_id"])
    op.create_index("ix_recruitment_applications_recruiter_id", "recruitment_applications", ["recruiter_id"])
    op.create_index("ix_recruitment_applications_status", "recruitment_applications", ["status"])
    op.create_index(
        "ix_recruitment_applications_tenant_candidate",
        "recruitment_applications",
        ["tenant_id", "candidate_id"],
    )
    op.create_index(
        "ix_recruitment_applications_tenant_lead",
        "recruitment_applications",
        ["tenant_id", "lead_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recruitment_applications_tenant_lead", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_tenant_candidate", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_status", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_recruiter_id", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_vacancy_id", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_lead_id", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_candidate_id", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_tenant_id", table_name="recruitment_applications")
    op.drop_table("recruitment_applications")
