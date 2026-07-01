"""Add public link fields to intake source profiles.

Revision ID: 202608200002_intake_source_profiles_public_link
Revises: 202608200001_leads_converted_client_id
Create Date: 2026-08-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202608200002_intake_source_profiles_public_link"
down_revision: Union[str, Sequence[str], None] = "202608200001_leads_converted_client_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("public_slug", sa.Column("public_slug", sa.String(length=64), nullable=True)),
    ("form_type", sa.Column("form_type", sa.String(length=64), nullable=True)),
    ("lead_type", sa.Column("lead_type", sa.String(length=32), nullable=True)),
    ("lead_target_type", sa.Column("lead_target_type", sa.String(length=32), nullable=True)),
    ("source", sa.Column("source", sa.String(length=64), nullable=True)),
    ("supported_languages", sa.Column("supported_languages", sa.String(length=64), nullable=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "intake_source_profiles" not in insp.get_table_names():
        return
    dialect = bind.dialect.name
    if dialect == "postgresql":
        for name, column in _COLUMNS:
            op.execute(
                f"ALTER TABLE intake_source_profiles ADD COLUMN IF NOT EXISTS {name} "
                f"{column.type.compile(dialect=bind.dialect)}"
            )
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_intake_source_profiles_public_slug "
            "ON intake_source_profiles (public_slug) WHERE public_slug IS NOT NULL AND public_slug <> ''"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_intake_source_profiles_public_slug "
            "ON intake_source_profiles (public_slug)"
        )
        return

    cols = {c["name"] for c in insp.get_columns("intake_source_profiles")}
    for name, column in _COLUMNS:
        if name not in cols:
            op.add_column("intake_source_profiles", column)
    indexes = {idx["name"] for idx in insp.get_indexes("intake_source_profiles")}
    if "ix_intake_source_profiles_public_slug" not in indexes:
        op.create_index(
            "ix_intake_source_profiles_public_slug",
            "intake_source_profiles",
            ["public_slug"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "intake_source_profiles" not in insp.get_table_names():
        return
    indexes = {idx["name"] for idx in insp.get_indexes("intake_source_profiles")}
    if "ix_intake_source_profiles_public_slug" in indexes:
        op.drop_index("ix_intake_source_profiles_public_slug", table_name="intake_source_profiles")
    cols = {c["name"] for c in insp.get_columns("intake_source_profiles")}
    for name, _column in reversed(_COLUMNS):
        if name in cols:
            op.drop_column("intake_source_profiles", name)
