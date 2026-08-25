"""ADR-022 — Form Purpose and Submission Policy columns.

Revision ID: 202607151000_adr022_form_purpose
Revises: 202607141200_tenant_license_usage_limit_columns
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607151000_adr022_form_purpose"
down_revision: RevisionType = "202607141200_tenant_license_usage_limit_columns"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "tenant_lead_forms",
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="inquiry"),
    )
    op.add_column(
        "tenant_lead_forms",
        sa.Column("target_entity_profile_code", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "tenant_lead_forms",
        sa.Column("submission_policy", JSONType, nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "tenant_lead_forms",
        sa.Column("published_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "tenant_lead_forms",
        sa.Column("is_system_preset", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "intake_source_profiles",
        sa.Column("publication_config_v1", JSONType, nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("intake_source_profiles", "publication_config_v1")
    op.drop_column("tenant_lead_forms", "is_system_preset")
    op.drop_column("tenant_lead_forms", "published_version")
    op.drop_column("tenant_lead_forms", "submission_policy")
    op.drop_column("tenant_lead_forms", "target_entity_profile_code")
    op.drop_column("tenant_lead_forms", "purpose")
