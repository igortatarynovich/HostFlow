"""Add vacancies.settings_json for sparse lead lifecycle email overrides (ADR-033)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607290001_vacancy_settings_json"
down_revision: Union[str, Sequence[str], None] = "202607280001_sales_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column(
            "settings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("vacancies", "settings_json")
