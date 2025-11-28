"""Unify documents schema and introduce document templates.

Revision ID: 202512150001_unify_documents_module
Revises: fe5d16892956_users_add_supervisor_id_user_
Create Date: 2025-12-15 10:00:00.000000
"""

from __future__ import annotations

import json
from typing import Iterable, Mapping, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202512150001_unify_documents_module"
down_revision = "fe5d16892956"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


DOCUMENT_KIND = ("driver", "employer", "process")
DOCUMENT_STATUS = (
    "missing",
    "requested",
    "in_progress",
    "received",
    "approved",
    "rejected",
    "expired",
)
DOCUMENT_REQUESTED_FROM = ("driver", "employer", "agency")
DOCUMENT_PROCESS_TYPE = (
    "none",
    "work_permit",
    "visa",
    "residence_card",
    "tachograph_card",
    "driver_license_exchange",
    "swiadectwo_kierowcy",
    "other",
)

DOC_TYPE_NORMALIZATION: Mapping[str, Mapping[str, str]] = {
    "identity_document": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": [
            "passport",
            "national_id",
            "identity_document",
            "id_card",
        ],
    },
    "driver_license": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": [
            "driver_license",
            "drivers_license_ce",
            "prawo_jazdy",
        ],
    },
    "code95": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": ["code95", "code_95"],
    },
    "tachograph_card": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "tachograph_card",
        "aliases": ["tachograph_card", "karta_tachografu", "tachograph"],
    },
    "medical_certificate": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": ["medical_certificate", "medical_cert", "badania_lekarskie"],
    },
    "criminal_record": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": ["criminal_record"],
    },
    "insurance_a1": {
        "kind": "driver",
        "requested_from": "employer",
        "process_type": "none",
        "aliases": ["insurance_a1", "insurance_confirmation"],
    },
    "photo": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": ["photo", "photo_id"],
    },
    "bank_account_confirmation": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": ["bank_account_confirmation", "bank_account_doc"],
    },
    "pesel": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
        "aliases": ["pesel", "pesel_confirm"],
    },
    "employment_contract": {
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
        "aliases": ["employment_contract", "umowa_o_prace"],
    },
    "work_assignment": {
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
        "aliases": ["work_assignment", "oswiadczenie"],
    },
    "employer_insurance": {
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
        "aliases": ["employer_insurance"],
    },
    "bhp_instruction": {
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
        "aliases": ["bhp_instruction", "szkolenia_bhp"],
    },
    "accommodation_declaration": {
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
        "aliases": ["accommodation_declaration", "accommodation"],
    },
    "work_permit": {
        "kind": "process",
        "requested_from": "agency",
        "process_type": "work_permit",
        "aliases": ["work_permit", "zezwolenie_a"],
    },
    "visa": {
        "kind": "process",
        "requested_from": "driver",
        "process_type": "visa",
        "aliases": ["visa", "visa_d", "entry_permit_or_visa"],
    },
    "residence_card": {
        "kind": "process",
        "requested_from": "driver",
        "process_type": "residence_card",
        "aliases": ["residence_card", "karta_pobytu"],
    },
    "swiadectwo_kierowcy": {
        "kind": "process",
        "requested_from": "agency",
        "process_type": "swiadectwo_kierowcy",
        "aliases": ["swiadectwo_kierowcy", "driver_attestation"],
    },
    "tachograph_exchange": {
        "kind": "process",
        "requested_from": "agency",
        "process_type": "tachograph_card",
        "aliases": ["tachograph_exchange"],
    },
    "driver_license_exchange": {
        "kind": "process",
        "requested_from": "agency",
        "process_type": "driver_license_exchange",
        "aliases": ["driver_license_exchange"],
    },
    "other": {
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "other",
        "aliases": ["other", "translation", "custom"],
    },
}


STATUS_MAPPING = {
    "planned": "missing",
    "pending": "requested",
    "pending_validation": "in_progress",
    "submitted": "in_progress",
    "upload": "received",
    "uploaded": "received",
    "received": "received",
    "ready": "approved",
    "approved": "approved",
    "verified": "approved",
    "invalid": "rejected",
    "rejected": "rejected",
    "expired": "expired",
}


def _has_table(inspector: sa.Inspector, table: str) -> bool:
    try:
        return table in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    try:
        return any(col.get("name") == column for col in inspector.get_columns(table))
    except Exception:
        return False


def _lower_aliases(aliases: Iterable[str]) -> Sequence[str]:
    return sorted({alias.lower() for alias in aliases})


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)

    kind_enum = postgresql.ENUM(*DOCUMENT_KIND, name="document_kind_enum", create_type=False)
    status_enum = postgresql.ENUM(*DOCUMENT_STATUS, name="document_status_enum_v2", create_type=False)
    req_enum = postgresql.ENUM(*DOCUMENT_REQUESTED_FROM, name="document_requested_from_enum", create_type=False)
    process_enum = postgresql.ENUM(*DOCUMENT_PROCESS_TYPE, name="document_process_type_enum", create_type=False)

    for enum_type in (kind_enum, status_enum, req_enum, process_enum):
        enum_type.create(bind, checkfirst=True)

    # Drop legacy indexes before renaming columns
    for idx in ("ix_documents_type", "ix_documents_tenant_candidate_type"):
        try:
            op.drop_index(idx, table_name="documents")
        except sa.exc.SQLAlchemyError:
            pass

    if _has_column(inspector, "documents", "type") and not _has_column(inspector, "documents", "doc_type"):
        op.alter_column("documents", "type", new_column_name="doc_type", existing_type=sa.String(length=100))

    if _has_column(inspector, "documents", "issued_at"):
        op.alter_column("documents", "issued_at", new_column_name="issue_date")
        op.alter_column(
            "documents",
            "issue_date",
            type_=sa.Date(),
            existing_type=sa.DateTime(timezone=True),
            postgresql_using="issue_date::date",
        )

    if _has_column(inspector, "documents", "expires_at"):
        op.alter_column("documents", "expires_at", new_column_name="expire_date")
        op.alter_column(
            "documents",
            "expire_date",
            type_=sa.Date(),
            existing_type=sa.DateTime(timezone=True),
            postgresql_using="expire_date::date",
        )

    # Add new structural columns (guarded for idempotency)
    if not _has_column(inspector, "documents", "company_id"):
        op.add_column("documents", sa.Column("company_id", sa.String(length=36), nullable=True))
    if not _has_column(inspector, "documents", "kind"):
        op.add_column(
            "documents",
            sa.Column(
                "kind",
                kind_enum,
                nullable=False,
                server_default="driver",
            ),
        )
    if not _has_column(inspector, "documents", "custom_name"):
        op.add_column("documents", sa.Column("custom_name", sa.String(length=255), nullable=True))
    if not _has_column(inspector, "documents", "requested_from"):
        op.add_column(
            "documents",
            sa.Column(
                "requested_from",
                req_enum,
                nullable=False,
                server_default="driver",
            ),
        )
    if not _has_column(inspector, "documents", "process_type"):
        op.add_column(
            "documents",
            sa.Column(
                "process_type",
                process_enum,
                nullable=False,
                server_default="none",
            ),
        )
    if not _has_column(inspector, "documents", "workflow"):
        op.add_column(
            "documents",
            sa.Column("workflow", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    if not _has_column(inspector, "documents", "status_new"):
        op.add_column(
            "documents",
            sa.Column(
                "status_new",
                status_enum,
                nullable=False,
                server_default="missing",
            ),
        )

    if not _has_column(inspector, "documents", "meta"):
        op.add_column(
            "documents",
            sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    # Normalise doc_type values
    if _has_column(inspector, "documents", "doc_type"):
        op.execute("UPDATE documents SET doc_type = COALESCE(NULLIF(lower(doc_type), ''), 'other')")

        for canonical, info in DOC_TYPE_NORMALIZATION.items():
            aliases = _lower_aliases(info["aliases"])
            placeholders = ", ".join(f"'{alias}'" for alias in aliases)
            bind.execute(
                sa.text(
                    f"""
                    UPDATE documents
                    SET doc_type = :canonical
                    WHERE doc_type IN ({placeholders})
                    """
                ),
                {"canonical": canonical},
            )

        # Default doc_type when still empty
        op.execute("UPDATE documents SET doc_type = 'other' WHERE doc_type IS NULL OR doc_type = ''")

    # Merge extra/meta_json into meta JSONB
    existing_cols = {col["name"] for col in inspector.get_columns("documents")}
    if "meta" in existing_cols:
        if "extra" in existing_cols:
            op.execute(
                """
                UPDATE documents
                SET meta = COALESCE(meta, extra::jsonb)
                WHERE extra IS NOT NULL
                """
            )
        if "meta_json" in existing_cols:
            op.execute(
                """
                UPDATE documents
                SET meta = COALESCE(
                    meta,
                    CASE
                        WHEN meta_json IS NULL OR trim(meta_json) = '' THEN '{}'::jsonb
                        ELSE meta_json::jsonb
                    END
                )
                """
            )

    # Ensure meta is at least empty object
    if _has_column(inspector, "documents", "meta"):
        op.execute("UPDATE documents SET meta = '{}'::jsonb WHERE meta IS NULL")

    # Update status values into new enum column
    if _has_column(inspector, "documents", "status_new"):
        status_cases = " ".join(
            f"WHEN lower(status) = '{old}' THEN '{new}'" for old, new in STATUS_MAPPING.items()
        )
        op.execute(
            f"""
            UPDATE documents
            SET status_new = CAST(CASE
                {status_cases}
                ELSE 'missing'
            END AS document_status_enum_v2)
            """
        )

    # Derive kind/requested_from/process_type from doc_type
    if _has_column(inspector, "documents", "doc_type"):
        for canonical, info in DOC_TYPE_NORMALIZATION.items():
            bind.execute(
                sa.text(
                    """
                    UPDATE documents
                    SET kind = :kind,
                        requested_from = :requested_from,
                        process_type = :process_type
                    WHERE doc_type = :canonical
                    """
                ),
                {
                    "kind": info["kind"],
                    "requested_from": info["requested_from"],
                    "process_type": info["process_type"],
                    "canonical": canonical,
                },
            )

    # Fallbacks for anything unmapped
    op.execute("UPDATE documents SET kind = 'driver' WHERE kind IS NULL")
    op.execute("UPDATE documents SET requested_from = 'driver' WHERE requested_from IS NULL")
    op.execute("UPDATE documents SET process_type = 'other' WHERE process_type IS NULL")

    # Replace old status column
    if _has_column(inspector, "documents", "status"):
        op.drop_column("documents", "status")
    if _has_column(inspector, "documents", "status_new"):
        op.alter_column("documents", "status_new", new_column_name="status", server_default=None)

    # Convert files column to JSONB if present
    if _has_column(inspector, "documents", "files"):
        op.alter_column(
            "documents",
            "files",
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_type=sa.JSON(),
            postgresql_using="files::jsonb",
        )

    # Drop legacy columns superseded by meta
    for legacy in ("extra", "meta_json"):
        if _has_column(inspector, "documents", legacy):
            op.drop_column("documents", legacy)

    # Drop server defaults introduced for backfill
    if _has_column(inspector, "documents", "kind"):
        op.alter_column("documents", "kind", server_default=None)
    if _has_column(inspector, "documents", "requested_from"):
        op.alter_column("documents", "requested_from", server_default=None)
    if _has_column(inspector, "documents", "process_type"):
        op.alter_column("documents", "process_type", server_default=None)

    # Recreate indices on doc_type
    if _has_column(inspector, "documents", "doc_type"):
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("documents")}
        if "ix_documents_doc_type" not in existing_indexes:
            op.create_index("ix_documents_doc_type", "documents", ["doc_type"])
        if "ix_documents_tenant_candidate_doc_type" not in existing_indexes:
            op.create_index(
                "ix_documents_tenant_candidate_doc_type",
                "documents",
                ["tenant_id", "candidate_id", "doc_type"],
            )

    # Create document_templates table
    if not _has_table(inspector, "document_templates"):
        op.create_table(
            "document_templates",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_unique_constraint(
            "uq_document_templates_tenant_code",
            "document_templates",
            ("tenant_id", "code"),
        )
        op.create_index("ix_document_templates_tenant_id", "document_templates", ["tenant_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Remove templates table
    op.drop_index("ix_document_templates_tenant_id", table_name="document_templates")
    op.drop_constraint("uq_document_templates_tenant_code", "document_templates", type_="unique")
    op.drop_table("document_templates")

    # Drop new indexes
    for idx in ("ix_documents_doc_type", "ix_documents_tenant_candidate_doc_type"):
        try:
            op.drop_index(idx, table_name="documents")
        except sa.exc.SQLAlchemyError:
            pass

    # Recreate legacy columns for downgrade compatibility
    op.add_column(
        "documents",
        sa.Column("extra", sa.JSON(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("meta_json", sa.Text(), nullable=False, server_default="{}"),
    )

    if _has_column(inspector, "documents", "meta"):
        op.execute(
            """
            UPDATE documents
            SET extra = meta::json,
                meta_json = COALESCE(meta::text, '{}')
            """
        )
        op.drop_column("documents", "meta")

    # Revert files column to JSON
    if _has_column(inspector, "documents", "files"):
        op.alter_column(
            "documents",
            "files",
            type_=sa.JSON(),
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            postgresql_using="files::json",
        )

    # Restore legacy status column as text
    op.add_column(
        "documents",
        sa.Column("status_old", sa.String(length=50), nullable=False, server_default="pending_validation"),
    )
    op.execute(
        """
        UPDATE documents
        SET status_old = CASE status
            WHEN 'missing' THEN 'planned'
            WHEN 'requested' THEN 'pending_validation'
            WHEN 'in_progress' THEN 'pending_validation'
            WHEN 'received' THEN 'received'
            WHEN 'approved' THEN 'approved'
            WHEN 'rejected' THEN 'invalid'
            WHEN 'expired' THEN 'expired'
            ELSE 'pending_validation'
        END
        """
    )
    op.drop_column("documents", "status")
    op.alter_column(
        "documents",
        "status_old",
        new_column_name="status",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default="pending_validation",
    )

    # Remove newly added columns
    for column in (
        "workflow",
        "process_type",
        "requested_from",
        "custom_name",
        "kind",
        "company_id",
    ):
        if _has_column(inspector, "documents", column):
            op.drop_column("documents", column)

    # Rename columns back
    if _has_column(inspector, "documents", "doc_type"):
        op.alter_column("documents", "doc_type", new_column_name="type")
    if _has_column(inspector, "documents", "issue_date"):
        op.alter_column(
            "documents",
            "issue_date",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.Date(),
            postgresql_using="issue_date::timestamp",
        )
        op.alter_column("documents", "issue_date", new_column_name="issued_at")
    if _has_column(inspector, "documents", "expire_date"):
        op.alter_column(
            "documents",
            "expire_date",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.Date(),
            postgresql_using="expire_date::timestamp",
        )
        op.alter_column("documents", "expire_date", new_column_name="expires_at")

    # Recreate old indexes
    op.create_index("ix_documents_type", "documents", ["type"])
    op.create_index(
        "ix_documents_tenant_candidate_type",
        "documents",
        ["tenant_id", "candidate_id", "type"],
    )

    # Drop new enum types
    for enum_name in (
        "document_process_type_enum",
        "document_requested_from_enum",
        "document_status_enum_v2",
        "document_kind_enum",
    ):
        try:
            postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
        except sa.exc.SQLAlchemyError:
            pass
