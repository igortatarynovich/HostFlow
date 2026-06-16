from __future__ import annotations

from backend.app.reference.reference_field_schema_registry import (
    CATALOG_VERSION,
    get_reference_field_schema,
    list_reference_field_schemas,
)


def test_reference_field_schema_registry_baseline_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1c-field-schema-")
    fields = list_reference_field_schemas()
    assert len(fields) >= 1
    for item in fields:
        assert item.field_key
        assert item.field_type
        assert item.group
        assert item.reference_domain


def test_reference_field_schema_registry_lookup() -> None:
    row = get_reference_field_schema("citizenship")
    assert row is not None
    assert row.field_key == "citizenship"
    assert row.reference_domain == "citizenships"

    assert get_reference_field_schema("unknown_key") is None


def test_reference_field_schema_registry_workforce_transport_fields_present() -> None:
    expected_keys = {
        "workforce_category",
        "employment_type",
        "transport_mode",
        "transport_qualification_type",
        "driver_capability_class",
    }
    fields = {item.field_key for item in list_reference_field_schemas()}
    assert expected_keys.issubset(fields)
