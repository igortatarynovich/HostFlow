"""Forms Platform C4 — read-only Form Runtime.

Adapter resolve DTO (frozen FormPublicationVersion) → Runtime Model.

Runtime does not look up publications, import Builder, publish, or submit.
"""

from __future__ import annotations

import copy
from types import MappingProxyType
from typing import Any, Mapping

from backend.app.forms_platform.contract_identity import (
    parse_contract_identity,
    verify_identity_against_schema,
)
from backend.app.forms_platform.errors import (
    FormsIdentityIncompleteError,
    FormsRuntimeNotPublicationError,
)
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT, RuntimeModel
from backend.app.forms_platform.schema import extract_field_schema

# Authoring / Builder keys. Presence means this is not a frozen publication.
_DRAFT_MARKERS = frozenset(
    {
        "builder_state",
        "definition_id",
        "draft_id",
        "composition",
    }
)


def serve(publication: Mapping[str, Any]) -> RuntimeModel:
    """Build a read-only Runtime Model from an Adapter resolve DTO.

    The only legal producer of `publication` is Adapter `resolve`.
    Runtime does not search, persist, publish, or accept submissions.
    """
    if not isinstance(publication, Mapping):
        raise FormsRuntimeNotPublicationError(details={"reason": "publication_not_object"})

    leaked = [key for key in _DRAFT_MARKERS if key in publication]
    if leaked:
        raise FormsRuntimeNotPublicationError(
            details={"reason": "authoring_payload", "keys": leaked}
        )

    form_id = str(publication.get("publication_id") or publication.get("form_id") or "").strip()
    if not form_id:
        raise FormsRuntimeNotPublicationError(details={"reason": "form_id_required"})

    try:
        published_version = int(publication.get("published_version") or 0)
    except (TypeError, ValueError) as exc:
        raise FormsRuntimeNotPublicationError(
            details={"reason": "published_version_invalid"}
        ) from exc
    if published_version < 1:
        raise FormsRuntimeNotPublicationError(
            details={"reason": "unpublished", "published_version": published_version}
        )

    raw_identity = publication.get("contract_identity")
    if raw_identity is None:
        raise FormsIdentityIncompleteError(details={"reason": "runtime_requires_frozen_identity"})
    identity = parse_contract_identity(raw_identity)

    field_schema = extract_field_schema(dict(publication))
    if field_schema is None:
        raise FormsIdentityIncompleteError(details={"reason": "runtime_requires_frozen_schema"})
    verify_identity_against_schema(identity, field_schema)

    schema_copy = copy.deepcopy(field_schema)
    identity_copy = dict(identity.to_dict())
    consent = publication.get("consent_pin")
    consent_copy = copy.deepcopy(consent) if isinstance(consent, dict) else {}

    slug_raw = publication.get("public_slug")
    public_slug = str(slug_raw).strip() or None if slug_raw is not None else None

    return RuntimeModel(
        contract=RUNTIME_MODEL_CONTRACT,
        form_id=form_id,
        published_version=published_version,
        contract_identity=MappingProxyType(identity_copy),
        field_schema=MappingProxyType(schema_copy),
        lifecycle_status=str(publication.get("lifecycle_status") or "").strip() or "active",
        title=str(publication.get("title") or ""),
        public_slug=public_slug,
        purpose=str(publication.get("purpose") or ""),
        consent_pin=MappingProxyType(consent_copy),
        is_active=bool(publication.get("is_active", True)),
    )
