"""ADR-018 requirement policy pin on candidates (merge heads)."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608250001_adr018_requirement_policy_pin"
down_revision: RevisionType = (
    "202607081400_mfr_svc_code",
    "202606300001_funnels_company_module_scope_p0",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column(
            "requirement_policy_ref",
            sa.String(length=128),
            nullable=True,
            comment="Pinned RequirementPolicy ref e.g. recruitment.driver_ce.pl/v1",
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("requirement_policy_pinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_candidates_requirement_policy_ref",
        "candidates",
        ["requirement_policy_ref"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_candidates_requirement_policy_ref", table_name="candidates")
    op.drop_column("candidates", "requirement_policy_pinned_at")
    op.drop_column("candidates", "requirement_policy_ref")
