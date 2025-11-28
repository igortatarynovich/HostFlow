"""Convert companies.contacts and companies.extra to JSONB with defaults."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202512090001_companies_jsonb_contacts_extra"
down_revision: Union[str, Sequence[str], None] = "e361778a4c4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _upgrade_postgresql() -> None:
    conn = op.get_bind()

    for column in ("contacts", "extra"):
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column} DROP DEFAULT
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                UPDATE companies
                SET {column} = NULL
                WHERE {column} = '' OR {column} IS NULL
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column}
                TYPE jsonb
                USING COALESCE({column}, '{{}}')::jsonb
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                UPDATE companies
                SET {column} = '{{}}'::jsonb
                WHERE {column} IS NULL
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column}
                SET DEFAULT '{{}}'::jsonb
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column}
                SET NOT NULL
                """
            )
        )


def _upgrade_sqlite_like() -> None:
    # SQLite already stores JSON as TEXT; ensure defaults only.
    for column in ("contacts", "extra"):
        op.execute(
            sa.text(
                f"UPDATE companies SET {column} = '{{}}' WHERE {column} IS NULL OR {column} = ''"
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _upgrade_postgresql()
    else:
        _upgrade_sqlite_like()


def _downgrade_postgresql() -> None:
    for column in ("contacts", "extra"):
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column} DROP DEFAULT
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column}
                TYPE text
                USING {column}::text
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                ALTER TABLE companies
                ALTER COLUMN {column}
                DROP NOT NULL
                """
            )
        )


def _downgrade_sqlite_like() -> None:
    # No-op for SQLite.
    return


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _downgrade_postgresql()
    else:
        _downgrade_sqlite_like()
