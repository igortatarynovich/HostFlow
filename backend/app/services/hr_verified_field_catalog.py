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
}

# Per document-key field specs for verification cards (PR3).
FIELD_SPECS: dict[str, list[dict[str, Any]]] = {
    "Legal stay": [
        {
            "field_code": "full_name",
            "label": "Full name",
            "downstream_use": ["contract", "zus"],
            "profile_keys": ["employee.display_name", "snapshot.first_name", "snapshot.last_name"],
        },
        {
            "field_code": "citizenship",
            "label": "Citizenship",
            "downstream_use": ["work_permit", "zus"],
            "profile_keys": ["eligibility.citizenship", "snapshot.citizenship"],
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
            "profile_keys": ["employee.display_name"],
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
            "profile_keys": ["employee.display_name"],
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
            "profile_keys": ["employee.display_name"],
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
            "profile_keys": ["employee.display_name"],
        },
        {
            "field_code": "exam_valid_until",
            "label": "Psychological validity",
            "downstream_use": ["compliance"],
            "profile_keys": ["document.expires_at", "context.expires_at"],
        },
    ],
}
