"""Map recruitment_applications.status active -> applied (lifecycle canon).

Revision ID: 202605120001_ra_applied
Revises: 202607150005_dptt
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605120001_ra_applied"
down_revision: Union[str, None] = "202607150005_dptt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "UPDATE recruitment_applications SET status = 'applied' "
                "WHERE status = 'active'"
            )
        )
        op.alter_column(
            "recruitment_applications",
            "status",
            server_default=sa.text("'applied'"),
            existing_type=sa.String(length=32),
            existing_nullable=False,
        )
    else:
        # SQLite / CI: table may be empty; keep behavior consistent.
        op.execute(
            sa.text(
                "UPDATE recruitment_applications SET status = 'applied' "
                "WHERE status = 'active'"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "UPDATE recruitment_applications SET status = 'active' "
                "WHERE status = 'applied'"
            )
        )
        op.alter_column(
            "recruitment_applications",
            "status",
            server_default=sa.text("'active'"),
            existing_type=sa.String(length=32),
            existing_nullable=False,
        )
    else:
        op.execute(
            sa.text(
                "UPDATE recruitment_applications SET status = 'active' "
                "WHERE status = 'applied'"
            )
        )
