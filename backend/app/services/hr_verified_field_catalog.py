"""Canonical HR verified field definitions (shared by document verification + SoT layer)."""

from __future__ import annotations

from typing import Any

# Fields that must be verified (or overridden) before employment approval.
CRITICAL_FIELD_CODES: frozenset[str] = frozenset(
    {
        "full_name",
        "citizenship",
        "work_country",
        "pesel",
        "document_expiry",
        "permit_type",
    }
)

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
            "field_code": "document_expiry",
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
}
