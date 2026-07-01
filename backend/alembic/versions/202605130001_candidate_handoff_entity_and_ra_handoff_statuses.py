"""CandidateHandoff full entity fields + recruitment application handoff statuses.

Revision ID: 202605130001_ch_ra_handoff
Revises: 202605120001_ra_applied
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605130001_ch_ra_handoff"
down_revision: Union[str, None] = "202605120001_ra_applied"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_handoffs",
        sa.Column("application_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("from_company_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("to_company_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column(
            "handoff_type",
            sa.String(length=32),
            nullable=False,
            server_default="client_portal",
        ),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("returned_by_user_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("returned_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidate_handoffs",
        sa.Column("accepted_by_user_id", sa.String(length=36), nullable=True),
    )

    op.create_index(
        "ix_candidate_handoffs_application_id",
        "candidate_handoffs",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_handoffs_from_company_id",
        "candidate_handoffs",
        ["from_company_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_handoffs_to_company_id",
        "candidate_handoffs",
        ["to_company_id"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_candidate_handoffs_application_id",
            "candidate_handoffs",
            "recruitment_applications",
            ["application_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_candidate_handoffs_from_company_id",
            "candidate_handoffs",
            "companies",
            ["from_company_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_candidate_handoffs_to_company_id",
            "candidate_handoffs",
            "companies",
            ["to_company_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_candidate_handoffs_returned_by_user_id",
            "candidate_handoffs",
            "users",
            ["returned_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_candidate_handoffs_accepted_by_user_id",
            "candidate_handoffs",
            "users",
            ["accepted_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        sa.text(
            "UPDATE candidate_handoffs SET handoff_type = CASE "
            "WHEN destination = 'internal_hr' THEN 'internal_hr' "
            "WHEN client_tenant_id IS NOT NULL THEN 'client_account' "
            "ELSE 'client_portal' END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE candidate_handoffs SET returned_reason = return_reason "
            "WHERE returned_reason IS NULL AND return_reason IS NOT NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("fk_candidate_handoffs_accepted_by_user_id", "candidate_handoffs", type_="foreignkey")
        op.drop_constraint("fk_candidate_handoffs_returned_by_user_id", "candidate_handoffs", type_="foreignkey")
        op.drop_constraint("fk_candidate_handoffs_to_company_id", "candidate_handoffs", type_="foreignkey")
        op.drop_constraint("fk_candidate_handoffs_from_company_id", "candidate_handoffs", type_="foreignkey")
        op.drop_constraint("fk_candidate_handoffs_application_id", "candidate_handoffs", type_="foreignkey")

    op.drop_index("ix_candidate_handoffs_to_company_id", table_name="candidate_handoffs")
    op.drop_index("ix_candidate_handoffs_from_company_id", table_name="candidate_handoffs")
    op.drop_index("ix_candidate_handoffs_application_id", table_name="candidate_handoffs")

    op.drop_column("candidate_handoffs", "accepted_by_user_id")
    op.drop_column("candidate_handoffs", "accepted_at")
    op.drop_column("candidate_handoffs", "returned_reason")
    op.drop_column("candidate_handoffs", "returned_by_user_id")
    op.drop_column("candidate_handoffs", "locked_at")
    op.drop_column("candidate_handoffs", "completed_at")
    op.drop_column("candidate_handoffs", "handoff_type")
    op.drop_column("candidate_handoffs", "to_company_id")
    op.drop_column("candidate_handoffs", "from_company_id")
    op.drop_column("candidate_handoffs", "application_id")
