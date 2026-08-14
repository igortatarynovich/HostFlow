"""Forms Platform C2 — Manifest Gate.

Unknown keys, removed required keys, structure, incompatible version.
"""

from __future__ import annotations

from backend.app.forms_platform.manifest import (
    FORMS_MANIFEST_KEYS,
    FORMS_MANIFEST_VERSION,
    forms_manifest_document,
)

_SEALED_MANIFEST_KEYS = frozenset(
    {
        "forms.general.default_language",
        "forms.general.public_url_base",
        "forms.defaults.tier",
        "forms.defaults.consent_required",
        "forms.policies.consent_version_pin",
        "forms.feature_flags.builder_enabled",
        "forms.feature_flags.themes_advanced",
        "forms.feature_flags.multi_language",
        "forms.limits.max_active_publications",
        "forms.adapter.contract_id",
        "forms.adapter.id",
        "forms.license.advanced_forms",
    }
)
_SEALED_MANIFEST_VERSION = "1.0.0"
_REQUIRED_ENTRY_FIELDS = frozenset({"section", "type", "required", "default", "scope"})


def test_c2_manifest_key_set_unchanged_without_version_bump() -> None:
    assert FORMS_MANIFEST_VERSION == _SEALED_MANIFEST_VERSION
    assert frozenset(FORMS_MANIFEST_KEYS) == _SEALED_MANIFEST_KEYS


def test_c2_manifest_no_unknown_or_missing_required_entry_fields() -> None:
    allowed_top = frozenset(_REQUIRED_ENTRY_FIELDS | {"allowed_values", "label_key", "description_key"})
    for key, entry in FORMS_MANIFEST_KEYS.items():
        assert isinstance(entry, dict), key
        missing = _REQUIRED_ENTRY_FIELDS - frozenset(entry)
        assert not missing, (key, missing)
        unknown = frozenset(entry) - allowed_top
        assert not unknown, (key, unknown)


def test_c2_manifest_document_version_matches_sealed() -> None:
    doc = forms_manifest_document()
    assert doc["version"] == _SEALED_MANIFEST_VERSION
    assert frozenset(doc["keys"]) == _SEALED_MANIFEST_KEYS
