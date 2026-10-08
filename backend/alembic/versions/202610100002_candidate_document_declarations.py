"""add recruitment candidate document declarations

Revision ID: 202610100002_candidate_document_declarations
Revises: 202610100001_entity_profile_version_bindings
"""

from alembic import op
import sqlalchemy as sa


revision = "202610100002_candidate_document_declarations"
down_revision = "202610100001_entity_profile_version_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recruitment_candidate_document_declarations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("entity_profile_version_id", sa.String(length=36), nullable=False),
        sa.Column("document_type_version_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('unknown', 'does_not_have', 'has_document', 'upload_requested')",
            name="ck_recruitment_candidate_doc_declaration_state",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["entity_profile_version_id"],
            ["ep_entity_profile_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_type_version_id"],
            ["ref_document_type_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "candidate_id",
            "entity_profile_version_id",
            "document_type_version_id",
            name="uq_recruitment_candidate_doc_declaration_scope",
        ),
    )

    op.create_index(
        op.f("ix_recruitment_candidate_document_declarations_tenant_id"),
        "recruitment_candidate_document_declarations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recruitment_candidate_document_declarations_candidate_id"),
        "recruitment_candidate_document_declarations",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recruitment_candidate_document_declarations_entity_profile_version_id"),
        "recruitment_candidate_document_declarations",
        ["entity_profile_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recruitment_candidate_document_declarations_document_type_version_id"),
        "recruitment_candidate_document_declarations",
        ["document_type_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recruitment_candidate_document_declarations_document_type_version_id"),
        table_name="recruitment_candidate_document_declarations",
    )
    op.drop_index(
        op.f("ix_recruitment_candidate_document_declarations_entity_profile_version_id"),
        table_name="recruitment_candidate_document_declarations",
    )
    op.drop_index(
        op.f("ix_recruitment_candidate_document_declarations_candidate_id"),
        table_name="recruitment_candidate_document_declarations",
    )
    op.drop_index(
        op.f("ix_recruitment_candidate_document_declarations_tenant_id"),
        table_name="recruitment_candidate_document_declarations",
    )
    op.drop_table("recruitment_candidate_document_declarations")
