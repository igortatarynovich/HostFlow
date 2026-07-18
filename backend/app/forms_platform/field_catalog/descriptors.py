"""Forms Field Catalog P1.2 — declarative descriptor contract.

Contract id: forms.field_catalog.descriptors.v1

Descriptors describe capabilities; they do NOT execute code.
No callbacks, eval/exec, callables, or framework-specific payloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from backend.app.forms_platform.errors import (
    FormsCatalogDescriptorInvalidError,
    FormsCatalogDescriptorMissingError,
    FormsCatalogDescriptorUnsupportedError,
)
from backend.app.forms_platform.field_catalog.versioning import parse_component_version

DESCRIPTOR_CONTRACT = "forms.field_catalog.descriptors.v1"

DESCRIPTOR_KINDS = ("builder", "public", "validation", "normalization")
DESCRIPTOR_KIND_SET = frozenset(DESCRIPTOR_KINDS)

# Keys that imply executable / framework-bound logic (rejected anywhere in payload).
_FORBIDDEN_KEY_FRAGMENTS = frozenset(
    {
        "callback",
        "callbacks",
        "handler",
        "handlers",
        "eval",
        "exec",
        "onclick",
        "onchange",
        "on_click",
        "on_change",
        "jsx",
        "tsx",
        "react",
        "vue",
        "angular",
        "svelte",
        "lambda",
        "function",
        "__callable__",
        "script",
        "javascript",
        "component_class",
        "render_fn",
        "renderer_fn",
    }
)

_BUILDER_VALUE_TYPES = frozenset({"string", "number", "boolean", "enum", "string_list"})
_PUBLIC_INPUT_KINDS = frozenset(
    {
        "text",
        "textarea",
        "number",
        "email",
        "phone",
        "date",
        "checkbox",
        "radio",
        "select",
        "multiselect",
        "file",
        "hidden",
        "custom",
    }
)
# Compose Sprint 4/5 canonical value types (answers/validation).
_VALUE_TYPES = frozenset(
    {"string", "number", "boolean", "date", "email", "phone", "file", "object", "array", "integer"}
)
_VALIDATION_RULE_CODES = frozenset(
    {
        "required",
        "min_length",
        "max_length",
        "pattern",
        "min",
        "max",
        "one_of",
        "email_format",
        "phone_format",
        "date_format",
    }
)
_NORMALIZATION_OPS = frozenset(
    {
        "trim",
        "lower",
        "upper",
        "strip_spaces",
        "canonical_email",
        "canonical_phone",
        "to_bool",
        "to_number",
        "to_integer",
        "to_date",
        "identity",
    }
)


def _is_json_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _assert_json_safe(value: Any, *, path: str) -> None:
    if callable(value):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": path, "reason": "callable_forbidden"},
        )
    if _is_json_primitive(value):
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _assert_json_safe(item, path=f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise FormsCatalogDescriptorInvalidError(
                    details={"path": path, "reason": "non_string_key"},
                )
            key_l = key.strip().lower()
            if key_l in _FORBIDDEN_KEY_FRAGMENTS or any(
                frag in key_l for frag in ("callback", "handler", "onclick", "onchange")
            ):
                raise FormsCatalogDescriptorInvalidError(
                    details={"path": f"{path}.{key}", "reason": "forbidden_key", "key": key},
                )
            _assert_json_safe(item, path=f"{path}.{key}")
        return
    raise FormsCatalogDescriptorInvalidError(
        details={"path": path, "reason": "non_serializable_type", "type": type(value).__name__},
    )


def _require_mapping(raw: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": path, "reason": "expected_object"},
        )
    return dict(raw)


def _require_str(raw: Any, *, path: str, allow_empty: bool = False) -> str:
    if not isinstance(raw, str):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": path, "reason": "expected_string"},
        )
    text = raw.strip()
    if not allow_empty and not text:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": path, "reason": "empty_string"},
        )
    return text if allow_empty else text


def _require_bool(raw: Any, *, path: str) -> bool:
    if not isinstance(raw, bool):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": path, "reason": "expected_boolean"},
        )
    return raw


def _sorted_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic key order for serialization."""
    out: dict[str, Any] = {}
    for key in sorted(data.keys()):
        value = data[key]
        if isinstance(value, dict):
            out[key] = _sorted_dict(value)
        elif isinstance(value, list):
            out[key] = [
                _sorted_dict(v) if isinstance(v, dict) else v for v in value
            ]
        else:
            out[key] = value
    return out


def _validate_builder_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    label_key = _require_str(payload.get("label_key"), path="builder.label_key")
    icon = payload.get("icon")
    icon_out = None if icon is None else _require_str(icon, path="builder.icon")
    category = payload.get("category")
    category_out = None if category is None else _require_str(category, path="builder.category")
    supports_preview = _require_bool(
        payload.get("supports_preview", False), path="builder.supports_preview"
    )
    raw_fields = payload.get("config_fields", [])
    if not isinstance(raw_fields, list):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "builder.config_fields", "reason": "expected_array"},
        )
    config_fields: list[dict[str, Any]] = []
    for i, item in enumerate(raw_fields):
        field = _require_mapping(item, path=f"builder.config_fields[{i}]")
        key = _require_str(field.get("key"), path=f"builder.config_fields[{i}].key")
        value_type = _require_str(
            field.get("value_type"), path=f"builder.config_fields[{i}].value_type"
        )
        if value_type not in _BUILDER_VALUE_TYPES:
            raise FormsCatalogDescriptorInvalidError(
                details={
                    "path": f"builder.config_fields[{i}].value_type",
                    "reason": "unsupported_value_type",
                    "value_type": value_type,
                },
            )
        required = _require_bool(
            field.get("required", False), path=f"builder.config_fields[{i}].required"
        )
        enum_values = field.get("enum_values")
        enum_out: list[str] | None = None
        if enum_values is not None:
            if not isinstance(enum_values, list) or not all(isinstance(x, str) for x in enum_values):
                raise FormsCatalogDescriptorInvalidError(
                    details={
                        "path": f"builder.config_fields[{i}].enum_values",
                        "reason": "expected_string_array",
                    },
                )
            enum_out = [x.strip() for x in enum_values]
        default = field.get("default")
        if default is not None:
            _assert_json_safe(default, path=f"builder.config_fields[{i}].default")
        flabel = field.get("label_key")
        flabel_out = (
            None if flabel is None else _require_str(flabel, path=f"builder.config_fields[{i}].label_key")
        )
        unknown = set(field) - {"key", "value_type", "required", "enum_values", "default", "label_key"}
        if unknown:
            raise FormsCatalogDescriptorInvalidError(
                details={
                    "path": f"builder.config_fields[{i}]",
                    "reason": "unknown_fields",
                    "fields": sorted(unknown),
                },
            )
        config_fields.append(
            {
                "key": key,
                "value_type": value_type,
                "required": required,
                "enum_values": enum_out,
                "default": default,
                "label_key": flabel_out,
            }
        )
    unknown_top = set(payload) - {"label_key", "icon", "category", "config_fields", "supports_preview"}
    if unknown_top:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "builder", "reason": "unknown_fields", "fields": sorted(unknown_top)},
        )
    return {
        "label_key": label_key,
        "icon": icon_out,
        "category": category_out,
        "config_fields": config_fields,
        "supports_preview": supports_preview,
    }


def _validate_public_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    input_kind = _require_str(payload.get("input_kind"), path="public.input_kind")
    if input_kind not in _PUBLIC_INPUT_KINDS:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "public.input_kind", "reason": "unsupported_input_kind", "input_kind": input_kind},
        )
    widget_token = _require_str(payload.get("widget_token"), path="public.widget_token")
    label_key = payload.get("label_key")
    placeholder_key = payload.get("placeholder_key")
    help_key = payload.get("help_key")
    attributes = payload.get("attributes", {})
    attrs = _require_mapping(attributes, path="public.attributes")
    for k, v in attrs.items():
        if not isinstance(k, str) or not k.strip():
            raise FormsCatalogDescriptorInvalidError(
                details={"path": "public.attributes", "reason": "invalid_attribute_key"},
            )
        if not _is_json_primitive(v):
            raise FormsCatalogDescriptorInvalidError(
                details={"path": f"public.attributes.{k}", "reason": "attribute_must_be_primitive"},
            )
    unknown = set(payload) - {
        "input_kind",
        "widget_token",
        "label_key",
        "placeholder_key",
        "help_key",
        "attributes",
    }
    if unknown:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "public", "reason": "unknown_fields", "fields": sorted(unknown)},
        )
    return {
        "input_kind": input_kind,
        "widget_token": widget_token,
        "label_key": None if label_key is None else _require_str(label_key, path="public.label_key"),
        "placeholder_key": None
        if placeholder_key is None
        else _require_str(placeholder_key, path="public.placeholder_key"),
        "help_key": None if help_key is None else _require_str(help_key, path="public.help_key"),
        "attributes": {str(k): v for k, v in sorted(attrs.items())},
    }


def _validate_validation_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    value_type = _require_str(payload.get("value_type"), path="validation.value_type")
    if value_type not in _VALUE_TYPES:
        raise FormsCatalogDescriptorInvalidError(
            details={
                "path": "validation.value_type",
                "reason": "unsupported_value_type",
                "value_type": value_type,
            },
        )
    required_default = _require_bool(
        payload.get("required_default", False), path="validation.required_default"
    )
    raw_rules = payload.get("rules", [])
    if not isinstance(raw_rules, list):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "validation.rules", "reason": "expected_array"},
        )
    rules: list[dict[str, Any]] = []
    for i, item in enumerate(raw_rules):
        rule = _require_mapping(item, path=f"validation.rules[{i}]")
        code = _require_str(rule.get("code"), path=f"validation.rules[{i}].code")
        if code not in _VALIDATION_RULE_CODES:
            raise FormsCatalogDescriptorInvalidError(
                details={
                    "path": f"validation.rules[{i}].code",
                    "reason": "unsupported_rule_code",
                    "code": code,
                },
            )
        params = rule.get("params", {})
        params_m = _require_mapping(params, path=f"validation.rules[{i}].params")
        _assert_json_safe(params_m, path=f"validation.rules[{i}].params")
        message_key = rule.get("message_key")
        unknown = set(rule) - {"code", "params", "message_key"}
        if unknown:
            raise FormsCatalogDescriptorInvalidError(
                details={
                    "path": f"validation.rules[{i}]",
                    "reason": "unknown_fields",
                    "fields": sorted(unknown),
                },
            )
        rules.append(
            {
                "code": code,
                "params": _sorted_dict(params_m),
                "message_key": None
                if message_key is None
                else _require_str(message_key, path=f"validation.rules[{i}].message_key"),
            }
        )
    unknown_top = set(payload) - {"value_type", "required_default", "rules"}
    if unknown_top:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "validation", "reason": "unknown_fields", "fields": sorted(unknown_top)},
        )
    return {
        "value_type": value_type,
        "required_default": required_default,
        "rules": rules,
    }


def _validate_normalization_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    value_type = _require_str(payload.get("value_type"), path="normalization.value_type")
    if value_type not in _VALUE_TYPES:
        raise FormsCatalogDescriptorInvalidError(
            details={
                "path": "normalization.value_type",
                "reason": "unsupported_value_type",
                "value_type": value_type,
            },
        )
    raw_steps = payload.get("steps", [])
    if not isinstance(raw_steps, list):
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "normalization.steps", "reason": "expected_array"},
        )
    steps: list[dict[str, Any]] = []
    for i, item in enumerate(raw_steps):
        step = _require_mapping(item, path=f"normalization.steps[{i}]")
        op = _require_str(step.get("op"), path=f"normalization.steps[{i}].op")
        if op not in _NORMALIZATION_OPS:
            raise FormsCatalogDescriptorInvalidError(
                details={
                    "path": f"normalization.steps[{i}].op",
                    "reason": "unsupported_op",
                    "op": op,
                },
            )
        params = step.get("params", {})
        params_m = _require_mapping(params, path=f"normalization.steps[{i}].params")
        _assert_json_safe(params_m, path=f"normalization.steps[{i}].params")
        unknown = set(step) - {"op", "params"}
        if unknown:
            raise FormsCatalogDescriptorInvalidError(
                details={
                    "path": f"normalization.steps[{i}]",
                    "reason": "unknown_fields",
                    "fields": sorted(unknown),
                },
            )
        steps.append({"op": op, "params": _sorted_dict(params_m)})
    unknown_top = set(payload) - {"value_type", "steps"}
    if unknown_top:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "normalization", "reason": "unknown_fields", "fields": sorted(unknown_top)},
        )
    return {"value_type": value_type, "steps": steps}


_PAYLOAD_VALIDATORS = {
    "builder": _validate_builder_payload,
    "public": _validate_public_payload,
    "validation": _validate_validation_payload,
    "normalization": _validate_normalization_payload,
}


@dataclass(frozen=True, slots=True)
class ComponentDescriptor:
    kind: str
    component_id: str
    component_version: str
    payload: dict[str, Any]
    contract: str = DESCRIPTOR_CONTRACT

    def to_dict(self) -> dict[str, Any]:
        return _sorted_dict(
            {
                "contract": self.contract,
                "kind": self.kind,
                "component_id": self.component_id,
                "component_version": self.component_version,
                "payload": self.payload,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ComponentDescriptors:
    """Optional set of the four declarative surfaces (partial allowed until P1.3)."""

    builder: ComponentDescriptor | None = None
    public: ComponentDescriptor | None = None
    validation: ComponentDescriptor | None = None
    normalization: ComponentDescriptor | None = None

    def get(self, kind: str) -> ComponentDescriptor | None:
        normalized = str(kind or "").strip().lower()
        if normalized not in DESCRIPTOR_KIND_SET:
            raise FormsCatalogDescriptorUnsupportedError(details={"kind": kind})
        return getattr(self, normalized)

    def require(self, kind: str) -> ComponentDescriptor:
        found = self.get(kind)
        if found is None:
            raise FormsCatalogDescriptorMissingError(details={"kind": str(kind).strip().lower()})
        return found

    @property
    def present_kinds(self) -> tuple[str, ...]:
        return tuple(k for k in DESCRIPTOR_KINDS if getattr(self, k) is not None)

    @property
    def is_complete(self) -> bool:
        return len(self.present_kinds) == len(DESCRIPTOR_KINDS)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"contract": DESCRIPTOR_CONTRACT, "kinds": {}}
        for kind in DESCRIPTOR_KINDS:
            desc = getattr(self, kind)
            if desc is not None:
                out["kinds"][kind] = desc.to_dict()
        return _sorted_dict(out)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def parse_descriptor(
    kind: str,
    payload: Mapping[str, Any] | None,
    *,
    component_id: str,
    component_version: str,
) -> ComponentDescriptor:
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind not in DESCRIPTOR_KIND_SET:
        raise FormsCatalogDescriptorUnsupportedError(details={"kind": kind})
    cid = str(component_id or "").strip()
    ver = str(parse_component_version(component_version))
    if not cid:
        raise FormsCatalogDescriptorInvalidError(
            details={"path": "component_id", "reason": "empty_string"},
        )
    body = _require_mapping(payload, path=normalized_kind)
    _assert_json_safe(body, path=normalized_kind)
    validated = _PAYLOAD_VALIDATORS[normalized_kind](body)
    return ComponentDescriptor(
        kind=normalized_kind,
        component_id=cid,
        component_version=ver,
        payload=validated,
        contract=DESCRIPTOR_CONTRACT,
    )


def parse_descriptors(
    raw: Mapping[str, Any] | None,
    *,
    component_id: str,
    component_version: str,
    require_complete: bool = False,
) -> ComponentDescriptors:
    """Parse a mapping of kind → payload. Unknown kinds → unsupported error."""
    if raw is None:
        raw = {}
    data = _require_mapping(raw, path="descriptors")
    unknown = set(data) - DESCRIPTOR_KIND_SET
    if unknown:
        raise FormsCatalogDescriptorUnsupportedError(
            details={"kinds": sorted(unknown)},
        )
    parsed: dict[str, ComponentDescriptor | None] = {k: None for k in DESCRIPTOR_KINDS}
    for kind in DESCRIPTOR_KINDS:
        if kind not in data:
            continue
        parsed[kind] = parse_descriptor(
            kind,
            data[kind],
            component_id=component_id,
            component_version=component_version,
        )
    result = ComponentDescriptors(
        builder=parsed["builder"],
        public=parsed["public"],
        validation=parsed["validation"],
        normalization=parsed["normalization"],
    )
    if require_complete and not result.is_complete:
        missing = [k for k in DESCRIPTOR_KINDS if getattr(result, k) is None]
        raise FormsCatalogDescriptorMissingError(
            details={"kinds": missing, "reason": "incomplete_descriptors"},
        )
    return result
