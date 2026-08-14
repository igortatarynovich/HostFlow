"""Forms Platform C4 — Runtime Model.

Read-only serving representation. Downstream (render / C5 validation /
execution) uses this model, not FormPublicationVersion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

RUNTIME_MODEL_CONTRACT = "forms.runtime.model.v1"


@dataclass(frozen=True, slots=True)
class RuntimeModel:
    """Runtime Representation. Not a publication. Not a draft. Not an engine."""

    contract: str
    form_id: str
    published_version: int
    contract_identity: Mapping[str, str]
    field_schema: Mapping[str, Any]
    lifecycle_status: str
    title: str
    public_slug: str | None
    purpose: str
    consent_pin: Mapping[str, Any]
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "form_id": self.form_id,
            "published_version": self.published_version,
            "contract_identity": dict(self.contract_identity),
            "field_schema": dict(self.field_schema),
            "lifecycle_status": self.lifecycle_status,
            "title": self.title,
            "public_slug": self.public_slug,
            "purpose": self.purpose,
            "consent_pin": dict(self.consent_pin),
            "is_active": self.is_active,
        }
