"""users: add supervisor_id; user_memberships: add timestamps

Revision ID: fe5d16892956
Revises: 1e7d294073ca
Create Date: 2025-10-15 06:14:14.722347+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


def _has_column(conn, table: str, column: str) -> bool:
    """Return True if `column` exists in `table` for current dialect."""
    if conn.dialect.name == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == column for r in rows)
    res = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return res is not None


# revision identifiers, used by Alembic.
revision: str = 'fe5d16892956'
down_revision: Union[str, Sequence[str], None] = '1e7d294073ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    # 1) users.supervisor_id + FK(users.id) — через batch для совместимости с SQLite
    with op.batch_alter_table("users") as batch:
        if not _has_column(conn, "users", "supervisor_id"):
            batch.add_column(sa.Column("supervisor_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_users_supervisor_id_users",
                "users",
                ["supervisor_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # 2) user_memberships: добавить created_at / updated_at, чтобы сидер не падал
    with op.batch_alter_table("user_memberships") as batch:
        if not _has_column(conn, "user_memberships", "created_at"):
            batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        if not _has_column(conn, "user_memberships", "updated_at"):
            batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Откат для user_memberships
    with op.batch_alter_table("user_memberships") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("created_at")

    # Откат для users.supervisor_id и внешнего ключа
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_supervisor_id_users", type_="foreignkey")
        batch.drop_column("supervisor_id")
