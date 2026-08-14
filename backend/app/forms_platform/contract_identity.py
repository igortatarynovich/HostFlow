"""Immutable Contract Identity for FormPublicationVersion (Forms C2).

Identity is frozen on a publication version. lifecycle_status is not identity.
Live Builder drafts are not required to carry this tuple.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.forms_platform.canonical import schema_hash_sha256
from backend.app.forms_platform.compatibility import assert_compatible_tuple
from backend.app.forms_platform.constants import (
    ADAPTER_ID,
    OBJECT_KIND_PUBLICATION_VERSION,
    PUBLIC_CONTRACT_ID,
    PUBLIC_CONTRACT_VERSION,
)
from backend.app.forms_platform.errors import (
    FormsIdentityIncompleteError,
    FormsIdentityUnreconstructableError,
    FormsPublicationVersionImmutableError,
    FormsSchemaHashMismatchError,
)
from backend.app.forms_platform.manifest import FORMS_MANIFEST_VERSION
from backend.app.forms_platform.schema import FIELD_SCHEMA_CONTRACT, extract_field_schema

IDENTITY_KEYS = (
    "contract_id",
    "manifest_version",
    "public_contract_version",
    "object_kind",
    "schema_hash",
    "adapter_version",
)


@dataclass(frozen=True)
class ContractIdentity:
    contract_id: str
    manifest_version: str
    public_contract_version: str
    object_kind: str
    schema_hash: str
    adapter_version: str

    def to_dict(self) -> dict[str, str]:
        return {key: getattr(self, key) for key in IDENTITY_KEYS}


def freeze_contract_identity(field_schema: dict[str, Any]) -> ContractIdentity:
    """Build identity for a new publication version (current sealed lineage)."""
    if not isinstance(field_schema, dict) or field_schema.get("schema_contract") != FIELD_SCHEMA_CONTRACT:
        raise FormsIdentityIncompleteError(
            details={"reason": "field_schema_required_to_freeze"}
        )
    identity = ContractIdentity(
        contract_id=PUBLIC_CONTRACT_ID,
        manifest_version=FORMS_MANIFEST_VERSION,
        public_contract_version=PUBLIC_CONTRACT_VERSION,
        object_kind=OBJECT_KIND_PUBLICATION_VERSION,
        schema_hash=schema_hash_sha256(field_schema),
        adapter_version=ADAPTER_ID,
    )
    assert_compatible_tuple(
        manifest_version=identity.manifest_version,
        public_contract_version=identity.public_contract_version,
        adapter_version=identity.adapter_version,
    )
    return identity


def parse_contract_identity(raw: Any) -> ContractIdentity:
    if not isinstance(raw, dict):
        raise FormsIdentityIncompleteError(details={"reason": "identity_not_object"})
    missing = [key for key in IDENTITY_KEYS if not str(raw.get(key) or "").strip()]
    extra = [key for key in raw.keys() if key not in IDENTITY_KEYS]
    if missing or extra:
        raise FormsIdentityIncompleteError(
            details={"missing": missing, "unknown_keys": extra}
        )
    identity = ContractIdentity(
        contract_id=str(raw["contract_id"]).strip(),
        manifest_version=str(raw["manifest_version"]).strip(),
        public_contract_version=str(raw["public_contract_version"]).strip(),
        object_kind=str(raw["object_kind"]).strip(),
        schema_hash=str(raw["schema_hash"]).strip().lower(),
        adapter_version=str(raw["adapter_version"]).strip(),
    )
    assert_compatible_tuple(
        manifest_version=identity.manifest_version,
        public_contract_version=identity.public_contract_version,
        adapter_version=identity.adapter_version,
    )
    return identity


def verify_identity_against_schema(
    identity: ContractIdentity,
    field_schema: dict[str, Any] | None,
) -> None:
    if not isinstance(field_schema, dict):
        raise FormsSchemaHashMismatchError(details={"reason": "field_schema_missing"})
    digest = schema_hash_sha256(field_schema)
    if digest != identity.schema_hash:
        raise FormsSchemaHashMismatchError(
            details={"expected": identity.schema_hash, "computed": digest}
        )


def reconstruct_contract_identity(snapshot: dict[str, Any]) -> ContractIdentity:
    """Provable reconstruct: frozen field_schema + sealed current lineage.

    Fail-closed when schema is absent. Never invent unknown/legacy identity.
    """
    field_schema = extract_field_schema(snapshot)
    if field_schema is None:
        raise FormsIdentityUnreconstructableError(
            details={"reason": "frozen_field_schema_missing"}
        )
    return freeze_contract_identity(field_schema)


def identity_from_snapshot(snapshot: dict[str, Any] | None) -> ContractIdentity:
    """Return frozen identity, or reconstruct if the block is absent and provable."""
    snap = snapshot if isinstance(snapshot, dict) else {}
    raw = snap.get("contract_identity")
    field_schema = extract_field_schema(snap)
    if raw is not None:
        identity = parse_contract_identity(raw)
        verify_identity_against_schema(identity, field_schema)
        return identity
    return reconstruct_contract_identity(snap)


def attach_identity_to_snapshot(
    snapshot: dict[str, Any],
    identity: ContractIdentity,
) -> dict[str, Any]:
    out = dict(snapshot)
    out["contract_identity"] = identity.to_dict()
    if "field_schema" not in out:
        raise FormsIdentityIncompleteError(details={"reason": "snapshot_missing_field_schema"})
    verify_identity_against_schema(identity, out.get("field_schema") if isinstance(out.get("field_schema"), dict) else None)
    return out


def backfill_snapshot_identity(snapshot: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Fill missing identity when reconstructable. Never rewrite existing identity/schema.

    Returns (snapshot, wrote). wrote=False if identity already present and valid.
    """
    snap = dict(snapshot or {})
    if snap.get("contract_identity") is not None:
        identity_from_snapshot(snap)
        return snap, False
    identity = reconstruct_contract_identity(snap)
    return attach_identity_to_snapshot(snap, identity), True


def forbid_identity_or_schema_mutation(
    *,
    stored: dict[str, Any],
    attempted: dict[str, Any],
) -> None:
    """Existing ledger row: field_schema + identity must be byte-equal."""
    stored_schema = stored.get("field_schema")
    attempted_schema = attempted.get("field_schema")
    stored_identity = stored.get("contract_identity")
    attempted_identity = attempted.get("contract_identity")
    if stored_schema != attempted_schema or stored_identity != attempted_identity:
        raise FormsPublicationVersionImmutableError(
            details={"reason": "schema_or_identity_changed"}
        )
