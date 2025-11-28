"""Add structured metadata columns to document_types

Revision ID: 202604020001_document_type_structured_fields
Revises: 202604010001_candidate_employments
Create Date: 2026-04-02 11:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202604020001_document_type_structured_fields"
down_revision = "202604010001_candidate_employments"
branch_labels = None
depends_on = None


def _json_type(dialect_name: str) -> Any:
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(dialect_name: str) -> sa.sql.elements.TextClause:
    if dialect_name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


duplicate_policy_enum = sa.Enum(
    "one_per_candidate",
    "many_allowed",
    name="document_duplicate_policy_enum",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    json_type = _json_type(dialect)
    json_default = _json_default(dialect)

    duplicate_policy_enum.create(bind, checkfirst=True)

    op.add_column(
        "document_types",
        sa.Column("title", json_type, nullable=False, server_default=json_default),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "metadata_schema",
            json_type,
            nullable=False,
            server_default=json_default,
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "required_files",
            json_type,
            nullable=False,
            server_default=json_default,
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "expiry_rule",
            json_type,
            nullable=False,
            server_default=json_default,
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "duplicate_policy",
            duplicate_policy_enum,
            nullable=False,
            server_default=sa.text("'one_per_candidate'"),
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "orderable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0" if dialect == "sqlite" else "false"),
        ),
    )

    rows = bind.execute(
        sa.text("SELECT id, COALESCE(name, code) AS label FROM document_types")
    ).fetchall()
    if rows:
        if dialect == "postgresql":
            stmt_pg = sa.text(
                "UPDATE document_types SET title = jsonb_build_object('en', :label) WHERE id = :id"
            ).bindparams(sa.bindparam("label", type_=sa.Text()))
            for row in rows:
                bind.execute(stmt_pg, {"label": row.label, "id": row.id})
        else:
            stmt_sqlite = sa.text(
                "UPDATE document_types SET title = :payload WHERE id = :id"
            )
            for row in rows:
                payload = json.dumps({"en": row.label})
                bind.execute(stmt_sqlite, {"payload": payload, "id": row.id})


def downgrade() -> None:
    op.drop_column("document_types", "orderable")
    op.drop_column("document_types", "duplicate_policy")
    op.drop_column("document_types", "expiry_rule")
    op.drop_column("document_types", "required_files")
    op.drop_column("document_types", "metadata_schema")
    op.drop_column("document_types", "title")
    duplicate_policy_enum.drop(op.get_bind(), checkfirst=True)
