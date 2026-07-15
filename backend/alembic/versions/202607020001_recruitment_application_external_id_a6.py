"""Recruitment applications: external_id for portal second-apply idempotency (A6 C2b).

Revision ID: 202607020001_ra_ext
Revises: 202606300004
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202607020001_ra_ext"
down_revision: Union[str, None] = "202606300004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recruitment_applications",
        sa.Column("external_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_recruitment_applications_external_id",
        "recruitment_applications",
        ["external_id"],
    )
    op.create_index(
        "ix_recruitment_applications_tenant_candidate_source_ext",
        "recruitment_applications",
        ["tenant_id", "candidate_id", "source", "external_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recruitment_applications_tenant_candidate_source_ext", table_name="recruitment_applications")
    op.drop_index("ix_recruitment_applications_external_id", table_name="recruitment_applications")
    op.drop_column("recruitment_applications", "external_id")
