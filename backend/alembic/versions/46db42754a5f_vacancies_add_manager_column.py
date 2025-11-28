import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "46db42754a5f"
down_revision = "20250906_users_ts"  # <-- ВАЖНО: ставим родителя!
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vacancies", sa.Column("manager", sa.String(), nullable=True))
    op.create_index("ix_vacancies_manager", "vacancies", ["manager"], unique=False)


def downgrade():
    op.drop_index("ix_vacancies_manager", table_name="vacancies")
    op.drop_column("vacancies", "manager")
