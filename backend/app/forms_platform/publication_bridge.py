"""Bridge TenantLeadForm → ADR-007 Form Publication view (C4)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.forms_platform.constants import (
    FORMS_PLATFORM_ADR,
    FORMS_PLATFORM_CONTRACT_VERSION,
    FORMS_TIER_BASIC,
    PUBLICATION_MODE_LINKED,
    PUBLICATION_MODE_STANDALONE,
    STORAGE_BACKEND_TENANT_LEAD_FORM,
)
from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.forms_platform.handlers import (
    disposition_handler,
    list_registered_handlers,
    resolve_submission_handler,
)
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.intake_routing import crud as intake_crud


async def _load_lead_form_by_slug(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str,
) -> TenantLeadForm | None:
    slug = str(public_slug or "").strip()
    if not slug:
        return None
    return await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == str(tenant_id),
            TenantLeadForm.public_slug == slug,
        )
    )


async def _load_lead_form_by_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> TenantLeadForm | None:
    fid = str(form_id or "").strip()
    if not fid:
        return None
    return await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == str(tenant_id),
            TenantLeadForm.id == fid,
        )
    )


async def _publication_mode_for_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source: IntakeSourceProfile | None,
) -> str:
    if intake_source is None:
        return PUBLICATION_MODE_STANDALONE
    bindings = await intake_crud.list_bindings_for_profile(
        db,
        tenant_id=str(tenant_id),
        profile_id=str(intake_source.id),
    )
    for binding in bindings:
        key = str(getattr(binding, "external_key", "") or "")
        if key.startswith("vacancy_id:") or key.startswith("job_post_id:"):
            return PUBLICATION_MODE_LINKED
    return PUBLICATION_MODE_STANDALONE


def build_forms_platform_publication_view(
    *,
    lead_form: TenantLeadForm,
    intake_source: IntakeSourceProfile | None,
    entity_profile_code: str,
    publication_mode: str,
) -> dict[str, Any]:
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None
    raw_intent = None
    if intake_source is not None:
        raw_intent = str(getattr(intake_source, "route_intent", None) or "").strip() or None

    routing_status = "resolved"
    routing_reason: str | None = None
    route_intent: str | None = raw_intent
    try:
        if intake_source is None or not raw_intent:
            raise FormsRoutingUnresolvedError(
                details={"reason": "missing_route_intent"},
                message="Intake source profile with explicit route_intent is required",
            )
        handler = resolve_submission_handler(route_intent=raw_intent)
        route_intent = str(handler.get("route_intent") or raw_intent)
    except FormsRoutingUnresolvedError as exc:
        routing_status = "unresolved"
        routing_reason = str((exc.details or {}).get("reason") or "missing_route_intent")
        handler = disposition_handler(reason=routing_reason, route_intent=raw_intent)
        route_intent = None

    ep_code = str(entity_profile_code or DRIVER_CE_PROFILE_CODE).strip() or DRIVER_CE_PROFILE_CODE
    presentation_code = str(getattr(intake_source, "presentation_code", None) or "").strip() or None
    snap = getattr(lead_form, "published_snapshot_v1", None)
    snap_dict = snap if isinstance(snap, dict) else {}
    field_schema = snap_dict.get("field_schema") if isinstance(snap_dict.get("field_schema"), dict) else None
    has_field_schema = bool(
        field_schema and field_schema.get("schema_contract") == "forms.field_schema.v1"
    )

    return {
        "contract_version": FORMS_PLATFORM_CONTRACT_VERSION,
        "adr": FORMS_PLATFORM_ADR,
        "publication_id": str(lead_form.id),
        "storage_backend": STORAGE_BACKEND_TENANT_LEAD_FORM,
        "title": str(lead_form.title or ""),
        "public_slug": public_slug,
        "is_active": bool(lead_form.is_active),
        "lifecycle_status": str(getattr(lead_form, "lifecycle_status", None) or "active"),
        "published_version": int(getattr(lead_form, "published_version", 1) or 1),
        "published_at": (
            lead_form.published_at.isoformat()
            if getattr(lead_form, "published_at", None) is not None
            else None
        ),
        "has_immutable_snapshot": bool(snap_dict),
        "consent_pin": snap_dict.get("consent_pin"),
        "has_field_schema": has_field_schema,
        "field_schema": field_schema,
        "mode": publication_mode,
        "tier": FORMS_TIER_BASIC,
        "module_owner": handler.get("module_owner"),
        "entity_profile_code": ep_code,
        "presentation_code": presentation_code,
        "intake_source_profile_id": str(intake_source.id) if intake_source else None,
        "route_intent": route_intent,
        "routing_status": routing_status,
        "routing_reason": routing_reason,
        "public_intake_path": "/api/v1/public/intake",
        "public_apply_path_template": "/public/apply/{token}",
        "submission_handler": handler,
        "capabilities": {
            "file_uploads": True,
            "field_mapping": True,
            "consent_capture": True,
            "presentation_rules": True,
            "immutable_publish": True,
            "field_schema_validation": has_field_schema,
        },
        "canon": "TenantLeadForm is bridged as ADR-007 publication until FormTemplate migration",
    }


async def resolve_forms_platform_publication(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str | None = None,
    form_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve ADR-007 publication contract for a tenant lead form."""
    lead_form: TenantLeadForm | None = None
    if form_id:
        lead_form = await _load_lead_form_by_id(db, tenant_id=str(tenant_id), form_id=str(form_id))
    elif public_slug:
        lead_form = await _load_lead_form_by_slug(db, tenant_id=str(tenant_id), public_slug=str(public_slug))
    if lead_form is None:
        return None

    slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None
    intake_source_profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=str(lead_form.id),
        public_slug=slug,
    )
    intake_source: IntakeSourceProfile | None = None
    if intake_source_profile_id:
        intake_source = await intake_crud.get_profile_by_id(
            db,
            tenant_id=str(tenant_id),
            profile_id=str(intake_source_profile_id),
        )

    entity_profile_code = (
        str(getattr(intake_source, "entity_profile_code", None) or "").strip()
        or DRIVER_CE_PROFILE_CODE
    )
    mode = await _publication_mode_for_intake_source(
        db,
        tenant_id=str(tenant_id),
        intake_source=intake_source,
    )
    return build_forms_platform_publication_view(
        lead_form=lead_form,
        intake_source=intake_source,
        entity_profile_code=entity_profile_code,
        publication_mode=mode,
    )


async def build_forms_platform_admin_block(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any]:
    """Admin-facing ADR-007 block for intake form detail."""
    publication = await resolve_forms_platform_publication(
        db,
        tenant_id=str(tenant_id),
        form_id=str(form_id),
    )
    if publication is None:
        return {
            "contract_version": FORMS_PLATFORM_CONTRACT_VERSION,
            "adr": FORMS_PLATFORM_ADR,
            "available_handlers": list_registered_handlers(),
        }
    return {
        **publication,
        "available_handlers": list_registered_handlers(),
    }
