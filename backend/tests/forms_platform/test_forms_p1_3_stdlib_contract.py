"""Forms Product Layer P1.3 — Standard Library contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.errors import FormsCatalogComponentDuplicateError
from backend.app.forms_platform.field_catalog import (
    DESCRIPTOR_KINDS,
    STANDARD_COMPONENT_IDS,
    STDLIB_COMPONENT_VERSION,
    STDLIB_CONTRACT,
    FieldCatalogRegistry,
    bootstrap_platform_standard_library,
    register_standard_library,
    reset_platform_registry,
    standard_library_component_ids,
)


def test_forms_p1_3_stdlib_contract_and_ids():
    assert STDLIB_CONTRACT == "forms.field_catalog.stdlib.v1"
    assert STDLIB_COMPONENT_VERSION == "1.0.0"
    assert len(STANDARD_COMPONENT_IDS) == 12
    assert standard_library_component_ids() == STANDARD_COMPONENT_IDS
    assert STANDARD_COMPONENT_IDS == (
        "forms.field.text",
        "forms.field.textarea",
        "forms.field.number",
        "forms.field.email",
        "forms.field.phone",
        "forms.field.date",
        "forms.field.checkbox",
        "forms.field.radio",
        "forms.field.select",
        "forms.field.multiselect",
        "forms.field.file",
        "forms.field.hidden",
    )


def test_forms_p1_3_register_all_twelve_with_complete_descriptors():
    registry = FieldCatalogRegistry()
    records = register_standard_library(registry)
    assert len(records) == 12
    for cid in STANDARD_COMPONENT_IDS:
        rec = registry.get(cid, STDLIB_COMPONENT_VERSION)
        assert rec.component_version == STDLIB_COMPONENT_VERSION
        descs = registry.get_descriptors(cid, STDLIB_COMPONENT_VERSION)
        assert descs.is_complete is True
        assert set(descs.present_kinds) == set(DESCRIPTOR_KINDS)
        for kind in DESCRIPTOR_KINDS:
            d = registry.get_descriptor(cid, STDLIB_COMPONENT_VERSION, kind)
            assert d.component_id == cid
            assert d.component_version == STDLIB_COMPONENT_VERSION


def test_forms_p1_3_idempotent_bootstrap():
    registry = FieldCatalogRegistry()
    first = register_standard_library(registry, idempotent=True)
    second = register_standard_library(registry, idempotent=True)
    assert len(first) == 12
    assert len(second) == 12
    assert len(registry.find()) == 12
    with pytest.raises(FormsCatalogComponentDuplicateError):
        register_standard_library(registry, idempotent=False)


def test_forms_p1_3_platform_bootstrap_idempotent():
    reset_platform_registry()
    a = bootstrap_platform_standard_library()
    b = bootstrap_platform_standard_library()
    assert len(a) == 12
    assert len(b) == 12
    reset_platform_registry()


def test_forms_p1_3_find_order_deterministic():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    found = registry.find(query="basic")
    ids = [r.component_id for r in found]
    # Registry order: component_id ASC, version DESC — all same version.
    assert ids == sorted(ids)
    assert set(ids) == set(STANDARD_COMPONENT_IDS)


def test_forms_p1_3_compatibility_resolution():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    got = registry.resolve_compatible("forms.field.email", "1.0.0")
    assert got.component_version == "1.0.0"
    descs = registry.get_descriptors_compatible("forms.field.email", "1.0.0")
    assert descs.is_complete is True


def test_forms_p1_3_no_layout_or_style_in_config():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    forbidden = {"css", "color", "layout", "x", "y", "width", "height", "style"}
    for cid in STANDARD_COMPONENT_IDS:
        builder = registry.get_descriptor(cid, STDLIB_COMPONENT_VERSION, "builder")
        keys = {f["key"] for f in builder.payload["config_fields"]}
        assert keys.isdisjoint(forbidden), cid


def test_forms_p1_3_builder_unlocked_by_manifest():
    from backend.app.forms_platform.manifest import (
        FORMS_MANIFEST_KEYS,
        builder_is_locked_by_manifest,
    )

    assert FORMS_MANIFEST_KEYS["forms.feature_flags.builder_enabled"]["default"] is True
    assert builder_is_locked_by_manifest() is False
