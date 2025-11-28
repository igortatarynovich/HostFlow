"""merge heads: memberships + vacancies_manager

Revision ID: d843b1b2009f
Revises: 20250908_user_memberships, 46db42754a5f
Create Date: 2025-09-08 09:18:33.586395+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "d843b1b2009f"
down_revision: Union[str, Sequence[str], None] = (
    "20250908_user_memberships",
    "46db42754a5f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
