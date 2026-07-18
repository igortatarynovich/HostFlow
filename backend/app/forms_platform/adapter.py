"""Forms Sprint 1 — P-01 Form / HostFlow Form Endpoint Adapter.

Public contract: forms.public_contract.v1
Ops: publish → endpoint → submission → result (handoff)

Wraps C4 publication bridge. Does not own routing, Outcome, or KPI.
Builder remains locked (see manifest.builder_is_locked_by_manifest).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.constants import FORMS_PLATFORM_CONTRACT_VERSION
from backend.app.forms_platform.manifest import (
    FORMS_MANIFEST_KEYS,
    builder_is_locked_by_manifest,
    forms_manifest_document,
)
from backend.app.forms_platform.publication_bridge import resolve_forms_platform_publication

FORMS_PUBLIC_CONTRACT_ID = "forms.public_contract.v1"
FORMS_ADAPTER_ID = "forms.endpoint_adapter_v1"
ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM = "hostflow_public_form"


@dataclass(frozen=True)
class FormsEndpointIdentity:
    endpoint_type: str
    form_id: str
    publication_id: str
    public_slug: Optional[str]
    intake_source_profile_id: Optional[str]
    public_intake_path: str
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def publish(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str | None = None,
    form_id: str | None = None,
) -> dict[str, Any] | None:
    """Op: publish — resolve HostFlow Form publication view."""
    return await resolve_forms_platform_publication(
        db,
        tenant_id=str(tenant_id),
        public_slug=public_slug,
        form_id=form_id,
    )


def endpoint_from_publication(publication: dict[str, Any]) -> FormsEndpointIdentity:
    """Op: endpoint — HostFlow Public Form is-a Endpoint specialization."""
    pub_id = str(publication["publication_id"])
    return FormsEndpointIdentity(
        endpoint_type=ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM,
        form_id=pub_id,
        publication_id=pub_id,
        public_slug=publication.get("public_slug"),
        intake_source_profile_id=publication.get("intake_source_profile_id"),
        public_intake_path=str(publication.get("public_intake_path") or "/api/v1/public/intake"),
        is_active=bool(publication.get("is_active")),
    )


async def resolve_endpoint(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str | None = None,
    form_id: str | None = None,
) -> FormsEndpointIdentity | None:
    publication = await publish(
        db, tenant_id=tenant_id, public_slug=public_slug, form_id=form_id
    )
    if publication is None:
        return None
    return endpoint_from_publication(publication)


def submission_entry(publication: dict[str, Any]) -> dict[str, Any]:
    """Op: submission — entry contract for Shared Intake (not a second submit engine)."""
    return {
        "forms_role": "submission_surface",
        "public_intake_path": publication.get("public_intake_path") or "/api/v1/public/intake",
        "storage_backend": publication.get("storage_backend"),
        "submission_handler": publication.get("submission_handler"),
        "publication_id": publication.get("publication_id"),
        "contract_version": publication.get("contract_version") or FORMS_PLATFORM_CONTRACT_VERSION,
        "builder_locked": builder_is_locked_by_manifest(),
    }


def result_handoff(*, submission_id: str | None = None) -> dict[str, Any]:
    """Op: result — handoff only; Result/Outcome/KPI owned outside Forms."""
    return {
        "forms_role": "submission_surface",
        "result_owner": "destination_module_via_decision",
        "submission_id": submission_id,
        "acquisition_compose": [
            "acquisition.submission_routing.resolve_universal_submission_routing",
            "acquisition.result_attribution.record_result_attribution_from_routing",
            "acquisition.outcome_service.apply_attribution_to_outcome",
            "acquisition.kpi_aggregates.aggregate_flight_kpi",
        ],
        "forbidden": [
            "forms_owned_result_sot",
            "forms_owned_outcome",
            "forms_owned_kpi",
            "forms_owned_routing_engine",
            "forms_builder",
        ],
        "adapter_id": FORMS_ADAPTER_ID,
        "contract_id": FORMS_PUBLIC_CONTRACT_ID,
    }


def adapter_identity() -> dict[str, Any]:
    return {
        "adapter_id": FORMS_ADAPTER_ID,
        "contract_id": FORMS_PUBLIC_CONTRACT_ID,
        "contract_version": FORMS_PLATFORM_CONTRACT_VERSION,
        "ops": ["publish", "endpoint", "submission", "result"],
        "builder_locked": builder_is_locked_by_manifest(),
        "manifest_builder_flag_default": FORMS_MANIFEST_KEYS[
            "forms.feature_flags.builder_enabled"
        ]["default"],
        "manifest": forms_manifest_document(),
    }
