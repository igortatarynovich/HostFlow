"""Write orchestration for public intake forms (P8).

Creates TenantLeadForm + IntakeSourceProfile + bindings + tenant presentation.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import ENTITY_LEAD, SERVICE_SALES_MODULE
from backend.app.entity_profile.presentation_write import (
    PresentationWriteError,
    build_tenant_form_presentation_code,
    merge_client_fields_with_platform_preset,
    upsert_tenant_intake_presentation,
    validate_presentation_fields_for_profile,
)
from backend.app.models.entity_profile import EpEntityProfile
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeChannel, IntakeProvider, RouteIntent
from backend.app.models.mixins import now_utc
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.services.intake_form_admin_context import build_intake_form_admin_context
from backend.app.services.lead_forms_quota import (
    ensure_public_slug_unique_for_tenant,
    ensure_tenant_lead_form_active_count_allows_transition,
    normalize_and_validate_public_slug,
)
from backend.app.intake_platform.entity_profile_gate import validate_form_definition_triple
from backend.app.intake_platform.constants import FormLifecycleStatus
from backend.app.intake_platform.form_definition import (
    apply_form_definition_fields,
    default_submission_policy_for_entity_profile,
    format_supported_languages,
    read_form_definition,
    resolve_create_form_languages,
)
from backend.app.services.plan_feature_gates import count_tenant_lead_sources, ensure_lead_source_limit


_INTAKE_SOURCE_CODE_MAX_LEN = 64
_INTAKE_SOURCE_CODE_PREFIX = "public-form-"


def _public_form_profile_code(public_slug: str) -> str:
    slug = str(public_slug or "").strip().lower()
    safe = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-") or "form"
    prefix = _INTAKE_SOURCE_CODE_PREFIX
    max_len = _INTAKE_SOURCE_CODE_MAX_LEN - len(prefix)
    if len(safe) <= max_len:
        return f"{prefix}{safe}"
    digest = hashlib.sha1(safe.encode("utf-8")).hexdigest()[:8]
    keep = max(8, max_len - 9)
    return f"{prefix}{safe[:keep].rstrip('-')}-{digest}"


async def _intake_routing_for_entity_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
) -> dict[str, str]:
    """Map Entity Profile to intake routing (sales lead vs candidate application)."""
    from backend.app.entity_profile.constants import PLATFORM_TENANT_SCOPE

    code = str(entity_profile_code or "").strip()
    entity_type = ""
    row = await db.scalar(
        select(EpEntityProfile.entity_type)
        .where(
            EpEntityProfile.profile_code == code,
            EpEntityProfile.status == "active",
            EpEntityProfile.tenant_id.in_([str(tenant_id), PLATFORM_TENANT_SCOPE]),
        )
        .order_by(EpEntityProfile.tenant_id.desc())
        .limit(1)
    )
    if row is not None:
        entity_type = str(row or "").strip()

    is_sales_lead = entity_type == ENTITY_LEAD or code.startswith(f"{SERVICE_SALES_MODULE}.")
    if is_sales_lead:
        return {
            "route_intent": RouteIntent.sales_inquiry.value,
            "form_type": "sales_questionnaire",
            "lead_type": "client",
            "lead_target_type": "client_lead",
            "source": "public_intake",
        }
    return {
        "route_intent": RouteIntent.candidate_application.value,
        "form_type": "candidate_intake",
        "lead_type": "candidate",
        "lead_target_type": "candidate",
        "source": "public_intake",
    }


def _apply_intake_routing(profile: IntakeSourceProfile, routing: dict[str, str]) -> None:
    profile.route_intent = routing["route_intent"]
    profile.form_type = routing["form_type"]
    profile.lead_type = routing["lead_type"]
    profile.lead_target_type = routing["lead_target_type"]
    if routing.get("source"):
        profile.source = routing["source"]


async def _default_own_company_id(db: AsyncSession, tenant_id: str) -> str:
    row = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    if row is None:
        raise HTTPException(status_code=422, detail="Tenant has no active own company for intake routing")
    return str(row)


async def _load_form(db: AsyncSession, *, tenant_id: str, form_id: str) -> TenantLeadForm:
    row = await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == str(tenant_id),
            TenantLeadForm.id == str(form_id),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lead form not found")
    return row


async def _load_intake_source_for_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    public_slug: Optional[str],
) -> Optional[IntakeSourceProfile]:
    from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id

    profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=str(form_id),
        public_slug=public_slug,
    )
    if not profile_id:
        return None
    return await intake_crud.get_profile_by_id(db, tenant_id=str(tenant_id), profile_id=str(profile_id))


async def _sync_public_slug_bindings(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_profile: IntakeSourceProfile,
    lead_form_id: str,
    public_slug: str,
    old_slug: Optional[str] = None,
) -> None:
    slug_key = f"public_slug:{public_slug}"
    form_key = f"lead_form_id:{lead_form_id}"

    for binding in await intake_crud.list_bindings_for_profile(
        db, tenant_id=str(tenant_id), profile_id=str(intake_profile.id)
    ):
        # Shared profiles keep alias slug keys (unique on tenant+provider+key).
        # Never rename an existing public_slug:* row onto slug_key.
        if binding.external_key == slug_key:
            binding.is_active = True

    if not any(b.external_key == slug_key for b in await intake_crud.list_bindings_for_profile(
        db, tenant_id=str(tenant_id), profile_id=str(intake_profile.id)
    )):
        await intake_crud.create_binding(
            db,
            tenant_id=str(tenant_id),
            intake_source_profile_id=str(intake_profile.id),
            provider=IntakeProvider.public_intake.value,
            external_key=slug_key,
            priority=10,
        )

    bindings = await intake_crud.list_bindings_for_profile(
        db, tenant_id=str(tenant_id), profile_id=str(intake_profile.id)
    )
    if not any(b.external_key == form_key for b in bindings):
        await intake_crud.create_binding(
            db,
            tenant_id=str(tenant_id),
            intake_source_profile_id=str(intake_profile.id),
            provider=IntakeProvider.public_intake.value,
            external_key=form_key,
            priority=20,
        )

    if old_slug and old_slug != public_slug:
        stale_key = f"public_slug:{old_slug}"
        for binding in bindings:
            if binding.external_key == stale_key:
                binding.is_active = False


async def _deactivate_lead_form_id_bindings(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> None:
    """Drop this form's identity bindings without rewriting shared slug keys."""
    fid = str(form_id or "").strip()
    if not fid:
        return
    keys = [f"lead_form_id:{fid}", fid, f"form_id:{fid}"]
    rows = (
        await db.execute(
            select(IntakeSourceBinding).where(
                IntakeSourceBinding.tenant_id == str(tenant_id),
                IntakeSourceBinding.provider == IntakeProvider.public_intake.value,
                IntakeSourceBinding.external_key.in_(keys),
            )
        )
    ).scalars().all()
    for row in rows:
        row.is_active = False


async def _load_reusable_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    public_slug: str,
    profile_code: str,
) -> Optional[IntakeSourceProfile]:
    bound = await _load_intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        public_slug=public_slug,
    )
    if bound is not None:
        return bound
    by_code = await intake_crud.get_profile_by_code(
        db,
        tenant_id=str(tenant_id),
        code=profile_code,
    )
    if by_code is not None:
        return by_code
    return await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == str(tenant_id),
            IntakeSourceProfile.public_slug == public_slug,
        )
    )


async def _ensure_intake_source_for_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form: TenantLeadForm,
    entity_profile_code: str,
    own_company_id: str,
    default_language: Optional[str] = None,
    supported_languages: Optional[str] = None,
) -> IntakeSourceProfile:
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    if not public_slug:
        raise HTTPException(status_code=422, detail="public_slug is required before binding intake source")

    profile_code = _public_form_profile_code(public_slug)
    existing = await _load_reusable_intake_source(
        db,
        tenant_id=str(tenant_id),
        form_id=str(lead_form.id),
        public_slug=public_slug,
        profile_code=profile_code,
    )
    presentation_code = build_tenant_form_presentation_code(
        entity_profile_code=entity_profile_code,
        public_slug=public_slug,
    )

    routing = await _intake_routing_for_entity_profile(
        db,
        tenant_id=str(tenant_id),
        entity_profile_code=entity_profile_code,
    )

    if existing is not None:
        existing.entity_profile_code = str(entity_profile_code).strip()
        existing.presentation_code = presentation_code
        existing.public_slug = public_slug
        existing.name = lead_form.title or existing.name
        existing.is_active = bool(lead_form.is_active)
        if default_language:
            existing.default_language = default_language
        if supported_languages:
            existing.supported_languages = supported_languages
        _apply_intake_routing(existing, routing)
        await db.flush()
        await _sync_public_slug_bindings(
            db,
            tenant_id=str(tenant_id),
            intake_profile=existing,
            lead_form_id=str(lead_form.id),
            public_slug=public_slug,
        )
        return existing

    try:
        profile = await intake_crud.create_profile(
            db,
            tenant_id=str(tenant_id),
            code=profile_code,
            name=lead_form.title or profile_code,
            own_company_id=own_company_id,
            provider=IntakeProvider.public_intake.value,
            channel=IntakeChannel.direct.value,
            route_intent=routing["route_intent"],
            public_slug=public_slug,
            form_type=routing["form_type"],
            lead_type=routing["lead_type"],
            lead_target_type=routing["lead_target_type"],
            entity_profile_code=str(entity_profile_code).strip(),
            source=routing["source"],
            default_language=default_language or "pl",
            supported_languages=supported_languages or "pl,en,ru",
            is_active=bool(lead_form.is_active),
        )
    except intake_crud.IntakeRoutingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    profile.presentation_code = presentation_code
    await db.flush()
    await _sync_public_slug_bindings(
        db,
        tenant_id=str(tenant_id),
        intake_profile=profile,
        lead_form_id=str(lead_form.id),
        public_slug=public_slug,
    )
    return profile


def _http_from_presentation_error(exc: PresentationWriteError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": exc.code,
            "message": exc.message,
            **({"details": exc.details} if exc.details else {}),
        },
    )


async def create_public_intake_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    title: str,
    public_slug: str,
    entity_profile_code: str,
    fields: list[dict[str, Any]],
    is_active: bool = True,
    default_language: Optional[str] = None,
    supported_languages: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create lead form slot, intake source, bindings, and tenant presentation."""
    try:
        slug = normalize_and_validate_public_slug(public_slug)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "public_slug_invalid", "message": str(exc)}) from exc
    if not slug:
        raise HTTPException(status_code=422, detail="public_slug is required")

    current_sources = await count_tenant_lead_sources(db, str(tenant_id))
    await ensure_lead_source_limit(db, str(tenant_id), current_count=current_sources, extra_sources=1)
    await ensure_tenant_lead_form_active_count_allows_transition(
        db,
        str(tenant_id),
        was_active=False,
        will_be_active=bool(is_active),
    )

    form_id = str(uuid4())
    await ensure_public_slug_unique_for_tenant(db, str(tenant_id), slug=slug, exclude_form_id=form_id)

    preset_fields: list[dict[str, Any]] = []
    try:
        preset_payload = await load_entity_profile_presentation_preset(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=entity_profile_code,
        )
        raw_preset = preset_payload.get("fields") or []
        if isinstance(raw_preset, list):
            preset_fields = [row for row in raw_preset if isinstance(row, dict)]
    except HTTPException:
        preset_fields = []
    fields = merge_client_fields_with_platform_preset(fields, preset_fields)

    try:
        field_subset, presentation_overrides, profile_view = await validate_presentation_fields_for_profile(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=entity_profile_code,
            fields=fields,
        )
    except PresentationWriteError as exc:
        raise _http_from_presentation_error(exc) from exc
    profile_meta = profile_view.get("profile") or {}
    entity_profile_id = str(profile_meta.get("id") or "").strip()
    if not entity_profile_id:
        raise HTTPException(status_code=422, detail="Entity profile id could not be resolved")

    presentation_code = build_tenant_form_presentation_code(
        entity_profile_code=entity_profile_code,
        public_slug=slug,
    )

    default_lang, supported_langs = resolve_create_form_languages(
        default_language=default_language,
        supported_languages=supported_languages,
    )
    supported_languages_csv = format_supported_languages(supported_langs)

    lead_form = TenantLeadForm(
        id=form_id,
        tenant_id=str(tenant_id),
        title=(title or "").strip() or "Lead form",
        public_slug=slug,
        is_active=bool(is_active),
    )
    apply_form_definition_fields(
        lead_form,
        target_entity_profile_code=entity_profile_code,
        published_version=1,
        supported_languages=supported_languages_csv,
    )
    policy = default_submission_policy_for_entity_profile(entity_profile_code)
    validate_form_definition_triple(
        purpose=str(lead_form.purpose),
        target_entity_profile_code=entity_profile_code,
        submission_policy=policy,
    )
    lead_form.submission_policy = policy
    db.add(lead_form)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="public_slug already taken for this tenant") from exc

    own_company_id = await _default_own_company_id(db, str(tenant_id))
    intake_profile = await _ensure_intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        lead_form=lead_form,
        entity_profile_code=entity_profile_code,
        own_company_id=own_company_id,
        default_language=default_lang,
        supported_languages=supported_languages_csv,
    )

    await upsert_tenant_intake_presentation(
        db,
        tenant_id=str(tenant_id),
        entity_profile_id=entity_profile_id,
        presentation_code=presentation_code,
        field_subset=field_subset,
        presentation_overrides=presentation_overrides,
    )
    intake_profile.presentation_code = presentation_code
    await db.commit()
    return await build_intake_form_admin_context(db, tenant_id=str(tenant_id), form_id=form_id)


async def update_public_intake_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    title: Optional[str] = None,
    public_slug: Optional[str] = None,
    is_active: Optional[bool] = None,
    entity_profile_code: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
) -> dict[str, Any]:
    lead_form = await _load_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    old_slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None

    if title is not None:
        lead_form.title = (title or "").strip() or lead_form.title
    if is_active is not None:
        await ensure_tenant_lead_form_active_count_allows_transition(
            db,
            str(tenant_id),
            was_active=bool(lead_form.is_active),
            will_be_active=bool(is_active),
        )
        lead_form.is_active = bool(is_active)

    if lifecycle_status is not None:
        status = str(lifecycle_status).strip()
        if status not in {
            FormLifecycleStatus.draft.value,
            FormLifecycleStatus.active.value,
            FormLifecycleStatus.archived.value,
        }:
            raise HTTPException(status_code=422, detail="Invalid lifecycle_status")
        lead_form.lifecycle_status = status
        if status == FormLifecycleStatus.archived.value:
            lead_form.is_active = False

    new_slug = old_slug
    if public_slug is not None:
        try:
            normalized = normalize_and_validate_public_slug(public_slug)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "public_slug_invalid", "message": str(exc)}) from exc
        if not normalized:
            raise HTTPException(status_code=422, detail="public_slug cannot be cleared once published")
        await ensure_public_slug_unique_for_tenant(
            db, str(tenant_id), slug=normalized, exclude_form_id=str(lead_form.id)
        )
        lead_form.public_slug = normalized
        new_slug = normalized

    lead_form.updated_at = now_utc()
    await db.flush()

    archiving = str(getattr(lead_form, "lifecycle_status", "") or "") == FormLifecycleStatus.archived.value and (
        lifecycle_status is not None
    )
    if archiving:
        await _deactivate_lead_form_id_bindings(
            db,
            tenant_id=str(tenant_id),
            form_id=str(lead_form.id),
        )
        await db.commit()
        return await build_intake_form_admin_context(db, tenant_id=str(tenant_id), form_id=str(form_id))

    intake_profile = await _load_intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        form_id=str(lead_form.id),
        public_slug=new_slug,
    )
    ep_code = str(entity_profile_code or "").strip() if entity_profile_code else None
    if intake_profile is None and ep_code and new_slug:
        own_company_id = await _default_own_company_id(db, str(tenant_id))
        intake_profile = await _ensure_intake_source_for_form(
            db,
            tenant_id=str(tenant_id),
            lead_form=lead_form,
            entity_profile_code=ep_code,
            own_company_id=own_company_id,
        )
    elif intake_profile is not None:
        if ep_code:
            intake_profile.entity_profile_code = ep_code
            routing = await _intake_routing_for_entity_profile(
                db,
                tenant_id=str(tenant_id),
                entity_profile_code=ep_code,
            )
            _apply_intake_routing(intake_profile, routing)
        intake_profile.name = lead_form.title or intake_profile.name
        intake_profile.is_active = bool(lead_form.is_active)
        if public_slug is not None and new_slug:
            intake_profile.public_slug = new_slug
            if ep_code or intake_profile.entity_profile_code:
                bound_ep = ep_code or str(intake_profile.entity_profile_code or "").strip()
                intake_profile.presentation_code = build_tenant_form_presentation_code(
                    entity_profile_code=bound_ep,
                    public_slug=new_slug,
                )
            await _sync_public_slug_bindings(
                db,
                tenant_id=str(tenant_id),
                intake_profile=intake_profile,
                lead_form_id=str(lead_form.id),
                public_slug=new_slug,
                old_slug=old_slug if old_slug != new_slug else None,
            )
        await db.flush()

    await db.commit()
    return await build_intake_form_admin_context(db, tenant_id=str(tenant_id), form_id=str(form_id))


async def upsert_public_intake_form_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    entity_profile_code: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    lead_form = await _load_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    if not public_slug:
        raise HTTPException(status_code=422, detail="Lead form must have public_slug before saving presentation")

    own_company_id = await _default_own_company_id(db, str(tenant_id))
    intake_profile = await _ensure_intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        lead_form=lead_form,
        entity_profile_code=entity_profile_code,
        own_company_id=own_company_id,
    )

    try:
        field_subset, presentation_overrides, profile_view = await validate_presentation_fields_for_profile(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=entity_profile_code,
            fields=fields,
        )
    except PresentationWriteError as exc:
        raise _http_from_presentation_error(exc) from exc

    profile_meta = profile_view.get("profile") or {}
    entity_profile_id = str(profile_meta.get("id") or "").strip()
    presentation_code = build_tenant_form_presentation_code(
        entity_profile_code=entity_profile_code,
        public_slug=public_slug,
    )

    try:
        await upsert_tenant_intake_presentation(
            db,
            tenant_id=str(tenant_id),
            entity_profile_id=entity_profile_id,
            presentation_code=presentation_code,
            field_subset=field_subset,
            presentation_overrides=presentation_overrides,
        )
    except PresentationWriteError as exc:
        raise _http_from_presentation_error(exc) from exc

    intake_profile.entity_profile_code = str(entity_profile_code).strip()
    intake_profile.presentation_code = presentation_code
    lead_form.published_version = int(getattr(lead_form, "published_version", None) or 0) + 1
    await db.commit()
    return await build_intake_form_admin_context(db, tenant_id=str(tenant_id), form_id=str(form_id))


async def load_entity_profile_presentation_preset(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    presentation_code: str | None = None,
) -> dict[str, Any]:
    """Load platform intake presentation as constructor-ready field rows."""
    from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
    from backend.app.entity_profile.facade import resolve_entity_profile_facade
    from backend.app.entity_profile.presentation_runtime import (
        FormPresentationNotFoundError,
        resolve_form_presentation,
    )

    code = str(entity_profile_code or "").strip()
    try:
        profile_view = await resolve_entity_profile_facade(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=code,
            include_presentations=True,
        )
    except EntityProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    presentations = list(profile_view.get("presentations") or [])
    pres_code = str(presentation_code or "").strip()
    if not pres_code:
        if not presentations:
            raise HTTPException(status_code=404, detail="No platform presentation presets for this profile")
        pres_code = str(presentations[0].get("presentation_code") or "").strip()
    if not pres_code:
        raise HTTPException(status_code=404, detail="presentation_code is required")

    try:
        runtime = await resolve_form_presentation(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=code,
            presentation_code=pres_code,
        )
    except FormPresentationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    fields_out: list[dict[str, Any]] = []
    for row in runtime.get("fields") or []:
        if not isinstance(row, dict):
            continue
        qcode = str(row.get("qualified_code") or "").strip()
        if not qcode:
            continue
        overrides = row.get("presentation_overrides") if isinstance(row.get("presentation_overrides"), dict) else {}
        payload: dict[str, Any] = {
            "qualified_code": qcode,
            "label_override": str(row.get("label") or "").strip() or None,
            "intake_level": str(row.get("intake_level") or "optional"),
            "sort_order": int(row.get("sort_order") or 0),
        }
        widget_hint = str(overrides.get("widget_hint") or row.get("widget_hint") or "").strip()
        if widget_hint:
            payload["widget_hint"] = widget_hint
        rules = overrides.get("presentation_rules") or row.get("presentation_rules")
        if isinstance(rules, dict) and rules:
            payload["presentation_rules"] = dict(rules)
        fields_out.append({k: v for k, v in payload.items() if v is not None})

    profile_meta = profile_view.get("profile") or {}
    return {
        "entity_profile_code": code,
        "presentation_code": pres_code,
        "profile_name": profile_meta.get("name"),
        "fields": fields_out,
    }


async def list_selectable_entity_profiles(db: AsyncSession, *, tenant_id: str) -> list[dict[str, Any]]:
    from backend.app.entity_profile.constants import PLATFORM_TENANT_SCOPE
    from backend.app.models.entity_profile import EpEntityProfile

    rows = (
        await db.execute(
            select(EpEntityProfile)
            .where(
                EpEntityProfile.status == "active",
                EpEntityProfile.tenant_id.in_([str(tenant_id), PLATFORM_TENANT_SCOPE]),
            )
            .order_by(EpEntityProfile.profile_code.asc())
        )
    ).scalars().all()
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        code = str(row.profile_code or "").strip()
        if not code or code in seen:
            continue
        if row.tenant_id == str(tenant_id):
            seen.add(code)
            out.append({"code": code, "name": row.name, "entity_type": row.entity_type, "scope": "tenant"})
        elif code not in seen:
            seen.add(code)
            out.append({"code": code, "name": row.name, "entity_type": row.entity_type, "scope": "platform"})
    return out
