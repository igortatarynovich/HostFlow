"""Forms Platform C2 — Public Contract Gate.

API ops / error codes / DTO identity fields. Change without version bump fails.
Does not rewrite historical publication identities.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.forms_platform.adapter import adapter_identity
from backend.app.forms_platform.constants import (
    ADAPTER_ID,
    OBJECT_KIND_PUBLICATION_VERSION,
    PUBLIC_CONTRACT_ID,
    PUBLIC_CONTRACT_VERSION,
)
from backend.app.forms_platform.errors import (
    FormsIdentityIncompatibleError,
    FormsIdentityIncompleteError,
    FormsIdentityUnreconstructableError,
    FormsPublicationVersionImmutableError,
    FormsSchemaHashMismatchError,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _REPO_ROOT / "docs/specs/architecture/forms-public-contract.md"

_SEALED_OPS = (
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
)
_SEALED_ERROR_CODES = frozenset(
    {
        "forms_publication_not_found",
        "forms_endpoint_inactive",
        "forms_publication_archived",
        "forms_stale_published_version",
        "forms_publication_key_required",
        "forms_builder_locked",
        "forms_publication_version_not_found",
        "forms_publication_version_pinned",
        "forms_submission_validation_failed",
        "forms_contract_identity_incomplete",
        "forms_contract_identity_incompatible",
        "forms_schema_hash_mismatch",
        "forms_publication_version_immutable",
        "forms_contract_identity_unreconstructable",
    }
)


def test_c2_public_contract_version_matches_id_lineage() -> None:
    assert PUBLIC_CONTRACT_ID == "forms.public_contract.v1"
    assert PUBLIC_CONTRACT_VERSION == "v1"
    assert PUBLIC_CONTRACT_ID.endswith(f".{PUBLIC_CONTRACT_VERSION}")


def test_c2_public_contract_ops_sealed_without_version_bump() -> None:
    assert tuple(adapter_identity()["ops"]) == _SEALED_OPS


def test_c2_public_contract_error_codes_documented() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    for code in _SEALED_ERROR_CODES:
        assert code in text, code
    assert FormsIdentityIncompleteError.code in _SEALED_ERROR_CODES
    assert FormsIdentityIncompatibleError.code in _SEALED_ERROR_CODES
    assert FormsSchemaHashMismatchError.code in _SEALED_ERROR_CODES
    assert FormsPublicationVersionImmutableError.code in _SEALED_ERROR_CODES
    assert FormsIdentityUnreconstructableError.code in _SEALED_ERROR_CODES


def test_c2_public_contract_documents_identity_and_object_kind() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    for token in (
        "contract_id",
        "manifest_version",
        "public_contract_version",
        "object_kind",
        "schema_hash",
        "adapter_version",
        "lifecycle_status",
        OBJECT_KIND_PUBLICATION_VERSION,
        ADAPTER_ID,
        "RFC 8785",
    ):
        assert token in text, token
    # lifecycle is Publication State, not identity
    assert "Not `lifecycle_status`" in text or "not identity" in text.lower()
