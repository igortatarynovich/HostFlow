import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# Alembic identifiers
revision = "20250906_users_add_extra_jsonb"
down_revision = "5dad3d78dd72"  # предыдущая ревизия в твоей цепочке
branch_labels = None
depends_on = None

# если хочешь постгр: from sqlalchemy.dialects import postgresql


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
        return any(r[1] == column for r in rows)
    else:
        row = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :t
                  AND column_name = :c
                LIMIT 1
                """
            ),
            {"t": table, "c": column},
        ).fetchone()
        return row is not None


def upgrade():
    if not _has_column("users", "extra"):
        conn = op.get_bind()
        if conn.dialect.name == "postgresql":
            # JSONB в Postgres
            from sqlalchemy.dialects import postgresql

            op.add_column("users", sa.Column("extra", postgresql.JSONB, nullable=True))
        else:
            # JSON в SQLite/других — хранится как TEXT, но SQLAlchemy даст удобный API
            op.add_column("users", sa.Column("extra", sa.JSON(), nullable=True))


def downgrade():
    # безопасно удаляем, если есть
    if _has_column("users", "extra"):
        op.drop_column("users", "extra")
