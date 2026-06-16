"""Fleet vehicle canonical fields and default card layout."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import (
    DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
    ENTITY_FLEET_VEHICLE,
    FLEET_MODULE,
)


def _vehicle_field(
    field_code: str,
    *,
    field_type: str,
    name: str,
    storage: dict[str, Any],
    section: str,
    reference_domain: str | None = None,
) -> dict[str, Any]:
    qualified = f"fleet.vehicle.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code,
        "entity_type": ENTITY_FLEET_VEHICLE,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.fleet_vehicle_{field_code}",
        "ownership": FLEET_MODULE,
        "pii_class": None,
        "reference_domain": reference_domain,
        "storage": storage,
        "legacy_aliases": [field_code],
        "default_section": section,
    }


def fleet_vehicle_fields() -> list[dict[str, Any]]:
    return [
        _vehicle_field(
            "internal_code",
            field_type="text",
            name="Internal code",
            storage={"kind": "column", "path": "internal_code"},
            section="identity",
        ),
        _vehicle_field(
            "registration_plate",
            field_type="text",
            name="Registration plate",
            storage={"kind": "column", "path": "registration_plate"},
            section="identity",
        ),
        _vehicle_field(
            "vin",
            field_type="text",
            name="VIN",
            storage={"kind": "column", "path": "vin"},
            section="identity",
        ),
        _vehicle_field(
            "brand",
            field_type="text",
            name="Brand",
            storage={"kind": "column", "path": "brand"},
            section="technical",
        ),
        _vehicle_field(
            "model",
            field_type="text",
            name="Model",
            storage={"kind": "column", "path": "model"},
            section="technical",
        ),
        _vehicle_field(
            "year",
            field_type="integer",
            name="Year",
            storage={"kind": "column", "path": "year"},
            section="technical",
        ),
        _vehicle_field(
            "status",
            field_type="code",
            name="Vehicle status",
            storage={"kind": "column", "path": "status"},
            section="operations",
            reference_domain="fleet_vehicle_statuses",
        ),
        _vehicle_field(
            "operating_company_id",
            field_type="code",
            name="Operating company",
            storage={"kind": "column", "path": "operating_company_id"},
            section="operations",
        ),
        _vehicle_field(
            "notes",
            field_type="textarea",
            name="Notes",
            storage={"kind": "column", "path": "notes"},
            section="notes",
        ),
    ]


def _layout_field(qualified_code: str, *, section: str, order: int, required: bool = False) -> dict[str, Any]:
    return {
        "qualified_code": qualified_code,
        "section_code": section,
        "sort_order": order,
        "visible": True,
        "required": required,
    }


def fleet_card_layouts() -> list[dict[str, Any]]:
    fields = []
    order = 10
    for row in fleet_vehicle_fields():
        fields.append(
            _layout_field(
                row["qualified_code"],
                section=str(row.get("default_section") or "general"),
                order=order,
                required=row["qualified_code"] == "fleet.vehicle.registration_plate",
            )
        )
        order += 10
    return [
        {
            "code": DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
            "name": "Fleet vehicle default card",
            "entity_type": ENTITY_FLEET_VEHICLE,
            "is_default": True,
            "fields": fields,
        }
    ]


def fleet_module_manifest() -> dict[str, Any]:
    return {
        "module": FLEET_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": fleet_vehicle_fields(),
        "card_layouts": fleet_card_layouts(),
    }
