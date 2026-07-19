"""Forms Product Layer P2.1 — Builder Read Model contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.builder import (
    BUILDER_READ_MODEL_CONTRACT,
    BuilderReadModel,
    builder_read_model,
)
from backend.app.forms_platform.errors import FormsCatalogComponentNotFoundError
from backend.app.forms_platform.field_catalog import (
    FieldCatalogRegistry,
    register_extension_component,
    register_standard_library,
)


def _full_descriptors(*, label_key: str = "ext.label", category: str = "domain") -> dict:
    return {
        "builder": {
            "label_key": label_key,
            "icon": "ext",
            "category": category,
            "supports_preview": True,
            "config_fields": [
                {
                    "key": "label",
                    "value_type": "string",
                    "required": False,
                    "label_key": "ext.cfg.label",
                }
            ],
        },
        "public": {
            "input_kind": "text",
            "widget_token": "ext.widget",
            "label_key": label_key,
            "attributes": {},
        },
        "validation": {"value_type": "string", "required_default": False, "rules": []},
        "normalization": {
            "value_type": "string",
            "steps": [{"op": "identity", "params": {}}],
        },
    }


def _seed(registry: FieldCatalogRegistry) -> None:
    register_standard_library(registry)
    register_extension_component(
        registry,
        module_id="recruitment",
        component_id="recruitment.field.driver_license",
        component_version="1.0.0",
        descriptors=_full_descriptors(label_key="recruitment.driver_license", category="domain"),
        category="domain",
        tags=("license",),
    )


def test_forms_p2_1_read_model_contract_id():
    assert BUILDER_READ_MODEL_CONTRACT == "forms.builder.read_model.v1"
    assert builder_read_model(FieldCatalogRegistry()).contract == BUILDER_READ_MODEL_CONTRACT


def test_forms_p2_1_palette_loads_unified_catalog():
    registry = FieldCatalogRegistry()
    _seed(registry)
    rm = BuilderReadModel(registry)
    palette = rm.list_palette()
    ids = [p.component_id for p in palette]
    assert "forms.field.text" in ids
    assert "recruitment.field.driver_license" in ids
    assert ids == sorted(ids)
    # Working model has no origin / source discriminator
    for item in palette:
        assert "source" not in item.to_dict()
        assert not hasattr(item, "source")


def test_forms_p2_1_basic_and_extension_equal_behavior():
    registry = FieldCatalogRegistry()
    _seed(registry)
    rm = BuilderReadModel(registry)
    basic = rm.get_component("forms.field.text", "1.0.0")
    ext = rm.get_component("recruitment.field.driver_license", "1.0.0")
    # Same shape; no origin field; both expose config_fields
    assert set(basic.to_dict()) == set(ext.to_dict())
    assert "source" not in basic.to_dict()
    assert "source" not in ext.to_dict()
    assert basic.config_fields  # stdlib has config
    assert ext.config_fields[0].key == "label"


def test_forms_p2_1_search_and_category_filter():
    registry = FieldCatalogRegistry()
    _seed(registry)
    rm = BuilderReadModel(registry)
    hits = rm.search("driver")
    assert [h.component_id for h in hits] == ["recruitment.field.driver_license"]
    domain = rm.list_palette(category="domain")
    assert all(i.category == "domain" for i in domain)
    assert "recruitment.field.driver_license" in {i.component_id for i in domain}


def test_forms_p2_1_group_by_category():
    registry = FieldCatalogRegistry()
    _seed(registry)
    rm = BuilderReadModel(registry)
    groups = rm.group_by_category()
    keys = [g.category for g in groups]
    assert keys == sorted(keys)
    assert "domain" in keys
    domain = next(g for g in groups if g.category == "domain")
    assert any(i.component_id == "recruitment.field.driver_license" for i in domain.items)


def test_forms_p2_1_exact_descriptor_lookup():
    registry = FieldCatalogRegistry()
    _seed(registry)
    rm = BuilderReadModel(registry)
    view = rm.get_component("forms.field.email", "1.0.0")
    assert view.component_id == "forms.field.email"
    assert view.component_version == "1.0.0"
    assert view.label_key is not None
    payload = rm.get_builder_descriptor_payload("forms.field.email", "1.0.0")
    assert "config_fields" in payload
    assert payload["label_key"] == view.label_key
    with pytest.raises(FormsCatalogComponentNotFoundError):
        rm.get_component("forms.field.email", "9.9.9")


def test_forms_p2_1_no_catalog_mutation():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    before = [(r.component_id, r.component_version) for r in registry.find()]
    rm = BuilderReadModel(registry)
    rm.list_palette()
    rm.search("email")
    rm.group_by_category()
    rm.get_component("forms.field.email", "1.0.0")
    after = [(r.component_id, r.component_version) for r in registry.find()]
    assert before == after
    assert not hasattr(rm, "register")
    assert not hasattr(BuilderReadModel, "register")
