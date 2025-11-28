"""Ensure employment_type is validated via CHECK constraint and default."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202409150001"
down_revision: Union[str, Sequence[str], None] = "6db42b14f482"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALLOWED_VALUES = ("full_time", "part_time", "b2b")
CHECK_NAME = "ck_vacancies_employment_type"


def upgrade() -> None:
    conn = op.get_bind()

    # Normalize existing values: replace NULL/blank/invalid with default.
    conn.execute(
        sa.text(
            """
            UPDATE vacancies
            SET employment_type = 'full_time'
            WHERE employment_type IS NULL
               OR TRIM(employment_type) = ''
               OR employment_type NOT IN ('full_time', 'part_time', 'b2b')
            """
        )
    )

    # Ensure column type, nullability, and default align with spec.
    if conn.dialect.name != "sqlite":
        op.alter_column(
            "vacancies",
            "employment_type",
            existing_type=sa.String(length=50),
            existing_server_default=None,
            type_=sa.Text(),
            nullable=False,
            server_default=sa.text("'full_time'"),
        )

        op.create_check_constraint(
            CHECK_NAME,
            "vacancies",
            "employment_type IN ('full_time','part_time','b2b')",
        )
    else:
        # SQLite cannot ALTER COLUMN or add constraints without table rebuild; rely on application validation.
        pass


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "sqlite":
        op.drop_constraint(CHECK_NAME, "vacancies", type_="check")
        op.alter_column(
            "vacancies",
            "employment_type",
            existing_type=sa.Text(),
            existing_server_default=sa.text("'full_time'"),
            type_=sa.String(length=50),
            nullable=True,
            server_default=None,
        )
