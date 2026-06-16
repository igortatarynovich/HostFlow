from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class CanonicalDocSeed:
    code: str
    public_name: str
    category_code: str
    subcategory_code: str | None
    criticality: str
    business_purposes: list[str]
    required_fields: list[str]
    expiry_required: bool
    reminder_days: list[int]
    entity_applicability: list[str]
    verification_profile: dict[str, Any]


def _seed_types() -> list[CanonicalDocSeed]:
    return [
        CanonicalDocSeed("passport", "Passport", "identity", "passport", "required", ["identification"], ["number", "expiry_date", "issuing_country"], True, [60, 30, 7], ["candidate", "employee"], {"check_personal_data_match": True, "check_expiry_validity": True}),
        CanonicalDocSeed("id_card", "ID Card", "identity", "national_id", "required", ["identification"], ["number", "expiry_date", "issuing_country"], True, [60, 30, 7], ["candidate", "employee"], {"check_personal_data_match": True, "check_expiry_validity": True}),
        CanonicalDocSeed("residence_card", "Residence Card", "immigration", "residence_permit", "compliance_critical", ["legal_stay", "right_to_work"], ["number", "expiry_date", "issuing_country"], True, [60, 30, 7], ["candidate", "employee"], {"check_right_to_work": True, "check_expiry_validity": True}),
        CanonicalDocSeed("visa", "Visa", "immigration", "visa", "compliance_critical", ["legal_stay"], ["number", "expiry_date", "issuing_country"], True, [60, 30, 7], ["candidate", "employee"], {"check_right_to_work": True, "check_expiry_validity": True}),
        CanonicalDocSeed("work_permit", "Work Permit", "work_authorization", "permit", "work_blocking", ["right_to_work"], ["permit_type", "expiry_date", "issuing_country"], True, [60, 30, 7], ["candidate", "employee"], {"check_right_to_work": True, "manual_review_required": True}),
        CanonicalDocSeed("driver_license", "Driver License", "driver_qualification", "license", "work_blocking", ["driver_compliance"], ["number", "categories", "expiry_date", "issuing_country"], True, [90, 60, 30], ["candidate", "employee"], {"check_category_or_class": True, "check_expiry_validity": True}),
        CanonicalDocSeed("code_95", "Code 95", "driver_qualification", "code95", "compliance_critical", ["driver_compliance"], ["number", "expiry_date"], True, [90, 60, 30], ["candidate", "employee"], {"check_category_or_class": True, "check_expiry_validity": True}),
        CanonicalDocSeed("tachograph_card", "Tachograph Card", "driver_qualification", "tachograph", "compliance_critical", ["driver_compliance"], ["number", "expiry_date", "issuing_country"], True, [90, 60, 30], ["candidate", "employee"], {"check_expiry_validity": True}),
        CanonicalDocSeed("medical_certificate", "Medical Certificate", "medical", "occupational_health", "work_blocking", ["driver_compliance"], ["issue_date", "expiry_date"], True, [60, 30, 7], ["candidate", "employee"], {"check_expiry_validity": True, "manual_review_required": True}),
        CanonicalDocSeed("psychotest", "Psychotest", "medical", "psychological", "work_blocking", ["driver_compliance"], ["issue_date", "expiry_date"], True, [60, 30, 7], ["candidate", "employee"], {"check_expiry_validity": True, "manual_review_required": True}),
        CanonicalDocSeed("employment_contract", "Employment Contract", "employment", "employment_contract", "required", ["employment_formalization"], ["contract_type", "start_date", "employer"], False, [30, 7], ["employee", "contract"], {"manual_review_required": True}),
        CanonicalDocSeed("civil_contract", "Civil Contract", "employment", "civil_contract", "required", ["employment_formalization"], ["contract_type", "start_date", "employer"], False, [30, 7], ["employee", "contract"], {"manual_review_required": True}),
        CanonicalDocSeed("zus_zua", "ZUS ZUA", "social_security", "zus", "required", ["payroll_setup"], ["submission_date", "registration_date", "reference_number"], False, [14, 7], ["employee", "payroll_profile"], {"manual_review_required": True}),
        CanonicalDocSeed("zus_zza", "ZUS ZZA", "social_security", "zus", "required", ["payroll_setup"], ["submission_date", "registration_date", "reference_number"], False, [14, 7], ["employee", "payroll_profile"], {"manual_review_required": True}),
        CanonicalDocSeed("tax_declaration", "Tax Declaration", "tax", "declaration", "required", ["payroll_setup"], ["submission_date"], False, [14, 7], ["employee", "payroll_profile"], {"manual_review_required": True}),
        CanonicalDocSeed("other", "Other", "other", None, "informational", ["internal_record"], ["custom_name"], False, [30], ["candidate", "employee", "company", "client", "vehicle"], {"manual_review_required": True}),
    ]


LEGACY_CODE_MAP: dict[str, str] = {
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

SYSTEM_CODES = {item.code for item in _seed_types()}


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def normalize_legacy_doc_type(value: Optional[str]) -> str:
    key = str(value or "").strip().lower()
    if not key:
        return "other"
    return LEGACY_CODE_MAP.get(key, "other")


def _schema(seed: CanonicalDocSeed) -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(seed.required_fields),
        "properties": {field: {"type": "string"} for field in seed.required_fields},
        "additionalProperties": True,
    }


def _expiry_rules(seed: CanonicalDocSeed) -> dict[str, Any]:
    return {
        "has_expiry": bool(seed.expiry_required),
        "expiry_required": bool(seed.expiry_required),
        "reminder_days": list(seed.reminder_days),
        "can_work_after_expiry": not bool(seed.expiry_required),
        "blocks_candidate": seed.criticality in {"compliance_critical", "work_blocking"},
        "blocks_employee": seed.criticality in {"compliance_critical", "work_blocking"},
        "renewal_flow_required": bool(seed.expiry_required),
    }


def _ensure_type(conn, seed: CanonicalDocSeed) -> tuple[str, str]:
    row = conn.execute(
        text("SELECT id FROM ref_document_types WHERE lower(code)=lower(:code)"),
        {"code": seed.code},
    ).mappings().first()
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
                "public_name": seed.public_name,
                "category_code": seed.category_code,
                "subcategory_code": seed.subcategory_code,
                "criticality": seed.criticality,
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
                "code": seed.code,
                "public_name": seed.public_name,
                "category_code": seed.category_code,
                "subcategory_code": seed.subcategory_code,
                "criticality": seed.criticality,
                "description": f"Seeded canonical document type: {seed.code}",
            },
        )

    ver = conn.execute(
        text("SELECT id FROM ref_document_type_versions WHERE document_type_id=:document_type_id AND version_code='v1'"),
        {"document_type_id": doc_id},
    ).mappings().first()

    payload = {
        "schema_json": _j(_schema(seed)),
        "expiry_rules_json": _j(_expiry_rules(seed)),
        "automation_flags_json": _j({"affects_reminders": True, "requires_manual_verification": True}),
        "verification_profile_json": _j(seed.verification_profile),
        "stage_applicability_json": _j({"default": True}),
        "position_applicability_json": _j({"profiles": ["driver", "office_worker", "other"]}),
        "entity_applicability_json": _j({"entity_types": seed.entity_applicability}),
        "business_purposes_json": _j({"purposes": seed.business_purposes}),
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

    return doc_id, ver_id


def seed_and_sync_on_connection(conn) -> dict[str, str]:
    code_to_doc_id: dict[str, str] = {}
    code_to_ver_id: dict[str, str] = {}

    for seed in _seed_types():
        doc_id, ver_id = _ensure_type(conn, seed)
        code_to_doc_id[seed.code] = doc_id
        code_to_ver_id[seed.code] = ver_id

    conn.execute(
        text(
            """
            UPDATE ref_document_types
            SET origin='tenant_custom', updated_at=CURRENT_TIMESTAMP
            WHERE origin <> 'system'
              AND lower(code) NOT IN :system_codes
            """
        ).bindparams(bindparam("system_codes", expanding=True)),
        {"system_codes": tuple(sorted(SYSTEM_CODES))},
    )

    docs = conn.execute(
        text("SELECT id, doc_type FROM documents WHERE document_type_id IS NULL OR document_type_version_id IS NULL")
    ).mappings().all()
    for row in docs:
        code = normalize_legacy_doc_type(row.get("doc_type"))
        conn.execute(
            text("UPDATE documents SET document_type_id=:document_type_id, document_type_version_id=:document_type_version_id WHERE id=:id"),
            {
                "id": row["id"],
                "document_type_id": code_to_doc_id.get(code, code_to_doc_id["other"]),
                "document_type_version_id": code_to_ver_id.get(code, code_to_ver_id["other"]),
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
        code = normalize_legacy_doc_type(row.get("legacy_code"))
        conn.execute(
            text("UPDATE document_policies SET ref_document_type_id=:ref_document_type_id WHERE id=:id"),
            {
                "id": row["policy_id"],
                "ref_document_type_id": code_to_doc_id.get(code, code_to_doc_id["other"]),
            },
        )

    _seed_m4_packs(conn, code_to_ver_id)
    return code_to_doc_id


def _ensure_pack(conn, *, code: str, country_code: str | None, industry_code: str | None, meta: dict[str, Any]) -> str:
    row = conn.execute(text("SELECT id FROM ref_packs WHERE lower(code)=lower(:code)"), {"code": code}).mappings().first()
    if row:
        pack_id = str(row["id"])
        conn.execute(
            text(
                """
                UPDATE ref_packs
                SET country_code=:country_code,
                    industry_code=:industry_code,
                    status='active',
                    version=1,
                    meta=:meta,
                    published_at=CURRENT_TIMESTAMP
                WHERE id=:id
                """
            ),
            {"id": pack_id, "country_code": country_code, "industry_code": industry_code, "meta": _j(meta)},
        )
        return pack_id
    pack_id = str(uuid4())
    conn.execute(
        text(
            """
            INSERT INTO ref_packs (id, code, country_code, industry_code, status, version, published_at, meta)
            VALUES (:id, :code, :country_code, :industry_code, 'active', 1, CURRENT_TIMESTAMP, :meta)
            """
        ),
        {"id": pack_id, "code": code, "country_code": country_code, "industry_code": industry_code, "meta": _j(meta)},
    )
    return pack_id


def _seed_m4_packs(conn, code_to_ver_id: dict[str, str]) -> None:
    packs: list[dict[str, Any]] = [
        {
            "code": "pl_base_hr",
            "country_code": "PL",
            "industry_code": "hr",
            "meta": {"name": "Poland Base HR"},
            "items": [("passport", "required"), ("tax_declaration", "required"), ("employment_contract", "required"), ("zus_zua", "required"), ("zus_zza", "optional")],
            "rules": [
                {"priority": 100, "condition_expr": {"work_country": "pl"}, "effect_type": "set_requirement", "effect_payload": {"required": True, "due_point": "before_employment", "reason": "Poland base HR baseline"}},
            ],
        },
        {
            "code": "pl_non_eu_worker",
            "country_code": "PL",
            "industry_code": "hr",
            "meta": {"name": "Poland Non-EU Worker"},
            "items": [("work_permit", "required"), ("residence_card", "required"), ("visa", "optional")],
            "rules": [
                {"priority": 50, "condition_expr": {"work_country": "pl", "citizenship_group": "non_eu"}, "effect_type": "set_requirement", "effect_payload": {"required": True, "due_point": "before_arrival", "reason": "Non-EU legal stay and work authorization in Poland"}},
                {"priority": 200, "condition_expr": {"citizenship_group": "eu"}, "effect_type": "set_requirement", "effect_payload": {"required": False, "due_point": "before_employment", "reason": "EU worker path"}},
            ],
        },
        {
            "code": "pl_transport_driver",
            "country_code": "PL",
            "industry_code": "transport",
            "meta": {"name": "Poland Transport Driver"},
            "items": [("driver_license", "required"), ("code_95", "required"), ("tachograph_card", "required"), ("medical_certificate", "required"), ("psychotest", "required")],
            "rules": [
                {"priority": 60, "condition_expr": {"work_country": "pl", "position_category": "driver"}, "effect_type": "set_requirement", "effect_payload": {"required": True, "due_point": "before_first_route", "reason": "Driver compliance in Poland transport"}},
                {"priority": 220, "condition_expr": {"position_category": ["office_worker", "warehouse_worker", "other", ""]}, "effect_type": "set_requirement", "effect_payload": {"required": False, "reason": "Non-driver role"}},
            ],
        },
        {
            "code": "eu_driver_compliance",
            "country_code": None,
            "industry_code": "transport",
            "meta": {"name": "EU Driver Compliance"},
            "items": [("driver_license", "required"), ("code_95", "required"), ("tachograph_card", "required")],
            "rules": [
                {"priority": 80, "condition_expr": {"position_category": "driver", "citizenship_group": "eu"}, "effect_type": "set_requirement", "effect_payload": {"required": True, "due_point": "before_client_submission", "reason": "EU transport qualification baseline"}},
            ],
        },
        {
            "code": "client_specific_requirements",
            "country_code": None,
            "industry_code": None,
            "meta": {"name": "Client Specific Requirements"},
            "items": [("other", "optional")],
            "rules": [
                {"priority": 100, "condition_expr": {}, "effect_type": "set_requirement", "effect_payload": {"required": False, "due_point": "before_client_submission", "reason": "Client contract-specific attachment"}},
            ],
        },
    ]

    for pack in packs:
        pack_id = _ensure_pack(
            conn,
            code=str(pack["code"]),
            country_code=pack.get("country_code"),
            industry_code=pack.get("industry_code"),
            meta=dict(pack.get("meta") or {}),
        )

        conn.execute(text("DELETE FROM ref_pack_items WHERE pack_id=:pack_id"), {"pack_id": pack_id})
        conn.execute(text("DELETE FROM ref_pack_rules WHERE pack_id=:pack_id"), {"pack_id": pack_id})

        for doc_code, role in pack["items"]:
            ver_id = code_to_ver_id.get(str(doc_code))
            if not ver_id:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO ref_pack_items (id, pack_id, document_type_version_id, role)
                    VALUES (:id, :pack_id, :ver_id, :role)
                    """
                ),
                {"id": str(uuid4()), "pack_id": pack_id, "ver_id": ver_id, "role": str(role)},
            )

        for rule in pack["rules"]:
            conn.execute(
                text(
                    """
                    INSERT INTO ref_pack_rules (id, pack_id, priority, condition_expr, effect_type, effect_payload)
                    VALUES (:id, :pack_id, :priority, :condition_expr, :effect_type, :effect_payload)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "pack_id": pack_id,
                    "priority": int(rule.get("priority") or 100),
                    "condition_expr": _j(dict(rule.get("condition_expr") or {})),
                    "effect_type": str(rule.get("effect_type") or "set_requirement"),
                    "effect_payload": _j(dict(rule.get("effect_payload") or {})),
                },
            )


async def seed_and_sync_document_references(session: AsyncSession) -> dict[str, str]:
    def _run(sync_session):
        return seed_and_sync_on_connection(sync_session.connection())

    return await session.run_sync(_run)
