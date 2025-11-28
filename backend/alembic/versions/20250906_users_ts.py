import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision = "20250906_users_ts"
down_revision = "20250906_users_add_extra_jsonb"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        # (cid, name, type, notnull, dflt_value, pk)
        return any(r[1] == column for r in rows)
    else:
        res = conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :t
                  AND column_name = :c
                """
            ),
            {"t": table, "c": column},
        ).fetchone()
        return res is not None


def _add_ts_columns():
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        ts_tz = sa.TIMESTAMP(timezone=True)
        now_default = sa.text("now()")
    else:
        # SQLite (и др.) — без таймзоны
        ts_tz = sa.DateTime()
        # SQLite принимает CURRENT_TIMESTAMP; в Alembic лучше без скобок
        now_default = sa.text("CURRENT_TIMESTAMP")

    # created_at: NOT NULL + default now
    if not _has_column("users", "created_at"):
        op.add_column(
            "users",
            sa.Column("created_at", ts_tz, nullable=False, server_default=now_default),
        )

    # updated_at: NULL + default now (или оставь NULL без default, как решишь)
    if not _has_column("users", "updated_at"):
        op.add_column(
            "users",
            sa.Column("updated_at", ts_tz, nullable=True, server_default=now_default),
        )

    # deleted_at: NULL, без default
    if not _has_column("users", "deleted_at"):
        op.add_column(
            "users",
            sa.Column("deleted_at", ts_tz, nullable=True),
        )


def upgrade():
    _add_ts_columns()


def downgrade():
    # удаляем безопасно, только если есть
    if _has_column("users", "deleted_at"):
        op.drop_column("users", "deleted_at")
    if _has_column("users", "updated_at"):
        op.drop_column("users", "updated_at")
    if _has_column("users", "created_at"):
        op.drop_column("users", "created_at")
