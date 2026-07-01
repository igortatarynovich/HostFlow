"""Platform identity canonical fields (shared namespace)."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import ENTITY_CANDIDATE, PLATFORM_MODULE


def _field(
    field_code: str,
    *,
    field_type: str,
    name: str,
    storage: dict[str, Any],
    pii_class: str = "identity",
    reference_domain: str | None = None,
    legacy_aliases: list[str] | None = None,
) -> dict[str, Any]:
    qualified = f"platform.identity.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code,
        "entity_type": ENTITY_CANDIDATE,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.{qualified.replace('.', '_')}",
        "ownership": PLATFORM_MODULE,
        "pii_class": pii_class,
        "reference_domain": reference_domain,
        "storage": storage,
        "legacy_aliases": legacy_aliases or [],
    }


def platform_identity_fields() -> list[dict[str, Any]]:
    return [
        _field(
            "birth_date",
            field_type="date",
            name="Birth date",
            storage={"kind": "json_path", "path": "personal_data.birth_date"},
            legacy_aliases=["birth_date", "personal.birth_date"],
        ),
        _field(
            "citizenship",
            field_type="reference_code",
            name="Citizenship",
            storage={"kind": "json_path", "path": "personal_data.citizenship"},
            reference_domain="citizenships",
            legacy_aliases=["citizenship", "personal.citizenship"],
        ),
        _field(
            "address",
            field_type="text",
            name="Address",
            storage={"kind": "json_path", "path": "personal_data.address"},
            legacy_aliases=["address", "personal.address"],
        ),
    ]


def platform_module_manifest() -> dict[str, Any]:
    return {
        "module": PLATFORM_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": platform_identity_fields(),
        "card_layouts": [],
    }
