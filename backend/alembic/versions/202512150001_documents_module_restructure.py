"""Restructure documents module to unified model.

Revision ID: 202512150001_documents_module_restructure
Revises: 202512010200_admin_v2
Create Date: 2025-12-15 09:00:00.000000
"""

from __future__ import annotations

import json
from typing import Iterable, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202512150001_documents_module_restructure"
down_revision = "202512010200_admin_v2"
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

DOC_NORMALIZATION = [
    {
        "target": "identity_document",
        "aliases": ("identity_document", "passport", "national_id", "id_card"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "driver_license",
        "aliases": ("driver_license", "drivers_license_ce", "prawo_jazdy"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "code95",
        "aliases": ("code95", "code_95"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "tachograph_card",
        "aliases": ("tachograph_card", "karta_tachografu", "tachograph"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "tachograph_card",
    },
    {
        "target": "medical_certificate",
        "aliases": ("medical_certificate", "medical_cert", "badania_lekarskie"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "criminal_record",
        "aliases": ("criminal_record",),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "insurance_a1",
        "aliases": ("insurance_a1", "insurance_confirmation"),
        "kind": "driver",
        "requested_from": "employer",
        "process_type": "none",
    },
    {
        "target": "photo",
        "aliases": ("photo", "photo_id"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "bank_account_confirmation",
        "aliases": ("bank_account_confirmation", "bank_account_doc"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "pesel",
        "aliases": ("pesel", "pesel_confirm"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "none",
    },
    {
        "target": "employment_contract",
        "aliases": ("employment_contract", "umowa_o_prace"),
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
    },
    {
        "target": "work_assignment",
        "aliases": ("work_assignment", "oswiadczenie"),
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
    },
    {
        "target": "employer_insurance",
        "aliases": ("employer_insurance", "employer_insurance_confirmation"),
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
    },
    {
        "target": "bhp_instruction",
        "aliases": ("bhp_instruction", "szkolenia_bhp"),
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
    },
    {
        "target": "accommodation_declaration",
        "aliases": ("accommodation_declaration", "accommodation"),
        "kind": "employer",
        "requested_from": "employer",
        "process_type": "none",
    },
    {
        "target": "work_permit",
        "aliases": ("work_permit", "zezwolenie_a"),
        "kind": "process",
        "requested_from": "agency",
        "process_type": "work_permit",
    },
    {
        "target": "visa",
        "aliases": ("visa", "visa_d", "entry_permit_or_visa"),
        "kind": "process",
        "requested_from": "driver",
        "process_type": "visa",
    },
    {
        "target": "residence_card",
        "aliases": ("residence_card", "karta_pobytu"),
        "kind": "process",
        "requested_from": "driver",
        "process_type": "residence_card",
    },
    {
        "target": "swiadectwo_kierowcy",
        "aliases": ("swiadectwo_kierowcy", "driver_attestation"),
        "kind": "process",
        "requested_from": "agency",
        "process_type": "swiadectwo_kierowcy",
    },
    {
        "target": "tachograph_exchange",
        "aliases": ("tachograph_exchange",),
        "kind": "process",
        "requested_from": "agency",
        "process_type": "tachograph_card",
    },
    {
        "target": "driver_license_exchange",
        "aliases": ("driver_license_exchange",),
        "kind": "process",
        "requested_from": "agency",
        "process_type": "driver_license_exchange",
    },
    {
        "target": "other",
        "aliases": ("other", "custom", "translation"),
        "kind": "driver",
        "requested_from": "driver",
        "process_type": "other",
    },
]


def _lower_aliases(aliases: Iterable[str]) -> tuple[str, ...]:
    return tuple({alias.lower() for alias in aliases})


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("documents")}

    # --- Create enums ---
    kind_enum = postgresql.ENUM(*DOCUMENT_KIND, name="document_kind_enum", create_type=False)
    status_enum = postgresql.ENUM(*DOCUMENT_STATUS, name="document_status_enum_v2", create_type=False)
    requested_from_enum = postgresql.ENUM(
        *DOCUMENT_REQUESTED_FROM, name="document_requested_from_enum", create_type=False
    )
    process_type_enum = postgresql.ENUM(
        *DOCUMENT_PROCESS_TYPE, name="document_process_type_enum", create_type=False
    )

    for enum_type in (kind_enum, status_enum, requested_from_enum, process_type_enum):
        enum_type.create(bind, checkfirst=True)

    # --- Rename columns ---
    if "type" in existing_cols and "doc_type" not in existing_cols:
        op.alter_column("documents", "type", new_column_name="doc_type")
        existing_cols.discard("type")
        existing_cols.add("doc_type")
    if "issued_at" in existing_cols and "issue_date" not in existing_cols:
        op.alter_column("documents", "issued_at", new_column_name="issue_date")
        existing_cols.discard("issued_at")
        existing_cols.add("issue_date")
    if "expires_at" in existing_cols and "expire_date" not in existing_cols:
        op.alter_column("documents", "expires_at", new_column_name="expire_date")
        existing_cols.discard("expires_at")
        existing_cols.add("expire_date")
    if "extra" in existing_cols and "meta" not in existing_cols:
        op.alter_column("documents", "extra", new_column_name="meta")
        existing_cols.discard("extra")
        existing_cols.add("meta")

    # --- Type adjustments ---
    if "issue_date" in existing_cols:
        op.alter_column(
            "documents",
            "issue_date",
            type_=sa.Date(),
            existing_type=sa.DateTime(timezone=True),
            postgresql_using="issue_date::date",
        )
    if "expire_date" in existing_cols:
        op.alter_column(
            "documents",
            "expire_date",
            type_=sa.Date(),
            existing_type=sa.DateTime(timezone=True),
            postgresql_using="expire_date::date",
        )
    if "meta" in existing_cols:
        op.alter_column(
            "documents",
            "meta",
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_type=postgresql.JSON(astext_type=sa.Text()),
            postgresql_using="meta::jsonb",
        )

    # --- Add new columns ---
    if "company_id" not in existing_cols:
        op.add_column("documents", sa.Column("company_id", sa.String(length=36), nullable=True))
    if "kind" not in existing_cols:
        op.add_column(
            "documents",
            sa.Column(
                "kind",
                kind_enum,
                nullable=False,
                server_default="driver",
            ),
        )
    if "custom_name" not in existing_cols:
        op.add_column(
            "documents",
            sa.Column("custom_name", sa.String(length=255), nullable=True),
        )
    if "status_tmp" not in existing_cols and "status" not in existing_cols:
        op.add_column(
            "documents",
            sa.Column(
                "status_tmp",
                status_enum,
                nullable=False,
                server_default="missing",
            ),
        )
    if "requested_from" not in existing_cols:
        op.add_column(
            "documents",
            sa.Column(
                "requested_from",
                requested_from_enum,
                nullable=False,
                server_default="driver",
            ),
        )
    if "process_type" not in existing_cols:
        op.add_column(
            "documents",
            sa.Column(
                "process_type",
                process_type_enum,
                nullable=False,
                server_default="none",
            ),
        )
    if "workflow" not in existing_cols:
        op.add_column(
            "documents",
            sa.Column("workflow", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    # Ensure meta is not null for merge
    op.execute("UPDATE documents SET meta = COALESCE(meta, '{}'::jsonb)")

    # Merge meta_json into meta
    inspector = sa.inspect(bind)
    if inspector.has_table("documents"):
        columns: Sequence[dict[str, object]] = inspector.get_columns("documents")
        if any(col.get("name") == "meta_json" for col in columns):
            op.execute(
                """
                UPDATE documents
                SET meta = COALESCE(meta, '{}'::jsonb) ||
                          COALESCE(NULLIF(meta_json, '')::jsonb, '{}'::jsonb)
                WHERE meta_json IS NOT NULL AND meta_json <> ''
                """
            )
            op.drop_column("documents", "meta_json")

    # Normalise doc_type to lower case
    op.execute("UPDATE documents SET doc_type = lower(doc_type)")

    # Map doc types to canonical values and fill derived columns
    for entry in DOC_NORMALIZATION:
        target = entry["target"]
        aliases = _lower_aliases(entry["aliases"])
        kind = entry["kind"]
        requested_from = entry["requested_from"]
        process_type = entry["process_type"]
        placeholders = ", ".join(f"'{alias}'" for alias in aliases)
        op.execute(
            f"""
            UPDATE documents
            SET doc_type = '{target}',
                kind = '{kind}',
                requested_from = '{requested_from}',
                process_type = '{process_type}'
            WHERE doc_type IN ({placeholders})
            """
        )

    # Default fallback assignments
    op.execute(
        """
        UPDATE documents
        SET kind = 'driver'
        WHERE kind IS NULL
        """
    )
    op.execute(
        """
        UPDATE documents
        SET requested_from = 'driver'
        WHERE requested_from IS NULL
        """
    )
    op.execute(
        """
        UPDATE documents
        SET process_type = 'none'
        WHERE process_type IS NULL
        """
    )

    current_cols = {col["name"] for col in sa.inspect(bind).get_columns("documents")}

    if "status_tmp" in current_cols and "status" in current_cols:
        op.execute(
            """
            UPDATE documents
            SET status_tmp = CASE lower(status)
                WHEN 'planned' THEN 'missing'
                WHEN 'pending' THEN 'requested'
                WHEN 'pending_validation' THEN 'in_progress'
                WHEN 'requested' THEN 'requested'
                WHEN 'submitted' THEN 'in_progress'
                WHEN 'in_progress' THEN 'in_progress'
                WHEN 'upload' THEN 'received'
                WHEN 'uploaded' THEN 'received'
                WHEN 'received' THEN 'received'
                WHEN 'ready' THEN 'approved'
                WHEN 'approved' THEN 'approved'
                WHEN 'verified' THEN 'approved'
                WHEN 'invalid' THEN 'rejected'
                WHEN 'rejected' THEN 'rejected'
                WHEN 'expired' THEN 'expired'
                ELSE 'missing'
            END
            """
        )

        op.drop_column("documents", "status")
        op.alter_column(
            "documents",
            "status_tmp",
            new_column_name="status",
            existing_type=status_enum,
            nullable=False,
        )
        op.alter_column("documents", "status", server_default=None)

    # Drop server defaults added for migration
    if "kind" in current_cols:
        op.alter_column("documents", "kind", server_default=None)
    if "requested_from" in current_cols:
        op.alter_column("documents", "requested_from", server_default=None)
    if "process_type" in current_cols:
        op.alter_column("documents", "process_type", server_default=None)

    inspector = sa.inspect(bind)
    if not inspector.has_table("document_templates"):
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

    # Drop templates table
    op.drop_index("ix_document_templates_tenant_id", table_name="document_templates")
    op.drop_constraint("uq_document_templates_tenant_code", "document_templates", type_="unique")
    op.drop_table("document_templates")

    # Recreate old status column as VARCHAR
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
            WHEN 'received' THEN 'verified'
            WHEN 'approved' THEN 'verified'
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

    # Revert defaults
    op.alter_column("documents", "status", server_default="pending_validation")

    # Drop new columns
    op.drop_column("documents", "workflow")
    op.drop_column("documents", "process_type")
    op.drop_column("documents", "requested_from")
    op.drop_column("documents", "custom_name")
    op.drop_column("documents", "kind")
    op.drop_column("documents", "company_id")

    # Rename columns back
    op.alter_column("documents", "doc_type", new_column_name="type")
    op.alter_column("documents", "issue_date", new_column_name="issued_at")
    op.alter_column("documents", "expire_date", new_column_name="expires_at")
    op.alter_column("documents", "meta", new_column_name="extra")

    # Convert dates back to timestamptz
    op.alter_column(
        "documents",
        "issued_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        postgresql_using="issued_at::timestamp",
    )
    op.alter_column(
        "documents",
        "expires_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        postgresql_using="expires_at::timestamp",
    )

    # Remove enum columns - cast back to text
    op.alter_column(
        "documents",
        "extra",
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="extra::json",
    )

    # Recreate meta_json column
    op.add_column(
        "documents",
        sa.Column("meta_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.execute("UPDATE documents SET meta_json = '{}' WHERE meta_json IS NULL")

    # Drop enums
    for enum in (
        "document_process_type_enum",
        "document_requested_from_enum",
        "document_status_enum_v2",
        "document_kind_enum",
    ):
        postgresql.ENUM(name=enum).drop(bind, checkfirst=True)
