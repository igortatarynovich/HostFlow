"""Convert vacancies.status enum to TEXT for extended workflow states."""

from typing import Sequence, Union

from alembic import op


revision: str = "202512090002_vacancies_status_text"
down_revision: Union[str, Sequence[str], None] = "202512090001_companies_jsonb_contacts_extra"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE vacancies ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE vacancies ALTER COLUMN status TYPE TEXT USING status::text")
    op.execute("ALTER TABLE vacancies ALTER COLUMN status SET DEFAULT 'open'")
    op.execute("DROP TYPE IF EXISTS vacancystatus")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE TYPE vacancystatus AS ENUM ('open', 'closed')")
    op.execute("ALTER TABLE vacancies ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE vacancies
        ALTER COLUMN status
        TYPE vacancystatus
        USING (
            CASE
                WHEN status IN ('open', 'closed') THEN status::vacancystatus
                ELSE 'open'::vacancystatus
            END
        )
        """
    )
    op.execute("ALTER TABLE vacancies ALTER COLUMN status SET DEFAULT 'open'")
