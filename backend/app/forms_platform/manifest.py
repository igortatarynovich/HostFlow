"""Forms Sprint 1 — Settings Manifest keys (code mirror of docs outline).

Docs SoT: docs/specs/architecture/capability-settings-manifest.md #forms
Values are draft defaults for Sprint 1; admin shell wiring is later.
"""

from __future__ import annotations

from typing import Any

FORMS_MANIFEST_VERSION = "1.0.0"
FORMS_CAPABILITY_ID = "forms"

# key → entry (Sprint 1 concrete keys)
FORMS_MANIFEST_KEYS: dict[str, dict[str, Any]] = {
    "forms.general.default_language": {
        "section": "general",
        "type": "string",
        "required": True,
        "default": "pl",
        "scope": "tenant",
        "label_key": "settings.forms.general.default_language",
    },
    "forms.general.public_url_base": {
        "section": "general",
        "type": "url",
        "required": False,
        "default": None,
        "scope": "tenant",
        "label_key": "settings.forms.general.public_url_base",
    },
    "forms.defaults.tier": {
        "section": "defaults",
        "type": "enum",
        "required": True,
        "default": "basic",
        "allowed_values": ["basic", "advanced"],
        "scope": "tenant",
        "label_key": "settings.forms.defaults.tier",
    },
    "forms.defaults.consent_required": {
        "section": "defaults",
        "type": "boolean",
        "required": True,
        "default": True,
        "scope": "tenant",
        "label_key": "settings.forms.defaults.consent_required",
    },
    "forms.policies.consent_version_pin": {
        "section": "policies",
        "type": "boolean",
        "required": True,
        "default": True,
        "scope": "tenant",
        "label_key": "settings.forms.policies.consent_version_pin",
    },
    "forms.feature_flags.builder_enabled": {
        "section": "feature_flags",
        "type": "boolean",
        "required": True,
        "default": True,
        "scope": "tenant",
        "label_key": "settings.forms.feature_flags.builder_enabled",
        "description_key": "settings.forms.feature_flags.builder_enabled.help",
    },
    "forms.feature_flags.themes_advanced": {
        "section": "feature_flags",
        "type": "boolean",
        "required": True,
        "default": False,
        "scope": "tenant",
        "label_key": "settings.forms.feature_flags.themes_advanced",
    },
    "forms.feature_flags.multi_language": {
        "section": "feature_flags",
        "type": "boolean",
        "required": True,
        "default": False,
        "scope": "tenant",
        "label_key": "settings.forms.feature_flags.multi_language",
    },
    "forms.limits.max_active_publications": {
        "section": "policies",
        "type": "number",
        "required": True,
        "default": 50,
        "scope": "tenant",
        "label_key": "settings.forms.limits.max_active_publications",
    },
    "forms.adapter.contract_id": {
        "section": "integrations",
        "type": "string",
        "required": True,
        "default": "forms.public_contract.v1",
        "scope": "module",
        "label_key": "settings.forms.adapter.contract_id",
    },
    "forms.adapter.id": {
        "section": "integrations",
        "type": "string",
        "required": True,
        "default": "forms.endpoint_adapter_v1",
        "scope": "module",
        "label_key": "settings.forms.adapter.id",
    },
    "forms.license.advanced_forms": {
        "section": "license_gates",
        "type": "boolean",
        "required": True,
        "default": False,
        "scope": "tenant",
        "label_key": "settings.forms.license.advanced_forms",
    },
}


def forms_manifest_document() -> dict[str, Any]:
    """Return Manifest document shape for Sprint 1 (not persisted settings DB)."""
    return {
        "capability_id": FORMS_CAPABILITY_ID,
        "version": FORMS_MANIFEST_VERSION,
        "keys": dict(FORMS_MANIFEST_KEYS),
    }


def builder_is_locked_by_manifest() -> bool:
    entry = FORMS_MANIFEST_KEYS["forms.feature_flags.builder_enabled"]
    return entry["default"] is False
