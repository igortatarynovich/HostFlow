"""seed initial document_types and ruleset v1.1 (sandbox)

Revision ID: 0002_seed_types_ruleset
Revises: 0001_documents_baseline
Create Date: 2025-09-07
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0002_seed_types_ruleset"
down_revision = "0001_documents_baseline"
branch_labels = None
depends_on = None

TENANT = "00000000-0000-0000-0000-000000000001"  # sandbox tenant UUID


def upgrade() -> None:
    conn = op.get_bind()

    # --- inline meta_schemas (сокращённо) ---
    passport = {
        "fields": {
            "number": {"type": "string", "required": True, "regex": "^[A-Z0-9]{6,10}$"},
            "surname": {"type": "string", "required": True},
            "given_names": {"type": "string", "required": True},
            "nationality": {"type": "string", "required": True},
            "date_of_birth": {"type": "date", "required": True},
            "sex": {"type": "string", "required": False, "enum": ["M", "F", "X"]},
            "issuing_country": {"type": "string", "required": True},
            "issued_at": {"type": "date", "required": True},
            "expires_at": {"type": "date", "required": True},
        },
        "ocr": {
            "mrz": True,
            "langs": ["eng", "pol", "rus", "ukr"],
            "hints": ["passport", "mrz", "icao_td3"],
        },
    }
    qualification_card = {
        "fields": {
            "card_number": {
                "type": "string",
                "required": True,
                "regex": "^[0-9]{8,12}$",
            },
            "issued_at": {"type": "date", "required": False},
            "expires_at": {"type": "date", "required": True},
            "issuing_country": {"type": "string", "required": False},
        },
        "ocr": {"langs": ["eng", "pol"], "hints": ["code95", "qualification_card"]},
    }
    tachograph = {
        "fields": {
            "card_number": {"type": "string", "required": True, "regex": "^[0-9]{16}$"},
            "issued_at": {"type": "date", "required": True},
            "expires_at": {"type": "date", "required": True},
            "issuing_country": {"type": "string", "required": True},
        },
        "ocr": {
            "langs": ["eng", "pol"],
            "hints": ["tachograph", "chip_card", "barcode"],
        },
    }
    driver_att = {
        "fields": {
            "attestation_number": {"type": "string", "required": True},
            "company_name": {"type": "string", "required": True},
            "issuing_authority": {"type": "string", "required": False},
            "issued_at": {"type": "date", "required": True},
            "expires_at": {"type": "date", "required": True},
        },
        "ocr": {"langs": ["eng", "pol"], "hints": ["attestation", "template_form"]},
    }
    entry_permit = {
        "fields": {
            "type": {
                "type": "string",
                "required": True,
                "enum": ["visa", "pobyt", "work_permit", "osw"],
            },
            "number": {"type": "string", "required": False},
            "issuing_country": {"type": "string", "required": True},
            "issued_at": {"type": "date", "required": False},
            "expires_at": {"type": "date", "required": True},
        },
        "ocr": {
            "langs": ["eng", "pol", "rus", "ukr"],
            "hints": ["visa", "sticker", "permit"],
        },
    }

    doc_types = [
        ("identity_document", "Identity document", "candidate", passport, None, None),
        ("qualification_code95", "Qualification card (Code 95)", "candidate", qualification_card, None, None),
        ("tachograph_card", "Tachograph card", "candidate", tachograph, None, None),
        (
            "swiadectwo_kierowcy",
            "Świadectwo kierowcy",
            "candidate",
            driver_att,
            None,
            None,
        ),
        (
            "visa",
            "Visa",
            "candidate",
            entry_permit,
            None,
            None,
        ),
    ]

    insert_dt_sql = sa.text(
        """
        INSERT INTO document_types
            (tenant_id, code, name, entity_scope, meta_schema, number_regex, default_validity_days, is_active)
        VALUES
            (:tenant_id, :code, :name, :scope, CAST(:schema AS jsonb), :regex, :valid_days, TRUE)
        ON CONFLICT (tenant_id, code) DO NOTHING;
        """
    )

    for code, name, scope, schema, number_regex, validity_days in doc_types:
        conn.execute(
            insert_dt_sql,
            {
                "tenant_id": TENANT,
                "code": code,
                "name": name,
                "scope": scope,
                "schema": json.dumps(schema),
                "regex": number_regex,
                "valid_days": validity_days,
            },
        )

    # Ruleset v1.1
    ruleset_v11 = {
        "version": "1.1.0",
        "expiring_soon_default_days": 30,
        "candidate": {
            "defaults": {
                "requiredTypes": ["identity_document", "qualification_code95"],
                "optionalTypes": ["tachograph_card", "medical_certificate"],
            },
            "overrides": [
                {
                    "when": {
                        "citizenship": ["UA", "BY", "IN", "ZW"],
                        "residency_status": ["no_residence_card"],
                    },
                    "require": ["visa"],
                },
                {
                    "when": {
                        "citizenship": ["PL", "EU"],
                        "residency_status": ["eu_citizen"],
                    },
                    "remove": ["visa"],
                },
            ],
        },
        "vacancy": {
            "category_sets": {
                "driver": {
                    "requiredTypes": ["identity_document", "qualification_code95"],
                    "optionalTypes": [
                        "tachograph_card",
                        "driver_license",
                        "swiadectwo_kierowcy",
                        "medical_certificate",
                    ],
                },
                "non_driver": {
                    "requiredTypes": ["identity_document"],
                    "optionalTypes": [
                        "identity_document",
                        "residence_card",
                        "visa",
                        "bank_account_confirmation",
                        "pesel",
                        "criminal_record",
                    ],
                },
            },
            "additions": [
                {
                    "when": {"requires_driver_attestation": True},
                    "require": ["swiadectwo_kierowcy"],
                }
            ],
        },
        "validity": {
            "identity_document": {"expiring_soon_days": 180},
            "qualification_code95": {"expiring_soon_days": 45},
            "driver_license": {"expiring_soon_days": 60},
            "tachograph_card": {"expiring_soon_days": 60},
        },
    }

    conn.execute(
        sa.text(
            """
            INSERT INTO rulesets (tenant_id, json)
            VALUES (:tenant_id, CAST(:json AS jsonb))
            ON CONFLICT (tenant_id) DO UPDATE SET json = EXCLUDED.json, updated_at = NOW();
            """
        ),
        {"tenant_id": TENANT, "json": json.dumps(ruleset_v11)},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM rulesets WHERE tenant_id = :t"), {"t": TENANT})
    conn.execute(
        sa.text("DELETE FROM document_types WHERE tenant_id = :t"), {"t": TENANT}
    )
