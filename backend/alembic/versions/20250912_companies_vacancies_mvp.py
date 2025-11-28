

"""companies + vacancies MVP (no-op)

Revision ID: 20250912_companies_vacancies_mvp
Revises: d843b1b2009f
Create Date: 2025-09-12 00:00:00.000000+00:00

"""

from typing import Sequence, Union

# Alembic requires these identifiers
revision: str = "20250912_companies_vacancies_mvp"
down_revision: Union[str, Sequence[str], None] = "d843b1b2009f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Schema already created previously; this revision is a no-op to link history."""


def downgrade() -> None:
    """No-op downgrade for linkage revision."""
