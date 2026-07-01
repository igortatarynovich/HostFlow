"""Backfill first_name_latin, last_name_latin for existing candidates.

Revision ID: 202608060002
Revises: 202608060001_normalization_latin
Create Date: 2026-08-06 10:30:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608060002_backfill_latin"
down_revision: RevisionType = "202608060001_normalization_latin"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    from backend.app.services.transliterate import has_cyrillic, transliterate

    conn: Connection = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    result = conn.execute(text("SELECT id, first_name, last_name FROM candidates"))
    rows = result.fetchall()
    for row in rows:
        cid, fn, ln = row[0], row[1] or "", row[2] or ""
        fn_latin = transliterate(fn) if fn and has_cyrillic(fn) else None
        ln_latin = transliterate(ln) if ln and has_cyrillic(ln) else None
        if fn_latin or ln_latin:
            conn.execute(
                text("""
                    UPDATE candidates SET
                        first_name_latin = :fn_latin,
                        last_name_latin = :ln_latin
                    WHERE id = :cid
                """),
                {"fn_latin": fn_latin, "ln_latin": ln_latin, "cid": cid},
            )


def downgrade() -> None:
    pass
