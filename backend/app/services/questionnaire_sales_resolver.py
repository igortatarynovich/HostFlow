"""Unified Sales questionnaire resolver (Questionnaire SSOT repair slice)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.entity_profile.presentation_write import build_tenant_form_presentation_code
from backend.app.entity_profile.seed_targeted_advertising_form import ensure_tenant_targeted_advertising_intake_form
from backend.app.intake_platform.constants import FormLifecycleStatus
from backend.app.intake_platform.form_definition import parse_supported_languages, read_form_definition
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.services.questionnaire_form_binding import intake_profile_for_lead_form
from backend.app.services.questionnaire_ssot_repair import (
    READINESS_NEEDS_REPAIR,
    READINESS_NOT_CONFIGURED,
    READINESS_READY,
    form_has_tenant_presentation,
    repair_targeted_advertising_form,
)


def _form_option_payload(form: TenantLeadForm, *, presentation_code: str | None = None) -> dict[str, Any]:
    definition = read_form_definition(form)
    return {
        "id": str(form.id),
        "title": form.title,
        "public_slug": form.public_slug,
        "is_system_preset": bool(form.is_system_preset),
        "lifecycle_status": definition["lifecycle_status"],
        "supported_languages": definition["supported_languages"],
        "presentation_code": presentation_code,
        "target_entity_profile_code": definition["target_entity_profile_code"],
    }


async def resolve_sales_questionnaire_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    auto_repair: bool = True,
) -> dict[str, Any]:
    """Return primary form, alternates, readiness, languages, and config error for Sales."""
    await ensure_tenant_targeted_advertising_intake_form(db, str(tenant_id))

    rows = (
        await db.execute(
            select(TenantLeadForm)
            .where(
                TenantLeadForm.tenant_id == str(tenant_id),
                TenantLeadForm.target_entity_profile_code == TARGETED_ADVERTISING_PROFILE_CODE,
            )
            .order_by(TenantLeadForm.is_system_preset.desc(), TenantLeadForm.updated_at.desc())
        )
    ).scalars().all()

    active_rows = [
        row
        for row in rows
        if str(getattr(row, "lifecycle_status", FormLifecycleStatus.active.value) or FormLifecycleStatus.active.value)
        != FormLifecycleStatus.archived.value
        and bool(row.is_active)
    ]

    if auto_repair:
        for form in active_rows:
            await repair_targeted_advertising_form(db, tenant_id=str(tenant_id), lead_form=form)

    ready_forms: list[dict[str, Any]] = []
    config_errors: list[str] = []

    for form in active_rows:
        intake_profile = await intake_profile_for_lead_form(
            db,
            tenant_id=str(tenant_id),
            lead_form=form,
        )
        public_slug = str(form.public_slug or "").strip()
        presentation_code = None
        if public_slug:
            presentation_code = build_tenant_form_presentation_code(
                entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
                public_slug=public_slug,
            )
        if intake_profile is not None:
            bound = str(getattr(intake_profile, "presentation_code", None) or "").strip()
            if bound:
                presentation_code = bound

        has_presentation = await form_has_tenant_presentation(db, tenant_id=str(tenant_id), lead_form=form)
        if not public_slug:
            config_errors.append(f"{form.id}:missing_public_slug")
            continue
        if intake_profile is None:
            config_errors.append(f"{form.id}:missing_intake_source_profile")
            continue
        if not has_presentation:
            config_errors.append(f"{form.id}:missing_tenant_presentation")
            continue

        ready_forms.append(_form_option_payload(form, presentation_code=presentation_code))

    primary_form = ready_forms[0] if ready_forms else None
    alternate_forms = ready_forms[1:] if len(ready_forms) > 1 else []

    if primary_form:
        readiness = READINESS_READY
        config_error = None
    elif config_errors:
        readiness = READINESS_NEEDS_REPAIR
        config_error = config_errors[0]
    else:
        readiness = READINESS_NOT_CONFIGURED
        config_error = "no_active_targeted_advertising_form"

    languages = primary_form.get("supported_languages") if primary_form else ["pl", "en", "ru"]
    if not languages:
        languages = parse_supported_languages(None)

    legacy_forms = [
        _form_option_payload(row)
        for row in rows
        if str(getattr(row, "lifecycle_status", FormLifecycleStatus.active.value) or FormLifecycleStatus.active.value)
        == FormLifecycleStatus.archived.value
    ]

    return {
        "primary_form": primary_form,
        "alternate_forms": alternate_forms,
        "archived_forms": legacy_forms,
        "readiness": readiness,
        "supported_languages": languages,
        "config_error": config_error,
    }


async def list_active_questionnaire_forms_for_sales(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[dict[str, Any]]:
    context = await resolve_sales_questionnaire_context(db, tenant_id=str(tenant_id), auto_repair=True)
    forms: list[dict[str, Any]] = []
    if context.get("primary_form"):
        forms.append(context["primary_form"])
    forms.extend(context.get("alternate_forms") or [])
    return forms
