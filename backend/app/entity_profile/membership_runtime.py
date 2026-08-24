"""CL2 — Entity Profile membership runtime.

Named producer for role-manifest membership: which fields belong to a
profile, with baseline presence ``intake`` / ``card_save`` only.

``transition`` / ``handoff`` are not Profile-field properties (CL0).
Layout, builder, Q&A, and Flight stay in later CL slices. No DB column drop.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

CONTRACT_ID = "entity_profile_membership.v1"
MEMBERSHIP_CONTEXTS = frozenset({"intake", "card_save"})
FORBIDDEN_PROFILE_CONTEXTS = frozenset({"transition", "handoff"})
PRESENCE_LEVELS = frozenset({"required", "optional", "hidden"})


def _platform_manifests() -> dict[str, dict[str, Any]]:
    from backend.app.entity_profile.manifests.recruitment import (
        recruitment_module_entity_profiles,
    )
    from backend.app.entity_profile.manifests.service_sales import (
        service_sales_module_entity_profiles,
    )

    out: dict[str, dict[str, Any]] = {}
    for row in (
        *recruitment_module_entity_profiles(),
        *service_sales_module_entity_profiles(),
    ):
        code = str(row.get("profile_code") or "").strip()
        if code:
            out[code] = row
    return out


@lru_cache(maxsize=1)
def platform_membership_catalog() -> dict[str, dict[str, Any]]:
    return _platform_manifests()


def _screening_pack_code(manifest: dict[str, Any]) -> Optional[str]:
    explicit = str(manifest.get("screening_pack_code") or "").strip()
    if explicit:
        return explicit
    config = manifest.get("config") or {}
    nested = str(config.get("screening_pack_code") or "").strip()
    return nested or None


def _presence_from_field(row: dict[str, Any]) -> dict[str, str]:
    intake = str(row.get("intake_level") or "optional").strip() or "optional"
    card_save = str(row.get("card_save_level") or "optional").strip() or "optional"
    if intake not in PRESENCE_LEVELS:
        intake = "optional"
    if card_save not in PRESENCE_LEVELS:
        card_save = "optional"
    return {"intake": intake, "card_save": card_save}


def _member_row(row: dict[str, Any]) -> dict[str, Any]:
    code = str(row.get("qualified_code") or "").strip()
    return {
        "qualified_code": code,
        "kind": "canonical",
        "is_member": True,
        "sort_order": int(row.get("sort_order") or 0),
        "presence": _presence_from_field(row),
    }


def resolve_membership(profile_code: str) -> Optional[dict[str, Any]]:
    """Project CL0 membership for a platform Entity Profile.

    Returns ``None`` when the profile is not in the platform catalog.
    Tenant custom-field overlay is an empty list in this slice.
    """
    code = str(profile_code or "").strip()
    if not code:
        return None
    manifest = platform_membership_catalog().get(code)
    if manifest is None:
        return None

    fields = [
        _member_row(row)
        for row in (manifest.get("fields") or [])
        if isinstance(row, dict) and str(row.get("qualified_code") or "").strip()
    ]
    return {
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "fields": fields,
        "custom_fields": [],
        "refs": {
            "default_layout_code": manifest.get("default_layout_code") or None,
            "document_pack_code": manifest.get("document_pack_code") or None,
            "screening_pack_code": _screening_pack_code(manifest),
            "process_profile_code": manifest.get("process_profile_code") or None,
        },
    }


def is_field_member(profile_code: str, qualified_code: str) -> bool:
    membership = resolve_membership(profile_code)
    if membership is None:
        return False
    needle = str(qualified_code or "").strip()
    if not needle:
        return False
    return any(row["qualified_code"] == needle for row in membership["fields"])


def presence_level(
    profile_code: str,
    qualified_code: str,
    context: str,
) -> Optional[str]:
    """Baseline presence for ``intake`` / ``card_save``.

    ``transition`` / ``handoff`` are never answered from Profile membership.
    """
    ctx = str(context or "").strip()
    if ctx in FORBIDDEN_PROFILE_CONTEXTS or ctx not in MEMBERSHIP_CONTEXTS:
        return None
    membership = resolve_membership(profile_code)
    if membership is None:
        return None
    needle = str(qualified_code or "").strip()
    for row in membership["fields"]:
        if row["qualified_code"] == needle:
            return str(row["presence"][ctx])
    return None


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "producer": "backend.app.entity_profile.membership_runtime",
    }
