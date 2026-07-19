"""Forms Product Layer P2.2 — Composition Model contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.builder import (
    BUILDER_COMPOSITION_CONTRACT,
    CompositionInstance,
    FormDraftComposition,
    build_composition,
    build_instance,
    parse_composition,
)
from backend.app.forms_platform.errors import (
    FormsBuilderCompositionConfigError,
    FormsBuilderCompositionInvalidError,
)
from backend.app.forms_platform.field_catalog import (
    FieldCatalogRegistry,
    register_extension_component,
    register_standard_library,
)


def _ext_descriptors() -> dict:
    return {
        "builder": {
            "label_key": "ext.label",
            "icon": "ext",
            "category": "domain",
            "supports_preview": True,
            "config_fields": [
                {"key": "label", "value_type": "string", "required": True, "label_key": "ext.cfg.label"},
                {"key": "help", "value_type": "string", "required": False, "label_key": "ext.cfg.help"},
            ],
        },
        "public": {
            "input_kind": "text",
            "widget_token": "ext.widget",
            "label_key": "ext.label",
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
        descriptors=_ext_descriptors(),
        category="domain",
    )


def test_forms_p2_2_composition_contract_id():
    assert BUILDER_COMPOSITION_CONTRACT == "forms.builder.composition.v1"


def test_forms_p2_2_minimal_instance_and_draft_identity():
    registry = FieldCatalogRegistry()
    _seed(registry)
    a = build_instance(
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "Name"},
        registry=registry,
    )
    b = build_instance(
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "Title"},
        registry=registry,
    )
    # Same component may appear multiple times
    assert a.component_id == b.component_id
    assert a.instance_id != b.instance_id
    draft = build_composition(instances=[a, b], registry=registry)
    assert draft.contract == BUILDER_COMPOSITION_CONTRACT
    assert draft.draft_id
    assert draft.instance_order() == (a.instance_id, b.instance_id)
    payload = draft.to_dict()
    assert "source" not in payload
    assert "source" not in payload["instances"][0]
    assert "validation" not in payload["instances"][0]
    assert "normalization" not in payload["instances"][0]


def test_forms_p2_2_version_pin_required_and_exact():
    registry = FieldCatalogRegistry()
    _seed(registry)
    inst = build_instance(
        component_id="forms.field.email",
        component_version="1.0.0",
        registry=registry,
    )
    assert inst.pinned_version == "1.0.0"
    with pytest.raises(FormsBuilderCompositionInvalidError) as exc:
        build_instance(
            component_id="forms.field.email",
            component_version="9.9.9",
            registry=registry,
        )
    assert exc.value.details.get("reason") == "unknown_component_or_version"


def test_forms_p2_2_unknown_component_diagnosable():
    registry = FieldCatalogRegistry()
    _seed(registry)
    orphan = CompositionInstance(
        instance_id="i1",
        component_id="does.not.exist",
        component_version="1.0.0",
        config={},
    )
    draft = FormDraftComposition(draft_id="d1", instances=(orphan,))
    issues = draft.diagnose(registry)
    assert len(issues) == 1
    assert issues[0].code == "unknown_component_or_version"
    assert draft.is_valid(registry) is False
    with pytest.raises(FormsBuilderCompositionInvalidError) as exc:
        draft.assert_valid(registry)
    assert "issues" in exc.value.details


def test_forms_p2_2_config_limited_to_builder_descriptor():
    registry = FieldCatalogRegistry()
    _seed(registry)
    with pytest.raises(FormsBuilderCompositionConfigError):
        build_instance(
            component_id="recruitment.field.driver_license",
            component_version="1.0.0",
            config={"label": "DL", "unknown_key": "x"},
            registry=registry,
        )
    with pytest.raises(FormsBuilderCompositionConfigError):
        build_instance(
            component_id="recruitment.field.driver_license",
            component_version="1.0.0",
            config={},  # required label missing
            registry=registry,
        )
    ok = build_instance(
        component_id="recruitment.field.driver_license",
        component_version="1.0.0",
        config={"label": "DL"},
        registry=registry,
    )
    assert ok.config["label"] == "DL"


def test_forms_p2_2_parse_rejects_layout_and_origin_leakage():
    with pytest.raises(FormsBuilderCompositionInvalidError) as exc:
        parse_composition(
            {
                "contract": BUILDER_COMPOSITION_CONTRACT,
                "draft_id": "d1",
                "source": "platform",
                "instances": [],
            }
        )
    assert exc.value.details.get("reason") == "forbidden_root_fields"
    with pytest.raises(FormsBuilderCompositionInvalidError):
        parse_composition(
            {
                "contract": BUILDER_COMPOSITION_CONTRACT,
                "draft_id": "d1",
                "instances": [
                    {
                        "instance_id": "i1",
                        "component_id": "forms.field.text",
                        "component_version": "1.0.0",
                        "config": {},
                        "x": 10,
                        "y": 20,
                    }
                ],
            }
        )


def test_forms_p2_2_parse_roundtrip_order_stable():
    registry = FieldCatalogRegistry()
    _seed(registry)
    a = build_instance(
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "A"},
        instance_id="aaa",
        registry=registry,
    )
    b = build_instance(
        component_id="forms.field.email",
        component_version="1.0.0",
        config={"label": "B"},
        instance_id="bbb",
        registry=registry,
    )
    draft = build_composition(draft_id="draft-1", instances=[a, b], registry=registry)
    again = parse_composition(draft.to_dict())
    assert again.draft_id == "draft-1"
    assert again.instance_order() == ("aaa", "bbb")
    # parse does not auto-validate against catalog; diagnose still works
    assert again.is_valid(registry) is True


def test_forms_p2_2_no_persistence_or_publish_api():
    assert not hasattr(FormDraftComposition, "save")
    assert not hasattr(FormDraftComposition, "publish")
    assert not hasattr(FormDraftComposition, "persist")
    assert not hasattr(FormDraftComposition, "load")
