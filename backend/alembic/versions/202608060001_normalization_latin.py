"""Add countries table and *_latin columns for normalization.

Revision ID: 202608060001
Revises: 202608050001_tenant_email_config
Create Date: 2026-08-06 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608060001_normalization_latin"
down_revision: RevisionType = "202608050001_tenant_email_config"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _has_table(conn, "countries"):
        op.create_table(
            "countries",
            sa.Column("iso2", sa.String(length=8), primary_key=True, nullable=False),
            sa.Column("name_pl", sa.String(length=128), nullable=False),
            sa.Column("name_en", sa.String(length=128), nullable=False),
            sa.Column("aliases", JSONB, nullable=True, comment="JSON array of alternate names/codes"),
        )
        op.execute("""
            INSERT INTO countries (iso2, name_pl, name_en) VALUES
            ('PL', 'Polska', 'Poland'),
            ('UA', 'Ukraina', 'Ukraine'),
            ('BY', 'Białoruś', 'Belarus'),
            ('RU', 'Rosja', 'Russia'),
            ('LT', 'Litwa', 'Lithuania'),
            ('LV', 'Lotwa', 'Latvia'),
            ('EE', 'Estonia', 'Estonia'),
            ('MD', 'Moldova', 'Moldova'),
            ('GE', 'Gruzja', 'Georgia'),
            ('KZ', 'Kazachstan', 'Kazakhstan'),
            ('DE', 'Niemcy', 'Germany'),
            ('CZ', 'Czechy', 'Czech Republic'),
            ('SK', 'Slovakia', 'Slovakia'),
            ('GB', 'Wielka Brytania', 'United Kingdom'),
            ('XX', 'Inne', 'Other')
        """)

    if _has_table(conn, "candidates"):
        for col in ("first_name_latin", "last_name_latin"):
            if not _has_column(conn, "candidates", col):
                op.add_column(
                    "candidates",
                    sa.Column(col, sa.String(length=256), nullable=True),
                )


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    if _has_table(conn, "candidates"):
        for col in ("first_name_latin", "last_name_latin"):
            if _has_column(conn, "candidates", col):
                op.drop_column("candidates", col)
    if _has_table(conn, "countries"):
        op.drop_table("countries")
