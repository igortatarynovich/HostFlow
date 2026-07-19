"""Forms Product Layer P1.4 — Extension API contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.errors import (
    FormsCatalogBasicOverrideError,
    FormsCatalogComponentDuplicateError,
    FormsCatalogDescriptorInvalidError,
)
from backend.app.forms_platform.field_catalog import (
    DESCRIPTOR_KINDS,
    EXTENSION_CONTRACT,
    SOURCE_PLATFORM,
    FieldCatalogRegistry,
    get_component_source,
    list_catalog_for_builder,
    register_extension_component,
    register_module_components,
    register_standard_library,
)


def _full_descriptors(*, input_kind: str = "text", value_type: str = "string") -> dict:
    return {
        "builder": {
            "label_key": "ext.label",
            "icon": "ext",
            "category": "domain",
            "supports_preview": True,
            "config_fields": [
                {"key": "label", "value_type": "string", "required": False, "label_key": "ext.cfg.label"}
            ],
        },
        "public": {
            "input_kind": input_kind,
            "widget_token": "ext.widget",
            "label_key": "ext.label",
            "attributes": {},
        },
        "validation": {"value_type": value_type, "required_default": False, "rules": []},
        "normalization": {
            "value_type": value_type,
            "steps": [{"op": "identity", "params": {}}],
        },
    }


def test_forms_p1_4_extension_contract_id():
    assert EXTENSION_CONTRACT == "forms.field_catalog.extension.v1"


def test_forms_p1_4_register_extension_success_and_source():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    rec = register_extension_component(
        registry,
        module_id="recruitment",
        component_id="recruitment.field.driver_license",
        component_version="1.0.0",
        descriptors=_full_descriptors(),
        category="domain",
        tags=("license",),
    )
    assert rec.source == "module:recruitment"
    assert get_component_source(rec) == "module:recruitment"
    descs = registry.get_descriptors("recruitment.field.driver_license", "1.0.0")
    assert descs.is_complete is True
    assert set(descs.present_kinds) == set(DESCRIPTOR_KINDS)


def test_forms_p1_4_basic_override_forbidden():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    with pytest.raises(FormsCatalogBasicOverrideError) as exc:
        register_extension_component(
            registry,
            module_id="recruitment",
            component_id="forms.field.email",
            component_version="9.0.0",
            descriptors=_full_descriptors(input_kind="email", value_type="email"),
        )
    assert exc.value.code == "forms_catalog_basic_override_forbidden"
    # Original Basic untouched
    assert registry.get("forms.field.email", "1.0.0").source == SOURCE_PLATFORM


def test_forms_p1_4_version_conflict_no_silent_replace():
    registry = FieldCatalogRegistry()
    register_extension_component(
        registry,
        module_id="hr",
        component_id="hr.field.pesel",
        component_version="1.0.0",
        descriptors=_full_descriptors(),
    )
    with pytest.raises(FormsCatalogComponentDuplicateError):
        register_extension_component(
            registry,
            module_id="hr",
            component_id="hr.field.pesel",
            component_version="1.0.0",
            descriptors=_full_descriptors(),
        )


def test_forms_p1_4_invalid_descriptors_rejected():
    registry = FieldCatalogRegistry()
    with pytest.raises(FormsCatalogDescriptorInvalidError):
        register_extension_component(
            registry,
            module_id="fleet",
            component_id="fleet.field.vehicle",
            component_version="1.0.0",
            descriptors={"builder": {"label_key": "x", "callback": "bad"}},
        )


def test_forms_p1_4_module_error_isolation():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    result = register_module_components(
        registry,
        module_id="recruitment",
        components=[
            {
                "component_id": "forms.field.email",  # basic override — fail
                "component_version": "2.0.0",
                "descriptors": _full_descriptors(input_kind="email", value_type="email"),
            },
            {
                "component_id": "recruitment.field.ce_category",
                "component_version": "1.0.0",
                "descriptors": _full_descriptors(),
            },
            {
                "component_id": "recruitment.field.bad",
                "component_version": "1.0.0",
                "descriptors": {"public": {"input_kind": "text"}},  # incomplete/invalid
            },
        ],
    )
    assert result.ok is False
    assert len(result.registered) == 1
    assert result.registered[0].component_id == "recruitment.field.ce_category"
    assert len(result.failures) == 2
    codes = {f.error_code for f in result.failures}
    assert "forms_catalog_basic_override_forbidden" in codes
    # Catalog still has Basic + one extension
    assert registry.get("forms.field.text", "1.0.0")
    assert registry.get("recruitment.field.ce_category", "1.0.0")


def test_forms_p1_4_load_order_deterministic():
    def _load(order: list[str]) -> list[str]:
        registry = FieldCatalogRegistry()
        register_standard_library(registry)
        packs = {
            "recruitment": [
                {
                    "component_id": "recruitment.field.b",
                    "component_version": "1.0.0",
                    "descriptors": _full_descriptors(),
                },
                {
                    "component_id": "recruitment.field.a",
                    "component_version": "1.0.0",
                    "descriptors": _full_descriptors(),
                },
            ],
            "fleet": [
                {
                    "component_id": "fleet.field.z",
                    "component_version": "1.0.0",
                    "descriptors": _full_descriptors(),
                }
            ],
        }
        for mid in order:
            register_module_components(registry, module_id=mid, components=packs[mid])
        return [r.component_id for r in registry.find()]

    assert _load(["recruitment", "fleet"]) == _load(["fleet", "recruitment"])


def test_forms_p1_4_builder_unified_catalog_no_origin_split():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    register_extension_component(
        registry,
        module_id="service",
        component_id="service.field.service_type",
        component_version="1.0.0",
        descriptors=_full_descriptors(),
    )
    catalog = list_catalog_for_builder(registry)
    ids = [c["component_id"] for c in catalog]
    assert ids == sorted(ids)
    assert "forms.field.text" in ids
    assert "service.field.service_type" in ids
    # Builder composition keys do not require a type/origin discriminator beyond id/version
    for row in catalog:
        assert "component_id" in row and "component_version" in row
