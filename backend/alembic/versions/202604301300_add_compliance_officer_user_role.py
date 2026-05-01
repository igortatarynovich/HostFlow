"""users.role enum: add compliance_officer (document / process specialist)

Revision ID: 202604301300_compliance_officer
Revises: 202604190002_owner_fk_set_null
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604301300_compliance_officer"
down_revision: Union[str, None] = "202604190002_owner_fk_set_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pg_enum_type_for_column(conn, table: str, column: str) -> str | None:
    row = conn.execute(
        sa.text(
            """
            SELECT pg_type.typname
            FROM pg_attribute
            JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
            JOIN pg_type ON pg_type.oid = pg_attribute.atttypid
            WHERE pg_class.relname = :t
              AND pg_attribute.attname = :c
              AND pg_type.typtype = 'e'
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return str(row[0]) if row and row[0] else None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    enum_type = _pg_enum_type_for_column(conn, "users", "role")
    if not enum_type:
        return
    ctx = op.get_context()
    with ctx.autocommit_block():
        conn.exec_driver_sql(
            f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS 'compliance_officer';"
        )


def downgrade() -> None:
    pass
