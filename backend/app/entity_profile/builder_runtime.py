"""CL4 — Entity Profile builder runtime (two modes).

Compiles a draft into exactly one artifact:

* card → ``layout_instance`` written to the layout registry
* form → ``form_definition`` written to the Forms platform (in-memory)

Closed page-type catalog (CL3). Fields ⊆ CL2 members. Builder does not mint
field semantics (``phone`` vs ``recruitment.candidate.contacts.phone``).
Card and form do not share one saved template. Q&A / Flight / E8 /
DR1-runtime stay later. No DB column drop. No alembic.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
    FIELD_WIDGET,
    PAGE_TYPE_CANDIDATE_CARD,
    PAGE_TYPE_CATALOG,
    PAGE_TYPE_INTAKE_FORM,
    page_type_mode,
)
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID as MEMBERSHIP_CONTRACT_ID,
    is_field_member,
    presence_level,
    resolve_membership,
)
from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE

CONTRACT_ID = "entity_profile_builder.v1"
MODE_CARD = "card"
MODE_FORM = "form"
ARTIFACT_LAYOUT_INSTANCE = "layout_instance"
ARTIFACT_FORM_DEFINITION = "form_definition"
WRITES_TO_LAYOUT_REGISTRY = "layout_registry"
WRITES_TO_FORMS_PLATFORM = "forms_platform"

ERROR_UNKNOWN_PAGE_TYPE = "unknown_page_type"
ERROR_UNKNOWN_PROFILE = "unknown_profile"
ERROR_MODE_MISMATCH = "mode_mismatch"
ERROR_MIXED_DRAFT = "mixed_draft"
ERROR_NON_MEMBER_FIELD = "non_member_field"
ERROR_DISALLOWED_WIDGET = "disallowed_widget"
ERROR_MINTED_FIELD_SEMANTICS = "minted_field_semantics"

_CARD_BODY_KEYS = frozenset({"card", "card_placements", "layout", "layout_instance"})
_FORM_BODY_KEYS = frozenset({"form", "form_placements", "form_definition"})


def list_builder_modes() -> tuple[str, ...]:
    seen: list[str] = []
    for spec in PAGE_TYPE_CATALOG.values():
        mode = str(spec["mode"])
        if mode not in seen:
            seen.append(mode)
    return tuple(seen)


def palette(profile_code: str, page_type: str) -> Optional[dict[str, Any]]:
    """CL2 members + widgets allowed for a closed page type."""
    code = str(profile_code or "").strip()
    ptype = str(page_type or "").strip()
    spec = PAGE_TYPE_CATALOG.get(ptype)
    if not code or spec is None:
        return None
    membership = resolve_membership(code)
    if membership is None:
        return None
    return {
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "page_type": ptype,
        "mode": spec["mode"],
        "writes_to": spec["writes_to"],
        "fields": [
            {
                "qualified_code": row["qualified_code"],
                "kind": row["kind"],
                "presence": dict(row["presence"]),
            }
            for row in membership["fields"]
        ],
        "widgets": tuple(sorted(spec["widgets"])),
    }


def compile_draft(draft: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compile one draft into one artifact. Never both card and form."""
    payload = dict(draft or {})
    if _is_mixed_draft(payload):
        return _fail(ERROR_MIXED_DRAFT)

    profile_code = str(payload.get("profile_code") or "").strip()
    page_type = str(payload.get("page_type") or "").strip()
    mode = str(payload.get("mode") or "").strip()
    spec = PAGE_TYPE_CATALOG.get(page_type)
    if spec is None:
        return _fail(ERROR_UNKNOWN_PAGE_TYPE)

    expected_mode = str(spec["mode"])
    if mode != expected_mode:
        return _fail(ERROR_MODE_MISMATCH)

    membership = resolve_membership(profile_code)
    if membership is None:
        return _fail(ERROR_UNKNOWN_PROFILE)

    allowed_widgets = spec["widgets"]
    placements = _placements(payload)
    compiled_fields: list[dict[str, Any]] = []
    for index, row in enumerate(placements):
        if not isinstance(row, dict):
            continue
        qualified = str(row.get("qualified_code") or "").strip()
        widget = str(row.get("widget") or FIELD_WIDGET).strip() or FIELD_WIDGET
        if _is_minted_field_code(qualified):
            return _fail(ERROR_MINTED_FIELD_SEMANTICS, qualified_code=qualified)
        if not is_field_member(profile_code, qualified):
            return _fail(ERROR_NON_MEMBER_FIELD, qualified_code=qualified)
        if widget not in allowed_widgets:
            return _fail(ERROR_DISALLOWED_WIDGET, widget=widget)
        section_code = str(row.get("section_code") or "general").strip() or "general"
        compiled_fields.append(
            {
                "qualified_code": qualified,
                "section_code": section_code,
                "sort_order": int(row.get("sort_order") or index),
                "widget": widget,
                "presence": _presence_for_mode(profile_code, qualified, expected_mode),
            }
        )

    if expected_mode == MODE_CARD:
        return {
            "ok": True,
            "contract_id": CONTRACT_ID,
            "artifact_kind": ARTIFACT_LAYOUT_INSTANCE,
            "writes_to": WRITES_TO_LAYOUT_REGISTRY,
            "page_type": page_type,
            "mode": MODE_CARD,
            "artifact": _layout_instance_artifact(
                profile_code, page_type, membership, compiled_fields
            ),
        }

    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "artifact_kind": ARTIFACT_FORM_DEFINITION,
        "writes_to": WRITES_TO_FORMS_PLATFORM,
        "page_type": page_type,
        "mode": MODE_FORM,
        "artifact": _form_definition_artifact(profile_code, page_type, compiled_fields),
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "proof_card_page_type": PAGE_TYPE_CANDIDATE_CARD,
        "proof_form_page_type": PAGE_TYPE_INTAKE_FORM,
        "producer": "backend.app.entity_profile.builder_runtime",
    }


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": error, "contract_id": CONTRACT_ID}
    out.update(extra)
    return out


def _is_minted_field_code(code: str) -> bool:
    """Leaf names like ``phone`` are not field SoT; place the qualified code."""
    return "." not in code


def _is_mixed_draft(draft: Mapping[str, Any]) -> bool:
    keys = set(draft)
    if keys & _CARD_BODY_KEYS and keys & _FORM_BODY_KEYS:
        return True

    raw_modes = draft.get("modes")
    if isinstance(raw_modes, (list, tuple)):
        listed = {str(item).strip() for item in raw_modes if str(item).strip()}
        if len(listed) > 1:
            return True

    raw_page_types = draft.get("page_types")
    if isinstance(raw_page_types, (list, tuple)):
        catalog_modes = {
            page_type_mode(str(item).strip())
            for item in raw_page_types
            if str(item).strip()
        }
        catalog_modes.discard(None)
        if len(catalog_modes) > 1:
            return True
    return False


def _placements(draft: Mapping[str, Any]) -> list[Any]:
    for key in ("placements", "card_placements", "form_placements"):
        rows = draft.get(key)
        if isinstance(rows, list):
            return rows
    for key in ("card", "form", "layout"):
        nested = draft.get(key)
        if isinstance(nested, dict) and isinstance(nested.get("placements"), list):
            return nested["placements"]
    return []


def _presence_for_mode(profile_code: str, qualified: str, mode: str) -> dict[str, str]:
    context = "card_save" if mode == MODE_CARD else "intake"
    level = presence_level(profile_code, qualified, context) or "optional"
    return {context: level}


def _layout_instance_artifact(
    profile_code: str,
    page_type: str,
    membership: Mapping[str, Any],
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    layout_code = str(membership["refs"].get("default_layout_code") or "").strip()
    if not layout_code:
        layout_code = DEFAULT_CANDIDATE_LAYOUT_CODE
    sections: dict[str, dict[str, Any]] = {}
    for item in fields:
        section_code = item["section_code"]
        section = sections.setdefault(
            section_code,
            {"code": section_code, "order": item["sort_order"], "fields": []},
        )
        section["fields"].append(item)
    return {
        "contract_id": LAYOUT_CONTRACT_ID,
        "membership_contract_id": MEMBERSHIP_CONTRACT_ID,
        "profile_code": profile_code,
        "page_type": page_type,
        "mode": MODE_CARD,
        "layout_code": layout_code,
        "fields": fields,
        "sections": sorted(sections.values(), key=lambda row: row.get("order") or 0),
    }


def _form_definition_artifact(
    profile_code: str,
    page_type: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    # In-memory Forms platform artifact. Persistence stays Forms C3 — no alembic.
    return {
        "profile_code": profile_code,
        "page_type": page_type,
        "mode": MODE_FORM,
        "fields": fields,
    }
