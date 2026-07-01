"""Read-only admin context for Intake Source / Form Builder UI (P6)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    DRIVER_CE_INTAKE_PRESENTATION_CODE,
    DRIVER_CE_PROFILE_CODE,
)
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import resolve_entity_profile_for_intake_source
from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.entity_profile.presentation_runtime import (
    FormPresentationNotFoundError,
    resolve_form_presentation,
    resolve_form_presentation_for_intake_source,
)
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.tenant_lead_form import TenantLeadForm


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


async def _load_lead_form(db: AsyncSession, *, tenant_id: str, form_id: str) -> TenantLeadForm:
    row = await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == str(tenant_id),
            TenantLeadForm.id == str(form_id),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lead form not found")
    return row


async def _load_intake_source_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
) -> Optional[IntakeSourceProfile]:
    return await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == str(tenant_id),
            IntakeSourceProfile.id == str(profile_id),
        )
    )


def _submit_destination(*, entity_profile_code: str, route_intent: Optional[str]) -> dict[str, Any]:
    intent = str(route_intent or "candidate_application").strip()
    if intent in {"sales_inquiry", "client_lead"}:
        pipeline = "Lead draft → Decision Layer → Client lead (no Candidate on create)"
    else:
        pipeline = (
            "Lead draft → Ingest Envelope → Decision Layer → Outcome Executor "
            "(Candidate only when disposition is create_candidate)"
        )
    return {
        "pipeline": pipeline,
        "route_intent": intent,
        "entity_profile_code": entity_profile_code,
        "creates_candidate_on_create": False,
        "creates_lead_draft_on_create": True,
    }


async def build_intake_form_admin_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any]:
    """Aggregate lead form + intake source + entity profile + presentation preview."""
    lead_form = await _load_lead_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None

    intake_source_profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=str(lead_form.id),
        public_slug=public_slug,
    )
    intake_source: Optional[IntakeSourceProfile] = None
    if intake_source_profile_id:
        intake_source = await _load_intake_source_profile(
            db,
            tenant_id=str(tenant_id),
            profile_id=intake_source_profile_id,
        )

    entity_profile_code = (
        str(getattr(intake_source, "entity_profile_code", None) or "").strip()
        or DRIVER_CE_PROFILE_CODE
    )
    presentation_code = str(getattr(intake_source, "presentation_code", None) or "").strip()
    route_intent = str(getattr(intake_source, "route_intent", None) or "candidate_application")

    try:
        if intake_source_profile_id:
            profile_view = await resolve_entity_profile_for_intake_source(
                db,
                tenant_id=str(tenant_id),
                intake_source_profile_id=str(intake_source_profile_id),
                entity_profile_code=entity_profile_code,
                include_presentations=True,
            )
        else:
            from backend.app.entity_profile.facade import resolve_entity_profile_facade

            profile_view = await resolve_entity_profile_facade(
                db,
                tenant_id=str(tenant_id),
                entity_profile_code=entity_profile_code,
                include_presentations=True,
            )
    except EntityProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    presentations = list(profile_view.get("presentations") or [])
    if not presentation_code and presentations:
        first_code = str(presentations[0].get("presentation_code") or "").strip()
        if first_code:
            presentation_code = first_code
    if not presentation_code:
        presentation_code = DRIVER_CE_INTAKE_PRESENTATION_CODE

    if not presentation_code:
        presentation_code = DRIVER_CE_INTAKE_PRESENTATION_CODE

    codes_to_try: list[str] = []
    if presentation_code:
        codes_to_try.append(presentation_code)
    if DRIVER_CE_INTAKE_PRESENTATION_CODE not in codes_to_try:
        codes_to_try.append(DRIVER_CE_INTAKE_PRESENTATION_CODE)

    presentation_runtime = None
    last_error: FormPresentationNotFoundError | None = None
    for code in codes_to_try:
        try:
            if intake_source_profile_id:
                presentation_runtime = await resolve_form_presentation_for_intake_source(
                    db,
                    tenant_id=str(tenant_id),
                    intake_source_profile_id=str(intake_source_profile_id),
                    presentation_code=code,
                )
            else:
                presentation_runtime = await resolve_form_presentation(
                    db,
                    tenant_id=str(tenant_id),
                    entity_profile_code=entity_profile_code,
                    presentation_code=code,
                    intake_source_profile_id=intake_source_profile_id,
                )
            break
        except FormPresentationNotFoundError as exc:
            last_error = exc
            continue
    if presentation_runtime is None:
        raise HTTPException(status_code=404, detail=str(last_error or "Form presentation not found"))

    profile_meta = _record(profile_view.get("profile"))
    intake_source_payload: Optional[dict[str, Any]] = None
    if intake_source is not None:
        intake_source_payload = {
            "id": str(intake_source.id),
            "code": intake_source.code,
            "name": intake_source.name,
            "provider": intake_source.provider,
            "channel": intake_source.channel,
            "route_intent": intake_source.route_intent,
            "entity_profile_code": intake_source.entity_profile_code,
            "presentation_code": intake_source.presentation_code,
            "default_assignee_id": intake_source.default_assignee_id,
            "default_language": intake_source.default_language,
            "is_active": bool(intake_source.is_active),
        }

    return {
        "form": {
            "id": str(lead_form.id),
            "title": lead_form.title or "",
            "public_slug": public_slug,
            "is_active": bool(lead_form.is_active),
            "created_at": lead_form.created_at,
            "updated_at": lead_form.updated_at,
        },
        "intake_source_profile": intake_source_payload,
        "intake_source_profile_id": intake_source_profile_id,
        "entity_profile": {
            "code": entity_profile_code,
            "name": profile_meta.get("name"),
            "entity_type": profile_meta.get("entity_type"),
            "resolution_source": profile_view.get("resolution_source"),
        },
        "presentation": presentation_runtime,
        "presentations_available": presentations,
        "submit_destination": _submit_destination(
            entity_profile_code=entity_profile_code,
            route_intent=route_intent,
        ),
    }


async def run_intake_form_smoke_test(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any]:
    """Create a lead-first draft via the same path as public intake (no Candidate INSERT)."""
    from backend.app.entity_profile.public_intake_draft_session import (
        create_or_reuse_public_intake_lead_draft,
    )
    from backend.app.services.lead_forms_quota import lead_form_meta_for_intake_state
    from backend.app.services.source_labels import normalize_candidate_source

    lead_form = await _load_lead_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    if not lead_form.is_active:
        raise HTTPException(status_code=422, detail="Lead form must be active for smoke test")
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    if not public_slug:
        raise HTTPException(status_code=422, detail="Lead form must have a published public slug")

    suffix = uuid4().hex[:10]
    contacts = {
        "phone_country_code": "+48",
        "phone": f"600{suffix[:7]}",
        "email": f"smoke-{suffix}@example.com",
    }
    lf_meta = lead_form_meta_for_intake_state(lead_form)
    lead, token, expires_at = await create_or_reuse_public_intake_lead_draft(
        db,
        tenant_id=str(tenant_id),
        contacts=contacts,
        intake_source=normalize_candidate_source("settings_smoke_test"),
        vacancy_id=None,
        application_kind="candidate",
        lead_form_meta=lf_meta,
        client_company=None,
    )
    await db.commit()
    return {
        "lead_id": str(lead.id),
        "candidate_id": None,
        "token": token,
        "expires_at": expires_at,
        "contacts": contacts,
        "stage": getattr(lead, "stage", None),
        "message": "Smoke test created a Lead draft session; no Candidate row was inserted.",
    }
