"""documents module baseline

Revision ID: 0001_documents_baseline
Revises:
Create Date: 2025-09-07

This is a sandbox migration file intended to be moved into the real Alembic environment later.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as psql

# revision identifiers, used by Alembic.
revision = "0001_documents_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- prerequisites: extensions & helper function for updated_at ---
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # --- document_types ---
    op.create_table(
        "document_types",
        sa.Column(
            "id",
            psql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "entity_scope", sa.Text(), nullable=False
        ),  # candidate|company|vacancy
        sa.Column(
            "meta_schema",
            psql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("number_regex", sa.Text(), nullable=True),
        sa.Column("default_validity_days", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")
        ),
        sa.Column(
            "created_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "entity_scope IN ('candidate','company','vacancy')",
            name="ck_document_types_scope",
        ),
        sa.UniqueConstraint("tenant_id", "code", name="uq_document_types_tenant_code"),
    )
    op.create_index(
        "ix_document_types_tenant_scope",
        "document_types",
        ["tenant_id", "entity_scope"],
    )

    op.execute(
        """
        CREATE TRIGGER document_types_set_updated_at
        BEFORE UPDATE ON document_types
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column(
            "id",
            psql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("document_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("owner_type", sa.Text(), nullable=False),  # candidate|company|vacancy
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'uploaded'")
        ),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column(
            "meta_json",
            psql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "owner_type IN ('candidate','company','vacancy')",
            name="ck_documents_owner_type",
        ),
        sa.CheckConstraint(
            "status IN ('missing','uploaded','approved','rejected','expired')",
            name="ck_documents_status",
        ),
    )
    op.create_index(
        "ix_documents_tenant_owner",
        "documents",
        ["tenant_id", "owner_type", "owner_id"],
    )
    op.create_index("ix_documents_tenant_type", "documents", ["tenant_id", "type_id"])
    op.create_index("ix_documents_tenant_status", "documents", ["tenant_id", "status"])
    op.create_index(
        "ix_documents_tenant_expires_at", "documents", ["tenant_id", "expires_at"]
    )
    op.create_index(
        "ix_documents_meta_gin",
        "documents",
        [sa.text("meta_json")],
        postgresql_using="gin",
    )

    op.execute(
        """
        CREATE TRIGGER documents_set_updated_at
        BEFORE UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # --- document_attachments ---
    op.create_table(
        "document_attachments",
        sa.Column(
            "id",
            psql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_document_attachments_doc", "document_attachments", ["document_id"]
    )

    # --- document_checks ---
    op.create_table(
        "document_checks",
        sa.Column(
            "id",
            psql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),  # approved|rejected|pending
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "decision IN ('approved','rejected','pending')",
            name="ck_document_checks_decision",
        ),
    )
    op.create_index("ix_document_checks_doc", "document_checks", ["document_id"])
    op.create_index("ix_document_checks_reviewer", "document_checks", ["reviewer_id"])

    # --- rulesets ---
    op.create_table(
        "rulesets",
        sa.Column(
            "id",
            psql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", psql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("json", psql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            psql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.execute(
        """
        CREATE TRIGGER rulesets_set_updated_at
        BEFORE UPDATE ON rulesets
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # Optional: safeguard to avoid multiple approved per type per owner (enforceable later)
    # We'll add a partial unique index in a follow-up migration if required by business rules.


def downgrade() -> None:
    # drop in reverse order
    op.execute("DROP TRIGGER IF EXISTS rulesets_set_updated_at ON rulesets;")
    op.drop_table("rulesets")

    op.drop_index("ix_document_checks_reviewer", table_name="document_checks")
    op.drop_index("ix_document_checks_doc", table_name="document_checks")
    op.drop_table("document_checks")

    op.drop_index("ix_document_attachments_doc", table_name="document_attachments")
    op.drop_table("document_attachments")

    op.execute("DROP TRIGGER IF EXISTS documents_set_updated_at ON documents;")
    op.drop_index("ix_documents_meta_gin", table_name="documents")
    op.drop_index("ix_documents_tenant_expires_at", table_name="documents")
    op.drop_index("ix_documents_tenant_status", table_name="documents")
    op.drop_index("ix_documents_tenant_type", table_name="documents")
    op.drop_index("ix_documents_tenant_owner", table_name="documents")
    op.drop_table("documents")

    op.execute(
        "DROP TRIGGER IF EXISTS document_types_set_updated_at ON document_types;"
    )
    op.drop_index("ix_document_types_tenant_scope", table_name="document_types")
    op.drop_table("document_types")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
    # keep pgcrypto extension (harmless), or drop if you must:
    # op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
