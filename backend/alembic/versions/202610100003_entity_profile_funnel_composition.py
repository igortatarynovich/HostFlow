"""add Entity Profile Funnel composition

Revision ID: 202610100003_entity_profile_funnel_composition
Revises: 202610100002_candidate_document_declarations
"""

from alembic import op
import sqlalchemy as sa


revision = "202610100003_entity_profile_funnel_composition"
down_revision = "202610100002_candidate_document_declarations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ep_entity_profiles",
        sa.Column("funnel_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_ep_entity_profiles_funnel_id_funnels",
        "ep_entity_profiles",
        "funnels",
        ["funnel_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_ep_entity_profiles_funnel_id"),
        "ep_entity_profiles",
        ["funnel_id"],
        unique=False,
    )

    op.add_column(
        "ep_entity_profile_versions",
        sa.Column("funnel_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_ep_entity_profile_versions_funnel_id_funnels",
        "ep_entity_profile_versions",
        "funnels",
        ["funnel_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_ep_entity_profile_versions_funnel_id"),
        "ep_entity_profile_versions",
        ["funnel_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ep_entity_profile_versions_funnel_id"),
        table_name="ep_entity_profile_versions",
    )
    op.drop_constraint(
        "fk_ep_entity_profile_versions_funnel_id_funnels",
        "ep_entity_profile_versions",
        type_="foreignkey",
    )
    op.drop_column("ep_entity_profile_versions", "funnel_id")

    op.drop_index(
        op.f("ix_ep_entity_profiles_funnel_id"),
        table_name="ep_entity_profiles",
    )
    op.drop_constraint(
        "fk_ep_entity_profiles_funnel_id_funnels",
        "ep_entity_profiles",
        type_="foreignkey",
    )
    op.drop_column("ep_entity_profiles", "funnel_id")
