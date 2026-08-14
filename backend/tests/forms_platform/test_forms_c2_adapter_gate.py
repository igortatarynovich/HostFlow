"""Forms Platform C2 — Adapter Gate.

Adapter implements claimed ops. Must not accept keys absent from Manifest/Contract.
Serving adapter must declare compatibility with frozen adapter_version.
"""

from __future__ import annotations

import pytest

from backend.app.forms_platform.adapter import adapter_identity
from backend.app.forms_platform.compatibility import COMPATIBLE_TUPLES, is_compatible_tuple
from backend.app.forms_platform.constants import ADAPTER_ID, PUBLIC_CONTRACT_ID
from backend.app.forms_platform.contract_identity import (
    IDENTITY_KEYS,
    freeze_contract_identity,
    parse_contract_identity,
)
from backend.app.forms_platform.errors import FormsIdentityIncompleteError, FormsIdentityIncompatibleError
from backend.app.forms_platform.manifest import FORMS_MANIFEST_KEYS, forms_manifest_document
from backend.app.forms_platform.schema import build_field_schema_v1

_SEALED_OPS = frozenset(
    {
        "resolve",
        "publish",
        "activate",
        "deactivate",
        "endpoint",
        "submission",
        "result",
        "list_versions",
        "get_version",
        "validate_submission",
        "normalize_answers",
        "persist_submission",
        "get_submission",
        "list_submissions",
    }
)


def test_c2_adapter_ops_match_public_contract() -> None:
    ident = adapter_identity()
    assert ident["adapter_id"] == ADAPTER_ID
    assert ident["contract_id"] == PUBLIC_CONTRACT_ID
    assert frozenset(ident["ops"]) == _SEALED_OPS


def test_c2_adapter_manifest_defaults_match_ids() -> None:
    doc = forms_manifest_document()
    assert doc["keys"]["forms.adapter.id"]["default"] == ADAPTER_ID
    assert doc["keys"]["forms.adapter.contract_id"]["default"] == PUBLIC_CONTRACT_ID
    assert "forms.adapter.id" in FORMS_MANIFEST_KEYS


def test_c2_adapter_version_on_identity_is_declared_compatible() -> None:
    schema = build_field_schema_v1(fields=[{"id": "n.first", "type": "text", "required": True}])
    identity = freeze_contract_identity(schema)
    assert identity.adapter_version == ADAPTER_ID
    assert is_compatible_tuple(
        manifest_version=identity.manifest_version,
        public_contract_version=identity.public_contract_version,
        adapter_version=identity.adapter_version,
    )
    assert any(row.adapter_version == ADAPTER_ID for row in COMPATIBLE_TUPLES)


def test_c2_adapter_rejects_identity_keys_outside_contract() -> None:
    schema = build_field_schema_v1(fields=[])
    identity = freeze_contract_identity(schema).to_dict()
    identity["extra_field"] = "nope"
    with pytest.raises(FormsIdentityIncompleteError) as exc:
        parse_contract_identity(identity)
    assert "extra_field" in str(exc.value.details)


def test_c2_adapter_rejects_undeclared_adapter_version() -> None:
    schema = build_field_schema_v1(fields=[])
    identity = freeze_contract_identity(schema).to_dict()
    identity["adapter_version"] = "forms.endpoint_adapter_v9"
    with pytest.raises(FormsIdentityIncompatibleError):
        parse_contract_identity(identity)
    assert set(IDENTITY_KEYS) == set(freeze_contract_identity(schema).to_dict())
