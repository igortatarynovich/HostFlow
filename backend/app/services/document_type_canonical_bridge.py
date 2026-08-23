"""Bridge module catalog doc types → Platform Reference canonical codes (SSOT).

All legacy alias normalization delegates to ``document_types.registry`` which loads
``document-type-legacy-aliases-v1.json``. Used by reference sync, runtime resolver,
pack projection, and eligibility.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from backend.app.document_types.registry import (
    build_legacy_to_canonical_map as build_registry_legacy_map,
    normalize_input_doc_type,
)


def _norm(value: Optional[str]) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@lru_cache(maxsize=1)
def build_legacy_to_ref_canonical_map() -> dict[str, str]:
    """Alias → ref canonical map filtered to seeded reference codes."""
    from backend.app.services.document_reference_sync import SYSTEM_CODES

    full = build_registry_legacy_map()
    return {key: (value if value in SYSTEM_CODES else "other") for key, value in full.items()}


def normalize_legacy_doc_type(value: Optional[str]) -> str:
    """Map any legacy/module doc_type string to a platform ref canonical code."""
    canonical = normalize_input_doc_type(value)
    from backend.app.services.document_reference_sync import SYSTEM_CODES

    return canonical if canonical in SYSTEM_CODES else "other"


def legacy_codes_for_ref_canonical(ref_code: str) -> frozenset[str]:
    """All legacy strings that resolve to the given ref canonical code."""
    target = _norm(ref_code)
    return frozenset(k for k, v in build_legacy_to_ref_canonical_map().items() if v == target)


__all__ = [
    "build_legacy_to_ref_canonical_map",
    "legacy_codes_for_ref_canonical",
    "normalize_legacy_doc_type",
]
