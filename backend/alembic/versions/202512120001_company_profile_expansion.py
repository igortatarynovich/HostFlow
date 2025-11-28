"""Company profile base columns (country)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import NoSuchTableError

revision: str = "202512120001_company_profile_expansion"
down_revision: Union[str, Sequence[str], None] = "202512100001_documents_module_expansion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    try:
        cols = inspector.get_columns(table)
    except NoSuchTableError:
        return False
    return any(col["name"] == column for col in cols)


def upgrade() -> None:
    if not _has_column("companies", "country"):
        op.add_column(
            "companies",
            sa.Column("country", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    if _has_column("companies", "country"):
        op.drop_column("companies", "country")
