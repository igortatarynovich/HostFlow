"""HR review: candidate_id + nullable employee_id for delayed workforce (stage B).

Revision ID: 202605181200_hr_review_handoff
Revises: 202605171200_hr_reviews
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202605181200_hr_review_handoff"
down_revision: Union[str, None] = "202605171200_hr_reviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workforce_hr_reviews",
        sa.Column(
            "candidate_id",
            sa.String(36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    op.execute(
        """
        UPDATE workforce_hr_reviews r
        SET candidate_id = e.candidate_id
        FROM workforce_employees e
        WHERE r.employee_id = e.id AND r.candidate_id IS NULL
        """
    )
    op.alter_column("workforce_hr_reviews", "employee_id", existing_type=sa.String(36), nullable=True)
    op.drop_constraint("uq_workforce_hr_review_tenant_employee", "workforce_hr_reviews", type_="unique")
    op.create_unique_constraint(
        "uq_workforce_hr_review_tenant_handoff",
        "workforce_hr_reviews",
        ["tenant_id", "handoff_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_workforce_hr_review_tenant_handoff", "workforce_hr_reviews", type_="unique")
    op.create_unique_constraint(
        "uq_workforce_hr_review_tenant_employee",
        "workforce_hr_reviews",
        ["tenant_id", "employee_id"],
    )
    op.alter_column("workforce_hr_reviews", "employee_id", existing_type=sa.String(36), nullable=False)
    op.drop_column("workforce_hr_reviews", "candidate_id")
