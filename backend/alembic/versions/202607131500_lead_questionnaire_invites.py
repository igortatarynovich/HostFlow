"""lead_questionnaire_invites — sales questionnaire token bound to existing Lead."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607131500_lqi"
down_revision: Union[str, None] = "202607131401_client_account_link_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "lead_questionnaire_invites" in insp.get_table_names():
        return

    op.create_table(
        "lead_questionnaire_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("lead_form_id", sa.String(length=36), nullable=True),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="not_sent"),
        sa.Column("entity_profile_code", sa.String(length=128), nullable=True),
        sa.Column("presentation_code", sa.String(length=128), nullable=True),
        sa.Column("apply_url", sa.String(length=512), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_form_id"], ["tenant_lead_forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_lead_questionnaire_invites_lead_id", "lead_questionnaire_invites", ["lead_id"])
    op.create_index("ix_lead_questionnaire_invites_tenant_id", "lead_questionnaire_invites", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_questionnaire_invites_tenant_id", table_name="lead_questionnaire_invites")
    op.drop_index("ix_lead_questionnaire_invites_lead_id", table_name="lead_questionnaire_invites")
    op.drop_table("lead_questionnaire_invites")
