"""Candidate consent log table

Revision ID: 202606250001_candidate_consents_log
Revises: 202606200001_tenant_vacancy_access
Create Date: 2025-06-25 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202606250001_candidate_consents_log"
down_revision: RevisionType = "202606200001_tenant_vacancy_access"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "candidate_consents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("consent_code", sa.String(length=64), nullable=False),
        sa.Column("text_version", sa.String(length=32), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column("user_agent", sa.String(length=255)),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_candidate_consents_tenant_id", "candidate_consents", ["tenant_id"])
    op.create_index("ix_candidate_consents_candidate_id", "candidate_consents", ["candidate_id"])
    op.create_index("ix_candidate_consents_code", "candidate_consents", ["consent_code"])


def downgrade() -> None:
    op.drop_index("ix_candidate_consents_code", table_name="candidate_consents")
    op.drop_index("ix_candidate_consents_candidate_id", table_name="candidate_consents")
    op.drop_index("ix_candidate_consents_tenant_id", table_name="candidate_consents")
    op.drop_table("candidate_consents")
