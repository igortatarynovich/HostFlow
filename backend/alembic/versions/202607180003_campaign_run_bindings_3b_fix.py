"""Stage 3B fix: drop association snapshots; enforce one active primary per Flight.

Revision ID: 202607180003_campaign_run_bindings_3b_fix
Revises: 202607180002_campaign_run_bindings_3b
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180003_campaign_run_bindings_3b_fix"
down_revision: RevisionType = "202607180002_campaign_run_bindings_3b"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.drop_column("acq_campaign_run_intake_sources", "external_ref")
    op.drop_column("acq_campaign_run_intake_sources", "provider")

    # At most one active primary Form / Intake Source per Flight (DB guarantee).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_acq_campaign_run_forms_one_active_primary
        ON acq_campaign_run_forms (campaign_run_id)
        WHERE role = 'primary' AND is_active IS TRUE
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_acq_campaign_run_intake_sources_one_active_primary
        ON acq_campaign_run_intake_sources (campaign_run_id)
        WHERE role = 'primary' AND is_active IS TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_acq_campaign_run_intake_sources_one_active_primary")
    op.execute("DROP INDEX IF EXISTS uq_acq_campaign_run_forms_one_active_primary")
    op.add_column(
        "acq_campaign_run_intake_sources",
        sa.Column(
            "provider",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
    )
    op.add_column(
        "acq_campaign_run_intake_sources",
        sa.Column(
            "external_ref",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
