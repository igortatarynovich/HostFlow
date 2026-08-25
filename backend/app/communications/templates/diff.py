"""Pure TemplateVersion diff for PR-4 API (no I/O)."""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.communications.templates.renderer.types import TemplateVersionPayload


def diff_version_payloads(
    left: TemplateVersionPayload,
    right: TemplateVersionPayload,
) -> dict[str, Any]:
    """Structural diff between two pure version payloads."""

    def _vars(p: TemplateVersionPayload) -> dict[str, dict[str, Any]]:
        return {
            v.name: {
                "var_type": v.var_type,
                "required": v.required,
                "default_value": v.default_value,
                "enum_values": list(v.enum_values),
            }
            for v in p.variables
        }

    fields = ("status", "locale", "subject", "body_text", "body_html")
    changed_fields: dict[str, Mapping[str, Any]] = {}
    for name in fields:
        lv = getattr(left, name)
        rv = getattr(right, name)
        if lv != rv:
            changed_fields[name] = {"from": lv, "to": rv}

    left_ch = sorted(left.channels)
    right_ch = sorted(right.channels)
    if left_ch != right_ch:
        changed_fields["channels"] = {"from": left_ch, "to": right_ch}

    left_vars = _vars(left)
    right_vars = _vars(right)
    var_keys = sorted(set(left_vars) | set(right_vars))
    var_changes: dict[str, Any] = {}
    for key in var_keys:
        if key not in left_vars:
            var_changes[key] = {"op": "added", "to": right_vars[key]}
        elif key not in right_vars:
            var_changes[key] = {"op": "removed", "from": left_vars[key]}
        elif left_vars[key] != right_vars[key]:
            var_changes[key] = {
                "op": "changed",
                "from": left_vars[key],
                "to": right_vars[key],
            }
    if var_changes:
        changed_fields["variables"] = var_changes

    return {
        "from_version_id": left.template_version_id,
        "to_version_id": right.template_version_id,
        "changed": changed_fields,
        "identical": not changed_fields,
    }


__all__ = ["diff_version_payloads"]
