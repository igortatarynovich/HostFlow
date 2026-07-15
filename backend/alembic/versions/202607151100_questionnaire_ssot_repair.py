"""Questionnaire SSOT repair — lifecycle_status + supported_languages on tenant_lead_forms.

Revision ID: 202607151100_questionnaire_ssot_repair
Revises: 202607151000_adr022_form_purpose
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607151100_questionnaire_ssot_repair"
down_revision: RevisionType = "202607151000_adr022_form_purpose"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "tenant_lead_forms",
        sa.Column("lifecycle_status", sa.String(length=16), nullable=False, server_default="active"),
    )
    op.add_column(
        "tenant_lead_forms",
        sa.Column(
            "supported_languages",
            sa.String(length=32),
            nullable=False,
            server_default="pl,en,ru",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_lead_forms", "supported_languages")
    op.drop_column("tenant_lead_forms", "lifecycle_status")
