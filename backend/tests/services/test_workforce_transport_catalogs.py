from __future__ import annotations

from backend.app.reference.workforce_transport_catalogs import (
    CATALOG_VERSION,
    get_driver_capability_class_by_code,
    get_transport_mode_by_code,
    get_workforce_category_by_code,
    list_driver_capability_classes_canonical,
    list_employment_types_canonical,
    list_transport_modes_canonical,
    list_transport_qualification_types_canonical,
    list_workforce_categories_canonical,
)


def test_workforce_transport_catalogs_baseline_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1c-workforce-transport-")
    assert len(list_workforce_categories_canonical()) >= 1
    assert len(list_employment_types_canonical()) >= 1
    assert len(list_transport_modes_canonical()) >= 1
    assert len(list_transport_qualification_types_canonical()) >= 1
    assert len(list_driver_capability_classes_canonical()) >= 1


def test_workforce_transport_catalog_resolvers() -> None:
    category = get_workforce_category_by_code("driver_local")
    assert category is not None
    assert category.code == "driver_local"

    mode = get_transport_mode_by_code("TRUCK")
    assert mode is not None
    assert mode.code == "truck"

    capability = get_driver_capability_class_by_code("ce")
    assert capability is not None
    assert capability.code == "CE"
