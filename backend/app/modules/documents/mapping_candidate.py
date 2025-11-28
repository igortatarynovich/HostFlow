from __future__ import annotations

from typing import Any, Dict

# Простая карта: doc_type -> { doc_field: candidate_field }
MAPPING: Dict[str, Dict[str, str]] = {
    "passport": {
        "surname": "last_name",
        "given_names": "first_name",
        "nationality": "citizenship",
        "date_of_birth": "dob",
    },
    "national_id": {
        "surname": "last_name",
        "given_names": "first_name",
        "nationality": "citizenship",
        "date_of_birth": "dob",
    },
}


def apply_mapping(
    candidate: Dict[str, Any], doc_type: str, fields: Dict[str, Any]
) -> Dict[str, Any]:
    cmap = MAPPING.get(doc_type, {})
    for src, dst in cmap.items():
        if src in fields:
            candidate[dst] = fields[src]
    return candidate
