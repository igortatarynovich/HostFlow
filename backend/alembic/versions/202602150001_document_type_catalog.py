"""Document type catalog enhancements

Revision ID: 202602150001
Revises: 202601020001
Create Date: 2025-11-02 16:50:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202602150001"
down_revision = "202601020001"
branch_labels = None
depends_on = None


DOCUMENT_KIND_ENUM = sa.Enum(
    "driver",
    "employer",
    "process",
    name="document_kind_enum",
    create_type=False,
)

DOCUMENT_PROCESS_ENUM = sa.Enum(
    "none",
    "work_permit",
    "visa",
    "residence_card",
    "tachograph_card",
    "driver_license_exchange",
    "swiadectwo_kierowcy",
    "other",
    name="document_process_type_enum",
    create_type=False,
)


def upgrade() -> None:
    with op.batch_alter_table("document_types") as batch_op:
        batch_op.alter_column("valid_days", new_column_name="default_expire_in_days")

    op.add_column(
        "document_types",
        sa.Column(
            "kind",
            DOCUMENT_KIND_ENUM,
            nullable=False,
            server_default=sa.text("'driver'::document_kind_enum"),
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "process_type",
            DOCUMENT_PROCESS_ENUM,
            nullable=True,
            server_default=sa.text("'none'::document_process_type_enum"),
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "required_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "owner_summary_weight",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "document_types",
        sa.Column("i18n_key", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "document_types",
        sa.Column(
            "requires_custom_name",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.execute(
        """
        UPDATE document_types
        SET
            default_expire_in_days = CASE code
                WHEN 'identity_document' THEN 3650
                WHEN 'driver_license' THEN 1825
                WHEN 'qualification_code95' THEN 1825
                WHEN 'medical_certificate' THEN 365
                WHEN 'criminal_record' THEN 365
                WHEN 'assignment' THEN 180
                WHEN 'insurance' THEN 365
                WHEN 'bhp' THEN 365
                WHEN 'accommodation' THEN 365
                WHEN 'tachograph_card' THEN 1825
                WHEN 'driver_license_exchange' THEN 730
                WHEN 'swiadectwo_kierowcy' THEN 730
                ELSE default_expire_in_days
            END,
            kind = CASE
                WHEN code IN ('contract','assignment','insurance','bhp','accommodation') THEN 'employer'
                WHEN code IN ('work_permit','visa','residence_card','tachograph_card','driver_license_exchange','swiadectwo_kierowcy','other') THEN 'process'
                ELSE 'driver'
            END::document_kind_enum,
            process_type = CASE code
                WHEN 'work_permit' THEN 'work_permit'
                WHEN 'visa' THEN 'visa'
                WHEN 'residence_card' THEN 'residence_card'
                WHEN 'tachograph_card' THEN 'tachograph_card'
                WHEN 'driver_license_exchange' THEN 'driver_license_exchange'
                WHEN 'swiadectwo_kierowcy' THEN 'swiadectwo_kierowcy'
                WHEN 'other' THEN 'other'
                ELSE 'none'
            END::document_process_type_enum,
            aliases = CASE code
                WHEN 'identity_document' THEN '["passport","id_card","national_id","dowod_osobisty"]'::jsonb
                WHEN 'driver_license' THEN '["license","driver_license_ce","drivers_license_ce","prawo_jazdy"]'::jsonb
                WHEN 'qualification_code95' THEN '["code95","code_95"]'::jsonb
                WHEN 'medical_certificate' THEN '["medical","medical_cert","badania_lekarskie"]'::jsonb
                WHEN 'criminal_record' THEN '["police_clearance"]'::jsonb
                WHEN 'photo' THEN '["photo_id"]'::jsonb
                WHEN 'bank_account_confirmation' THEN '["bank_statement","bank_account_doc"]'::jsonb
                WHEN 'pesel' THEN '["national_number","pesel_confirm"]'::jsonb
                WHEN 'contract' THEN '["employment_contract","work_contract","umowa_o_prace"]'::jsonb
                WHEN 'assignment' THEN '["delegation","work_assignment","assignment_letter","oswiadczenie"]'::jsonb
                WHEN 'insurance' THEN '["insurance_confirmation","insurance_a1","employer_insurance","ubezpieczenie"]'::jsonb
                WHEN 'bhp' THEN '["bhp_instruction","szkolenia_bhp"]'::jsonb
                WHEN 'accommodation' THEN '["accommodation_declaration","housing"]'::jsonb
                WHEN 'work_permit' THEN '["zezwolenie_na_prace","zezwolenie_a"]'::jsonb
                WHEN 'visa' THEN '["visa_type","visa_d","entry_permit_or_visa"]'::jsonb
                WHEN 'residence_card' THEN '["karta_pobytu"]'::jsonb
                WHEN 'tachograph_card' THEN '["tachograph","card_tacho","tachograph_exchange","karta_tachografu"]'::jsonb
                WHEN 'driver_license_exchange' THEN '["prawo_jazdy_exchange","exchange"]'::jsonb
                WHEN 'swiadectwo_kierowcy' THEN '["driver_attestation","swiadectwo"]'::jsonb
                WHEN 'other' THEN '["translation","custom"]'::jsonb
                ELSE aliases
            END,
            required_meta = CASE code
                WHEN 'identity_document' THEN '["country","number"]'::jsonb
                WHEN 'driver_license' THEN '["country","categories"]'::jsonb
                WHEN 'qualification_code95' THEN '["issuer"]'::jsonb
                WHEN 'medical_certificate' THEN '["issuer","facility"]'::jsonb
                WHEN 'criminal_record' THEN '["issuer"]'::jsonb
                WHEN 'bank_account_confirmation' THEN '["iban"]'::jsonb
                WHEN 'pesel' THEN '["number"]'::jsonb
                WHEN 'contract' THEN '["company_id","role"]'::jsonb
                WHEN 'assignment' THEN '["route"]'::jsonb
                WHEN 'insurance' THEN '["policy_number"]'::jsonb
                WHEN 'bhp' THEN '["issued_by","trainer"]'::jsonb
                WHEN 'accommodation' THEN '["address"]'::jsonb
                WHEN 'work_permit' THEN '["voivodeship","type"]'::jsonb
                WHEN 'visa' THEN '["country","category"]'::jsonb
                WHEN 'residence_card' THEN '["voivodeship"]'::jsonb
                WHEN 'tachograph_card' THEN '["country"]'::jsonb
                WHEN 'driver_license_exchange' THEN '["from_country"]'::jsonb
                WHEN 'swiadectwo_kierowcy' THEN '["issuer_country"]'::jsonb
                WHEN 'other' THEN '["custom_name"]'::jsonb
                ELSE required_meta
            END,
            owner_summary_weight = CASE code
                WHEN 'identity_document' THEN 50
                WHEN 'driver_license' THEN 60
                WHEN 'qualification_code95' THEN 40
                WHEN 'medical_certificate' THEN 30
                WHEN 'criminal_record' THEN 20
                WHEN 'photo' THEN 10
                WHEN 'bank_account_confirmation' THEN 10
                WHEN 'pesel' THEN 10
                WHEN 'contract' THEN 40
                WHEN 'assignment' THEN 30
                WHEN 'insurance' THEN 20
                WHEN 'bhp' THEN 20
                WHEN 'accommodation' THEN 10
                WHEN 'work_permit' THEN 70
                WHEN 'visa' THEN 60
                WHEN 'residence_card' THEN 60
                WHEN 'tachograph_card' THEN 50
                WHEN 'driver_license_exchange' THEN 40
                WHEN 'swiadectwo_kierowcy' THEN 50
                ELSE owner_summary_weight
            END,
            i18n_key = COALESCE(NULLIF(i18n_key, ''), 'documents.catalog.' || code),
            requires_custom_name = CASE WHEN code = 'other' THEN TRUE ELSE requires_custom_name END
        """
    )


def downgrade() -> None:
    op.drop_column("document_types", "requires_custom_name")
    op.drop_column("document_types", "i18n_key")
    op.drop_column("document_types", "owner_summary_weight")
    op.drop_column("document_types", "required_meta")
    op.drop_column("document_types", "aliases")
    op.drop_column("document_types", "process_type")
    op.drop_column("document_types", "kind")

    with op.batch_alter_table("document_types") as batch_op:
        batch_op.alter_column("default_expire_in_days", new_column_name="valid_days")
