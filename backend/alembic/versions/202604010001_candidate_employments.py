"""Add candidate_employments table for intake history.

Revision ID: 202604010001_candidate_employments
Revises: 202603250001_candidate_status_reason
Create Date: 2026-04-01 09:00:00.000000
"""

from __future__ import annotations

from typing import Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202604010001_candidate_employments"
down_revision = "202603250001_candidate_status_reason"
branch_labels = None
depends_on = None


def _json_type(dialect_name: str) -> Any:
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(dialect_name: str) -> sa.sql.elements.TextClause:
    if dialect_name == "postgresql":
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"
    json_type = _json_type(dialect)
    json_default = _json_default(dialect)

    op.create_table(
        "candidate_employments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("employer_name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("position", sa.String(length=255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("trailer_types", json_type, nullable=False, server_default=json_default),
        sa.Column("route_types", json_type, nullable=False, server_default=json_default),
        sa.Column("truck_brands", json_type, nullable=True),
        sa.Column("eu_routes", sa.Boolean(), nullable=True),
        sa.Column("reason_for_leaving", sa.Text(), nullable=True),
        sa.Column("reference_contact", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_candidate_employments_candidate_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_candidate_employments_tenant_id",
        "candidate_employments",
        ["tenant_id"],
    )
    op.create_index(
        "ix_candidate_employments_candidate_id",
        "candidate_employments",
        ["candidate_id"],
    )
    op.create_index(
        "ix_candidate_employments_tenant_candidate",
        "candidate_employments",
        ["tenant_id", "candidate_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_employments_tenant_candidate", table_name="candidate_employments")
    op.drop_index("ix_candidate_employments_candidate_id", table_name="candidate_employments")
    op.drop_index("ix_candidate_employments_tenant_id", table_name="candidate_employments")
    op.drop_table("candidate_employments")
