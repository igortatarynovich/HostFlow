"""Forms Product Layer P1.1 — Field Catalog registry contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.errors import (
    FormsCatalogComponentDuplicateError,
    FormsCatalogComponentNotFoundError,
    FormsCatalogVersionIncompatibleError,
    FormsCatalogVersionInvalidError,
)
from backend.app.forms_platform.field_catalog import (
    CATALOG_REGISTRY_CONTRACT,
    ComponentRecord,
    FieldCatalogRegistry,
    compare_versions,
    is_compatible,
    parse_component_version,
)


def _reg(*specs: tuple) -> FieldCatalogRegistry:
    registry = FieldCatalogRegistry()
    for spec in specs:
        if len(spec) == 2:
            cid, ver = spec
            registry.register(ComponentRecord(component_id=cid, component_version=ver))
        else:
            cid, ver, category, tags = spec
            registry.register(
                ComponentRecord(
                    component_id=cid,
                    component_version=ver,
                    category=category,
                    tags=tags,
                )
            )
    return registry


def test_forms_p1_1_registry_contract_id():
    assert CATALOG_REGISTRY_CONTRACT == "forms.field_catalog.registry.v1"


def test_forms_p1_1_register_and_get_exact_version():
    registry = _reg(("forms.field.text", "1.0.0"))
    got = registry.get("forms.field.text", "1.0.0")
    assert got.component_id == "forms.field.text"
    assert got.component_version == "1.0.0"
    assert got.to_dict()["component_id"] == "forms.field.text"


def test_forms_p1_1_duplicate_version_rejected():
    registry = _reg(("forms.field.text", "1.0.0"))
    with pytest.raises(FormsCatalogComponentDuplicateError) as exc:
        registry.register(ComponentRecord(component_id="forms.field.text", component_version="1.0.0"))
    assert exc.value.code == "forms_catalog_component_duplicate"
    # Different version of same id is allowed
    registry.register(ComponentRecord(component_id="forms.field.text", component_version="1.0.1"))


def test_forms_p1_1_get_missing_raises_not_found():
    registry = _reg(("forms.field.text", "1.0.0"))
    with pytest.raises(FormsCatalogComponentNotFoundError) as exc:
        registry.get("forms.field.text", "9.9.9")
    assert exc.value.code == "forms_catalog_component_not_found"
    with pytest.raises(FormsCatalogComponentNotFoundError):
        registry.get("forms.field.missing", "1.0.0")


def test_forms_p1_1_invalid_semver_rejected():
    with pytest.raises(FormsCatalogVersionInvalidError) as exc:
        ComponentRecord(component_id="forms.field.text", component_version="1.0")
    assert exc.value.code == "forms_catalog_version_invalid"
    with pytest.raises(FormsCatalogVersionInvalidError):
        parse_component_version("v1.0.0")


def test_forms_p1_1_find_deterministic_order():
    registry = _reg(
        ("forms.field.phone", "1.0.0", "input", ("phone",)),
        ("forms.field.email", "2.0.0", "input", ("email",)),
        ("forms.field.email", "1.1.0", "input", ("email",)),
        ("forms.field.email", "1.0.0", "input", ("email",)),
        ("forms.field.phone", "1.1.0", "input", ("phone",)),
    )
    found = registry.find()
    ids_versions = [(r.component_id, r.component_version) for r in found]
    assert ids_versions == [
        ("forms.field.email", "2.0.0"),
        ("forms.field.email", "1.1.0"),
        ("forms.field.email", "1.0.0"),
        ("forms.field.phone", "1.1.0"),
        ("forms.field.phone", "1.0.0"),
    ]


def test_forms_p1_1_find_by_query_and_category():
    registry = _reg(
        ("forms.field.email", "1.0.0", "input", ("email", "contact")),
        ("forms.field.file", "1.0.0", "media", ("upload",)),
    )
    assert [r.component_id for r in registry.find(query="email")] == ["forms.field.email"]
    assert [r.component_id for r in registry.find(category="media")] == ["forms.field.file"]
    assert registry.find(query="nope") == []


def test_forms_p1_1_compatibility_rules():
    assert is_compatible("1.2.0", "1.2.0") is True
    assert is_compatible("1.2.0", "1.2.1") is True
    assert is_compatible("1.2.0", "1.3.0") is True
    assert is_compatible("1.2.0", "1.1.9") is False
    assert is_compatible("1.2.0", "2.0.0") is False
    assert is_compatible("2.0.0", "2.1.0") is True
    assert compare_versions("1.0.0", "1.0.1") == -1
    assert compare_versions("1.2.0", "1.2.0") == 0


def test_forms_p1_1_resolve_latest_compatible_no_major_jump():
    registry = _reg(
        ("forms.field.email", "1.0.0"),
        ("forms.field.email", "1.2.0"),
        ("forms.field.email", "1.2.3"),
        ("forms.field.email", "2.0.0"),
    )
    got = registry.resolve_compatible("forms.field.email", "1.2.0")
    assert got.component_version == "1.2.3"
    # Exact older within major
    assert registry.resolve_compatible("forms.field.email", "1.0.0").component_version == "1.2.3"
    # Major 2 line
    assert registry.resolve_compatible("forms.field.email", "2.0.0").component_version == "2.0.0"


def test_forms_p1_1_resolve_incompatible_raises():
    registry = _reg(
        ("forms.field.email", "1.0.0"),
        ("forms.field.email", "2.0.0"),
    )
    with pytest.raises(FormsCatalogVersionIncompatibleError) as exc:
        registry.resolve_compatible("forms.field.email", "1.5.0")
    assert exc.value.code == "forms_catalog_version_incompatible"
    with pytest.raises(FormsCatalogVersionIncompatibleError):
        registry.resolve_compatible("forms.field.email", "3.0.0")


def test_forms_p1_1_assert_compatible():
    registry = _reg(
        ("forms.field.email", "1.2.0"),
        ("forms.field.email", "1.3.0"),
    )
    registry.assert_compatible("forms.field.email", "1.2.0", "1.3.0")
    with pytest.raises(FormsCatalogVersionIncompatibleError):
        registry.assert_compatible("forms.field.email", "1.3.0", "1.2.0")


def test_forms_p1_1_platform_registry_is_tenant_independent_singleton():
    from backend.app.forms_platform.field_catalog import (
        platform_registry,
        reset_platform_registry,
    )

    reset_platform_registry()
    a = platform_registry()
    b = platform_registry()
    assert a is b
    a.register(ComponentRecord(component_id="forms.field.text", component_version="1.0.0"))
    assert b.get("forms.field.text", "1.0.0").component_version == "1.0.0"
    reset_platform_registry()
    with pytest.raises(FormsCatalogComponentNotFoundError):
        platform_registry().get("forms.field.text", "1.0.0")


def test_forms_p1_1_list_versions_sorted_ascending():
    registry = _reg(
        ("forms.field.text", "1.2.0"),
        ("forms.field.text", "1.0.0"),
        ("forms.field.text", "1.10.0"),
    )
    assert registry.list_versions("forms.field.text") == ["1.0.0", "1.2.0", "1.10.0"]
