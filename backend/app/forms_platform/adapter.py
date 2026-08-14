"""Forms Sprint 1–2 — P-01 Form / HostFlow Form Endpoint Adapter.

Public contract: forms.public_contract.v1
Ops: resolve · publish · activate · deactivate · endpoint · submission · result

Sprint 2: immutable published snapshot, activation, typed errors, version pin.
Does not own routing, Outcome, or KPI. P3–P5 remain locked (Phase C).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.constants import (
    ADAPTER_ID,
    FORMS_PLATFORM_CONTRACT_VERSION,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_ARCHIVED,
    PUBLIC_CONTRACT_ID,
)
from backend.app.forms_platform.errors import (
    FormsArchivedError,
    FormsInactiveError,
    FormsMissingKeyError,
    FormsNotFoundError,
    FormsStaleVersionError,
)
from backend.app.forms_platform.manifest import (
    FORMS_MANIFEST_KEYS,
    builder_is_locked_by_manifest,
    forms_manifest_document,
)
from backend.app.forms_platform.schema import (
    FIELD_SCHEMA_CONTRACT,
    build_field_schema_v1,
    field_schema_from_presentation_runtime,
)
from backend.app.forms_platform.publication_bridge import (
    resolve_forms_platform_publication,
)
from backend.app.forms_platform.publication_versions import (
    append_publication_version,
    find_version_by_idempotency_key,
    get_publication_version,
    list_publication_versions,
    register_submission_pin,
    version_row_to_dict,
)
from backend.app.forms_platform.submission_envelope import (
    get_submission_envelope,
    list_submission_envelopes,
    persist_submission_envelope,
    set_envelope_processing_status,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.mixins import now_utc

FORMS_PUBLIC_CONTRACT_ID = PUBLIC_CONTRACT_ID
FORMS_ADAPTER_ID = ADAPTER_ID
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
    published_version: int
    lifecycle_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_keys(*, form_id: str | None, public_slug: str | None) -> None:
    if not form_id and not public_slug:
        raise FormsMissingKeyError()


async def resolve_publication(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str | None = None,
    form_id: str | None = None,
    require_active: bool = False,
) -> dict[str, Any]:
    """Idempotent read of publication view (Sprint 2 resolve)."""
    _require_keys(form_id=form_id, public_slug=public_slug)
    publication = await resolve_forms_platform_publication(
        db,
        tenant_id=str(tenant_id),
        public_slug=public_slug,
        form_id=form_id,
    )
    if publication is None:
        raise FormsNotFoundError(details={"tenant_id": tenant_id, "form_id": form_id, "public_slug": public_slug})
    if require_active and not publication.get("is_active"):
        raise FormsInactiveError(
            details={"publication_id": publication.get("publication_id"), "is_active": False}
        )
    if require_active and publication.get("lifecycle_status") == LIFECYCLE_ARCHIVED:
        raise FormsArchivedError(details={"publication_id": publication.get("publication_id")})
    return publication


# Sprint 1 compatibility alias (resolve-only). Prefer resolve_publication.
async def publish(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str | None = None,
    form_id: str | None = None,
) -> dict[str, Any] | None:
    """Deprecated alias for resolve_publication (Sprint 1). Returns None when missing."""
    try:
        return await resolve_publication(
            db, tenant_id=tenant_id, public_slug=public_slug, form_id=form_id, require_active=False
        )
    except FormsNotFoundError:
        return None
    except FormsMissingKeyError:
        return None


def _build_snapshot(
    lead_form: TenantLeadForm,
    *,
    published_version: int,
    consent_pin: dict[str, Any],
    field_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "published_version": published_version,
        "title": str(lead_form.title or ""),
        "public_slug": str(lead_form.public_slug or "") or None,
        "purpose": str(lead_form.purpose or "inquiry"),
        "target_entity_profile_code": lead_form.target_entity_profile_code,
        "submission_policy": dict(lead_form.submission_policy or {}),
        "lifecycle_status": LIFECYCLE_ACTIVE,
        "consent_pin": consent_pin,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
    }
    if field_schema and field_schema.get("schema_contract") == FIELD_SCHEMA_CONTRACT:
        snap["field_schema"] = field_schema
    return snap


async def commit_publish(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    terms_version: str | None = None,
    privacy_version: str | None = None,
    activate: bool = True,
    idempotency_key: str | None = None,
    field_schema: dict[str, Any] | None = None,
    fields: list[dict[str, Any]] | None = None,
    presentation_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Op: publish — append ledger row, update current pointer, bump version.

    Sprint 4: freeze field_schema into the immutable snapshot when provided
    (or built from fields / presentation_runtime).
    """
    if not form_id:
        raise FormsMissingKeyError("form_id is required to publish")

    lead_form = await db.get(TenantLeadForm, str(form_id))
    if lead_form is None or str(lead_form.tenant_id) != str(tenant_id):
        raise FormsNotFoundError(details={"form_id": form_id})
    if str(lead_form.lifecycle_status) == LIFECYCLE_ARCHIVED:
        raise FormsArchivedError(details={"form_id": form_id})

    # Idempotent publish: same key returns the original version (no new ledger row).
    if idempotency_key:
        existing = await find_version_by_idempotency_key(
            db,
            tenant_id=tenant_id,
            form_id=form_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            publication = await resolve_publication(
                db, tenant_id=tenant_id, form_id=str(form_id)
            )
            return {
                **publication,
                "idempotent_replay": True,
                "replayed_version": int(existing.version),
                "replayed_version_id": str(existing.id),
            }

    pin_required = bool(
        FORMS_MANIFEST_KEYS["forms.policies.consent_version_pin"]["default"]
    )
    consent_pin = {
        "pin_required": pin_required,
        "terms_version": (terms_version or "terms_v1").strip() or "terms_v1",
        "privacy_version": (privacy_version or "privacy_v1").strip() or "privacy_v1",
    }

    frozen_schema = field_schema
    if frozen_schema is None and presentation_runtime is not None:
        frozen_schema = field_schema_from_presentation_runtime(presentation_runtime)
    if frozen_schema is None and fields is not None:
        frozen_schema = build_field_schema_v1(
            fields=fields,
            entity_profile_code=lead_form.target_entity_profile_code,
        )

    next_version = int(lead_form.published_version or 0) + 1
    snapshot = _build_snapshot(
        lead_form,
        published_version=next_version,
        consent_pin=consent_pin,
        field_schema=frozen_schema,
    )
    published_at = now_utc()
    await append_publication_version(
        db,
        tenant_id=tenant_id,
        form_id=str(form_id),
        version=next_version,
        snapshot=snapshot,
        consent_pin=consent_pin,
        idempotency_key=idempotency_key,
        published_at=published_at,
    )
    # Current pointer (denormalized cache of latest ledger row — not full history).
    lead_form.published_version = next_version
    lead_form.published_snapshot_v1 = snapshot
    lead_form.published_at = published_at
    if activate:
        lead_form.is_active = True
        lead_form.lifecycle_status = LIFECYCLE_ACTIVE
    await db.flush()

    return await resolve_publication(db, tenant_id=tenant_id, form_id=str(form_id))


async def get_version_for_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> dict[str, Any]:
    """Read-only historical publication version (audit)."""
    row = await get_publication_version(
        db, tenant_id=tenant_id, form_id=form_id, version=version
    )
    return version_row_to_dict(row)


async def list_versions_for_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> list[dict[str, Any]]:
    return await list_publication_versions(db, tenant_id=tenant_id, form_id=form_id)


async def activate_endpoint(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any]:
    lead_form = await db.get(TenantLeadForm, str(form_id))
    if lead_form is None or str(lead_form.tenant_id) != str(tenant_id):
        raise FormsNotFoundError(details={"form_id": form_id})
    if str(lead_form.lifecycle_status) == LIFECYCLE_ARCHIVED:
        raise FormsArchivedError(details={"form_id": form_id})
    lead_form.is_active = True
    if str(lead_form.lifecycle_status) != LIFECYCLE_ACTIVE:
        lead_form.lifecycle_status = LIFECYCLE_ACTIVE
    await db.flush()
    return await resolve_publication(db, tenant_id=tenant_id, form_id=str(form_id))


async def deactivate_endpoint(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any]:
    lead_form = await db.get(TenantLeadForm, str(form_id))
    if lead_form is None or str(lead_form.tenant_id) != str(tenant_id):
        raise FormsNotFoundError(details={"form_id": form_id})
    lead_form.is_active = False
    await db.flush()
    return await resolve_publication(db, tenant_id=tenant_id, form_id=str(form_id))


def endpoint_from_publication(publication: dict[str, Any]) -> FormsEndpointIdentity:
    """Op: endpoint — HostFlow Public Form is-a Endpoint specialization."""
    if not publication.get("is_active"):
        raise FormsInactiveError(
            details={"publication_id": publication.get("publication_id")}
        )
    if publication.get("lifecycle_status") == LIFECYCLE_ARCHIVED:
        raise FormsArchivedError(
            details={"publication_id": publication.get("publication_id")}
        )
    pub_id = str(publication["publication_id"])
    return FormsEndpointIdentity(
        endpoint_type=ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM,
        form_id=pub_id,
        publication_id=pub_id,
        public_slug=publication.get("public_slug"),
        intake_source_profile_id=publication.get("intake_source_profile_id"),
        public_intake_path=str(publication.get("public_intake_path") or "/api/v1/public/intake"),
        is_active=True,
        published_version=int(publication.get("published_version") or 1),
        lifecycle_status=str(publication.get("lifecycle_status") or LIFECYCLE_ACTIVE),
    )


async def resolve_endpoint(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str | None = None,
    form_id: str | None = None,
) -> FormsEndpointIdentity:
    publication = await resolve_publication(
        db,
        tenant_id=tenant_id,
        public_slug=public_slug,
        form_id=form_id,
        require_active=True,
    )
    return endpoint_from_publication(publication)


def submission_entry(publication: dict[str, Any]) -> dict[str, Any]:
    """Op: submission — entry contract for Shared Intake (not a second submit engine)."""
    if not publication.get("is_active"):
        raise FormsInactiveError(
            details={"publication_id": publication.get("publication_id")}
        )
    version = int(publication.get("published_version") or 1)
    return {
        "forms_role": "submission_surface",
        "public_intake_path": publication.get("public_intake_path") or "/api/v1/public/intake",
        "storage_backend": publication.get("storage_backend"),
        "submission_handler": publication.get("submission_handler"),
        "publication_id": publication.get("publication_id"),
        "published_version": version,
        "publication_version_pin": {
            "form_id": publication.get("publication_id"),
            "version": version,
        },
        "consent_pin": publication.get("consent_pin"),
        "answer_contract": "forms.normalized_answers.v1",
        "field_schema_contract": (
            (publication.get("field_schema") or {}).get("schema_contract")
            if isinstance(publication.get("field_schema"), dict)
            else None
        ),
        "contract_version": publication.get("contract_version") or FORMS_PLATFORM_CONTRACT_VERSION,
        "builder_locked": builder_is_locked_by_manifest(),
    }


async def pin_submission_to_publication_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    published_version: int,
) -> dict[str, Any]:
    """Record that a submission is anchored to a ledger version (forbid later delete)."""
    row = await register_submission_pin(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        version=int(published_version),
    )
    return version_row_to_dict(row)


def assert_submission_version_compatible(
    publication: dict[str, Any],
    *,
    client_published_version: int | None,
) -> None:
    """Reject submissions that do not match the pinned published version."""
    pinned = int(publication.get("published_version") or 1)
    if client_published_version is None:
        raise FormsStaleVersionError(
            "published_version is required for submission compatibility",
            details={"pinned_published_version": pinned},
        )
    if int(client_published_version) != pinned:
        raise FormsStaleVersionError(
            details={
                "pinned_published_version": pinned,
                "client_published_version": int(client_published_version),
            }
        )


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
            "edit_published_version_in_place",
            "delete_pinned_publication_version",
        ],
        "adapter_id": FORMS_ADAPTER_ID,
        "contract_id": FORMS_PUBLIC_CONTRACT_ID,
    }


def adapter_identity() -> dict[str, Any]:
    return {
        "adapter_id": FORMS_ADAPTER_ID,
        "contract_id": FORMS_PUBLIC_CONTRACT_ID,
        "contract_version": FORMS_PLATFORM_CONTRACT_VERSION,
        "ops": [
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
        ],
        "builder_locked": builder_is_locked_by_manifest(),
        "manifest_builder_flag_default": FORMS_MANIFEST_KEYS[
            "forms.feature_flags.builder_enabled"
        ]["default"],
        "manifest": forms_manifest_document(),
    }


# Sprint 6 persistence surface (re-exported for adapter consumers)
persist_submission = persist_submission_envelope
get_submission = get_submission_envelope
list_submissions = list_submission_envelopes
set_submission_status = set_envelope_processing_status
