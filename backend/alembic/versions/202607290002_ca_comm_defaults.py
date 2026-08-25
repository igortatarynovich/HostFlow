"""ClientAccount.commercial_defaults JSON (ADR-032).

Revision ID: 202607290002_ca_comm_defaults
Revises: 202607290001_vacancy_settings_json
Create Date: 2026-07-29

NOTE: revision id ≤32 chars.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607290002_ca_comm_defaults"
down_revision: RevisionType = "202607290001_vacancy_settings_json"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "client_accounts",
        sa.Column(
            "commercial_defaults",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("client_accounts", "commercial_defaults")
