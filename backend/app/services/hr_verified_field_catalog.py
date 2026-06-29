"""Canonical HR verified field definitions (shared by document verification + SoT layer)."""

from __future__ import annotations

from typing import Any

# Verification blocks without a mandatory file (HR confirms data only).
DATA_ONLY_VERIFICATION_KEYS: frozenset[str] = frozenset({"Contacts & address"})

# Data blocks where an supporting document may be uploaded but is not required to confirm.
OPTIONAL_FILE_VERIFICATION_KEYS: frozenset[str] = frozenset({"Work experience"})

DOSSIER_DATA_VERIFICATION_KEYS: frozenset[str] = DATA_ONLY_VERIFICATION_KEYS | OPTIONAL_FILE_VERIFICATION_KEYS

# Fields required for every employment case (non-transport-specific).
BASE_CRITICAL_FIELD_CODES: frozenset[str] = frozenset(
    {
        "full_name",
        "citizenship",
        "work_country",
        "pesel",
        "document_expiry",
        "permit_type",
    }
)

# Backward-compatible alias (base set only).
CRITICAL_FIELD_CODES: frozenset[str] = BASE_CRITICAL_FIELD_CODES

DATE_FIELD_CODES: frozenset[str] = frozenset(
    {
        "birth_date",
        "document_issue_date",
        "document_expiry",
        "driver_license_expiry",
        "code95_expiry",
        "tacho_card_expiry",
        "exam_valid_until",
        "passport_issue_date",
        "passport_expiry",
        "passport_valid_to",
        "medical_expiry",
    }
)

COUNTRY_FIELD_CODES: frozenset[str] = frozenset(
    {"citizenship", "work_country", "address_country", "country_of_residence"}
)


def resolve_field_input_type(field_code: str, spec: dict[str, Any]) -> str:
    explicit = str(spec.get("input_type") or "").strip().lower()
    if explicit:
        return explicit
    code = str(field_code or "").strip()
    if code in COUNTRY_FIELD_CODES:
        return "country"
    if (
        code in DATE_FIELD_CODES
        or code.endswith("_date")
        or code.endswith("_expiry")
        or code.endswith("_valid_to")
    ):
        return "date"
    if code == "email":
        return "email"
    if code == "phone":
        return "tel"
    return "text"

FIELD_CATALOG: dict[str, dict[str, Any]] = {
    "full_name": {
        "label": "Full name",
        "downstream_use": ["contract", "zus", "permit_application"],
    },
    "citizenship": {
        "label": "Citizenship",
        "downstream_use": ["work_permit", "zus"],
    },
    "work_country": {
        "label": "Work country",
        "downstream_use": ["permit", "zus"],
    },
    "pesel": {
        "label": "PESEL / national id",
        "downstream_use": ["zus"],
    },
    "document_expiry": {
        "label": "Document expiry",
        "downstream_use": ["compliance"],
    },
    "permit_type": {
        "label": "Permit / document type",
        "downstream_use": ["permit"],
    },
    "exam_valid_until": {
        "label": "Exam / certificate validity",
        "downstream_use": ["compliance"],
    },
    "driver_license_expiry": {
        "label": "Driver license expiry",
        "downstream_use": ["compliance"],
    },
    "driver_license_number": {
        "label": "Driver license number",
        "downstream_use": ["compliance", "contract"],
    },
    "driver_license_categories": {
        "label": "Driver license categories",
        "downstream_use": ["compliance", "contract"],
    },
    "code95_number": {
        "label": "Code 95 certificate number",
        "downstream_use": ["compliance"],
    },
    "code95_expiry": {
        "label": "Code 95 expiry",
        "downstream_use": ["compliance"],
    },
    "tacho_card_number": {
        "label": "Tacho card number",
        "downstream_use": ["compliance"],
    },
    "tacho_card_expiry": {
        "label": "Tacho card expiry",
        "downstream_use": ["compliance"],
    },
}

# Per document-key field specs for verification cards (PR3 + PR11).
# Prefer handoff snapshot paths first — recruiter values at transfer time.
FIELD_SPECS: dict[str, list[dict[str, Any]]] = {
    "Passport / ID": [
        {
            "field_code": "full_name",
            "label": "Legal name",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "handoff.candidate.full_name",
                "handoff.candidate.first_name",
                "handoff.candidate.last_name",
                "employee.display_name",
                "snapshot.first_name",
                "snapshot.last_name",
                "snapshot.full_name",
            ],
        },
        {
            "field_code": "citizenship",
            "label": "Citizenship",
            "input_type": "country",
            "downstream_use": ["work_permit", "zus"],
            "profile_keys": [
                "handoff.candidate.citizenship",
                "candidate.citizenship",
                "candidate.extra.citizenship",
                "eligibility.citizenship",
                "snapshot.citizenship",
            ],
        },
        {
            "field_code": "birth_date",
            "label": "Date of birth",
            "input_type": "date",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "handoff.candidate.birth_date",
                "snapshot.birth_date",
                "employee.meta.personal_data.birth_date",
                "candidate.birth_date",
                "candidate.extra.birth_date",
            ],
        },
        {
            "field_code": "document_series",
            "label": "Document series",
            "downstream_use": ["contract", "compliance"],
            "profile_keys": [
                "document.meta.series",
                "document.meta.passport_series",
                "snapshot.passport_series",
                "employee.meta.personal_data.passport_series",
                "candidate.passport_series",
                "candidate.extra.passport_series",
            ],
        },
        {
            "field_code": "document_number",
            "label": "Document number",
            "downstream_use": ["contract", "zus", "compliance"],
            "profile_keys": [
                "document.number",
                "document.meta.document_number",
                "document.meta.passport_number",
                "snapshot.passport_number",
                "employee.meta.personal_data.passport_number",
                "candidate.passport_number",
                "candidate.extra.passport_number",
            ],
        },
        {
            "field_code": "document_issue_date",
            "label": "Issue date",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "document.issue_date",
                "document.meta.issue_date",
                "document.meta.issued_at",
                "snapshot.passport_issue_date",
                "employee.meta.personal_data.passport_issue_date",
            ],
        },
        {
            "field_code": "document_expiry",
            "label": "Document expiry",
            "downstream_use": ["compliance"],
            "profile_keys": ["document.expires_at", "context.expires_at", "document.meta.expires_at"],
        },
    ],
    "Legal stay": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "handoff.candidate.full_name",
                "employee.display_name",
                "snapshot.first_name",
                "snapshot.last_name",
            ],
        },
        {
            "field_code": "citizenship",
            "label": "Citizenship",
            "downstream_use": ["work_permit", "zus"],
            "profile_keys": [
                "handoff.candidate.citizenship",
                "candidate.citizenship",
                "candidate.extra.citizenship",
                "eligibility.citizenship",
                "snapshot.citizenship",
            ],
        },
        {
            "field_code": "document_expiry",
            "label": "Stay document expiry",
            "downstream_use": ["compliance"],
            "profile_keys": ["document.expires_at", "context.expires_at"],
        },
    ],
    "Work permit": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract", "permit_application"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "work_country",
            "label": "Work country",
            "downstream_use": ["permit", "zus"],
            "profile_keys": ["eligibility.work_country", "snapshot.work_country"],
        },
        {
            "field_code": "permit_type",
            "label": "Permit / document type",
            "downstream_use": ["permit"],
            "profile_keys": ["document.doc_type", "context.context_type"],
        },
    ],
    "Red paper": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["zus", "contract"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "pesel",
            "label": "PESEL / national id",
            "downstream_use": ["zus"],
            "profile_keys": ["snapshot.pesel", "snapshot.national_id", "employee.meta.pesel"],
        },
    ],
    "Medical": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "exam_valid_until",
            "label": "Medical validity",
            "downstream_use": ["compliance"],
            "profile_keys": ["document.expires_at", "context.expires_at"],
        },
    ],
    "Psychological": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "exam_valid_until",
            "label": "Psychological validity",
            "downstream_use": ["compliance"],
            "profile_keys": ["document.expires_at", "context.expires_at"],
        },
    ],
    "Driver license": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "driver_license_number",
            "label": "License number",
            "downstream_use": ["compliance", "contract"],
            "profile_keys": [
                "handoff.transport.driver_license.number",
                "document.meta.license_number",
                "document.meta.number",
                "employee.meta.license_number",
            ],
        },
        {
            "field_code": "driver_license_categories",
            "label": "License categories",
            "downstream_use": ["compliance", "contract"],
            "profile_keys": [
                "handoff.transport.driver_license.categories",
                "document.meta.categories",
                "document.meta.license_categories",
                "employee.meta.driver_license_categories",
            ],
        },
        {
            "field_code": "driver_license_expiry",
            "label": "License expiry",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "handoff.transport.driver_license.expires_at",
                "document.expires_at",
                "context.expires_at",
            ],
        },
    ],
    "Code95": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "code95_number",
            "label": "Code 95 number",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "handoff.transport.code95.number",
                "document.meta.number",
                "document.meta.code95_number",
            ],
        },
        {
            "field_code": "code95_expiry",
            "label": "Code 95 expiry",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "handoff.transport.code95.expires_at",
                "document.expires_at",
                "context.expires_at",
                "employee.meta.code95_expiry",
            ],
        },
    ],
    "Tacho card": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract"],
            "profile_keys": ["handoff.candidate.full_name", "employee.display_name"],
        },
        {
            "field_code": "tacho_card_number",
            "label": "Tacho card number",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "handoff.transport.tacho_card.number",
                "document.meta.number",
                "document.meta.card_number",
                "employee.meta.tacho_card_number",
            ],
        },
        {
            "field_code": "tacho_card_expiry",
            "label": "Tacho card expiry",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "handoff.transport.tacho_card.expires_at",
                "document.expires_at",
                "context.expires_at",
                "employee.meta.tacho_card_expiry",
            ],
        },
    ],
    "Contacts & address": [
        {
            "field_code": "phone",
            "label": "Phone",
            "input_type": "tel",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "handoff.candidate.phone",
                "contacts.phone",
                "snapshot.phone",
                "employee.meta.personal_data.phone",
            ],
        },
        {
            "field_code": "phone_country_code",
            "label": "Phone country code",
            "input_type": "dial_code",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "handoff.candidate.phone_country_code",
                "handoff.candidate.contacts.phone_country_code",
                "snapshot.phone_country_code",
                "contacts.phone_country_code",
                "employee.meta.personal_data.phone_country_code",
            ],
        },
        {
            "field_code": "email",
            "label": "Email",
            "input_type": "email",
            "downstream_use": ["contract"],
            "profile_keys": [
                "handoff.candidate.email",
                "contacts.email",
                "snapshot.email",
                "employee.meta.personal_data.email",
            ],
        },
        {
            "field_code": "work_country",
            "label": "Work country",
            "input_type": "country",
            "downstream_use": ["contract", "zus", "permit"],
            "profile_keys": [
                "handoff.candidate.work_country",
                "snapshot.work_country",
                "employee.meta.personal_data.work_country",
                "eligibility.work_country",
            ],
        },
        {
            "field_code": "country_of_residence",
            "label": "Country of residence",
            "input_type": "country",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "handoff.candidate.country_code",
                "snapshot.country_code",
                "employee.meta.personal_data.country_code",
                "candidate.extra.country_code",
            ],
        },
        {
            "field_code": "address_country",
            "label": "Country",
            "input_type": "country",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "snapshot.address_country",
                "handoff.candidate.address_country",
                "employee.meta.personal_data.address_country",
                "employee.meta.personal_data.address.country",
            ],
        },
        {
            "field_code": "city",
            "label": "City",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "snapshot.city",
                "handoff.candidate.city",
                "employee.meta.personal_data.city",
                "employee.meta.personal_data.address.city",
            ],
        },
        {
            "field_code": "postal_code",
            "label": "Postal code",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "snapshot.postal_code",
                "handoff.candidate.postal_code",
                "employee.meta.personal_data.postal_code",
                "employee.meta.personal_data.address.zip",
            ],
        },
        {
            "field_code": "address_street",
            "label": "Street",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "snapshot.address_street",
                "handoff.candidate.address_street",
                "employee.meta.personal_data.address_street",
                "employee.meta.personal_data.address.street",
            ],
        },
        {
            "field_code": "address_house",
            "label": "House number",
            "downstream_use": ["contract", "zus"],
            "profile_keys": [
                "snapshot.address_house",
                "handoff.candidate.address_house",
                "employee.meta.personal_data.address_house",
                "employee.meta.personal_data.address.house",
            ],
        },
        {
            "field_code": "address_apt",
            "label": "Apartment",
            "downstream_use": ["contract"],
            "profile_keys": [
                "snapshot.address_apt",
                "handoff.candidate.address_apt",
                "employee.meta.personal_data.address_apt",
                "employee.meta.personal_data.address.apt",
            ],
        },
    ],
    "Work experience": [
        {
            "field_code": "experience_summary",
            "label": "Work experience",
            "downstream_use": ["contract"],
            "profile_keys": [
                "snapshot.experience_summary",
                "snapshot.employments",
                "handoff.candidate.experience_summary",
                "candidate.extra.experience",
                "candidate.extra.employment_history",
                "employee.meta.experience_summary",
            ],
        },
        {
            "field_code": "last_position",
            "label": "Last position",
            "downstream_use": ["contract"],
            "profile_keys": [
                "snapshot.last_position",
                "handoff.candidate.last_position",
                "employee.meta.last_position",
                "candidate.extra.last_position",
            ],
        },
        {
            "field_code": "experience_eu_years",
            "label": "Experience in EU (years)",
            "downstream_use": ["compliance"],
            "profile_keys": [
                "snapshot.experience_eu_years",
                "handoff.candidate.experience_eu_years",
                "candidate.extra.experience_eu_years",
            ],
        },
    ],
}
