"""202607180009_forms_s6 — append-only form submission envelopes.

Revision ID: 202607180009_forms_s6
Revises: 202607180008_forms_s3
Create Date: 2026-07-18

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180009_forms_s6"
down_revision: RevisionType = "202607180008_forms_s3"
branch_labels: RevisionType = None
depends_on: RevisionType = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "form_submission_envelopes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("form_id", sa.String(length=36), nullable=False),
        sa.Column("published_version", sa.Integer(), nullable=False),
        sa.Column("schema_contract", sa.String(length=64), nullable=True),
        sa.Column("answer_contract", sa.String(length=64), nullable=False),
        sa.Column("raw_values", _JSON, nullable=False),
        sa.Column("normalized_values", _JSON, nullable=False),
        sa.Column("errors", _JSON, nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("intake_handoff", _JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["tenant_lead_forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_form_sub_env_tenant_id", "form_submission_envelopes", ["tenant_id"])
    op.create_index("ix_form_sub_env_form_id", "form_submission_envelopes", ["form_id"])
    op.create_index(
        "ix_form_sub_env_tenant_form",
        "form_submission_envelopes",
        ["tenant_id", "form_id"],
    )
    op.create_index(
        "ix_form_sub_env_tenant_created",
        "form_submission_envelopes",
        ["tenant_id", "created_at"],
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX ix_form_sub_env_idem "
                "ON form_submission_envelopes (tenant_id, form_id, idempotency_key) "
                "WHERE idempotency_key IS NOT NULL"
            )
        )
    else:
        op.create_index(
            "ix_form_sub_env_idem",
            "form_submission_envelopes",
            ["tenant_id", "form_id", "idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_form_sub_env_idem", table_name="form_submission_envelopes")
    op.drop_index("ix_form_sub_env_tenant_created", table_name="form_submission_envelopes")
    op.drop_index("ix_form_sub_env_tenant_form", table_name="form_submission_envelopes")
    op.drop_index("ix_form_sub_env_form_id", table_name="form_submission_envelopes")
    op.drop_index("ix_form_sub_env_tenant_id", table_name="form_submission_envelopes")
    op.drop_table("form_submission_envelopes")
