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


def hub_storage_keys_for_requirement_code(requirement_code: Optional[str]) -> tuple[str, ...]:
    """Ordered Hub/storage keys that may satisfy a pack/R5 requirement code.

    Exact requirement code first, then legacy/module storage aliases from the
    registry bridge (e.g. ``driver_qualification_card`` → ``code95``).

    Consumers (requirement evaluator, delivery contract, pack projection) MUST use
    this authority instead of inventing per-consumer alias tables.
    """
    code = _norm(requirement_code)
    if not code:
        return ()
    ref = _norm(normalize_legacy_doc_type(code))
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in (code, ref, *sorted(legacy_codes_for_ref_canonical(ref or code))):
        key = _norm(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return tuple(ordered)


def document_storage_type_matches(storage_type: Optional[str], *tokens: str) -> bool:
    """True if a Hub storage type satisfies any of the evidence/pick tokens.

    Uses ``hub_storage_keys_for_requirement_code`` — no per-consumer alias tables
    and no type-specific ``if`` branches in callers.
    """
    code = _norm(storage_type)
    if not code:
        return False
    accepted: set[str] = set()
    for token in tokens:
        accepted.update(hub_storage_keys_for_requirement_code(token))
    return code in accepted


__all__ = [
    "build_legacy_to_ref_canonical_map",
    "document_storage_type_matches",
    "hub_storage_keys_for_requirement_code",
    "legacy_codes_for_ref_canonical",
    "normalize_legacy_doc_type",
]
