from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d278bee1e7f4"
down_revision: Union[str, Sequence[str], None] = "20250912_companies_vacancies_mvp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite поддерживает добавление nullable-колонки просто через ADD COLUMN
    op.add_column(
        "vacancies",
        sa.Column("employment_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    # В SQLite DROP COLUMN поддерживается в новых версиях, Alembic сам подберёт стратегию.
    op.drop_column("vacancies", "employment_type")