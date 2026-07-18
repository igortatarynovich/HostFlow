"""202607180007_forms_s2 — immutable published snapshot for Forms Sprint 2.

Revision ID: 202607180007_forms_s2
Revises: 202607180006_acq_3d_k
Create Date: 2026-07-18

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180007_forms_s2"
down_revision: RevisionType = "202607180006_acq_3d_k"
branch_labels: RevisionType = None
depends_on: RevisionType = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.add_column(
        "tenant_lead_forms",
        sa.Column("published_snapshot_v1", _JSON, nullable=True),
    )
    op.add_column(
        "tenant_lead_forms",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_lead_forms", "published_at")
    op.drop_column("tenant_lead_forms", "published_snapshot_v1")
