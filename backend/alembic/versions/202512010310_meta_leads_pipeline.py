"""Meta leads ingestion pipeline.

- Adds leads + meta_ads_map tables.
- Extends candidates with source/origin fields.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "202512010310_meta_leads_pipeline"
down_revision = "202512010300_recruiter_assignment"
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("origin", JSONType, nullable=True),
    )

    op.create_table(
        "meta_ads_map",
        sa.Column("ad_id", sa.BigInteger(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column(
            "vacancy_id",
            sa.String(length=36),
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_meta_ads_map_tenant", "meta_ads_map", ["tenant_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column(
            "company_id",
            sa.String(length=36),
            sa.ForeignKey("companies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vacancy_id",
            sa.String(length=36),
            sa.ForeignKey("vacancies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=sa.text("'meta'")),
        sa.Column("ad_id", sa.BigInteger(), nullable=True),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("normalized", JSONType, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'new'")),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_leads_tenant", "leads", ["tenant_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_vacancy", "leads", ["vacancy_id"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "ix_leads_payload_gin",
            "leads",
            ["payload"],
            postgresql_using="gin",
        )
        op.create_index(
            "ix_leads_normalized_gin",
            "leads",
            ["normalized"],
            postgresql_using="gin",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("ix_leads_normalized_gin", table_name="leads")
        op.drop_index("ix_leads_payload_gin", table_name="leads")

    op.drop_index("ix_leads_vacancy", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_tenant", table_name="leads")
    op.drop_table("leads")

    op.drop_index("ix_meta_ads_map_tenant", table_name="meta_ads_map")
    op.drop_table("meta_ads_map")

    op.drop_column("candidates", "origin")
    op.drop_column("candidates", "source")
