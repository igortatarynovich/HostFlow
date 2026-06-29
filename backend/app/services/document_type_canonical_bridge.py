"""Bridge module catalog doc types → Platform Reference canonical codes (SSOT).

Recruitment/UI types live in ``document_types.definitions`` with ``canonical_ref_code``
pointing at ``ref_document_types.code``. All legacy aliases and supplemental codes
resolve through :func:`normalize_legacy_doc_type` — used by reference sync, runtime
resolver, pack projection, and eligibility.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS

# Legacy doc_type strings that are not module catalog codes but still appear in DB/API.
SUPPLEMENTAL_LEGACY_TO_REF: dict[str, str] = {
    "id": "id_card",
    "medical": "medical_certificate",
    "psycho_test": "psychotest",
    "contract": "employment_contract",
    "employment_contract": "employment_contract",
    "civil_contract": "civil_contract",
    "zus_zua": "zus_zua",
    "zus_zza": "zus_zza",
    "tax_declaration": "tax_declaration",
}


def _norm(value: Optional[str]) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@lru_cache(maxsize=1)
def build_legacy_to_ref_canonical_map() -> dict[str, str]:
    """Build alias → ref canonical map from platform seeds + module catalog."""
    from backend.app.services.document_reference_sync import SYSTEM_CODES

    out: dict[str, str] = {}

    for code in SYSTEM_CODES:
        out[_norm(code)] = _norm(code)

    for definition in DOCUMENT_TYPE_DEFINITIONS:
        ref_code = _norm(definition.canonical_ref_code or "other")
        if ref_code not in SYSTEM_CODES:
            ref_code = "other"
        out[_norm(definition.code)] = ref_code
        for alias in definition.aliases:
            out[_norm(alias)] = ref_code

    for legacy, ref in SUPPLEMENTAL_LEGACY_TO_REF.items():
        out[_norm(legacy)] = _norm(ref)

    return out


def normalize_legacy_doc_type(value: Optional[str]) -> str:
    """Map any legacy/module doc_type string to a platform ref canonical code."""
    key = _norm(value)
    if not key:
        return "other"
    return build_legacy_to_ref_canonical_map().get(key, "other")


def legacy_codes_for_ref_canonical(ref_code: str) -> frozenset[str]:
    """All legacy strings that resolve to the given ref canonical code."""
    target = _norm(ref_code)
    return frozenset(k for k, v in build_legacy_to_ref_canonical_map().items() if v == target)


__all__ = [
    "SUPPLEMENTAL_LEGACY_TO_REF",
    "build_legacy_to_ref_canonical_map",
    "legacy_codes_for_ref_canonical",
    "normalize_legacy_doc_type",
]
