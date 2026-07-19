"""202607190001_forms_p24 — Builder draft persistence (P2.4).

Revision ID: 202607190001_forms_p24
Revises: 202607180009_forms_s6
Create Date: 2026-07-19

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607190001_forms_p24"
down_revision: RevisionType = "202607180009_forms_s6"
branch_labels: RevisionType = None
depends_on: RevisionType = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "form_builder_drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=64), nullable=False),
        sa.Column("form_id", sa.String(length=36), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("composition_contract", sa.String(length=64), nullable=False),
        sa.Column("composition", _JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "draft_id", name="uq_form_builder_drafts_tenant_draft"),
    )
    op.create_index("ix_form_builder_drafts_tenant_id", "form_builder_drafts", ["tenant_id"])
    op.create_index("ix_form_builder_drafts_form_id", "form_builder_drafts", ["form_id"])
    op.create_index(
        "ix_form_builder_drafts_tenant_status",
        "form_builder_drafts",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_form_builder_drafts_tenant_updated",
        "form_builder_drafts",
        ["tenant_id", "updated_at"],
    )

    op.create_table(
        "form_builder_draft_revisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("composition_contract", sa.String(length=64), nullable=False),
        sa.Column("composition", _JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "draft_id",
            "revision",
            name="uq_form_builder_draft_revs_tenant_draft_rev",
        ),
    )
    op.create_index(
        "ix_form_builder_draft_revs_tenant_id",
        "form_builder_draft_revisions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_form_builder_draft_revs_tenant_draft",
        "form_builder_draft_revisions",
        ["tenant_id", "draft_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_form_builder_draft_revs_tenant_draft",
        table_name="form_builder_draft_revisions",
    )
    op.drop_index(
        "ix_form_builder_draft_revs_tenant_id",
        table_name="form_builder_draft_revisions",
    )
    op.drop_table("form_builder_draft_revisions")
    op.drop_index("ix_form_builder_drafts_tenant_updated", table_name="form_builder_drafts")
    op.drop_index("ix_form_builder_drafts_tenant_status", table_name="form_builder_drafts")
    op.drop_index("ix_form_builder_drafts_form_id", table_name="form_builder_drafts")
    op.drop_index("ix_form_builder_drafts_tenant_id", table_name="form_builder_drafts")
    op.drop_table("form_builder_drafts")
