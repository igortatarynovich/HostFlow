"""Forms Field Catalog P1.3 — Basic Standard Library (Catalog client).

Registers 12 Basic components exclusively via public Registry + Descriptors APIs.
No special-case branches in Catalog core. No UI/renderers/extensions/tenants.
"""

from __future__ import annotations

from typing import Any

from backend.app.forms_platform.errors import FormsCatalogComponentDuplicateError
from backend.app.forms_platform.field_catalog.models import (
    SOURCE_PLATFORM,
    build_component_record,
)
from backend.app.forms_platform.field_catalog.registry import (
    FieldCatalogRegistry,
    platform_registry,
)

STDLIB_CONTRACT = "forms.field_catalog.stdlib.v1"
STDLIB_COMPONENT_VERSION = "1.0.0"

# Deterministic catalog order (find order still id ASC / version DESC from Registry).
STANDARD_COMPONENT_IDS: tuple[str, ...] = (
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

assert len(STANDARD_COMPONENT_IDS) == 12


def _cfg(
    *,
    key: str,
    value_type: str,
    required: bool = False,
    default: Any = None,
    label_key: str | None = None,
    enum_values: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "value_type": value_type,
        "required": required,
        "default": default,
        "label_key": label_key or f"forms.config.{key}",
        "enum_values": enum_values,
    }


def _base_config(*, include_placeholder: bool = True, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    fields = [
        _cfg(key="label", value_type="string"),
        _cfg(key="help_text", value_type="string"),
        _cfg(key="required", value_type="boolean", default=False),
    ]
    if include_placeholder:
        fields.insert(2, _cfg(key="placeholder", value_type="string"))
    if extra:
        fields.extend(extra)
    return fields


def _builder(label_key: str, *, category: str, icon: str, config_fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "label_key": label_key,
        "icon": icon,
        "category": category,
        "supports_preview": True,
        "config_fields": config_fields,
    }


def _public(
    input_kind: str,
    widget_token: str,
    *,
    label_key: str,
    placeholder_key: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "input_kind": input_kind,
        "widget_token": widget_token,
        "label_key": label_key,
        "placeholder_key": placeholder_key,
        "help_key": None,
        "attributes": dict(attributes or {}),
    }


def _validation(value_type: str, *, required_default: bool = False, rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "value_type": value_type,
        "required_default": required_default,
        "rules": list(rules or []),
    }


def _normalization(value_type: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {"value_type": value_type, "steps": steps}


def _component(
    component_id: str,
    *,
    category: str,
    tags: tuple[str, ...],
    builder: dict[str, Any],
    public: dict[str, Any],
    validation: dict[str, Any],
    normalization: dict[str, Any],
):
    return build_component_record(
        component_id=component_id,
        component_version=STDLIB_COMPONENT_VERSION,
        category=category,
        tags=tags,
        descriptors={
            "builder": builder,
            "public": public,
            "validation": validation,
            "normalization": normalization,
        },
        metadata={"stdlib_contract": STDLIB_CONTRACT},
        source=SOURCE_PLATFORM,
        require_complete_descriptors=True,
    )


def _definitions() -> list:
    """Canonical Basic pack — capabilities only (no layout/CSS/coordinates)."""
    text_len = [
        _cfg(key="min_length", value_type="number", default=0),
        _cfg(key="max_length", value_type="number", default=255),
    ]
    return [
        _component(
            "forms.field.text",
            category="input",
            tags=("text", "basic"),
            builder=_builder(
                "forms.field.text.label",
                category="input",
                icon="text",
                config_fields=_base_config(extra=text_len),
            ),
            public=_public(
                "text",
                "forms.widget.text",
                label_key="forms.field.text.label",
                placeholder_key="forms.field.text.placeholder",
            ),
            validation=_validation(
                "string",
                rules=[
                    {"code": "min_length", "params": {"min": 0}, "message_key": None},
                    {"code": "max_length", "params": {"max": 255}, "message_key": None},
                ],
            ),
            normalization=_normalization(
                "string",
                [{"op": "trim", "params": {}}, {"op": "identity", "params": {}}],
            ),
        ),
        _component(
            "forms.field.textarea",
            category="input",
            tags=("textarea", "basic"),
            builder=_builder(
                "forms.field.textarea.label",
                category="input",
                icon="textarea",
                config_fields=_base_config(
                    extra=[
                        _cfg(key="min_length", value_type="number", default=0),
                        _cfg(key="max_length", value_type="number", default=4000),
                    ]
                ),
            ),
            public=_public(
                "textarea",
                "forms.widget.textarea",
                label_key="forms.field.textarea.label",
                placeholder_key="forms.field.textarea.placeholder",
            ),
            validation=_validation(
                "string",
                rules=[{"code": "max_length", "params": {"max": 4000}, "message_key": None}],
            ),
            normalization=_normalization("string", [{"op": "trim", "params": {}}]),
        ),
        _component(
            "forms.field.number",
            category="input",
            tags=("number", "basic"),
            builder=_builder(
                "forms.field.number.label",
                category="input",
                icon="number",
                config_fields=_base_config(
                    extra=[
                        _cfg(key="min", value_type="number"),
                        _cfg(key="max", value_type="number"),
                    ]
                ),
            ),
            public=_public(
                "number",
                "forms.widget.number",
                label_key="forms.field.number.label",
                placeholder_key="forms.field.number.placeholder",
            ),
            validation=_validation("number", rules=[]),
            normalization=_normalization(
                "number",
                [{"op": "trim", "params": {}}, {"op": "to_number", "params": {}}],
            ),
        ),
        _component(
            "forms.field.email",
            category="input",
            tags=("email", "contact", "basic"),
            builder=_builder(
                "forms.field.email.label",
                category="input",
                icon="mail",
                config_fields=_base_config(extra=[_cfg(key="max_length", value_type="number", default=254)]),
            ),
            public=_public(
                "email",
                "forms.widget.email",
                label_key="forms.field.email.label",
                placeholder_key="forms.field.email.placeholder",
                attributes={"autocomplete": "email"},
            ),
            validation=_validation(
                "email",
                rules=[{"code": "email_format", "params": {}, "message_key": "forms.validation.email"}],
            ),
            normalization=_normalization(
                "email",
                [{"op": "trim", "params": {}}, {"op": "canonical_email", "params": {}}],
            ),
        ),
        _component(
            "forms.field.phone",
            category="input",
            tags=("phone", "contact", "basic"),
            builder=_builder(
                "forms.field.phone.label",
                category="input",
                icon="phone",
                config_fields=_base_config(),
            ),
            public=_public(
                "phone",
                "forms.widget.phone",
                label_key="forms.field.phone.label",
                placeholder_key="forms.field.phone.placeholder",
                attributes={"autocomplete": "tel"},
            ),
            validation=_validation(
                "phone",
                rules=[{"code": "phone_format", "params": {}, "message_key": "forms.validation.phone"}],
            ),
            normalization=_normalization(
                "phone",
                [{"op": "trim", "params": {}}, {"op": "canonical_phone", "params": {}}],
            ),
        ),
        _component(
            "forms.field.date",
            category="input",
            tags=("date", "basic"),
            builder=_builder(
                "forms.field.date.label",
                category="input",
                icon="calendar",
                config_fields=_base_config(include_placeholder=False),
            ),
            public=_public(
                "date",
                "forms.widget.date",
                label_key="forms.field.date.label",
            ),
            validation=_validation(
                "date",
                rules=[{"code": "date_format", "params": {}, "message_key": "forms.validation.date"}],
            ),
            normalization=_normalization(
                "date",
                [{"op": "trim", "params": {}}, {"op": "to_date", "params": {}}],
            ),
        ),
        _component(
            "forms.field.checkbox",
            category="choice",
            tags=("checkbox", "boolean", "basic"),
            builder=_builder(
                "forms.field.checkbox.label",
                category="choice",
                icon="checkbox",
                config_fields=_base_config(include_placeholder=False),
            ),
            public=_public(
                "checkbox",
                "forms.widget.checkbox",
                label_key="forms.field.checkbox.label",
            ),
            validation=_validation("boolean", rules=[]),
            normalization=_normalization("boolean", [{"op": "to_bool", "params": {}}]),
        ),
        _component(
            "forms.field.radio",
            category="choice",
            tags=("radio", "basic"),
            builder=_builder(
                "forms.field.radio.label",
                category="choice",
                icon="radio",
                config_fields=_base_config(
                    include_placeholder=False,
                    extra=[_cfg(key="options", value_type="string_list", required=True)],
                ),
            ),
            public=_public(
                "radio",
                "forms.widget.radio",
                label_key="forms.field.radio.label",
            ),
            validation=_validation("string", rules=[]),
            normalization=_normalization("string", [{"op": "trim", "params": {}}]),
        ),
        _component(
            "forms.field.select",
            category="choice",
            tags=("select", "basic"),
            builder=_builder(
                "forms.field.select.label",
                category="choice",
                icon="select",
                config_fields=_base_config(
                    extra=[_cfg(key="options", value_type="string_list", required=True)],
                ),
            ),
            public=_public(
                "select",
                "forms.widget.select",
                label_key="forms.field.select.label",
                placeholder_key="forms.field.select.placeholder",
            ),
            validation=_validation("string", rules=[]),
            normalization=_normalization("string", [{"op": "trim", "params": {}}]),
        ),
        _component(
            "forms.field.multiselect",
            category="choice",
            tags=("multiselect", "basic"),
            builder=_builder(
                "forms.field.multiselect.label",
                category="choice",
                icon="multiselect",
                config_fields=_base_config(
                    extra=[_cfg(key="options", value_type="string_list", required=True)],
                ),
            ),
            public=_public(
                "multiselect",
                "forms.widget.multiselect",
                label_key="forms.field.multiselect.label",
                placeholder_key="forms.field.multiselect.placeholder",
            ),
            validation=_validation("array", rules=[]),
            normalization=_normalization("array", [{"op": "identity", "params": {}}]),
        ),
        _component(
            "forms.field.file",
            category="media",
            tags=("file", "upload", "basic"),
            builder=_builder(
                "forms.field.file.label",
                category="media",
                icon="file",
                config_fields=_base_config(
                    include_placeholder=False,
                    extra=[_cfg(key="accept", value_type="string_list")],
                ),
            ),
            public=_public(
                "file",
                "forms.widget.file",
                label_key="forms.field.file.label",
            ),
            validation=_validation("file", rules=[]),
            normalization=_normalization("file", [{"op": "identity", "params": {}}]),
        ),
        _component(
            "forms.field.hidden",
            category="system",
            tags=("hidden", "basic"),
            builder=_builder(
                "forms.field.hidden.label",
                category="system",
                icon="hidden",
                config_fields=[
                    _cfg(key="default_value", value_type="string"),
                    _cfg(key="required", value_type="boolean", default=False),
                ],
            ),
            public=_public(
                "hidden",
                "forms.widget.hidden",
                label_key="forms.field.hidden.label",
            ),
            validation=_validation("string", rules=[]),
            normalization=_normalization("string", [{"op": "identity", "params": {}}]),
        ),
    ]


def iter_standard_library_records():
    """Yield ComponentRecord instances in canonical STANDARD_COMPONENT_IDS order."""
    by_id = {r.component_id: r for r in _definitions()}
    for cid in STANDARD_COMPONENT_IDS:
        yield by_id[cid]


def register_standard_library(
    registry: FieldCatalogRegistry | None = None,
    *,
    idempotent: bool = True,
) -> list:
    """Register Basic pack via public Registry API only.

    Idempotent by default: duplicate (id, version) is treated as a no-op bootstrap hit.
    """
    target = registry if registry is not None else platform_registry()
    out = []
    for record in iter_standard_library_records():
        try:
            target.register(record)
            out.append(record)
        except FormsCatalogComponentDuplicateError:
            if not idempotent:
                raise
            out.append(target.get(record.component_id, record.component_version))
    return out


def bootstrap_platform_standard_library(*, force: bool = False) -> list:
    """Ensure platform registry has the Basic pack (idempotent unless force rebuild)."""
    reg = platform_registry()
    if force:
        # Re-register only missing; duplicates still skipped via idempotent path.
        # Clearing the whole platform registry would wipe non-stdlib entries — avoid.
        pass
    return register_standard_library(reg, idempotent=True)


def standard_library_component_ids() -> tuple[str, ...]:
    return STANDARD_COMPONENT_IDS
