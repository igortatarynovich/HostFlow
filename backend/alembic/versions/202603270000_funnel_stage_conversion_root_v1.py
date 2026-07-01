"""funnel_stages.conversion_root_v1 — §2.12 root funnel mapping (lead|qualified|active|final)

Revision ID: 202603270000_conv_root
Revises: 202603252100_meta_proc_mode
Create Date: 2026-03-27

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603270000_conv_root"
down_revision: Union[str, None] = "202603252100_meta_proc_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "funnel_stages",
        sa.Column("conversion_root_v1", sa.String(length=32), nullable=True),
    )
    # Backfill lead funnels: align with legacy GET /leads/conversion-funnel win path semantics.
    op.execute(
        sa.text(
            """
            UPDATE funnel_stages AS fs
            SET conversion_root_v1 = CASE lower(fs.code)
              WHEN 'new' THEN 'lead'
              WHEN 'contacted' THEN 'qualified'
              WHEN 'qualified' THEN 'active'
              WHEN 'converted' THEN 'final'
              ELSE NULL
            END
            FROM funnels AS f
            WHERE fs.funnel_id = f.id
              AND f.type = 'lead'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("funnel_stages", "conversion_root_v1")
