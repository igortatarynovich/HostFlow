"""CL3 — Entity Profile layout runtime.

Projects a closed page-type layout instance from Entity Profile membership
(CL2) + Field Registry layout code. Proof = D4 Information zone
(``candidate.card``). Builder / form templates / Q&A / Flight stay later.
No DB column drop.

Card and form do not share one saved template. ``intake.form`` is catalogued
but not resolved in this slice (Forms platform / CL4).
"""

from __future__ import annotations

from typing import Any, Optional

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID as MEMBERSHIP_CONTRACT_ID,
    is_field_member,
    presence_level,
    resolve_membership,
)
from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE

CONTRACT_ID = "entity_profile_layout.v1"
PAGE_TYPE_CANDIDATE_CARD = "candidate.card"
PAGE_TYPE_INTAKE_FORM = "intake.form"
FIELD_WIDGET = "field"

PAGE_TYPE_CATALOG: dict[str, dict[str, Any]] = {
    PAGE_TYPE_CANDIDATE_CARD: {
        "mode": "card",
        "writes_to": "layout_registry",
        "widgets": frozenset({FIELD_WIDGET}),
        "resolvable": True,
    },
    PAGE_TYPE_INTAKE_FORM: {
        "mode": "form",
        "writes_to": "forms_platform",
        "widgets": frozenset({FIELD_WIDGET}),
        "resolvable": False,
    },
}


def list_page_types() -> tuple[str, ...]:
    return tuple(PAGE_TYPE_CATALOG)


def page_type_mode(page_type: str) -> Optional[str]:
    row = PAGE_TYPE_CATALOG.get(str(page_type or "").strip())
    if row is None:
        return None
    return str(row["mode"])


def _layout_manifest(layout_code: str) -> Optional[dict[str, Any]]:
    from backend.app.field_registry.manifests.recruitment import recruitment_card_layouts

    needle = str(layout_code or "").strip()
    if not needle:
        return None
    for row in recruitment_card_layouts():
        if str(row.get("code") or "").strip() == needle:
            return row
    return None


def resolve_layout(
    profile_code: str,
    page_type: str = PAGE_TYPE_CANDIDATE_CARD,
) -> Optional[dict[str, Any]]:
    """Project a card layout for a profile. Non-members are dropped.

    ``intake.form`` is in the closed catalog but not produced here.
    """
    code = str(profile_code or "").strip()
    ptype = str(page_type or "").strip()
    spec = PAGE_TYPE_CATALOG.get(ptype)
    if not code or spec is None or not spec.get("resolvable"):
        return None

    membership = resolve_membership(code)
    if membership is None:
        return None

    layout_code = str(membership["refs"].get("default_layout_code") or "").strip()
    if not layout_code:
        layout_code = DEFAULT_CANDIDATE_LAYOUT_CODE
    manifest = _layout_manifest(layout_code)
    if manifest is None:
        return None

    fields: list[dict[str, Any]] = []
    sections: dict[str, dict[str, Any]] = {}
    for row in manifest.get("fields") or []:
        if not isinstance(row, dict):
            continue
        qualified = str(row.get("qualified_code") or "").strip()
        if not qualified or not is_field_member(code, qualified):
            continue
        section_code = str(row.get("section_code") or "general").strip() or "general"
        item = {
            "qualified_code": qualified,
            "section_code": section_code,
            "sort_order": int(row.get("sort_order") or 0),
            "widget": FIELD_WIDGET,
            "presence": {
                "card_save": presence_level(code, qualified, "card_save") or "optional",
            },
        }
        fields.append(item)
        section = sections.setdefault(
            section_code,
            {"code": section_code, "order": item["sort_order"], "fields": []},
        )
        section["fields"].append(item)

    return {
        "contract_id": CONTRACT_ID,
        "membership_contract_id": MEMBERSHIP_CONTRACT_ID,
        "profile_code": code,
        "page_type": ptype,
        "mode": spec["mode"],
        "layout_code": str(manifest.get("code") or layout_code),
        "fields": fields,
        "sections": sorted(sections.values(), key=lambda s: s.get("order") or 0),
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "proof_page_type": PAGE_TYPE_CANDIDATE_CARD,
        "producer": "backend.app.entity_profile.layout_runtime",
    }
