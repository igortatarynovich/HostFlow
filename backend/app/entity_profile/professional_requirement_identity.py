"""Stable identity of a professional vacancy requirement.

Producers use these constructors. ``qualified_code`` is the merge key.
``kind`` does not decide which requirements are the same requirement.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from backend.app.constants.catalogs import LANGUAGES
from backend.app.constants.reference_foundation import get_reference_domain
from backend.app.reference.professional_profile_catalogs import (
    CREW_MODE,
    MOVEMENT_PATTERN,
    OPERATION_SCOPE,
    PROFESSIONAL_CATALOG_CODES,
)

CAPABILITY_FLAGS = ("code95", "adr", "tachograph")
EXPERIENCE_FACETS = ("total", "CE", "EU", "international")
TRAILER_HIRING_CODES = ("curtain", "reefer", "container", "tanker", "dump", "platform")
CONSTRAINT_SUBJECTS = ("work_pattern", "vehicle", "trailer", "route", "geography", "qualification", "other")
STRENGTHS = ("mandatory", "preferred")
EXPERIENCE_MODES = ("presence", "minimum")
_PROFESSIONAL_PREFIXES = ("capability:", "experience:", "characteristic:", "language:")


def _licence_codes() -> set[str]:
    return {
        str(row.get("code") or "").strip().upper()
        for row in get_reference_domain("driver_license_categories")
        if str(row.get("code") or "").strip()
    }


def _language_codes() -> set[str]:
    return {str(row["code"]) for row in LANGUAGES if row.get("code") and row["code"] != "other"}


def _catalog_codes(vocabulary: str) -> set[str]:
    return {item.code for item in PROFESSIONAL_CATALOG_CODES if item.vocabulary == vocabulary}


def looks_like_professional_qualified_code(value: str) -> bool:
    text = str(value or "").strip()
    return any(text.startswith(prefix) for prefix in _PROFESSIONAL_PREFIXES)


def parse_qualified_code(value: str) -> Optional[dict[str, Any]]:
    """Return the identity parts, or None when the code is not a professional requirement."""
    text = str(value or "").strip()
    if text.startswith("capability:driving_category:"):
        code = text.removeprefix("capability:driving_category:")
        if code not in _licence_codes():
            return None
        return {"qualified_code": text, "domain": "capability", "facet": "driving_category", "code": code}
    if text.startswith("capability:"):
        flag = text.removeprefix("capability:")
        if flag not in CAPABILITY_FLAGS:
            return None
        return {"qualified_code": text, "domain": "capability", "facet": flag, "code": flag}
    if text in {f"experience:{facet}" for facet in EXPERIENCE_FACETS}:
        facet = text.removeprefix("experience:")
        return {"qualified_code": text, "domain": "experience", "facet": facet, "code": facet}
    if text.startswith("experience:trailer_hiring:"):
        code = text.removeprefix("experience:trailer_hiring:")
        if code not in TRAILER_HIRING_CODES:
            return None
        return {"qualified_code": text, "domain": "experience", "facet": "trailer_hiring", "code": code}
    for vocabulary in (OPERATION_SCOPE, MOVEMENT_PATTERN, CREW_MODE):
        prefix = f"experience:{vocabulary}:"
        if not text.startswith(prefix):
            continue
        code = text.removeprefix(prefix)
        if vocabulary == OPERATION_SCOPE and code == "international":
            return None
        if code not in _catalog_codes(vocabulary):
            return None
        return {"qualified_code": text, "domain": "experience", "facet": vocabulary, "code": code}
    if text.startswith("characteristic:"):
        rest = text.removeprefix("characteristic:")
        subject, separator, code = rest.partition(":")
        if not separator or subject not in CONSTRAINT_SUBJECTS or not code or ":" in code:
            return None
        if not code.replace("_", "").isalnum() or not code.islower():
            return None
        return {
            "qualified_code": text,
            "domain": "characteristic",
            "facet": subject,
            "subject": subject,
            "code": code,
        }
    if text.startswith("language:"):
        code = text.removeprefix("language:")
        if code not in _language_codes():
            return None
        return {"qualified_code": text, "domain": "language", "facet": "language", "code": code}
    return None


def parse_requirement_predicate(predicate: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Normalize one predicate. None means it is not a valid professional requirement."""
    identity = parse_qualified_code(str(predicate.get("qualified_code") or ""))
    if identity is None:
        return None
    strength = str(predicate.get("strength") or "").strip().lower()
    if strength not in STRENGTHS:
        return None
    domain = identity["domain"]
    mode = str(predicate.get("mode") or "").strip().lower()
    raw_days = predicate.get("minimum_days")
    if domain == "experience":
        if mode not in EXPERIENCE_MODES:
            return None
        if mode == "minimum":
            if isinstance(raw_days, bool) or not isinstance(raw_days, int) or raw_days <= 0:
                return None
            minimum_days: int | None = raw_days
        else:
            if raw_days not in (None, ""):
                return None
            minimum_days = None
    else:
        if mode not in ("", "presence"):
            return None
        if raw_days not in (None, ""):
            return None
        mode = "presence"
        minimum_days = None
    return {
        **identity,
        "strength": strength,
        "mode": mode,
        "minimum_days": minimum_days,
    }


def professional_delta(
    *,
    qualified_code: str,
    strength: str,
    mode: str | None = None,
    minimum_days: int | None = None,
    op: str = "add",
    owner: str = "vacancy",
) -> dict[str, Any]:
    """One Overlay value delta whose identity is the qualified code."""
    predicate: dict[str, Any] = {"qualified_code": qualified_code, "strength": strength}
    if mode is not None:
        predicate["mode"] = mode
    if minimum_days is not None:
        predicate["minimum_days"] = minimum_days
    if parse_requirement_predicate(predicate) is None:
        raise ValueError(f"invalid professional requirement: {qualified_code}")
    return {
        "kind": "value",
        "code": qualified_code,
        "owner": owner,
        "op": op,
        "predicate": predicate,
    }
