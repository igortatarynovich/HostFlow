"""Lead-bound questionnaire invite tokens (Stage Sales Intake 1 — targeted advertising)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    TARGETED_ADVERTISING_PROFILE_CODE,
)
from backend.app.entity_profile.presentation_write import build_tenant_form_presentation_code
from backend.app.entity_profile.public_intake_presentation_bridge import (
    PRESENTATION_VALUES_V1,
    presentation_values_dict_from_state,
)
from backend.app.intake_platform.constants import FormLifecycleStatus
from backend.app.intake_platform.form_definition import parse_supported_languages
from backend.app.services.questionnaire_form_binding import intake_profile_for_lead_form
from backend.app.models import Lead
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeProvider, RouteIntent
from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
from backend.app.intake_platform.policy_resolver import resolve_effective_policy_for_invite
from backend.app.intake_platform.submission_store import append_submission
from backend.app.models.tenant_lead_form import TenantLeadForm

INVITE_STATUS_NOT_SENT = "not_sent"
INVITE_STATUS_SENT = "sent"
INVITE_STATUS_OPENED = "opened"
INVITE_STATUS_IN_PROGRESS = "in_progress"
INVITE_STATUS_SUBMITTED = "submitted"

LEAD_STAGE_WAITING_FOR_RESPONSE = "waiting_for_response"
LEAD_STAGE_QUESTIONNAIRE_SUBMITTED = "questionnaire_submitted"

QUESTIONNAIRE_WAITING_STATUSES = frozenset(
    {INVITE_STATUS_SENT, INVITE_STATUS_OPENED, INVITE_STATUS_IN_PROGRESS}
)

QUESTIONNAIRE_INVITE_TTL_DAYS = 30
SALES_QUESTIONNAIRE_PREFIX = f"{TARGETED_ADVERTISING_PROFILE_CODE}."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_token() -> str:
    return secrets.token_urlsafe(24)


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _trim(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _apply_url_for_token(token: str, *, form_locale: str | None = None) -> str:
    base = f"/public/apply/{token}"
    locale = str(form_locale or "").strip().lower()
    if locale in {"pl", "en", "ru"}:
        return f"{base}?lang={locale}"
    return base


def _qualified_to_sales_key(qualified_code: str) -> str | None:
    code = str(qualified_code or "").strip()
    if not code.startswith(SALES_QUESTIONNAIRE_PREFIX):
        return None
    return code[len(SALES_QUESTIONNAIRE_PREFIX) :]


def invite_intake_state(invite: LeadQuestionnaireInvite) -> dict[str, Any]:
    meta = _record(invite.meta)
    state = meta.get("intake_state")
    return dict(state) if isinstance(state, dict) else {}


def write_invite_intake_state(invite: LeadQuestionnaireInvite, state: dict[str, Any]) -> None:
    meta = _record(invite.meta)
    meta["intake_state"] = dict(state)
    invite.meta = meta


async def _lead_form_for_intake_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_profile: IntakeSourceProfile,
) -> TenantLeadForm | None:
    bindings = (
        await db.execute(
            select(IntakeSourceBinding).where(
                IntakeSourceBinding.tenant_id == str(tenant_id),
                IntakeSourceBinding.intake_source_profile_id == str(intake_profile.id),
                IntakeSourceBinding.is_active.is_(True),
            )
        )
    ).scalars().all()
    for binding in bindings:
        key = str(binding.external_key or "").strip()
        if not key.startswith("lead_form_id:"):
            continue
        form_id = key.split(":", 1)[1].strip()
        if not form_id:
            continue
        lead_form = await db.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == str(tenant_id),
                TenantLeadForm.id == form_id,
            )
        )
        if lead_form is not None:
            return lead_form

    public_slug = str(getattr(intake_profile, "public_slug", None) or "").strip()
    if public_slug:
        return await db.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == str(tenant_id),
                TenantLeadForm.public_slug == public_slug,
            )
        )
    return None


async def _intake_profile_for_lead_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form: TenantLeadForm,
) -> IntakeSourceProfile | None:
    form_id = str(lead_form.id)
    bindings = (
        await db.execute(
            select(IntakeSourceBinding).where(
                IntakeSourceBinding.tenant_id == str(tenant_id),
                IntakeSourceBinding.external_key == f"lead_form_id:{form_id}",
                IntakeSourceBinding.is_active.is_(True),
            )
        )
    ).scalars().all()
    for binding in bindings:
        profile = await db.get(IntakeSourceProfile, str(binding.intake_source_profile_id))
        if (
            profile is not None
            and profile.is_active
            and str(profile.route_intent or "") == RouteIntent.sales_inquiry.value
        ):
            return profile

    public_slug = str(lead_form.public_slug or "").strip()
    if not public_slug:
        return None
    return await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == str(tenant_id),
            IntakeSourceProfile.public_slug == public_slug,
            IntakeSourceProfile.route_intent == RouteIntent.sales_inquiry.value,
            IntakeSourceProfile.is_active.is_(True),
        )
    )


async def resolve_lead_form_for_questionnaire(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form_id: str | None = None,
) -> tuple[TenantLeadForm, IntakeSourceProfile]:
    """Resolve B2B sales questionnaire form (explicit pick or tenant default)."""
    if lead_form_id:
        lead_form = await db.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == str(tenant_id),
                TenantLeadForm.id == str(lead_form_id),
                TenantLeadForm.is_active.is_(True),
            )
        )
        if lead_form is None:
            raise LookupError("Lead form not found or inactive")
        if str(lead_form.tenant_id) != str(tenant_id):
            raise LookupError("Lead form not found or inactive")
        profile_code = str(lead_form.target_entity_profile_code or "").strip()
        if profile_code != TARGETED_ADVERTISING_PROFILE_CODE:
            raise LookupError("Lead form is not a targeted advertising questionnaire")
        if str(getattr(lead_form, "lifecycle_status", FormLifecycleStatus.active.value) or FormLifecycleStatus.active.value) == FormLifecycleStatus.archived.value:
            raise LookupError("Lead form is archived")
        intake_profile = await intake_profile_for_lead_form(
            db,
            tenant_id=str(tenant_id),
            lead_form=lead_form,
        )
        if intake_profile is None:
            raise LookupError("Intake source profile is not configured for lead form")
        return lead_form, intake_profile
    return await resolve_lead_form_for_targeted_advertising(db, tenant_id=str(tenant_id))


async def list_questionnaire_forms_for_targeted_advertising(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[dict[str, Any]]:
    from backend.app.services.questionnaire_sales_resolver import list_active_questionnaire_forms_for_sales

    return await list_active_questionnaire_forms_for_sales(db, tenant_id=str(tenant_id))


async def resolve_lead_form_for_targeted_advertising(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[TenantLeadForm, IntakeSourceProfile]:
    """Resolve active B2B sales questionnaire form (seeded or constructor-created)."""
    from backend.app.services.questionnaire_sales_resolver import list_active_questionnaire_forms_for_sales

    forms = await list_active_questionnaire_forms_for_sales(db, tenant_id=str(tenant_id))
    if not forms:
        raise LookupError("Targeted advertising lead form is not configured for tenant")

    primary_id = str(forms[0]["id"])
    lead_form = await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == str(tenant_id),
            TenantLeadForm.id == primary_id,
        )
    )
    if lead_form is None:
        raise LookupError("Targeted advertising lead form is not configured for tenant")
    intake_profile = await intake_profile_for_lead_form(
        db,
        tenant_id=str(tenant_id),
        lead_form=lead_form,
    )
    if intake_profile is None:
        raise LookupError("Intake source profile is not configured for lead form")
    return lead_form, intake_profile


def _initial_intake_state(
    *,
    lead: Lead,
    lead_form: TenantLeadForm,
) -> dict[str, Any]:
    normalized = _record(lead.normalized)
    payload = _record(lead.payload)
    full_name = _trim(normalized.get("full_name")) or _trim(payload.get("full_name"))
    company_name = _trim(normalized.get("company_name")) or _trim(payload.get("company_name"))
    email = _trim(normalized.get("email")) or _trim(payload.get("email"))
    phone = _trim(normalized.get("phone")) or _trim(payload.get("phone"))

    presentation_values: dict[str, Any] = {}
    if full_name:
        presentation_values[f"{SALES_QUESTIONNAIRE_PREFIX}contact_full_name"] = full_name
    if company_name:
        presentation_values[f"{SALES_QUESTIONNAIRE_PREFIX}contact_company_name"] = company_name
    if email:
        presentation_values[f"{SALES_QUESTIONNAIRE_PREFIX}contact_email"] = email
    if phone:
        presentation_values[f"{SALES_QUESTIONNAIRE_PREFIX}contact_phone"] = phone

    return {
        "contacts": {
            "email": email,
            "phone": phone,
        },
        "personal": {"full_name": full_name},
        "client_company": {"name": company_name},
        "application_kind": "client",
        "lead_form": {
            "id": str(lead_form.id),
            "public_slug": lead_form.public_slug,
            "title": lead_form.title,
        },
        PRESENTATION_VALUES_V1: presentation_values,
    }


async def find_questionnaire_invite_by_token(
    db: AsyncSession,
    *,
    token: str,
) -> LeadQuestionnaireInvite | None:
    tok = str(token or "").strip()
    if not tok:
        return None
    return await db.scalar(
        select(LeadQuestionnaireInvite).where(LeadQuestionnaireInvite.token == tok).limit(1)
    )


async def find_active_questionnaire_invite_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> LeadQuestionnaireInvite | None:
    rows = (
        await db.execute(
            select(LeadQuestionnaireInvite)
            .where(
                LeadQuestionnaireInvite.tenant_id == str(tenant_id),
                LeadQuestionnaireInvite.lead_id == str(lead_id),
                LeadQuestionnaireInvite.status != INVITE_STATUS_SUBMITTED,
            )
            .order_by(LeadQuestionnaireInvite.created_at.desc())
        )
    ).scalars().all()
    now = _now()
    for invite in rows:
        if invite.expires_at and invite.expires_at < now:
            continue
        return invite
    return None


async def attach_questionnaire_invite_to_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    mark_sent: bool = False,
    lead_form_id: str | None = None,
    form_locale: str | None = None,
    create_if_missing: bool = False,
    force_new: bool = False,
) -> LeadQuestionnaireInvite:
    """Create or reuse a personal questionnaire token bound to an existing Lead.

    Public create endpoint keeps ``mark_sent=False`` from creating drafts.
    Email preview/send uses ``create_if_missing=True`` so an invite can exist
    before the outbound message is accepted.
    """
    lead_form, intake_profile = await resolve_lead_form_for_questionnaire(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=lead_form_id,
    )
    supported = parse_supported_languages(getattr(lead_form, "supported_languages", None))
    locale = str(form_locale or "").strip().lower()
    if locale and locale not in supported:
        raise LookupError(f"Unsupported questionnaire locale: {locale}")
    resolved_locale = locale or None
    existing = await find_active_questionnaire_invite_for_lead(
        db,
        tenant_id=str(tenant_id),
        lead_id=str(lead.id),
    )
    now = _now()
    expires_at = now + timedelta(days=QUESTIONNAIRE_INVITE_TTL_DAYS)

    if force_new and existing is not None:
        existing.expires_at = now
        existing.updated_at = now
        existing = None

    if existing is not None:
        invite = existing
        if mark_sent:
            if invite.status == INVITE_STATUS_NOT_SENT:
                invite.status = INVITE_STATUS_SENT
                invite.sent_at = now
            invite.updated_at = now
            _apply_questionnaire_lifecycle(lead, invite.status, form_locale=resolved_locale)
        if resolved_locale:
            meta = _record(invite.meta)
            meta["form_locale"] = resolved_locale
            invite.meta = meta
            invite.apply_url = _apply_url_for_token(invite.token, form_locale=resolved_locale)
        elif not invite.apply_url:
            invite.apply_url = _apply_url_for_token(invite.token, form_locale=resolved_locale)
        await db.flush()
        return invite

    if not mark_sent and not create_if_missing:
        raise LookupError("No questionnaire invite exists for this lead")

    token = _generate_token()
    intake_state = _initial_intake_state(lead=lead, lead_form=lead_form)
    entity_profile_code = (
        str(getattr(intake_profile, "entity_profile_code", None) or "").strip()
        or TARGETED_ADVERTISING_PROFILE_CODE
    )
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    presentation_code = (
        str(getattr(intake_profile, "presentation_code", None) or "").strip()
        or (build_tenant_form_presentation_code(
            entity_profile_code=entity_profile_code,
            public_slug=public_slug,
        ) if public_slug else "")
    )
    invite = LeadQuestionnaireInvite(
        tenant_id=str(tenant_id),
        lead_id=str(lead.id),
        lead_form_id=str(lead_form.id),
        token=token,
        status=INVITE_STATUS_SENT if mark_sent else INVITE_STATUS_NOT_SENT,
        entity_profile_code=entity_profile_code,
        presentation_code=presentation_code,
        apply_url=_apply_url_for_token(token, form_locale=resolved_locale),
        sent_at=now if mark_sent else None,
        expires_at=expires_at,
        meta={
            "intake_state": intake_state,
            "intake_source_profile_id": str(intake_profile.id),
            "questionnaire_kind": "targeted_advertising",
            **({"form_locale": resolved_locale} if resolved_locale else {}),
        },
    )
    db.add(invite)

    initial_status = INVITE_STATUS_SENT if mark_sent else INVITE_STATUS_NOT_SENT
    _apply_questionnaire_lifecycle(lead, initial_status, form_locale=resolved_locale)
    await db.flush()
    return invite


def questionnaire_invite_out_payload(invite: LeadQuestionnaireInvite) -> dict[str, Any]:
    lead_form_id = str(invite.lead_form_id or "").strip() or None
    meta = _record(invite.meta)
    return {
        "id": str(invite.id),
        "lead_id": str(invite.lead_id),
        "lead_form_id": lead_form_id,
        "token": invite.token,
        "apply_url": invite.apply_url or _apply_url_for_token(
            invite.token,
            form_locale=str(meta.get("form_locale") or "").strip() or None,
        ),
        "status": invite.status,
        "entity_profile_code": invite.entity_profile_code,
        "presentation_code": invite.presentation_code,
        "form_locale": meta.get("form_locale"),
        "sent_at": invite.sent_at,
        "opened_at": invite.opened_at,
        "submitted_at": invite.submitted_at,
        "expires_at": invite.expires_at,
    }


def _sync_lead_questionnaire_status(lead: Lead, status: str) -> None:
    normalized = _record(lead.normalized)
    normalized["sales_questionnaire_status"] = status
    lead.normalized = normalized


def _apply_questionnaire_lifecycle(lead: Lead, questionnaire_status: str, *, form_locale: str | None = None) -> None:
    """Keep invite status, CRM stage, and application list status in sync."""
    _sync_lead_questionnaire_status(lead, questionnaire_status)
    locale = str(form_locale or "").strip().lower()[:2]
    if locale:
        normalized = _record(lead.normalized)
        normalized["sales_questionnaire_locale"] = locale
        lead.normalized = normalized
    if questionnaire_status in QUESTIONNAIRE_WAITING_STATUSES:
        lead.stage = LEAD_STAGE_WAITING_FOR_RESPONSE
    elif questionnaire_status == INVITE_STATUS_SUBMITTED:
        lead.stage = LEAD_STAGE_QUESTIONNAIRE_SUBMITTED


async def mark_invite_opened(
    db: AsyncSession,
    *,
    invite: LeadQuestionnaireInvite,
    lead: Lead,
) -> None:
    if invite.status == INVITE_STATUS_SUBMITTED:
        return
    now = _now()
    if invite.opened_at is None:
        invite.opened_at = now
    if invite.status in {INVITE_STATUS_NOT_SENT, INVITE_STATUS_SENT}:
        invite.status = INVITE_STATUS_OPENED
    invite.updated_at = now
    locale = str(_record(invite.meta).get("form_locale") or "").strip() or None
    _apply_questionnaire_lifecycle(lead, INVITE_STATUS_OPENED, form_locale=locale)
    await db.flush()


async def mark_invite_in_progress(
    db: AsyncSession,
    *,
    invite: LeadQuestionnaireInvite,
    lead: Lead,
) -> None:
    if invite.status == INVITE_STATUS_SUBMITTED:
        return
    now = _now()
    if invite.status != INVITE_STATUS_IN_PROGRESS:
        invite.status = INVITE_STATUS_IN_PROGRESS
    invite.updated_at = now
    locale = str(_record(invite.meta).get("form_locale") or "").strip() or None
    _apply_questionnaire_lifecycle(lead, INVITE_STATUS_IN_PROGRESS, form_locale=locale)
    await db.flush()


def merge_presentation_into_sales_summary(
    lead: Lead,
    intake_state: dict[str, Any],
    *,
    submitted: bool = False,
) -> dict[str, Any]:
    """Map presentation values into lead.normalized sales summary + CRM contact blocks."""
    field_codes = [
        f"{SALES_QUESTIONNAIRE_PREFIX}{suffix}"
        for suffix in (
            "need_type",
            "primary_outcome",
            "recruitment_roles",
            "recruitment_other_role",
            "recruitment_headcount",
            "work_location_country",
            "work_location_city",
            "application_channel",
            "job_posting_ready",
            "recruitment_materials",
            "promotion_subject",
            "industry",
            "target_audience_description",
            "qualified_lead_definition",
            "client_geo_scope",
            "client_geo_detail",
            "conversion_destination",
            "offer_ready",
            "marketing_materials",
            "prior_ads_experience",
            "monthly_ad_budget",
            "start_timeline",
            "decision_maker",
            "contact_full_name",
            "contact_company_name",
            "contact_phone",
            "contact_email",
            "contact_website",
            "additional_notes",
        )
    ]
    values = presentation_values_dict_from_state(intake_state, field_codes)
    sales_questionnaire: dict[str, Any] = {}
    for qualified_code, raw in values.items():
        key = _qualified_to_sales_key(qualified_code)
        if key and raw not in (None, "", [], {}):
            sales_questionnaire[key] = raw

    normalized = _record(lead.normalized)
    if sales_questionnaire:
        normalized["sales_questionnaire"] = sales_questionnaire

    full_name = (
        _trim(sales_questionnaire.get("contact_full_name"))
        or _trim(normalized.get("full_name"))
        or _trim(_record(intake_state.get("personal")).get("full_name"))
    )
    company_name = (
        _trim(sales_questionnaire.get("contact_company_name"))
        or _trim(normalized.get("company_name"))
        or _trim(_record(intake_state.get("client_company")).get("name"))
    )
    contacts_block = _record(intake_state.get("contacts"))
    email = _trim(sales_questionnaire.get("contact_email")) or _trim(normalized.get("email")) or _trim(contacts_block.get("email"))
    phone = _trim(sales_questionnaire.get("contact_phone")) or _trim(normalized.get("phone")) or _trim(contacts_block.get("phone"))
    website = _trim(sales_questionnaire.get("contact_website"))

    if full_name:
        normalized["full_name"] = full_name
    if company_name:
        normalized["company_name"] = company_name
    if email:
        normalized["email"] = email
    if phone:
        normalized["phone"] = phone

    contact_person = {
        k: v
        for k, v in {
            "full_name": full_name,
            "email": email,
            "phone": phone,
        }.items()
        if v
    }
    if contact_person:
        normalized["contact_person"] = {
            **_record(normalized.get("contact_person")),
            **contact_person,
        }

    company_profile = {
        k: v
        for k, v in {
            "name": company_name,
            "website": website,
        }.items()
        if v
    }
    if company_profile:
        normalized["company_profile"] = {
            **_record(normalized.get("company_profile")),
            **company_profile,
        }

    need = _record(normalized.get("need"))
    need_summary_parts = [
        str(sales_questionnaire.get("need_type") or "").replace("_", " ").strip(),
        str(sales_questionnaire.get("primary_outcome") or "").replace("_", " ").strip(),
    ]
    need_summary = " — ".join(p for p in need_summary_parts if p)
    if need_summary:
        need["summary"] = need_summary
        need["questionnaire"] = sales_questionnaire
        normalized["need"] = need

    next_status = (
        INVITE_STATUS_SUBMITTED if submitted else normalized.get("sales_questionnaire_status") or INVITE_STATUS_IN_PROGRESS
    )
    normalized["entity_profile_code"] = TARGETED_ADVERTISING_PROFILE_CODE
    lead.normalized = normalized
    _apply_questionnaire_lifecycle(lead, str(next_status))
    normalized = _record(lead.normalized)
    normalized["entity_profile_code"] = TARGETED_ADVERTISING_PROFILE_CODE
    lead.normalized = normalized

    payload = _record(lead.payload)
    payload["sales_questionnaire"] = sales_questionnaire
    payload["questionnaire_intake_state"] = dict(intake_state)
    lead.payload = payload
    return normalized


async def _questionnaire_submit_notification_exists(
    db: AsyncSession,
    *,
    tenant_id: str,
    invite_id: str,
) -> bool:
    from backend.app.models.user_notification import UserNotification

    rows = (
        await db.execute(
            select(UserNotification)
            .where(
                UserNotification.tenant_id == str(tenant_id),
                UserNotification.event_type == "intake.questionnaire.submitted",
            )
            .order_by(UserNotification.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    for row in rows:
        payload = _record(row.payload)
        if str(payload.get("invite_id") or "") == str(invite_id):
            return True
    return False


async def _notify_questionnaire_submitted(
    db: AsyncSession,
    *,
    invite: LeadQuestionnaireInvite,
    lead: Lead,
    intake_state: dict[str, Any],
) -> None:
    from backend.app.constants import spa_paths
    from backend.app.models.user import Role, User
    from backend.app.modules.leads import pipeline_hooks
    from backend.app.services.audit import log_activity
    from backend.app.services.events import EventAudience, emit_event

    tenant_id = str(lead.tenant_id)
    invite_id = str(invite.id)
    if await _questionnaire_submit_notification_exists(db, tenant_id=tenant_id, invite_id=invite_id):
        return

    normalized = _record(lead.normalized)
    contact_name = (
        _trim(normalized.get("full_name"))
        or _trim(_record(normalized.get("contact_person")).get("full_name"))
        or "Контакт"
    )
    company_name = (
        _trim(_record(normalized.get("company_profile")).get("name"))
        or _trim(normalized.get("company_name"))
        or "Компания"
    )
    summary_line = f"{contact_name} — {company_name}"
    submitted_at = invite.submitted_at.isoformat() if invite.submitted_at else _now().isoformat()
    dedupe_key = f"intake.questionnaire.submitted:{invite_id}"

    assignee = await pipeline_hooks._lead_reminder_assignee_id(
        db,
        tenant_id=tenant_id,
        lead_id=str(lead.id),
    )
    if not assignee:
        row = await db.execute(
            select(User.id)
            .where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                User.role.in_(["administrator", "employee", "superadmin"]),
            )
            .order_by(User.created_at.asc())
            .limit(1)
        )
        assignee = row.scalar_one_or_none()

    payload = {
        "title": "Клиент заполнил анкету",
        "description": summary_line,
        "body": summary_line,
        "contact_name": contact_name,
        "company_name": company_name,
        "tenant_id": tenant_id,
        "lead_id": str(lead.id),
        "invite_id": invite_id,
        "submission_id": f"questionnaire-invite-submit:{invite.token}",
        "form_id": str(invite.lead_form_id) if invite.lead_form_id else None,
        "responsible_user_id": assignee,
        "submitted_at": submitted_at,
        "href": spa_paths.spa_lead(str(lead.id)),
        "dedupe_key": dedupe_key,
    }

    audience = (
        EventAudience(user_ids=[assignee])
        if assignee
        else EventAudience(roles=(Role.employee, Role.administrator))
    )
    try:
        await emit_event(
            db,
            tenant_id=tenant_id,
            event_type="intake.questionnaire.submitted",
            payload=payload,
            audience=audience,
            entity_type="lead",
            entity_id=str(lead.id),
            channel="in_app",
        )
    except Exception:
        from backend.app.models.user_notification import UserNotification
        from uuid import uuid4

        recipient_ids: list[str] = []
        if assignee:
            recipient_ids = [assignee]
        else:
            rows = await db.execute(
                select(User.id).where(
                    User.tenant_id == tenant_id,
                    User.is_active.is_(True),
                    User.role.in_(["administrator", "employee", "superadmin"]),
                )
            )
            recipient_ids = [str(uid) for uid in rows.scalars().all() if uid]
        for user_id in recipient_ids:
            db.add(
                UserNotification(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    event_type="intake.questionnaire.submitted",
                    payload=payload,
                    entity_type="lead",
                    entity_id=str(lead.id),
                    channel="in_app",
                )
            )
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="lead.questionnaire_submitted",
        target_type="lead",
        target_id=str(lead.id),
        payload={
            "invite_id": invite_id,
            "contact_name": contact_name,
            "company_name": company_name,
            "submitted_at": submitted_at,
            "form_id": payload["form_id"],
            "responsible_user_id": assignee,
        },
    )


async def mark_invite_submitted(
    db: AsyncSession,
    *,
    invite: LeadQuestionnaireInvite,
    lead: Lead,
    intake_state: dict[str, Any],
) -> None:
    now = _now()
    invite.status = INVITE_STATUS_SUBMITTED
    invite.submitted_at = now
    invite.updated_at = now
    write_invite_intake_state(invite, intake_state)
    merge_presentation_into_sales_summary(lead, intake_state, submitted=True)

    lead_form: TenantLeadForm | None = None
    if invite.lead_form_id:
        lead_form = await db.get(TenantLeadForm, str(invite.lead_form_id))
    effective = resolve_effective_policy_for_invite(
        form=lead_form,
        invite=invite,
        entity_profile_code=str(invite.entity_profile_code or TARGETED_ADVERTISING_PROFILE_CODE),
    )
    agreements = _record(intake_state.get("agreements"))
    presentation_values = intake_state.get("presentation_values")
    if not isinstance(presentation_values, dict):
        presentation_values = intake_state.get("presentation_values_v1")
    normalized_values = dict(presentation_values) if isinstance(presentation_values, dict) else {}
    await append_submission(
        db,
        tenant_id=str(lead.tenant_id),
        lead_id=str(lead.id),
        effective_policy=effective,
        normalized_values=normalized_values,
        presentation_code=str(invite.presentation_code or ""),
        consent_metadata={"consents": agreements},
        entry_context={
            "entry": "questionnaire_invite",
            "form_locale": str(_record(invite.meta).get("form_locale") or "").strip() or None,
        },
        idempotency_key=f"questionnaire-invite-submit:{invite.token}",
    )

    submit_locale = str(_record(invite.meta).get("form_locale") or "").strip() or None
    _apply_questionnaire_lifecycle(lead, INVITE_STATUS_SUBMITTED, form_locale=submit_locale)
    lead.status = "new"
    await _notify_questionnaire_submitted(
        db,
        invite=invite,
        lead=lead,
        intake_state=intake_state,
    )
    await db.flush()
