"""Questionnaire SSOT repair — backfill targeted-advertising forms to ADR-022 contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    TARGETED_ADVERTISING_PRESENTATION_CODE,
    TARGETED_ADVERTISING_PROFILE_CODE,
)
from backend.app.entity_profile.presentation_runtime import (
    FormPresentationNotFoundError,
    resolve_form_presentation,
)
from backend.app.entity_profile.presentation_write import (
    build_tenant_form_presentation_code,
    create_tenant_intake_presentation_if_absent,
)
from backend.app.entity_profile.provision_targeted_advertising import (
    TARGETED_ADVERTISING_FORM_SLUG,
    recover_targeted_advertising_capability,
)
from backend.app.entity_profile.registry import EntityProfileRegistry
from backend.app.intake_platform.constants import DEFAULT_INQUIRY_POLICY, FormLifecycleStatus, FormPurpose
from backend.app.intake_platform.form_definition import apply_form_definition_fields, parse_supported_languages
from backend.app.models.entity_profile import EpIntakePresentation
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeProvider, RouteIntent
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.services.questionnaire_form_binding import intake_profile_for_lead_form


READINESS_READY = "ready"
READINESS_NEEDS_REPAIR = "needs_repair"
READINESS_NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True)
class QuestionnaireRepairResult:
    tenant_id: str
    status: str
    repaired_forms: list[str] = field(default_factory=list)
    skipped_forms: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _is_platform_preset_presentation_code(code: str) -> bool:
    normalized = str(code or "").strip()
    if not normalized:
        return True
    if normalized == TARGETED_ADVERTISING_PRESENTATION_CODE:
        return True
    return ".public_" in normalized and ".form." not in normalized


def _looks_like_targeted_advertising_form(form: TenantLeadForm) -> bool:
    profile_code = str(getattr(form, "target_entity_profile_code", None) or "").strip()
    if profile_code == TARGETED_ADVERTISING_PROFILE_CODE:
        return True
    slug = str(getattr(form, "public_slug", None) or "").strip().lower()
    if slug == TARGETED_ADVERTISING_FORM_SLUG or slug.startswith(f"{TARGETED_ADVERTISING_FORM_SLUG}-"):
        return True
    title = str(getattr(form, "title", None) or "").strip().lower()
    return "target" in title and ("reklam" in title or "advertis" in title)


async def _candidate_targeted_advertising_forms(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[TenantLeadForm]:
    rows = (
        await db.execute(
            select(TenantLeadForm)
            .where(TenantLeadForm.tenant_id == str(tenant_id))
            .order_by(TenantLeadForm.is_system_preset.desc(), TenantLeadForm.updated_at.desc())
        )
    ).scalars().all()
    return [row for row in rows if _looks_like_targeted_advertising_form(row)]


async def _ensure_tenant_presentation_from_platform_if_absent(
    db: AsyncSession,
    *,
    tenant_id: str,
    public_slug: str,
) -> tuple[str, bool]:
    tenant_code = build_tenant_form_presentation_code(
        entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
        public_slug=public_slug,
    )
    entity = await EntityProfileRegistry.get_entity_profile(
        db,
        tenant_id=str(tenant_id),
        profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
    )
    if entity is None:
        raise RuntimeError("targeted_advertising entity profile missing")

    existing = await db.scalar(
        select(EpIntakePresentation).where(
            EpIntakePresentation.tenant_id == str(tenant_id),
            EpIntakePresentation.presentation_code == tenant_code,
        )
    )
    if existing is not None:
        return tenant_code, False

    try:
        platform_runtime = await resolve_form_presentation(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
            presentation_code=TARGETED_ADVERTISING_PRESENTATION_CODE,
        )
    except FormPresentationNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc

    field_subset = [
        str(code).strip()
        for code in (platform_runtime.get("field_subset") or [])
        if str(code).strip()
    ]
    if not field_subset:
        field_subset = [
            str(row.get("qualified_code") or "").strip()
            for row in (platform_runtime.get("fields") or [])
            if isinstance(row, dict) and str(row.get("qualified_code") or "").strip()
        ]

    presentation_overrides: dict[str, Any] = {}
    for row in platform_runtime.get("fields") or []:
        if not isinstance(row, dict):
            continue
        qcode = str(row.get("qualified_code") or "").strip()
        if not qcode:
            continue
        override = row.get("presentation_overrides")
        if isinstance(override, dict) and override:
            presentation_overrides[qcode] = dict(override)
        else:
            presentation_overrides[qcode] = {
                "intake_level": str(row.get("intake_level") or "optional"),
                **({"label_override": row["label"]} if row.get("label") else {}),
                **({"widget_hint": row["widget_hint"]} if row.get("widget_hint") else {}),
            }

    _, created = await create_tenant_intake_presentation_if_absent(
        db,
        tenant_id=str(tenant_id),
        entity_profile_id=str(entity.id),
        presentation_code=tenant_code,
        field_subset=field_subset,
        presentation_overrides=presentation_overrides,
    )
    return tenant_code, created


async def repair_targeted_advertising_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form: TenantLeadForm,
) -> dict[str, Any]:
    """Repair one sales questionnaire form; idempotent and non-destructive."""
    repaired: dict[str, bool] = {}
    # Capture scalars before awaits — concurrent repair may expire the ORM instance.
    form_id = str(lead_form.id)
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    if not public_slug:
        return {"repaired": repaired, "error": "missing_public_slug"}

    profile_code = str(getattr(lead_form, "target_entity_profile_code", None) or "").strip()
    if profile_code != TARGETED_ADVERTISING_PROFILE_CODE:
        apply_form_definition_fields(
            lead_form,
            target_entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
            purpose=FormPurpose.inquiry.value,
            submission_policy=DEFAULT_INQUIRY_POLICY,
        )
        repaired["target_entity_profile_code"] = True

    if not parse_supported_languages(getattr(lead_form, "supported_languages", None)):
        lead_form.supported_languages = "pl,en,ru"
        repaired["supported_languages"] = True

    lifecycle = str(getattr(lead_form, "lifecycle_status", None) or "").strip()
    if lifecycle not in {FormLifecycleStatus.draft.value, FormLifecycleStatus.active.value, FormLifecycleStatus.archived.value}:
        lead_form.lifecycle_status = FormLifecycleStatus.active.value
        repaired["lifecycle_status"] = True

    tenant_presentation_code, presentation_created = await _ensure_tenant_presentation_from_platform_if_absent(
        db,
        tenant_id=str(tenant_id),
        public_slug=public_slug,
    )
    if presentation_created:
        repaired["tenant_presentation"] = True

    # Re-bind after presentation create (may have used a savepoint / concurrent flush).
    lead_form = await db.get(TenantLeadForm, form_id) or lead_form

    intake_profile = await intake_profile_for_lead_form(
        db,
        tenant_id=str(tenant_id),
        lead_form=lead_form,
    )
    if intake_profile is None:
        return {"repaired": repaired, "error": "missing_intake_source_profile"}

    bound_presentation = str(getattr(intake_profile, "presentation_code", None) or "").strip()
    if bound_presentation != tenant_presentation_code and _is_platform_preset_presentation_code(bound_presentation):
        intake_profile.presentation_code = tenant_presentation_code
        repaired["intake_presentation_code"] = True

    if not str(getattr(intake_profile, "entity_profile_code", None) or "").strip():
        intake_profile.entity_profile_code = TARGETED_ADVERTISING_PROFILE_CODE
        repaired["intake_entity_profile_code"] = True

    if str(getattr(intake_profile, "supported_languages", None) or "").strip() != "pl,en,ru":
        intake_profile.supported_languages = "pl,en,ru"
        repaired["intake_supported_languages"] = True

    form_binding_key = f"lead_form_id:{form_id}"
    binding = await db.scalar(
        select(IntakeSourceBinding).where(
            IntakeSourceBinding.tenant_id == str(tenant_id),
            IntakeSourceBinding.intake_source_profile_id == str(intake_profile.id),
            IntakeSourceBinding.external_key == form_binding_key,
            IntakeSourceBinding.is_active.is_(True),
        )
    )
    if binding is None:
        await intake_crud.create_binding(
            db,
            tenant_id=str(tenant_id),
            intake_source_profile_id=str(intake_profile.id),
            provider=IntakeProvider.public_intake.value,
            external_key=form_binding_key,
            priority=20,
        )
        repaired["lead_form_binding"] = True

    await db.flush()
    return {"repaired": repaired, "presentation_code": tenant_presentation_code}


async def repair_targeted_advertising_questionnaires(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> QuestionnaireRepairResult:
    """Repair all targeted-advertising questionnaire forms for a tenant."""
    capability = await recover_targeted_advertising_capability(db, str(tenant_id))
    if capability.status == "failed":
        return QuestionnaireRepairResult(
            tenant_id=str(tenant_id),
            status="failed",
            errors=[capability.error or "capability_recovery_failed"],
        )

    repaired_ids: list[str] = []
    skipped_ids: list[str] = []
    errors: list[str] = []

    forms = await _candidate_targeted_advertising_forms(db, tenant_id=str(tenant_id))
    for lead_form in forms:
        lifecycle = str(getattr(lead_form, "lifecycle_status", FormLifecycleStatus.active.value) or "").strip()
        if lifecycle == FormLifecycleStatus.archived.value:
            skipped_ids.append(str(lead_form.id))
            continue
        result = await repair_targeted_advertising_form(db, tenant_id=str(tenant_id), lead_form=lead_form)
        error = str(result.get("error") or "").strip()
        if error:
            errors.append(f"{lead_form.id}:{error}")
            skipped_ids.append(str(lead_form.id))
            continue
        if result.get("repaired"):
            repaired_ids.append(str(lead_form.id))
        else:
            skipped_ids.append(str(lead_form.id))

    status = READINESS_READY if not errors else READINESS_NEEDS_REPAIR
    return QuestionnaireRepairResult(
        tenant_id=str(tenant_id),
        status=status,
        repaired_forms=repaired_ids,
        skipped_forms=skipped_ids,
        errors=errors,
    )


async def form_has_tenant_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form: TenantLeadForm,
) -> bool:
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    if not public_slug:
        return False
    tenant_code = build_tenant_form_presentation_code(
        entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
        public_slug=public_slug,
    )
    row = await db.scalar(
        select(EpIntakePresentation.id).where(
            EpIntakePresentation.tenant_id == str(tenant_id),
            EpIntakePresentation.presentation_code == tenant_code,
            EpIntakePresentation.is_active.is_(True),
        )
    )
    return row is not None
