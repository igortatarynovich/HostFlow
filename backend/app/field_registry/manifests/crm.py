"""CRM / client company canonical fields."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import CRM_MODULE, DEFAULT_CLIENT_LAYOUT_CODE, ENTITY_CLIENT


def _client_field(field_code: str, *, field_type: str, name: str, storage: dict[str, Any]) -> dict[str, Any]:
    qualified = f"crm.client.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code,
        "entity_type": ENTITY_CLIENT,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.crm_client_{field_code}",
        "ownership": CRM_MODULE,
        "pii_class": "business" if field_code in {"contact_email", "contact_phone"} else None,
        "reference_domain": None,
        "storage": storage,
        "legacy_aliases": [field_code],
        "default_section": "basic",
    }


def crm_client_fields() -> list[dict[str, Any]]:
    return [
        _client_field("name", field_type="text", name="Company name", storage={"kind": "column", "path": "name"}),
        _client_field("tax_id", field_type="text", name="Tax ID", storage={"kind": "column", "path": "tax_id"}),
        _client_field("contact_email", field_type="email", name="Contact email", storage={"kind": "json_path", "path": "extra.contact_email"}),
        _client_field("contact_phone", field_type="phone_e164", name="Contact phone", storage={"kind": "json_path", "path": "extra.contact_phone"}),
        _client_field("address", field_type="text", name="Address", storage={"kind": "json_path", "path": "extra.address"}),
    ]


def crm_card_layouts() -> list[dict[str, Any]]:
    fields = []
    order = 10
    for row in crm_client_fields():
        fields.append(
            {
                "qualified_code": row["qualified_code"],
                "section_code": "basic",
                "sort_order": order,
                "visible": True,
                "required": row["qualified_code"] == "crm.client.name",
            }
        )
        order += 10
    return [
        {
            "code": DEFAULT_CLIENT_LAYOUT_CODE,
            "name": "CRM client default card",
            "entity_type": ENTITY_CLIENT,
            "is_default": True,
            "fields": fields,
        }
    ]


def crm_module_manifest() -> dict[str, Any]:
    return {
        "module": CRM_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": crm_client_fields(),
        "card_layouts": crm_card_layouts(),
    }
