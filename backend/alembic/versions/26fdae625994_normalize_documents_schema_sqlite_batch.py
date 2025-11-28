from alembic import op
import sqlalchemy as sa

# ревизии
revision = "26fdae625994"
down_revision = "de8297d07bfa"
branch_labels = None
depends_on = None


def _has_table(conn, table: str) -> bool:
    insp = sa.inspect(conn)
    return table in insp.get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "documents"):
        return

    # --- существующие колонки: меняем nullable/типы аккуратно ---
    if _has_column(conn, "documents", "tenant_id"):
        op.alter_column(
            "documents",
            "tenant_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )

    if _has_column(conn, "documents", "owner_type"):
        op.alter_column(
            "documents",
            "owner_type",
            existing_type=sa.String(length=50),
            nullable=True,
        )

    if _has_column(conn, "documents", "owner_id"):
        op.alter_column(
            "documents",
            "owner_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )

    # --- новые поля: добавляем, если нет ---
    if not _has_column(conn, "documents", "candidate_id"):
        op.add_column("documents", sa.Column("candidate_id", sa.String(length=36), nullable=True))

    if not _has_column(conn, "documents", "key"):
        op.add_column("documents", sa.Column("key", sa.String(length=100), nullable=False, server_default="document"))
        # снять дефолт после проставления значений по умолчанию
        op.alter_column("documents", "key", server_default=None)

    if not _has_column(conn, "documents", "filename"):
        op.add_column("documents", sa.Column("filename", sa.Text(), nullable=True))

    if not _has_column(conn, "documents", "path"):
        op.add_column("documents", sa.Column("path", sa.Text(), nullable=True))

    if not _has_column(conn, "documents", "issued_date"):
        op.add_column("documents", sa.Column("issued_date", sa.Date(), nullable=True))

    if not _has_column(conn, "documents", "expires_date"):
        op.add_column("documents", sa.Column("expires_date", sa.Date(), nullable=True))

    if not _has_column(conn, "documents", "reminder_days_before"):
        op.add_column("documents", sa.Column("reminder_days_before", sa.Integer(), nullable=True))

    if not _has_column(conn, "documents", "extra"):
        op.add_column("documents", sa.Column("extra", sa.Text(), nullable=True))

    # совместимые «наследные»
    if not _has_column(conn, "documents", "status"):
        op.add_column("documents", sa.Column("status", sa.String(length=50), nullable=True, server_default="uploaded"))
        op.alter_column("documents", "status", server_default=None)

    if not _has_column(conn, "documents", "issued_at"):
        op.add_column("documents", sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_column(conn, "documents", "expires_at"):
        op.add_column("documents", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    # meta/version + таймстемпы
    if _has_column(conn, "documents", "meta_json"):
        op.alter_column(
            "documents",
            "meta_json",
            existing_type=sa.Text(),
            server_default=sa.text("'{}'"),
            nullable=False,
        )

    if _has_column(conn, "documents", "version"):
        op.alter_column(
            "documents",
            "version",
            existing_type=sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        )

    if _has_column(conn, "documents", "created_at"):
        op.alter_column(
            "documents",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        )

    if _has_column(conn, "documents", "updated_at"):
        op.alter_column(
            "documents",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        )

    # deleted_at может быть NULL — без изменений


def downgrade() -> None:
    # Ничего не откатываем (как и в исходной миграции)
    pass
