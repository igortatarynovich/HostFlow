"""Document reference M2 seed + canonical sync.

Revision ID: 202608130002_document_reference_seed_sync
Revises: 202608130001_document_reference_foundation
Create Date: 2026-08-13 11:00:00.000000
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608130002_document_reference_seed_sync"
down_revision: RevisionType = "202608130001_document_reference_foundation"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _seeds() -> list[dict[str, Any]]:
    return [
        {"code": "passport", "name": "Passport", "category": "identity", "sub": "passport", "criticality": "required", "purposes": ["identification"], "required": ["number", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "id_card", "name": "ID Card", "category": "identity", "sub": "national_id", "criticality": "required", "purposes": ["identification"], "required": ["number", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "residence_card", "name": "Residence Card", "category": "immigration", "sub": "residence_permit", "criticality": "compliance_critical", "purposes": ["legal_stay", "right_to_work"], "required": ["number", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "visa", "name": "Visa", "category": "immigration", "sub": "visa", "criticality": "compliance_critical", "purposes": ["legal_stay"], "required": ["number", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "work_permit", "name": "Work Permit", "category": "work_authorization", "sub": "permit", "criticality": "work_blocking", "purposes": ["right_to_work"], "required": ["permit_type", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "driver_license", "name": "Driver License", "category": "driver_qualification", "sub": "license", "criticality": "work_blocking", "purposes": ["driver_compliance"], "required": ["number", "categories", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "code_95", "name": "Code 95", "category": "driver_qualification", "sub": "code95", "criticality": "compliance_critical", "purposes": ["driver_compliance"], "required": ["number", "expiry_date"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "tachograph_card", "name": "Tachograph Card", "category": "driver_qualification", "sub": "tachograph", "criticality": "compliance_critical", "purposes": ["driver_compliance"], "required": ["number", "expiry_date", "issuing_country"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "medical_certificate", "name": "Medical Certificate", "category": "medical", "sub": "occupational_health", "criticality": "work_blocking", "purposes": ["driver_compliance"], "required": ["issue_date", "expiry_date"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "psychotest", "name": "Psychotest", "category": "medical", "sub": "psychological", "criticality": "work_blocking", "purposes": ["driver_compliance"], "required": ["issue_date", "expiry_date"], "expiry": True, "entities": ["candidate", "employee"]},
        {"code": "employment_contract", "name": "Employment Contract", "category": "employment", "sub": "employment_contract", "criticality": "required", "purposes": ["employment_formalization"], "required": ["contract_type", "start_date", "employer"], "expiry": False, "entities": ["employee", "contract"]},
        {"code": "civil_contract", "name": "Civil Contract", "category": "employment", "sub": "civil_contract", "criticality": "required", "purposes": ["employment_formalization"], "required": ["contract_type", "start_date", "employer"], "expiry": False, "entities": ["employee", "contract"]},
        {"code": "zus_zua", "name": "ZUS ZUA", "category": "social_security", "sub": "zus", "criticality": "required", "purposes": ["payroll_setup"], "required": ["submission_date", "registration_date", "reference_number"], "expiry": False, "entities": ["employee", "payroll_profile"]},
        {"code": "zus_zza", "name": "ZUS ZZA", "category": "social_security", "sub": "zus", "criticality": "required", "purposes": ["payroll_setup"], "required": ["submission_date", "registration_date", "reference_number"], "expiry": False, "entities": ["employee", "payroll_profile"]},
        {"code": "tax_declaration", "name": "Tax Declaration", "category": "tax", "sub": "declaration", "criticality": "required", "purposes": ["payroll_setup"], "required": ["submission_date"], "expiry": False, "entities": ["employee", "payroll_profile"]},
        {"code": "other", "name": "Other", "category": "other", "sub": None, "criticality": "informational", "purposes": ["internal_record"], "required": ["custom_name"], "expiry": False, "entities": ["candidate", "employee", "company", "client", "vehicle"]},
    ]


LEGACY = {
    "identity_document": "passport",
    "passport": "passport",
    "id": "id_card",
    "id_card": "id_card",
    "national_id": "id_card",
    "residence_card": "residence_card",
    "karta_pobytu": "residence_card",
    "visa": "visa",
    "visa_d": "visa",
    "visa_c": "visa",
    "work_permit": "work_permit",
    "zezwolenie_a": "work_permit",
    "driver_license": "driver_license",
    "driver_license_ce": "driver_license",
    "qualification_code95": "code_95",
    "code95": "code_95",
    "code_95": "code_95",
    "tachograph": "tachograph_card",
    "tachograph_card": "tachograph_card",
    "medical": "medical_certificate",
    "medical_certificate": "medical_certificate",
    "psycho_test": "psychotest",
    "psychotest": "psychotest",
    "contract": "employment_contract",
    "employment_contract": "employment_contract",
    "civil_contract": "civil_contract",
    "zus_zua": "zus_zua",
    "zus_zza": "zus_zza",
    "tax_declaration": "tax_declaration",
    "other": "other",
    "additional_document": "other",
}


def _norm(value: str | None) -> str:
    return LEGACY.get(str(value or "").strip().lower(), "other")


def _json_schema(required_fields: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(required_fields),
        "properties": {field: {"type": "string"} for field in required_fields},
        "additionalProperties": True,
    }


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def _seed_and_backfill(conn) -> None:
    code_to_doc_id: dict[str, str] = {}
    code_to_ver_id: dict[str, str] = {}

    for item in _seeds():
        row = conn.execute(text("SELECT id FROM ref_document_types WHERE lower(code)=lower(:code)"), {"code": item["code"]}).mappings().first()
        if row:
            doc_id = str(row["id"])
            conn.execute(
                text(
                    """
                    UPDATE ref_document_types
                    SET public_name=:public_name,
                        status='active',
                        origin='system',
                        category_code=:category_code,
                        subcategory_code=:subcategory_code,
                        criticality=:criticality,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=:id
                    """
                ),
                {
                    "id": doc_id,
                    "public_name": item["name"],
                    "category_code": item["category"],
                    "subcategory_code": item["sub"],
                    "criticality": item["criticality"],
                },
            )
        else:
            doc_id = str(uuid4())
            conn.execute(
                text(
                    """
                    INSERT INTO ref_document_types
                    (id, code, public_name, status, origin, category_code, subcategory_code, criticality, description)
                    VALUES
                    (:id, :code, :public_name, 'active', 'system', :category_code, :subcategory_code, :criticality, :description)
                    """
                ),
                {
                    "id": doc_id,
                    "code": item["code"],
                    "public_name": item["name"],
                    "category_code": item["category"],
                    "subcategory_code": item["sub"],
                    "criticality": item["criticality"],
                    "description": f"Seeded canonical document type: {item['code']}",
                },
            )

        code_to_doc_id[item["code"]] = doc_id

        ver = conn.execute(
            text("SELECT id FROM ref_document_type_versions WHERE document_type_id=:document_type_id AND version_code='v1'"),
            {"document_type_id": doc_id},
        ).mappings().first()
        payload = {
            "schema_json": _j(_json_schema(item["required"])),
            "expiry_rules_json": _j({
                "has_expiry": bool(item["expiry"]),
                "expiry_required": bool(item["expiry"]),
                "reminder_days": [60, 30, 7] if item["expiry"] else [14, 7],
                "can_work_after_expiry": not bool(item["expiry"]),
                "blocks_candidate": item["criticality"] in {"compliance_critical", "work_blocking"},
                "blocks_employee": item["criticality"] in {"compliance_critical", "work_blocking"},
                "renewal_flow_required": bool(item["expiry"]),
            }),
            "automation_flags_json": _j({"affects_reminders": True, "requires_manual_verification": True}),
            "verification_profile_json": _j({"manual_review_required": True, "check_expiry_validity": bool(item["expiry"])}),
            "stage_applicability_json": _j({"default": True}),
            "position_applicability_json": _j({"profiles": ["driver", "office_worker", "other"]}),
            "entity_applicability_json": _j({"entity_types": item["entities"]}),
            "business_purposes_json": _j({"purposes": item["purposes"]}),
        }
        if ver:
            ver_id = str(ver["id"])
            conn.execute(
                text(
                    """
                    UPDATE ref_document_type_versions
                    SET schema_json=:schema_json,
                        expiry_rules_json=:expiry_rules_json,
                        automation_flags_json=:automation_flags_json,
                        verification_profile_json=:verification_profile_json,
                        stage_applicability_json=:stage_applicability_json,
                        position_applicability_json=:position_applicability_json,
                        entity_applicability_json=:entity_applicability_json,
                        business_purposes_json=:business_purposes_json
                    WHERE id=:id
                    """
                ),
                {"id": ver_id, **payload},
            )
        else:
            ver_id = str(uuid4())
            conn.execute(
                text(
                    """
                    INSERT INTO ref_document_type_versions
                    (id, document_type_id, version_code, valid_from, schema_json, expiry_rules_json,
                     automation_flags_json, verification_profile_json, stage_applicability_json,
                     position_applicability_json, entity_applicability_json, business_purposes_json, status_model)
                    VALUES
                    (:id, :document_type_id, 'v1', :valid_from, :schema_json, :expiry_rules_json,
                     :automation_flags_json, :verification_profile_json, :stage_applicability_json,
                     :position_applicability_json, :entity_applicability_json, :business_purposes_json, 'evidence')
                    """
                ),
                {
                    "id": ver_id,
                    "document_type_id": doc_id,
                    "valid_from": date(2026, 1, 1),
                    **payload,
                },
            )
        code_to_ver_id[item["code"]] = ver_id

    rows = conn.execute(text("SELECT id, doc_type FROM documents WHERE document_type_id IS NULL OR document_type_version_id IS NULL")).mappings().all()
    for row in rows:
        canonical = _norm(row.get("doc_type"))
        conn.execute(
            text("UPDATE documents SET document_type_id=:did, document_type_version_id=:vid WHERE id=:id"),
            {
                "id": row["id"],
                "did": code_to_doc_id.get(canonical, code_to_doc_id["other"]),
                "vid": code_to_ver_id.get(canonical, code_to_ver_id["other"]),
            },
        )

    policies = conn.execute(
        text(
            """
            SELECT dp.id AS policy_id, dt.code AS legacy_code
            FROM document_policies dp
            LEFT JOIN document_types dt ON dt.id = dp.document_type_id
            WHERE dp.ref_document_type_id IS NULL
              AND dp.document_type_id IS NOT NULL
            """
        )
    ).mappings().all()
    for row in policies:
        canonical = _norm(row.get("legacy_code"))
        conn.execute(
            text("UPDATE document_policies SET ref_document_type_id=:rid WHERE id=:id"),
            {"id": row["policy_id"], "rid": code_to_doc_id.get(canonical, code_to_doc_id["other"])},
        )


def upgrade() -> None:
    op.create_index(
        "uq_ref_document_types_code_lower",
        "ref_document_types",
        [sa.text("lower(code)")],
        unique=True,
    )
    op.create_check_constraint(
        "ck_ref_document_types_tenant_custom_no_system_code",
        "ref_document_types",
        "NOT (origin = 'tenant_custom' AND lower(code) IN ("
        "'passport','id_card','residence_card','visa','work_permit','driver_license','code_95',"
        "'tachograph_card','medical_certificate','psychotest','employment_contract','civil_contract',"
        "'zus_zua','zus_zza','tax_declaration','other'"
        "))",
    )

    conn = op.get_bind()
    _seed_and_backfill(conn)


def downgrade() -> None:
    op.drop_constraint("ck_ref_document_types_tenant_custom_no_system_code", "ref_document_types", type_="check")
    op.drop_index("uq_ref_document_types_code_lower", table_name="ref_document_types")
