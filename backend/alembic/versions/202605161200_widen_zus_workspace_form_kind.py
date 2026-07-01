"""Widen workforce_zus_workspace_tasks.form_kind for monthly_settlement label.

Revision ID: 202605161200_widen_zus_ws_form_kind
Revises: 202605151300_zus_workspace_mvp
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202605161200_widen_zus_ws_form_kind"
down_revision: Union[str, None] = "202605151300_zus_workspace_mvp"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "workforce_zus_workspace_tasks",
        "form_kind",
        existing_type=sa.String(length=8),
        type_=sa.String(length=32),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "workforce_zus_workspace_tasks",
        "form_kind",
        existing_type=sa.String(length=32),
        type_=sa.String(length=8),
        existing_nullable=True,
    )
