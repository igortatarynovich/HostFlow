"""Forms Product Layer P1.2 — declarative descriptor contract tests."""

from __future__ import annotations

import json

import pytest

from backend.app.forms_platform.errors import (
    FormsCatalogDescriptorInvalidError,
    FormsCatalogDescriptorMissingError,
    FormsCatalogDescriptorUnsupportedError,
)
from backend.app.forms_platform.field_catalog import (
    DESCRIPTOR_CONTRACT,
    DESCRIPTOR_KINDS,
    ComponentRecord,
    FieldCatalogRegistry,
    build_component_record,
    parse_descriptors,
)


def _full_descriptor_payloads() -> dict:
    return {
        "builder": {
            "label_key": "forms.field.email.label",
            "icon": "mail",
            "category": "input",
            "supports_preview": True,
            "config_fields": [
                {
                    "key": "placeholder",
                    "value_type": "string",
                    "required": False,
                    "label_key": "forms.field.email.placeholder",
                }
            ],
        },
        "public": {
            "input_kind": "email",
            "widget_token": "forms.widget.email",
            "label_key": "forms.field.email.label",
            "placeholder_key": "forms.field.email.placeholder",
            "attributes": {"autocomplete": "email", "maxlength": 254},
        },
        "validation": {
            "value_type": "email",
            "required_default": True,
            "rules": [
                {"code": "email_format", "params": {}, "message_key": "forms.validation.email"},
            ],
        },
        "normalization": {
            "value_type": "email",
            "steps": [
                {"op": "trim", "params": {}},
                {"op": "canonical_email", "params": {}},
            ],
        },
    }


def test_forms_p1_2_descriptor_contract_id():
    assert DESCRIPTOR_CONTRACT == "forms.field_catalog.descriptors.v1"
    assert DESCRIPTOR_KINDS == ("builder", "public", "validation", "normalization")


def test_forms_p1_2_register_and_get_full_descriptors():
    registry = FieldCatalogRegistry()
    record = build_component_record(
        component_id="forms.field.email",
        component_version="1.0.0",
        descriptors=_full_descriptor_payloads(),
        require_complete_descriptors=True,
    )
    registry.register(record)
    descs = registry.get_descriptors("forms.field.email", "1.0.0")
    assert descs.is_complete is True
    assert set(descs.present_kinds) == set(DESCRIPTOR_KINDS)
    builder = registry.get_descriptor("forms.field.email", "1.0.0", "builder")
    assert builder.contract == DESCRIPTOR_CONTRACT
    assert builder.component_id == "forms.field.email"
    assert builder.component_version == "1.0.0"
    assert builder.payload["label_key"] == "forms.field.email.label"


def test_forms_p1_2_incomplete_descriptors_allowed_missing_raises():
    registry = FieldCatalogRegistry()
    record = build_component_record(
        component_id="forms.field.text",
        component_version="1.0.0",
        descriptors={"builder": _full_descriptor_payloads()["builder"]},
    )
    registry.register(record)
    assert registry.get_descriptors("forms.field.text", "1.0.0").is_complete is False
    registry.get_descriptor("forms.field.text", "1.0.0", "builder")
    with pytest.raises(FormsCatalogDescriptorMissingError) as exc:
        registry.get_descriptor("forms.field.text", "1.0.0", "public")
    assert exc.value.code == "forms_catalog_descriptor_missing"


def test_forms_p1_2_require_complete_on_build():
    with pytest.raises(FormsCatalogDescriptorMissingError):
        build_component_record(
            component_id="forms.field.text",
            component_version="1.0.0",
            descriptors={"builder": _full_descriptor_payloads()["builder"]},
            require_complete_descriptors=True,
        )


def test_forms_p1_2_unsupported_kind():
    with pytest.raises(FormsCatalogDescriptorUnsupportedError) as exc:
        parse_descriptors(
            {"builder": _full_descriptor_payloads()["builder"], "magic": {}},
            component_id="forms.field.text",
            component_version="1.0.0",
        )
    assert exc.value.code == "forms_catalog_descriptor_unsupported"
    registry = FieldCatalogRegistry()
    registry.register(
        build_component_record(
            component_id="forms.field.text",
            component_version="1.0.0",
            descriptors={"builder": _full_descriptor_payloads()["builder"]},
        )
    )
    with pytest.raises(FormsCatalogDescriptorUnsupportedError):
        registry.get_descriptor("forms.field.text", "1.0.0", "magic")


def test_forms_p1_2_invalid_payload_and_forbidden_executable_keys():
    with pytest.raises(FormsCatalogDescriptorInvalidError) as exc:
        parse_descriptors(
            {"builder": {"label_key": "x", "callback": "do_it"}},
            component_id="forms.field.text",
            component_version="1.0.0",
        )
    assert exc.value.code == "forms_catalog_descriptor_invalid"

    with pytest.raises(FormsCatalogDescriptorInvalidError):
        parse_descriptors(
            {"public": {"input_kind": "email"}},  # missing widget_token
            component_id="forms.field.email",
            component_version="1.0.0",
        )

    with pytest.raises(FormsCatalogDescriptorInvalidError):
        parse_descriptors(
            {
                "validation": {
                    "value_type": "email",
                    "rules": [{"code": "not_a_real_rule", "params": {}}],
                }
            },
            component_id="forms.field.email",
            component_version="1.0.0",
        )


def test_forms_p1_2_rejects_callables():
    with pytest.raises(FormsCatalogDescriptorInvalidError) as exc:
        parse_descriptors(
            {
                "normalization": {
                    "value_type": "string",
                    "steps": [{"op": "trim", "params": {"fn": lambda x: x}}],  # type: ignore[dict-item]
                }
            },
            component_id="forms.field.text",
            component_version="1.0.0",
        )
    assert "callable" in str(exc.value.details.get("reason", "")).lower() or exc.value.details.get(
        "reason"
    ) == "callable_forbidden"


def test_forms_p1_2_serializable_and_deterministic():
    descs = parse_descriptors(
        _full_descriptor_payloads(),
        component_id="forms.field.email",
        component_version="1.0.0",
    )
    a = descs.to_json()
    b = descs.to_json()
    assert a == b
    loaded = json.loads(a)
    assert loaded["contract"] == DESCRIPTOR_CONTRACT
    assert set(loaded["kinds"]) == set(DESCRIPTOR_KINDS)
    # deterministic key order in JSON (sort_keys)
    assert a.index('"builder"') < a.index('"normalization"')
    assert '"contract"' in a


def test_forms_p1_2_compatible_resolve_returns_descriptors():
    registry = FieldCatalogRegistry()
    registry.register(
        build_component_record(
            component_id="forms.field.email",
            component_version="1.0.0",
            descriptors={"builder": _full_descriptor_payloads()["builder"]},
        )
    )
    registry.register(
        build_component_record(
            component_id="forms.field.email",
            component_version="1.2.0",
            descriptors=_full_descriptor_payloads(),
            require_complete_descriptors=True,
        )
    )
    descs = registry.get_descriptors_compatible("forms.field.email", "1.0.0")
    assert descs.is_complete is True
    assert descs.builder is not None
    assert descs.builder.component_version == "1.2.0"


def test_forms_p1_2_p11_records_without_descriptors_still_work():
    registry = FieldCatalogRegistry()
    registry.register(ComponentRecord(component_id="forms.field.hidden", component_version="1.0.0"))
    descs = registry.get_descriptors("forms.field.hidden", "1.0.0")
    assert descs.present_kinds == ()
    dumped = registry.get("forms.field.hidden", "1.0.0").to_dict()
    assert dumped["descriptors"]["contract"] == DESCRIPTOR_CONTRACT
