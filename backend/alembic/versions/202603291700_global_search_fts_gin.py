"""Global search FTS helper function (§2.6) — hostflow_simple_tsvector

Revision ID: 202603291700_gs_fts_gin
Revises: 202603291600_doc_ruleset_oc
Create Date: 2026-03-29

``to_tsvector(regconfig, text)`` is **STABLE** in PostgreSQL. A thin SQL wrapper
marked **IMMUTABLE** is enough for **queries** (``GET /search`` uses
``hostflow_simple_tsvector`` in SQLAlchemy).

**GIN indexes** on ``hostflow_simple_tsvector(...)`` are **not** applied here:
PostgreSQL 15+ validates index expressions and rejects any chain that ultimately
calls ``to_tsvector`` (still STABLE inside the wrapper body). A C-level immutable
wrapper or a maintained ``tsvector`` column would be needed for GIN; seq scans
remain correct, only slower at large table sizes.

"""
from typing import Sequence, Union

from alembic import op

revision: str = "202603291700_gs_fts_gin"
down_revision: Union[str, None] = "202603291600_doc_ruleset_oc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hostflow_simple_tsvector(content text)
        RETURNS tsvector
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        AS $f$
          SELECT to_tsvector('pg_catalog.simple'::regconfig, COALESCE(content, ''));
        $f$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS hostflow_simple_tsvector(text)")
