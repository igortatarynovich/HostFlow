"""Versioned Entity Profile field/document requirement bindings.

Revision ID: 202610100001_entity_profile_version_bindings
Revises: 202610090001_entity_profile_publication_versions

ADR-043 Slice 2: immutable requirement bindings against published
Entity Profile Version identity.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610100001_entity_profile_version_bindings"
down_revision: Union[str, None] = "202610090001_entity_profile_publication_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ep_entity_profile_version_fields",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_profile_version_id", sa.String(length=36), nullable=False),
        sa.Column("canonical_field_id", sa.String(length=36), nullable=False),
        sa.Column("qualified_code", sa.String(length=191), nullable=False),
        sa.Column("requirement_level", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(
            ["entity_profile_version_id"],
            ["ep_entity_profile_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_field_id"],
            ["fr_canonical_fields.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_profile_version_id",
            "canonical_field_id",
            name="uq_ep_profile_version_fields_version_field",
        ),
    )
    op.create_index(
        "ix_ep_prof_ver_fields_version",
        "ep_entity_profile_version_fields",
        ["entity_profile_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_ep_prof_ver_fields_field",
        "ep_entity_profile_version_fields",
        ["canonical_field_id"],
        unique=False,
    )

    op.create_table(
        "ep_entity_profile_version_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_profile_version_id", sa.String(length=36), nullable=False),
        sa.Column("document_type_version_id", sa.String(length=36), nullable=False),
        sa.Column("requirement_level", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(
            ["entity_profile_version_id"],
            ["ep_entity_profile_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_type_version_id"],
            ["ref_document_type_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_profile_version_id",
            "document_type_version_id",
            name="uq_ep_profile_version_documents_version_doc",
        ),
    )
    op.create_index(
        "ix_ep_prof_ver_docs_version",
        "ep_entity_profile_version_documents",
        ["entity_profile_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_ep_prof_ver_docs_docver",
        "ep_entity_profile_version_documents",
        ["document_type_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ep_prof_ver_docs_docver",
        table_name="ep_entity_profile_version_documents",
    )
    op.drop_index(
        "ix_ep_prof_ver_docs_version",
        table_name="ep_entity_profile_version_documents",
    )
    op.drop_table("ep_entity_profile_version_documents")

    op.drop_index(
        "ix_ep_prof_ver_fields_field",
        table_name="ep_entity_profile_version_fields",
    )
    op.drop_index(
        "ix_ep_prof_ver_fields_version",
        table_name="ep_entity_profile_version_fields",
    )
    op.drop_table("ep_entity_profile_version_fields")
