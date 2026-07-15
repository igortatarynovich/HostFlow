from __future__ import annotations

import secrets
import mimetypes
import os
import copy
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Sequence
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Form, Request, Response, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, ValidationError, field_validator, model_validator
from sqlalchemy import delete, select, func, literal, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants import spa_paths
from backend.app.core.rate_limit import enforce_rate_limit, rate_limits
from backend.app.core.turnstile import require_turnstile
from backend.app.db.deps import bind_tenant_context_to_session, get_db
from backend.app.api.public.intake_tenant_bind import (
    public_intake_apply_session,
    public_intake_magic_link_redeem_session,
    public_intake_status_session,
    public_intake_storage_upload_session,
    resolve_intake_token_tenant_id,
    resolve_lead_form_tenant_and_id_by_form_id,
    resolve_lead_form_tenant_and_id_by_slug,
    resolve_tenant_uuid_for_public_intake_create,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.vacancy import Vacancy
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.candidate_consent import CandidateConsent
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.document import Document
from backend.app.models.magic_link import MagicLink
from backend.app.services.document_hub_delivery_contract import (
    build_synthetic_documents_via_contract,
    compute_candidate_checklist_via_contract,
    compute_owner_summary_via_contract,
    ensure_ruleset_seed_via_contract,
    get_uploads_root_via_contract,
    list_candidate_documents_via_contract,
    list_document_types_via_contract,
    list_equivalent_satisfaction_map_via_contract,
    sanitize_filename_via_contract,
)
from backend.app.services.document_orders import has_ready_document
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.document_catalog import (
    doc_type_requires_user_comment,
    get_doc_type_defaults,
)
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.services.document_files import resolve_document_file
from backend.app.security.document_events import emit_document_security_event_v1
from backend.app.security.event_taxonomy import (
    EVENT_DOCUMENT_FILE_DOWNLOADED,
    EVENT_DOCUMENT_SIGNED_URL_DENIED,
    EVENT_DOCUMENT_SIGNED_URL_GENERATED,
)
from backend.app.services.extractors import auto_fill_from_file
from backend.app.services import reminders as reminders_service
from backend.app.models.enums import DocumentStatus
from backend.app.services.activity import log_public_event
from backend.app.services.legal_documents import list_active_for_tenant
from backend.app.services.events import EventAudience, emit_event
from backend.app.models.user import Role
from backend.app.services.source_labels import normalize_candidate_source
from backend.app.services.tenant_quota import (
    ensure_active_records_quota,
    ensure_tenant_document_quota,
    ensure_tenant_storage_bytes_fits,
    sum_file_entries_bytes,
)
from backend.app.services.lead_forms_quota import (
    lead_form_meta_for_intake_state,
    list_active_lead_forms_with_public_slug,
    load_active_lead_form_for_public_intake,
)
from backend.app.services.candidate_telegram_notifications import (
    send_candidate_documents_progress_telegram,
    sync_candidate_ready_for_handoff_gate,
)
from backend.app.services.integration_inbound_normalization import (
    normalize_inbound_citizenship_alpha2,
    normalize_inbound_country_alpha2,
)


_UPLOADS_ROOT = Path(get_uploads_root_via_contract())

router = APIRouter(prefix="/public", tags=["public-intake"])

INTAKE_TOKEN_TTL_DAYS = 30
MAX_EMPLOYMENTS = 3
MAGIC_LINK_TTL_MINUTES = 60
MIN_MAGIC_LINK_INTERVAL_SECONDS = 120
MAX_MAGIC_LINKS_PER_DAY = 5
CONSENT_VERSION_DEFAULTS = {
    "privacy": "2025-02-01",
    "terms": "2025-02-01",
    "cookies": "2025-02-01",
}
logger = logging.getLogger(__name__)


def _coerce_intake_application_kind(value: Optional[str]) -> str:
    s = str(value or "candidate").strip().lower()
    return "client" if s == "client" else "candidate"


def _candidate_public_display_name(candidate: Candidate) -> str:
    full = " ".join(part for part in [candidate.first_name, candidate.last_name] if part).strip()
    state = _ensure_intake_state(candidate)
    personal = dict(state.get("personal") or {})
    from_intake = str(personal.get("full_name") or "").strip()
    if from_intake:
        return from_intake
    return full or candidate.first_name or candidate.last_name or candidate.id


async def _maybe_create_client_lead_from_public_intake(
    db: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
    *,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """When intake was started as **client**, create one CRM Lead row on submit (deduped by candidate id)."""
    state = _ensure_intake_state(candidate)
    if _coerce_intake_application_kind(str(state.get("application_kind"))) != "client":
        return

    from backend.app.modules.leads import crud as leads_crud

    external_id = f"public-intake:{candidate.id}"
    existing = await leads_crud.get_lead_by_external_id(
        db, tenant_id=tenant_id, source="public-intake", external_id=external_id
    )
    if existing is not None:
        return

    vac: Optional[Vacancy] = None
    if candidate.vacancy_id:
        vac = await db.get(Vacancy, str(candidate.vacancy_id))

    contacts = dict(state.get("contacts") or {})
    personal = dict(state.get("personal") or {})
    client_company = dict(state.get("client_company") or {})

    own_company_id: Optional[str] = None
    oc = getattr(candidate, "own_company_id", None)
    if oc:
        own_company_id = str(oc).strip() or None
    if not own_company_id and vac is not None and getattr(vac, "own_company_id", None):
        own_company_id = str(vac.own_company_id).strip() or None
    if not own_company_id:
        own_company_id = await _resolve_public_intake_own_company_id(db, tenant_id, state.get("lead_form"))
    if not own_company_id:
        logger.warning(
            "[public-intake] skip client Lead: no own_company_id (tenant=%s candidate=%s)",
            tenant_id,
            candidate.id,
        )
        await log_public_event(
            db,
            tenant_id=tenant_id,
            action="client_intake_no_owner_company_for_lead",
            target_id=candidate.id,
            payload={"candidate_id": candidate.id},
            ip=client_ip,
            ua=user_agent,
        )
        return

    full_name = str(personal.get("full_name") or "").strip()
    email = (candidate.email or contacts.get("email") or None)
    if email is not None:
        email = str(email).strip() or None
    phone = candidate.phone or contacts.get("phone")
    if phone is not None:
        phone = str(phone).strip() or None

    normalized: Dict[str, Any] = {
        "email": email,
        "phone": phone,
        "full_name": full_name or None,
        "company_name": str(client_company.get("name") or "").strip() or None,
        "intake_application_kind": "client",
        "source_candidate_id": candidate.id,
    }
    normalized = {k: v for k, v in normalized.items() if v}

    pl: Dict[str, Any] = {
        "intake": True,
        "candidate_id": candidate.id,
        "contacts": contacts,
        "personal": personal,
        "client_company": client_company,
    }
    try:
        lead = await leads_crud.create_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            company_id=None,
            vacancy_id=None,
            payload=pl,
            normalized=normalized or None,
            source="public-intake",
            ad_id=None,
            external_id=external_id,
            lead_type="client",
            lead_target_type="client_lead",
        )
    except Exception as exc:
        logger.warning(
            "[public-intake] client Lead create failed tenant=%s candidate=%s: %s",
            tenant_id,
            candidate.id,
            exc,
        )
        return

    lead.candidate_id = candidate.id
    lead.stage = "questionnaire_submitted"
    lead.status = "new"
    await db.flush()

    cname = _candidate_public_display_name(candidate)
    await emit_event(
        db,
        tenant_id=tenant_id,
        event_type="lead_public_intake_client",
        payload={
            "lead_id": str(lead.id),
            "candidate_id": candidate.id,
            "candidate_name": cname,
            "href": spa_paths.spa_lead(str(lead.id)),
        },
        audience=EventAudience(roles=(Role.manager, Role.recruiter)),
        entity_type="lead",
        entity_id=str(lead.id),
    )
    await log_public_event(
        db,
        tenant_id=tenant_id,
        action="client_lead_from_public_intake",
        target_id=str(lead.id),
        payload={"lead_id": str(lead.id), "candidate_id": candidate.id},
        ip=client_ip,
        ua=user_agent,
    )


async def _resolve_public_intake_vacancy_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_uuid: Optional[UUID],
) -> Optional[str]:
    """When the public UI sends vacancy_id, attach only if the vacancy belongs to the resolved tenant."""
    if vacancy_uuid is None:
        return None
    vid = str(vacancy_uuid)
    row = await db.get(Vacancy, vid)
    if row is None or str(row.tenant_id).strip() != str(tenant_id).strip():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "intake_vacancy_not_found",
                "message": "Vacancy not found in this workspace.",
            },
        )
    return vid


_email_str_adapter = TypeAdapter(EmailStr)


def _coerce_optional_email(value: Any) -> Optional[str]:
    """Avoid 500 when CRM/imports store non-RFC emails on the candidate row."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return str(_email_str_adapter.validate_python(s))
    except ValidationError:
        return None


def _coerce_iso3166_alpha2(value: Any) -> Optional[str]:
    """Normalize inbound country-like values to canonical ISO alpha-2."""
    return normalize_inbound_country_alpha2(value)


EU_COUNTRIES = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "IS",
    "NO",
    "LI",
    "CH",
}
_DEFAULT_RULESET = load_default_ruleset()
_DEFAULT_CANDIDATE_DEFAULTS = (
    (_DEFAULT_RULESET.get("candidate") or {}).get("defaults") or {}
)


class IntakeContacts(BaseModel):
    phone_country_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_messenger: Optional[str] = None

    def has_contact(self) -> bool:
        return bool((self.phone_country_code and self.phone) or self.email)


class IntakePersonal(BaseModel):
    full_name: Optional[str] = None
    citizenship: Optional[str] = Field(default=None, min_length=2, max_length=2)
    residency_status: Optional[str] = None
    in_poland: Optional[bool] = None
    birth_date: Optional[str] = None  # ISO date string 'YYYY-MM-DD'
    current_location: Optional[str] = None  # 'in_poland' | 'not_in_poland' | 'other'
    frigo_experience: Optional[bool] = None
    has_adr: Optional[bool] = None


class IntakeExperience(BaseModel):
    years_ce: Optional[int] = None
    intl_experience: Optional[bool] = None
    trailer_types: List[str] = Field(default_factory=list)
    route_types: List[str] = Field(default_factory=list)


class IntakeClientCompany(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    tax_id: Optional[str] = Field(default=None, max_length=64)
    website: Optional[str] = Field(default=None, max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=2)
    country: Optional[str] = Field(default=None, max_length=64)
    city: Optional[str] = Field(default=None, max_length=128)
    address: Optional[str] = Field(default=None, max_length=255)
    fleet_size: Optional[int] = Field(default=None, ge=0)
    transport_profile: Optional[str] = Field(default=None, max_length=128)

    @field_validator("country_code")
    @classmethod
    def _normalize_country_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None


class IntakeEmployment(BaseModel):
    id: Optional[str] = None
    employer_name: str
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    position: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    trailer_types: List[str] = Field(default_factory=list)
    route_types: List[str] = Field(default_factory=list)
    truck_brands: Optional[List[str]] = None
    eu_routes: Optional[bool] = None
    reason_for_leaving: Optional[str] = None
    reference_contact: Optional[str] = None

    @field_validator("employer_name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("employer_name must not be empty")
        return cleaned


class ConsentSelection(BaseModel):
    general: bool = False
    employer_share: bool = False
    terms_acceptance: bool = False

    def all_required(self) -> bool:
        return self.general and self.employer_share and self.terms_acceptance


class ConsentDocumentsVersion(BaseModel):
    privacy: str = Field(default=CONSENT_VERSION_DEFAULTS["privacy"], min_length=4, max_length=32)
    terms: str = Field(default=CONSENT_VERSION_DEFAULTS["terms"], min_length=4, max_length=32)
    cookies: str = Field(default=CONSENT_VERSION_DEFAULTS["cookies"], min_length=4, max_length=32)


class IntakeAgreements(BaseModel):
    general: bool = False
    employer_share: bool = False
    terms_acceptance: bool = False
    cookies_accepted: bool = False
    # legacy fields for backwards compatibility
    privacy: bool = False
    contact: bool = False


class IntakeData(BaseModel):
    contacts: IntakeContacts = Field(default_factory=IntakeContacts)
    personal: IntakePersonal = Field(default_factory=IntakePersonal)
    experience: IntakeExperience = Field(default_factory=IntakeExperience)
    employments: List[IntakeEmployment] = Field(default_factory=list)
    agreements: IntakeAgreements = Field(default_factory=IntakeAgreements)
    lead_form: Optional[Dict[str, Any]] = None
    client_company: Optional[IntakeClientCompany] = None
    presentation_values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="P7: values keyed by Field Registry qualified_code from form_presentation_runtime_v1.",
    )
    application_kind: Optional[Literal["candidate", "client"]] = Field(
        default=None,
        description="candidate (default): hiring intake only. client: B2B client inquiry — may create CRM Lead on submit when owner company is known.",
    )


class PublicIntakeCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "Start or resume a public candidate intake. "
                "Workspace (tenant) routing: send **lead_form_slug** or **lead_form_id** (globally resolves the form owner), "
                "or a non-demo **X-Tenant-Id** when using a tenant-default form without a published slug. "
                "Do not send both **lead_form_id** and **lead_form_slug**."
            ),
        }
    )

    contacts: IntakeContacts
    vacancy_id: Optional[UUID] = Field(
        default=None,
        description="Optional vacancy for this application link; must belong to the resolved workspace. Sets Candidate.vacancy_id (does not create a CRM Lead row).",
    )
    locale: Optional[str] = None
    source: Optional[str] = None
    lead_form_id: Optional[str] = Field(
        default=None,
        max_length=36,
        description="Active tenant lead form UUID; resolves the owning workspace without relying on X-Tenant-Id.",
    )
    lead_form_slug: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Globally unique published slug for an active form; resolves the owning workspace.",
    )
    application_kind: Optional[Literal["candidate", "client"]] = Field(
        default=None,
        description=(
            "Optional. **client** = B2B client application: same Candidate intake flow, but on successful **submit** "
            "the API may create a CRM **Lead** (`lead_type=client`, `source=public-intake`) when owner company can be "
            "resolved from the public entry point or tenant owner-company scope. "
            "Omit or **candidate** = hiring-only (no CRM Lead row)."
        ),
    )
    client_company: Optional[IntakeClientCompany] = Field(
        default=None,
        description="Optional B2B company data for application_kind=client. Stored on the client lead; does not create a Client/Company card.",
    )
    turnstile_token: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Cloudflare Turnstile token; required only when Turnstile is enabled server-side.",
    )


class PublicLeadFormListItem(BaseModel):
    id: str
    title: str
    public_slug: str


class PublicIntakeCreateResponse(BaseModel):
    apply_url: str
    token: str
    candidate_id: Optional[str] = None
    lead_id: Optional[str] = None
    expires_at: datetime


class PublicTimelineEntry(BaseModel):
    key: str
    title: str
    status: str
    description: Optional[str] = None
    completed_at: Optional[datetime] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class PublicIntakeState(BaseModel):
    token: str
    candidate_id: Optional[str] = None
    lead_id: Optional[str] = None
    status: str
    stage: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    data: IntakeData
    checklist: Dict[str, Any]
    documents: Dict[str, Any]
    timeline: List[PublicTimelineEntry] = Field(default_factory=list)
    status_share_token: Optional[str] = None
    form_presentation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="P7: form_presentation_runtime_v1 when intake source binds an Entity Profile presentation.",
    )


class PublicStatusState(BaseModel):
    candidate_id: Optional[str] = None
    lead_id: Optional[str] = None
    status: str
    stage: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    candidate_name: Optional[str] = None
    contacts: Optional[Dict[str, Any]] = None
    checklist: Dict[str, Any]
    documents: Dict[str, Any]
    timeline: List[PublicTimelineEntry] = Field(default_factory=list)


class PublicMagicLinkRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "Request a magic link for an existing draft candidate (same contact as stored). "
                "Tenant resolution order: **intake_token** (recommended on `/public/apply/...`) if present; "
                "else **lead_form_slug** or **lead_form_id**; else non-demo **X-Tenant-Id**. "
                "Do not send both **lead_form_id** and **lead_form_slug**. "
                "Response is always 200 with limits metadata; a link is created only if the contact matches a candidate in the resolved tenant."
            ),
        }
    )

    email: Optional[EmailStr] = Field(
        default=None,
        description="Candidate email; required unless **phone** (+ **phone_country_code**) is sent.",
    )
    phone_country_code: Optional[str] = Field(
        default=None,
        description="E.164-style country prefix (e.g. +48); use with **phone** when not using **email**.",
    )
    phone: Optional[str] = Field(
        default=None,
        description="National/significant number; use with **phone_country_code** when not using **email**.",
    )
    intake_token: Optional[str] = Field(
        default=None,
        max_length=128,
        description=(
            "Current public intake session token from `/public/apply/{token}`. "
            "When set, the workspace is derived from this token so **X-Tenant-Id** can be wrong or absent."
        ),
    )
    lead_form_id: Optional[str] = Field(
        default=None,
        max_length=36,
        description="Same as **POST /public/intake** — resolve tenant from this active form id (no **intake_token**).",
    )
    lead_form_slug: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Same as **POST /public/intake** — resolve tenant from this globally unique published slug.",
    )

    @model_validator(mode="after")
    def _ensure_contact(cls, data: "PublicMagicLinkRequest") -> "PublicMagicLinkRequest":
        if not (data.email or data.phone):
            raise ValueError("email or phone is required")
        return data


class PublicMagicLinkRequestResponse(BaseModel):
    status: str = Field(
        default="ok",
        description="Always `ok` when the request is accepted (including when no candidate matched — no email is sent in this API).",
    )
    cooldown_seconds: int = Field(
        default=MIN_MAGIC_LINK_INTERVAL_SECONDS,
        description="Minimum seconds between magic-link requests for the same contact in the same tenant.",
    )
    daily_limit: int = Field(
        default=MAX_MAGIC_LINKS_PER_DAY,
        description="Maximum magic-link requests per contact per rolling day in the same tenant.",
    )


class PublicMagicLinkRedeemResponse(BaseModel):
    token: str
    apply_url: str
    status_share_token: Optional[str] = None
    expires_at: datetime
    candidate_id: Optional[str] = None
    lead_id: Optional[str] = None
    cooldown_seconds: int = MIN_MAGIC_LINK_INTERVAL_SECONDS
    daily_limit: int = MAX_MAGIC_LINKS_PER_DAY


class PublicStatusRotateResponse(BaseModel):
    status_share_token: str
    expires_at: datetime


class PublicIntakeUpdateRequest(BaseModel):
    data: IntakeData


class PublicIntakeSubmitRequest(BaseModel):
    consents: ConsentSelection
    documents_version: ConsentDocumentsVersion = Field(default_factory=ConsentDocumentsVersion)
    cookies_accepted: bool = False

    def has_all_required(self) -> bool:
        return self.cookies_accepted and self.consents.all_required()


class PublicPresignRequest(BaseModel):
    doc_type: str
    filename: str


class PublicStatusDocumentsAccessRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_country_code: Optional[str] = None
    phone: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_contact(cls, data: "PublicStatusDocumentsAccessRequest") -> "PublicStatusDocumentsAccessRequest":
        if not (data.email or data.phone):
            raise ValueError("email or phone is required")
        return data


class PublicStatusDocumentsAccessResponse(BaseModel):
    verified: bool = True
    upload_url: str
    questionnaire_url: str
    expires_at: datetime


class PublicStatusPresignRequest(PublicPresignRequest):
    email: Optional[EmailStr] = None
    phone_country_code: Optional[str] = None
    phone: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_contact(cls, data: "PublicStatusPresignRequest") -> "PublicStatusPresignRequest":
        if not (data.email or data.phone):
            raise ValueError("email or phone is required")
        return data


class PublicPresignResponse(BaseModel):
    key: str
    url: str
    method: str
    headers: Dict[str, str] = Field(default_factory=dict)
    fields: Dict[str, str] = Field(default_factory=dict)


class CompanyIntakeCompany(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    tax_id: Optional[str] = Field(default=None, max_length=64)
    country: Optional[str] = Field(default=None, max_length=64)
    country_code: Optional[str] = Field(default=None, max_length=2)
    city: Optional[str] = Field(default=None, max_length=128)
    address: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    fleet_size: Optional[int] = Field(default=None, ge=0)
    transport_type: Optional[Literal["international", "domestic", "mixed"]] = None

    @field_validator("name")
    @classmethod
    def _trim_required_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("company name is required")
        return cleaned

    @field_validator("country_code")
    @classmethod
    def _normalize_company_country_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None


class CompanyIntakeContact(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(default=None, max_length=128)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=64)
    whatsapp: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def _trim_required_contact_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("contact full_name is required")
        return cleaned

    @model_validator(mode="after")
    def _require_contact_channel(self) -> "CompanyIntakeContact":
        if not (self.email or (self.phone or "").strip()):
            raise ValueError("contact email or phone is required")
        return self


class CompanyIntakeNeed(BaseModel):
    what_needed: Optional[str] = Field(default=None, max_length=255)
    people_count: Optional[int] = Field(default=None, ge=0)
    needed_when: Optional[str] = Field(default=None, max_length=64)
    cooperation_type: Optional[str] = Field(default=None, max_length=128)
    candidate_countries: List[str] = Field(default_factory=list)
    requirements: Optional[str] = Field(default=None, max_length=2000)


class CompanyIntakeTerms(BaseModel):
    rate: Optional[str] = Field(default=None, max_length=128)
    rate_amount: Optional[str] = Field(default=None, max_length=64)
    rate_currency: Optional[str] = Field(default=None, max_length=8)
    rate_period: Optional[str] = Field(default=None, max_length=32)
    rate_tax_mode: Optional[str] = Field(default=None, max_length=32)
    bonus: Optional[str] = Field(default=None, max_length=1000)
    schedule: Optional[str] = Field(default=None, max_length=128)
    work_systems: List[str] = Field(default_factory=list)
    night_driving: Optional[str] = Field(default=None, max_length=32)
    route_directions: List[str] = Field(default_factory=list)
    cargo_types: List[str] = Field(default_factory=list)
    body_types: List[str] = Field(default_factory=list)
    work_conditions: List[str] = Field(default_factory=list)
    base_location: Optional[str] = Field(default=None, max_length=255)
    truck_brands: List[str] = Field(default_factory=list)
    body_type: Optional[str] = Field(default=None, max_length=128)
    additional: Optional[str] = Field(default=None, max_length=2000)


class CompanyIntakeConsent(BaseModel):
    terms_accepted: bool
    privacy_accepted: bool
    data_processing_accepted: bool
    accuracy_confirmed: bool
    marketing_contact_accepted: bool = False
    terms_version: Optional[str] = Field(default=None, max_length=64)
    privacy_version: Optional[str] = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _mandatory_consents(self) -> "CompanyIntakeConsent":
        if not (
            self.terms_accepted
            and self.privacy_accepted
            and self.data_processing_accepted
            and self.accuracy_confirmed
        ):
            raise ValueError("mandatory consents are required")
        return self


class CompanyIntakeSubmitRequest(BaseModel):
    company: CompanyIntakeCompany
    contact: CompanyIntakeContact
    need: CompanyIntakeNeed = Field(default_factory=CompanyIntakeNeed)
    terms: CompanyIntakeTerms = Field(default_factory=CompanyIntakeTerms)
    consent: CompanyIntakeConsent
    source: Optional[str] = Field(default=None, max_length=32)
    service_intent: Optional[str] = Field(default=None, max_length=128)
    language: Optional[str] = Field(default=None, max_length=8)
    source_context: Optional[Dict[str, Any]] = None
    turnstile_token: Optional[str] = Field(default=None, max_length=2048)


class CompanyIntakeSubmitResponse(BaseModel):
    lead_id: str
    status: str = "new"
    stage: str = "questionnaire_submitted"
    own_company_id: str
    company_id: Optional[str] = None
    duplicate: bool = False
    lead_url: str


class CompanyIntakePublicConfigResponse(BaseModel):
    default_language: str = "pl"
    supported_languages: List[str] = Field(default_factory=lambda: ["pl", "en", "ru"])
    source: str = "company_intake_form"
    source_profile: Optional[Dict[str, Any]] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_token() -> str:
    return secrets.token_urlsafe(24)


def _full_name_parts(full_name: Optional[str]) -> Tuple[str, str]:
    if not full_name:
        return ("Candidate", "Draft")
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return ("Candidate", "Draft")
    if len(parts) == 1:
        return (parts[0], parts[0])
    return (parts[0], " ".join(parts[1:]))


def _auto_residency_status(citizenship: Optional[str], provided: Optional[str]) -> Optional[str]:
    if citizen := (citizenship or "").upper():
        if citizen in EU_COUNTRIES:
            return "eu_citizen"
    return provided


async def _load_candidate_for_storage_upload(
    session: AsyncSession,
    tenant_id: UUID,
    token: str,
) -> Candidate:
    """Resolve candidate for PUT /uploads/{token}/… (intake or status share token)."""
    stmt_intake = (
        select(Candidate)
        .where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.intake_token == token,
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    c = await session.scalar(stmt_intake)
    if c is not None:
        if c.intake_token_expires_at and c.intake_token_expires_at < _now():
            raise HTTPException(status_code=410, detail="Intake link expired")
        return c
    return await _load_candidate_by_status_token(session, tenant_id, token)


async def _load_public_intake_session(
    session: AsyncSession,
    tenant_id: UUID,
    token: str,
):
    from backend.app.entity_profile.public_intake_draft_session import resolve_public_intake_session

    return await resolve_public_intake_session(
        session,
        tenant_id=str(tenant_id),
        token=token,
        legacy_loader=_load_candidate_by_token,
    )


async def _build_checklist_and_docs_for_session(
    session: AsyncSession,
    tenant_id: UUID,
    public_session,
    *,
    download_scope: str = "apply",
    download_token: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if public_session.kind == "legacy_candidate" and public_session.candidate is not None:
        return await _build_checklist_and_docs(
            session,
            tenant_id,
            public_session.candidate,
            download_scope=download_scope,
            download_token=download_token,
        )
    from backend.app.entity_profile.public_intake_draft_session import session_intake_state

    state = session_intake_state(public_session)
    owner_id = public_session.lead_id or "draft"
    owner_context = _owner_context_from_state(state, owner_id)
    ruleset_version = await ensure_ruleset_seed_via_contract(
        session,
        tenant_id=str(tenant_id),
        ruleset_payload=load_default_ruleset(),
        own_company_id=None,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    checklist = compute_candidate_checklist_via_contract(owner_context, ruleset_payload)
    checklist = _ensure_checklist_defaults(checklist, ruleset_payload)
    pending = []
    if public_session.lead is not None:
        from backend.app.entity_profile.public_intake_draft_session import get_public_intake_draft_block

        pending = list(get_public_intake_draft_block(public_session.lead).get("pending_documents") or [])
    serialized_docs: List[Dict[str, Any]] = []
    token_for_download = download_token if download_token is not None else public_session.token
    for entry in pending:
        if not isinstance(entry, dict):
            continue
        doc_type = str(entry.get("doc_type") or "").strip()
        if not doc_type:
            continue
        download_url = None
        if entry.get("has_files") and token_for_download:
            download_url = f"/api/v1/public/apply/{token_for_download}/documents/{entry.get('id')}/file"
        serialized_docs.append(
            {
                "id": entry.get("id"),
                "type": doc_type,
                "doc_type": doc_type,
                "status": entry.get("status") or "submitted",
                "has_files": bool(entry.get("has_files")),
                "download_url": download_url,
            }
        )
    summary = compute_owner_summary_via_contract(owner_context, ruleset_payload, serialized_docs)
    synthetic = [
        entry.model_dump()
        for entry in build_synthetic_documents_via_contract(
            str(tenant_id), UUID(owner_id), checklist, serialized_docs
        )
    ]
    doc_entries = serialized_docs + synthetic
    doc_type_codes = _collect_doc_type_codes(checklist, doc_entries)
    if not doc_type_codes:
        catalog = await list_document_types_via_contract(session, tenant_id=str(tenant_id))
        doc_type_codes = [getattr(row, "code", None) or getattr(row, "key", None) or "" for row in catalog]
        doc_type_codes = [code for code in doc_type_codes if code]
    documents_payload = {
        "summary": summary,
        "documents": doc_entries,
        "doc_types": _serialize_doc_types(doc_type_codes),
    }
    return checklist, documents_payload


def _intake_data_from_state_dict(state: Dict[str, Any]) -> IntakeData:
    lf_raw = state.get("lead_form")
    lf = lf_raw if isinstance(lf_raw, dict) else None
    ak = _coerce_intake_application_kind(str(state.get("application_kind")))
    contacts_raw = dict(state.get("contacts") or {})
    personal_raw = dict(state.get("personal") or {})
    experience_raw = dict(state.get("experience") or {})
    agreements_raw = dict(state.get("agreements") or {})
    employments_raw = list(state.get("employments") or [])
    employments: List[IntakeEmployment] = []
    for row in employments_raw[:MAX_EMPLOYMENTS]:
        if isinstance(row, IntakeEmployment):
            employments.append(row)
        elif isinstance(row, dict):
            try:
                employments.append(IntakeEmployment(**row))
            except Exception:
                continue
    client_company = None
    if isinstance(state.get("client_company"), dict):
        client_company = IntakeClientCompany(**state["client_company"])
    pv_raw = state.get("presentation_values_v1")
    presentation_values = dict(pv_raw) if isinstance(pv_raw, dict) else None
    return IntakeData(
        contacts=IntakeContacts(**contacts_raw) if contacts_raw else IntakeContacts(),
        personal=IntakePersonal(**personal_raw) if personal_raw else IntakePersonal(),
        experience=IntakeExperience(**experience_raw) if experience_raw else IntakeExperience(),
        employments=employments,
        agreements=IntakeAgreements(**agreements_raw) if agreements_raw else IntakeAgreements(),
        lead_form=lf,
        client_company=client_company,
        presentation_values=presentation_values,
        application_kind=ak,
    )


async def _response_payload_from_session(
    db: AsyncSession,
    tenant_id: UUID,
    public_session,
    checklist: Dict[str, Any],
    documents: Dict[str, Any],
) -> PublicIntakeState:
    from backend.app.entity_profile.public_intake_draft_session import (
        session_created_at,
        session_expires_at,
        session_intake_state,
        session_intake_status,
        session_status_share_token,
        session_submitted_at,
    )

    if public_session.kind == "legacy_candidate" and public_session.candidate is not None:
        employments = await _list_employments(db, tenant_id, public_session.candidate.id)
        return _response_payload(public_session.candidate, employments, checklist, documents)

    state = session_intake_state(public_session)
    data_payload = _intake_data_from_state_dict(state)
    timeline = _build_timeline_entries_for_draft(public_session, data_payload, checklist, documents)
    from backend.app.entity_profile.public_intake_presentation_bridge import (
        presentation_values_dict_from_state,
        resolve_public_session_form_presentation,
    )

    form_presentation = await resolve_public_session_form_presentation(
        db,
        tenant_id=str(tenant_id),
        intake_state=state,
    )
    if form_presentation:
        field_codes = [
            str(f.get("qualified_code") or "")
            for f in (form_presentation.get("fields") or [])
            if isinstance(f, dict)
        ]
        merged_pv = presentation_values_dict_from_state(state, field_codes)
        if merged_pv:
            data_payload = data_payload.model_copy(update={"presentation_values": merged_pv})
    return PublicIntakeState(
        token=public_session.token,
        candidate_id=public_session.candidate_id,
        lead_id=public_session.lead_id,
        status=session_intake_status(public_session),
        stage=getattr(public_session.lead, "stage", None) if public_session.lead else None,
        created_at=session_created_at(public_session),
        expires_at=session_expires_at(public_session),
        submitted_at=session_submitted_at(public_session),
        data=data_payload,
        checklist=checklist,
        documents=documents,
        timeline=timeline,
        status_share_token=session_status_share_token(public_session),
        form_presentation=form_presentation,
    )


def _build_timeline_entries_for_draft(
    public_session,
    data: IntakeData,
    checklist: Dict[str, Any],
    documents_payload: Dict[str, Any],
) -> List[PublicTimelineEntry]:
    from backend.app.entity_profile.public_intake_draft_session import session_created_at, session_submitted_at

    created_at = session_created_at(public_session)
    submitted_at = session_submitted_at(public_session)
    required_types: List[str] = list(checklist.get("requiredTypes") or [])
    doc_entries = documents_payload.get("documents") or []
    entries_by_type: Dict[str, Dict[str, Any]] = {}
    for entry in doc_entries:
        doc_type = str(entry.get("doc_type") or entry.get("type") or "").strip()
        if doc_type:
            entries_by_type.setdefault(doc_type, entry)
    ready_required = sum(1 for code in required_types if entries_by_type.get(code, {}).get("has_files"))
    items = [
        {
            "key": "intake_created",
            "title": "Application started",
            "done": bool(created_at),
            "completed_at": created_at,
        },
        {
            "key": "submitted",
            "title": "Application submitted",
            "done": bool(submitted_at),
            "completed_at": submitted_at,
        },
    ]
    timeline: List[PublicTimelineEntry] = []
    pending_locked = False
    for item in items:
        status = "done" if item["done"] else "pending"
        if status != "done" and not pending_locked:
            status = "current"
            pending_locked = True
        timeline.append(
            PublicTimelineEntry(
                key=item["key"],
                title=item["title"],
                status=status,
                completed_at=item.get("completed_at"),
            )
        )
    return timeline


async def _load_candidate_by_token(
    session: AsyncSession,
    tenant_id: UUID,
    token: str,
) -> Candidate:
    stmt = (
        select(Candidate)
        .where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.intake_token == token,
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    candidate = await session.scalar(stmt)
    if not candidate:
        raise HTTPException(status_code=404, detail="Invalid intake token")
    if candidate.intake_token_expires_at and candidate.intake_token_expires_at < _now():
        raise HTTPException(status_code=410, detail="Intake link expired")
    return candidate


async def _load_candidate_by_id(
    session: AsyncSession,
    tenant_id: UUID,
    candidate_id: str,
) -> Candidate:
    stmt = (
        select(Candidate)
        .where(
            Candidate.id == str(candidate_id),
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    candidate = await session.scalar(stmt)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


async def _load_candidate_by_status_token(
    session: AsyncSession,
    tenant_id: UUID,
    share_token: str,
) -> Candidate:
    stmt = (
        select(Candidate)
        .where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.status_share_token == share_token,
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    candidate = await session.scalar(stmt)
    if not candidate:
        raise HTTPException(status_code=404, detail="Invalid status token")
    expires_at = getattr(candidate, "status_share_token_expires_at", None)
    if expires_at and expires_at < _now():
        raise HTTPException(status_code=410, detail="Status link expired")
    return candidate


def _ensure_intake_state(candidate: Candidate) -> Dict[str, Any]:
    state = candidate.intake_state or {}
    if not isinstance(state, dict):
        state = {}
    candidate.intake_state = state
    return state


def _ensure_status_share_token(candidate: Candidate) -> bool:
    now = _now()
    expires_at = getattr(candidate, "status_share_token_expires_at", None)
    if candidate.status_share_token and expires_at and expires_at > now:
        return False
    candidate.status_share_token = _generate_token()
    candidate.status_share_token_created_at = now
    candidate.status_share_token_expires_at = now + timedelta(days=INTAKE_TOKEN_TTL_DAYS)
    return True


def _ensure_intake_token(candidate: Candidate) -> None:
    now = _now()
    if candidate.intake_token and candidate.intake_token_expires_at and candidate.intake_token_expires_at > now:
        return
    candidate.intake_token = _generate_token()
    candidate.intake_token_created_at = now
    candidate.intake_token_expires_at = now + timedelta(days=INTAKE_TOKEN_TTL_DAYS)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lower()


def _json_text(column, key: str):
    """
    Return a SQL expression extracting JSON text for key, supporting both PostgreSQL and SQLite.
    """
    try:
        expr = column[key]
    except Exception:
        return None
    attr = getattr(expr, "astext", None)
    if attr is not None:
        return attr
    as_string = getattr(expr, "as_string", None)
    if callable(as_string):
        return as_string()
    return expr


def _normalize_intake_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_intake_phone(value: Any) -> Optional[str]:
    text = _normalize_intake_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or text


async def _resolve_company_intake_form(
    db: AsyncSession,
    public_token: str,
) -> tuple[UUID, Optional[TenantLeadForm]]:
    token = public_token.strip()
    if not token:
        raise HTTPException(status_code=404, detail="Company intake form not found")
    if _looks_like_uuid(token):
        pair = await resolve_lead_form_tenant_and_id_by_form_id(db, token)
        if not pair:
            raise HTTPException(status_code=404, detail="Company intake form not found")
        tenant_uuid = UUID(pair[0])
        await bind_tenant_context_to_session(db, tenant_uuid)
        form = await load_active_lead_form_for_public_intake(
            db, pair[0], lead_form_id=pair[1], lead_form_slug=None
        )
        if form is None:
            raise HTTPException(status_code=404, detail="Company intake form not found")
        return tenant_uuid, form

    pair = await resolve_lead_form_tenant_and_id_by_slug(db, token)
    if not pair:
        raise HTTPException(status_code=404, detail="Company intake form not found")
    tenant_uuid = UUID(pair[0])
    await bind_tenant_context_to_session(db, tenant_uuid)
    form = await load_active_lead_form_for_public_intake(db, pair[0], lead_form_id=None, lead_form_slug=token)
    if form is None:
        raise HTTPException(status_code=404, detail="Company intake form not found")
    return tenant_uuid, form


async def _resolve_company_intake_source_profile(
    db: AsyncSession,
    public_token: str,
) -> tuple[UUID, IntakeSourceProfile]:
    token = public_token.strip()
    if not token:
        raise HTTPException(status_code=404, detail="Company intake source not found")

    token_filters = [IntakeSourceProfile.public_slug == token]
    if _looks_like_uuid(token):
        token_filters.append(IntakeSourceProfile.id == token)

    profile = await db.scalar(
        select(IntakeSourceProfile)
        .where(
            IntakeSourceProfile.is_active.is_(True),
            or_(*token_filters),
            or_(
                IntakeSourceProfile.form_type.is_(None),
                IntakeSourceProfile.form_type == "",
                IntakeSourceProfile.form_type == "company_intake",
            ),
        )
        .order_by(IntakeSourceProfile.created_at.asc())
        .limit(1)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Company intake source not found")
    tenant_uuid = UUID(str(profile.tenant_id))
    await bind_tenant_context_to_session(db, tenant_uuid)
    return tenant_uuid, profile


async def _resolve_company_intake_source(
    db: AsyncSession,
    public_token: str,
) -> tuple[UUID, Optional[TenantLeadForm], Optional[IntakeSourceProfile], bool]:
    try:
        tenant_uuid, profile = await _resolve_company_intake_source_profile(db, public_token)
        return tenant_uuid, None, profile, False
    except HTTPException as exc:
        if exc.status_code != 404:
            raise

    tenant_uuid, form = await _resolve_company_intake_form(db, public_token)
    return tenant_uuid, form, None, True


def _lead_form_reference_from_meta(raw: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(raw, dict):
        return None, None
    form_id = str(raw.get("id") or raw.get("form_id") or "").strip() or None
    slug = str(raw.get("public_slug") or raw.get("slug") or "").strip() or None
    return form_id, slug


async def _resolve_public_intake_own_company_id(
    db: AsyncSession,
    tenant_id: str,
    lead_form: Any,
) -> Optional[str]:
    form_id: Optional[str] = None
    public_slug: Optional[str] = None
    if isinstance(lead_form, TenantLeadForm):
        form_id = str(lead_form.id or "").strip() or None
        public_slug = str(lead_form.public_slug or "").strip() or None
    else:
        form_id, public_slug = _lead_form_reference_from_meta(lead_form)

    binding_probes = []
    if form_id:
        binding_probes.append(f"lead_form_id:{form_id}")
        binding_probes.append(form_id)
    if public_slug:
        binding_probes.append(f"public_slug:{public_slug}")
        binding_probes.append(public_slug)
    if binding_probes:
        row = await db.scalar(
            select(IntakeSourceProfile.own_company_id)
            .join(IntakeSourceBinding, IntakeSourceBinding.intake_source_profile_id == IntakeSourceProfile.id)
            .where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.is_active.is_(True),
                IntakeSourceBinding.tenant_id == tenant_id,
                IntakeSourceBinding.provider == "public_intake",
                IntakeSourceBinding.is_active.is_(True),
                IntakeSourceBinding.external_key.in_(binding_probes),
            )
            .order_by(IntakeSourceBinding.priority.desc(), IntakeSourceProfile.created_at.asc())
            .limit(1)
        )
        if row:
            return str(row)

    profile_codes = []
    if form_id:
        profile_codes.append(f"public-form-{form_id}")
    if public_slug:
        profile_codes.append(f"public-form-{public_slug}")
    if profile_codes:
        row = await db.scalar(
            select(IntakeSourceProfile.own_company_id)
            .where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.is_active.is_(True),
                IntakeSourceProfile.provider == "public_intake",
                IntakeSourceProfile.code.in_(profile_codes),
            )
            .order_by(IntakeSourceProfile.created_at.asc())
            .limit(1)
        )
        if row:
            return str(row)

    row = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    return str(row) if row else None


async def _find_existing_company_for_company_intake(
    db: AsyncSession,
    *,
    tenant_id: str,
    tax_id: Optional[str],
    email: Optional[str],
    phone: Optional[str],
) -> Optional[Company]:
    conditions = [Company.tenant_id == tenant_id, Company.is_archived.is_(False)]
    probes = []
    if tax_id:
        probes.append(func.lower(Company.tax_id) == tax_id.lower())
    if email:
        contacts_email = _json_text(Company.contacts, "email")
        probes.append(func.lower(Company.email) == email.lower())
        if contacts_email is not None:
            probes.append(func.lower(contacts_email) == email.lower())
    phone_digits = _normalize_intake_phone(phone)
    if phone_digits:
        contacts_phone = _json_text(Company.contacts, "phone")
        probes.append(Company.phone == phone)
        if contacts_phone is not None:
            probes.append(contacts_phone == phone)
    if not probes:
        return None
    return await db.scalar(select(Company).where(*conditions, or_(*probes)).order_by(Company.created_at.asc()).limit(1))


async def _find_existing_company_intake_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    tax_id: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    company_name: Optional[str],
) -> Optional["Lead"]:
    from backend.app.models.lead import Lead

    probes = []
    norm = Lead.normalized
    if tax_id:
        company_tax_expr = _json_text(norm, "company_tax_id")
        if company_tax_expr is not None:
            probes.append(func.lower(company_tax_expr) == tax_id.lower())
    if email:
        email_expr = _json_text(norm, "contact_email")
        if email_expr is not None:
            probes.append(func.lower(email_expr) == email.lower())
    if phone:
        phone_expr = _json_text(norm, "contact_phone")
        if phone_expr is not None:
            probes.append(phone_expr == phone)
    if company_name and (tax_id or email or phone):
        company_name_expr = _json_text(norm, "company_name")
        if company_name_expr is not None:
            probes.append(func.lower(company_name_expr) == company_name.lower())
    if not probes:
        return None
    return await db.scalar(
        select(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.own_company_id == own_company_id,
            Lead.lead_type == "client",
            Lead.lead_target_type == "client_lead",
            Lead.stage.notin_(["converted", "lost"]),
            or_(*probes),
        )
        .order_by(Lead.created_at.desc())
        .limit(1)
    )


def _company_intake_source_profile_meta(profile: Optional[IntakeSourceProfile]) -> Optional[Dict[str, Any]]:
    if profile is None:
        return None
    return {
        k: v
        for k, v in {
            "id": str(profile.id),
            "code": profile.code,
            "name": profile.name,
            "public_slug": profile.public_slug,
            "form_type": profile.form_type,
            "lead_type": profile.lead_type,
            "lead_target_type": profile.lead_target_type,
            "source": profile.source,
            "default_language": profile.default_language,
            "supported_languages": profile.supported_languages,
            "default_assignee_id": profile.default_assignee_id,
        }.items()
        if v not in (None, "", [], {})
    }


def _company_intake_supported_languages(source_profile: Optional[IntakeSourceProfile]) -> List[str]:
    allowed = {"pl", "en", "ru"}
    raw = getattr(source_profile, "supported_languages", None) if source_profile is not None else None
    out: List[str] = []
    if isinstance(raw, list):
        for item in raw:
            value = str(item or "").strip().lower()
            if value in allowed and value not in out:
                out.append(value)
    elif isinstance(raw, str):
        for item in raw.split(","):
            value = str(item or "").strip().lower()
            if value in allowed and value not in out:
                out.append(value)
    return out or ["pl", "en", "ru"]


def _company_intake_default_language(source_profile: Optional[IntakeSourceProfile], supported: Sequence[str]) -> str:
    raw = str(getattr(source_profile, "default_language", "") or "").strip().lower()
    if raw in supported:
        return raw
    return str(supported[0] if supported else "pl")


def _company_intake_source(
    payload: CompanyIntakeSubmitRequest,
    source_profile: Optional[IntakeSourceProfile] = None,
) -> str:
    profile_source = str(getattr(source_profile, "source", "") or "").strip().lower()
    if profile_source:
        if profile_source in {"meta", "facebook", "instagram", "fb", "ig"}:
            return "meta_ads"
        if profile_source in {"company-intake-form"}:
            return "company_intake_form"
        return profile_source
    raw = (payload.source or "").strip().lower()
    if raw in {"meta", "facebook", "instagram"}:
        return "meta_ads"
    if raw in {"meta_ads", "website", "manual", "company_intake_form", "company-intake-form"}:
        return "company_intake_form" if raw == "company-intake-form" else raw
    ctx = payload.source_context if isinstance(payload.source_context, dict) else {}
    utm_source = str(ctx.get("utm_source") or "").strip().lower()
    if utm_source in {"meta", "facebook", "instagram", "fb", "ig"}:
        return "meta_ads"
    return "company_intake_form"


def _company_intake_payload(
    payload: CompanyIntakeSubmitRequest,
    form: Optional[TenantLeadForm],
    source_profile: Optional[IntakeSourceProfile] = None,
    *,
    consent_received_at: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "intake": True,
        "intake_flow": "client_company",
        "source": _company_intake_source(payload, source_profile),
        "source_profile": _company_intake_source_profile_meta(source_profile),
        "lead_form": lead_form_meta_for_intake_state(form) if form is not None else None,
        "company": payload.company.model_dump(mode="json", exclude_none=True),
        "contact": payload.contact.model_dump(mode="json", exclude_none=True),
        "need": payload.need.model_dump(mode="json", exclude_none=True),
        "terms": payload.terms.model_dump(mode="json", exclude_none=True),
        "consent": {
            **payload.consent.model_dump(mode="json", exclude_none=True),
            "received_at": consent_received_at,
            "ip": client_ip,
            "user_agent": user_agent,
        },
        "service_intent": payload.service_intent,
        "language": payload.language,
        "source_context": payload.source_context or {},
    }


def _company_intake_normalized(
    payload: CompanyIntakeSubmitRequest,
    source_profile: Optional[IntakeSourceProfile] = None,
    *,
    consent_received_at: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    company = payload.company
    contact = payload.contact
    need = payload.need
    terms = payload.terms
    source_context = payload.source_context if isinstance(payload.source_context, dict) else {}
    source = _company_intake_source(payload, source_profile)
    need_summary = " ".join(
        part
        for part in [
            str(need.people_count) if need.people_count is not None else "",
            need.what_needed or "",
        ]
        if str(part or "").strip()
    ).strip()
    company_profile = {
        "name": company.name,
        "legal_name": company.legal_name,
        "tax_id": company.tax_id,
        "country": company.country,
        "country_code": company.country_code,
        "city": company.city,
        "address": company.address,
        "website": company.website,
        "fleet_size": company.fleet_size,
        "transport_type": company.transport_type,
    }
    contact_person = {
        "full_name": contact.full_name,
        "role": contact.role,
        "email": str(contact.email) if contact.email else None,
        "phone": contact.phone,
        "whatsapp": contact.whatsapp,
    }
    need_block = {
        "summary": need_summary or None,
        "what_needed": need.what_needed,
        "people_count": need.people_count,
        "needed_when": need.needed_when,
        "cooperation_type": need.cooperation_type or payload.service_intent,
        "candidate_countries": need.candidate_countries,
        "requirements": need.requirements,
        "terms": {
            "rate": terms.rate,
            "rate_amount": terms.rate_amount,
            "rate_currency": terms.rate_currency,
            "rate_period": terms.rate_period,
            "rate_tax_mode": terms.rate_tax_mode,
            "bonus": terms.bonus,
            "schedule": terms.schedule,
            "work_systems": terms.work_systems,
            "night_driving": terms.night_driving,
            "route_directions": terms.route_directions,
            "cargo_types": terms.cargo_types,
            "body_types": terms.body_types,
            "work_conditions": terms.work_conditions,
            "base_location": terms.base_location,
            "truck_brands": terms.truck_brands,
            "body_type": terms.body_type,
            "additional": terms.additional,
        },
    }
    marketing = {
        "source": source,
        "campaign": source_context.get("campaign"),
        "utm_source": source_context.get("utm_source"),
        "utm_campaign": source_context.get("utm_campaign"),
        "utm_adset": source_context.get("utm_adset"),
        "utm_ad": source_context.get("utm_ad"),
        "fbclid": source_context.get("fbclid"),
        "landing_page": source_context.get("landing_page"),
        "referrer": source_context.get("referrer"),
    }
    meta = {
        "language": payload.language or getattr(source_profile, "default_language", None),
        "source_profile": _company_intake_source_profile_meta(source_profile),
        "assigned_manager_id": getattr(source_profile, "default_assignee_id", None),
        "submitted_flow": "company_intake",
        "form_id": source_context.get("form_id") or (str(source_profile.id) if source_profile is not None else None),
        "device": source_context.get("device"),
        "ip": client_ip,
        "user_agent": user_agent,
    }
    consent = {
        "rodo_consent": "received" if payload.consent.data_processing_accepted else None,
        "privacy_policy": "accepted" if payload.consent.privacy_accepted else None,
        "regulamin": "accepted" if payload.consent.terms_accepted else None,
        "accuracy_confirmed": bool(payload.consent.accuracy_confirmed),
        "marketing_contact_accepted": bool(payload.consent.marketing_contact_accepted),
        "consent_timestamp": consent_received_at,
        "terms_version": payload.consent.terms_version,
        "privacy_version": payload.consent.privacy_version,
        "language": payload.language or getattr(source_profile, "default_language", None),
        "source": source,
        "form_id": source_context.get("form_id") or (str(source_profile.id) if source_profile is not None else None),
        "ip": client_ip,
    }
    structured = {
        "company_profile": {k: v for k, v in company_profile.items() if v not in (None, "", [], {})},
        "contact_person": {k: v for k, v in contact_person.items() if v not in (None, "", [], {})},
        "need": {
            k: ({tk: tv for tk, tv in v.items() if tv not in (None, "", [], {})} if k == "terms" and isinstance(v, dict) else v)
            for k, v in need_block.items()
            if v not in (None, "", [], {})
        },
        "marketing": {k: v for k, v in marketing.items() if v not in (None, "", [], {})},
        "meta": {k: v for k, v in meta.items() if v not in (None, "", [], {})},
        "consent": {k: v for k, v in consent.items() if v not in (None, "", [], {})},
    }
    flat_aliases = {
        k: v
        for k, v in {
            "intake_flow": "client_company",
            "lead_type_label": "transport_company",
            "lead_source": source,
            "company_name": company.name,
            "company_legal_name": company.legal_name,
            "company_tax_id": company.tax_id,
            "company_country": company.country,
            "company_country_code": company.country_code,
            "company_city": company.city,
            "company_website": company.website,
            "fleet_size": company.fleet_size,
            "transport_type": company.transport_type,
            "contact_full_name": contact.full_name,
            "contact_role": contact.role,
            "contact_email": str(contact.email) if contact.email else None,
            "contact_phone": contact.phone,
            "contact_whatsapp": contact.whatsapp,
            "need_summary": need_summary or None,
            "need_people_count": need.people_count,
            "need_what": need.what_needed,
            "need_when": need.needed_when,
            "cooperation_type": need.cooperation_type or payload.service_intent,
            "candidate_countries": need.candidate_countries,
            "requirements": need.requirements,
            "rate": terms.rate,
            "rate_amount": terms.rate_amount,
            "rate_currency": terms.rate_currency,
            "rate_period": terms.rate_period,
            "rate_tax_mode": terms.rate_tax_mode,
            "bonus": terms.bonus,
            "schedule": terms.schedule,
            "work_systems": terms.work_systems,
            "night_driving": terms.night_driving,
            "route_directions": terms.route_directions,
            "cargo_types": terms.cargo_types,
            "body_types": terms.body_types,
            "work_conditions": terms.work_conditions,
            "base_location": terms.base_location,
            "truck_brands": terms.truck_brands,
            "body_type": terms.body_type,
            "additional_terms": terms.additional,
            "rodo_consent": consent["rodo_consent"],
            "privacy_policy": consent["privacy_policy"],
            "regulamin": consent["regulamin"],
            "consent_timestamp": consent_received_at,
            "utm_source": source_context.get("utm_source"),
            "campaign": source_context.get("campaign"),
            "utm_campaign": source_context.get("utm_campaign"),
            "utm_adset": source_context.get("utm_adset"),
            "utm_ad": source_context.get("utm_ad"),
            "fbclid": source_context.get("fbclid"),
            "landing_page": source_context.get("landing_page"),
            "referrer": source_context.get("referrer"),
        }.items()
        if v not in (None, "", [], {})
    }
    return {**structured, **flat_aliases}


@router.get("/company-intake/{public_token}/config", response_model=CompanyIntakePublicConfigResponse)
async def get_company_intake_config(
    public_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CompanyIntakePublicConfigResponse:
    await enforce_rate_limit(request, rate_limits().public_intake, scope="public:company_intake_config")
    _tenant_uuid, _form, source_profile, _legacy_lead_form_link = await _resolve_company_intake_source(db, public_token)
    supported = _company_intake_supported_languages(source_profile)
    default_language = _company_intake_default_language(source_profile, supported)
    return CompanyIntakePublicConfigResponse(
        default_language=default_language,
        supported_languages=supported,
        source=_company_intake_source(
            CompanyIntakeSubmitRequest(
                company=CompanyIntakeCompany(name="placeholder"),
                contact=CompanyIntakeContact(full_name="placeholder", email="placeholder@example.com"),
                consent=CompanyIntakeConsent(
                    terms_accepted=True,
                    privacy_accepted=True,
                    data_processing_accepted=True,
                    accuracy_confirmed=True,
                ),
            ),
            source_profile,
        ),
        source_profile=_company_intake_source_profile_meta(source_profile),
    )


@router.post("/company-intake/{public_token}/submit", response_model=CompanyIntakeSubmitResponse)
async def submit_company_intake(
    public_token: str,
    payload: CompanyIntakeSubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CompanyIntakeSubmitResponse:
    await enforce_rate_limit(request, rate_limits().public_intake, scope="public:company_intake")
    await require_turnstile(request, token=payload.turnstile_token)
    tenant_uuid, form, source_profile, legacy_lead_form_link = await _resolve_company_intake_source(db, public_token)
    tenant_id = str(tenant_uuid)
    own_company_id = str(source_profile.own_company_id) if source_profile is not None else None
    if not own_company_id:
        own_company_id = await _resolve_public_intake_own_company_id(db, tenant_id, form)
    if not own_company_id:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OWN_COMPANY_REQUIRED",
                "message": "Company intake form must be linked to an owner company before leads can be created.",
            },
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    consent_received_at = _now().isoformat()
    supported_languages = _company_intake_supported_languages(source_profile)
    default_language = _company_intake_default_language(source_profile, supported_languages)
    requested_language = str(payload.language or default_language).strip().lower()
    if requested_language not in supported_languages:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNSUPPORTED_INTAKE_LANGUAGE",
                "message": "Selected language is not enabled for this intake link.",
                "supported_languages": supported_languages,
            },
        )
    payload.language = requested_language
    normalized = _company_intake_normalized(
        payload,
        source_profile,
        consent_received_at=consent_received_at,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    if legacy_lead_form_link:
        normalized.setdefault("meta", {})
        if isinstance(normalized["meta"], dict):
            normalized["meta"]["legacy_link_source"] = "tenant_lead_form"
    company_name = _normalize_intake_text(normalized.get("company_name"))
    tax_id = _normalize_intake_text(normalized.get("company_tax_id"))
    contact_email = _normalize_intake_text(normalized.get("contact_email"))
    contact_phone = _normalize_intake_text(normalized.get("contact_phone"))

    existing_company = await _find_existing_company_for_company_intake(
        db,
        tenant_id=tenant_id,
        tax_id=tax_id,
        email=contact_email,
        phone=contact_phone,
    )
    if existing_company is not None:
        normalized["matched_existing_company_id"] = str(existing_company.id)
    existing_lead = await _find_existing_company_intake_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        tax_id=tax_id,
        email=contact_email,
        phone=contact_phone,
        company_name=company_name,
    )
    if existing_lead is not None:
        await log_public_event(
            db,
            tenant_id=tenant_id,
            action="company_intake_form_duplicate",
            target_id=str(existing_lead.id),
            payload={
                "lead_id": str(existing_lead.id),
                "own_company_id": own_company_id,
                "source_profile_id": str(source_profile.id) if source_profile is not None else None,
                "matched_existing_company_id": normalized.get("matched_existing_company_id"),
                "company_name": company_name,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
            },
            ip=client_ip,
            ua=user_agent,
        )
        await db.commit()
        return CompanyIntakeSubmitResponse(
            lead_id=str(existing_lead.id),
            status=existing_lead.status,
            stage=existing_lead.stage or "questionnaire_submitted",
            own_company_id=own_company_id,
            company_id=None,
            duplicate=True,
            lead_url=spa_paths.spa_lead(str(existing_lead.id)),
        )

    from backend.app.modules.leads import crud as leads_crud

    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload=_company_intake_payload(
            payload,
            form,
            source_profile,
            consent_received_at=consent_received_at,
            client_ip=client_ip,
            user_agent=user_agent,
        ),
        normalized=normalized,
        source=_company_intake_source(payload, source_profile),
        ad_id=None,
        external_id=None,
        lead_type="client",
        lead_target_type="client_lead",
    )
    lead.status = "new"
    lead.stage = "questionnaire_submitted"
    await db.flush()

    await emit_event(
        db,
        tenant_id=tenant_id,
        event_type="company_intake_submitted",
        payload={
            "lead_id": str(lead.id),
            "own_company_id": own_company_id,
            "source_profile_id": str(source_profile.id) if source_profile is not None else None,
            "matched_existing_company_id": normalized.get("matched_existing_company_id"),
            "company_name": company_name,
            "contact_name": normalized.get("contact_full_name"),
            "contact_phone": normalized.get("contact_phone"),
            "contact_email": normalized.get("contact_email"),
            "need_summary": normalized.get("need_summary"),
            "people_count": normalized.get("need_people_count"),
            "candidate_countries": normalized.get("candidate_countries"),
            "route_directions": normalized.get("route_directions"),
            "transport_type": normalized.get("transport_type"),
            "cargo_types": normalized.get("cargo_types"),
            "source": normalized.get("lead_source"),
            "campaign": normalized.get("campaign"),
            "utm_source": normalized.get("utm_source"),
            "utm_campaign": normalized.get("utm_campaign"),
            "language": payload.language,
            "href": spa_paths.spa_lead(str(lead.id)),
        },
        audience=EventAudience(roles=(Role.manager, Role.recruiter)),
        entity_type="lead",
        entity_id=str(lead.id),
    )
    await log_public_event(
        db,
        tenant_id=tenant_id,
        action="company_intake_form_submitted",
        target_id=str(lead.id),
        payload={
            "lead_id": str(lead.id),
            "own_company_id": own_company_id,
            "source_profile_id": str(source_profile.id) if source_profile is not None else None,
            "matched_existing_company_id": normalized.get("matched_existing_company_id"),
            "company_name": company_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "people_count": normalized.get("need_people_count"),
            "candidate_countries": normalized.get("candidate_countries"),
            "route_directions": normalized.get("route_directions"),
            "transport_type": normalized.get("transport_type"),
            "cargo_types": normalized.get("cargo_types"),
            "source": normalized.get("lead_source"),
            "campaign": normalized.get("campaign"),
            "utm_source": normalized.get("utm_source"),
            "utm_campaign": normalized.get("utm_campaign"),
            "language": payload.language,
        },
        ip=client_ip,
        ua=user_agent,
    )
    await db.commit()
    return CompanyIntakeSubmitResponse(
        lead_id=str(lead.id),
        status=lead.status,
        stage=lead.stage or "questionnaire_submitted",
        own_company_id=own_company_id,
        company_id=None,
        duplicate=False,
        lead_url=spa_paths.spa_lead(str(lead.id)),
    )


def _normalize_phone_parts(
    country_code: Optional[str],
    phone: Optional[str],
) -> Optional[tuple[Optional[str], str]]:
    number = (phone or "").strip()
    if not number:
        return None
    code = (country_code or "").strip()
    if code:
        code = code.lstrip("+")
        code = f"+{code}" if code else ""
    normalized_code = code or None
    return normalized_code, number


def _normalize_phone_digits(
    country_code: Optional[str],
    phone: Optional[str],
) -> Optional[str]:
    code_digits = ''.join(ch for ch in (country_code or '') if ch.isdigit())
    number_digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    combined = f"{code_digits}{number_digits}".strip()
    return combined or None


def _candidate_contact_matches(
    candidate: Candidate,
    *,
    email: Optional[str],
    phone_country_code: Optional[str],
    phone: Optional[str],
) -> bool:
    normalized_email = _normalize_email(email)
    normalized_phone_parts = _normalize_phone_parts(phone_country_code, phone)
    normalized_phone_digits = _normalize_phone_digits(phone_country_code, phone)

    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    candidate_email_values = {
        _normalize_email(getattr(candidate, "email", None)),
        _normalize_email(contacts.get("email") if isinstance(contacts, dict) else None),
    }
    candidate_email_values = {x for x in candidate_email_values if x}

    candidate_phone_variants: set[tuple[Optional[str], str]] = set()
    primary_phone = _normalize_phone_parts(getattr(candidate, "phone_country_code", None), getattr(candidate, "phone", None))
    if primary_phone:
        candidate_phone_variants.add(primary_phone)
    contacts_phone = _normalize_phone_parts(
        (contacts.get("phone_country_code") if isinstance(contacts, dict) else None),
        (contacts.get("phone") if isinstance(contacts, dict) else None),
    )
    if contacts_phone:
        candidate_phone_variants.add(contacts_phone)

    candidate_phone_digits = {
        _normalize_phone_digits(code, number)
        for code, number in candidate_phone_variants
    }
    candidate_phone_digits = {x for x in candidate_phone_digits if x}

    if normalized_email and normalized_email not in candidate_email_values:
        return False
    if normalized_phone_parts:
        _, normalized_number = normalized_phone_parts
        numbers = {number for _, number in candidate_phone_variants if number}
        if normalized_number not in numbers and (normalized_phone_digits not in candidate_phone_digits):
            return False
    return bool(normalized_email or normalized_phone_parts)


def _looks_like_uuid(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
    except Exception:
        return False
    return True

def _normalize_string_list(values: Optional[List[str]]) -> List[str]:
    if not values:
        return []
    normalized = []
    for item in values:
        if not item:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized

def _map_residency_status_to_poland_basis(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {'eu_citizen', 'eu', 'eea', 'ch'}:
        return 'eu_citizen'
    if normalized == 'visa_c':
        return 'visa_c'
    if normalized in {'visa_d', 'visa'}:
        return 'visa_d'
    if normalized in {'card', 'karta_pobytu', 'residence_card', 'residence_permit'}:
        return 'karta_pobytu'
    if normalized in {'none', 'other'}:
        return 'other'
    return None


async def _find_candidate_by_contact(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    email: Optional[str],
    phone_country_code: Optional[str],
    phone: Optional[str],
) -> Optional[Candidate]:
    """
    Находит существующего кандидата по контактам.
    Проверяет email ИЛИ телефон, но если указаны оба - проверяет оба одновременно для более точного поиска.
    """
    normalized_email = _normalize_email(email)
    contacts_email_column = _json_text(Candidate.contacts, "email")
    contacts_phone_column = _json_text(Candidate.contacts, "phone")
    contacts_phone_code_column = _json_text(Candidate.contacts, "phone_country_code")
    
    phone_parts = _normalize_phone_parts(phone_country_code, phone)
    
    # Если указаны и email, и телефон - проверяем оба одновременно для более точного поиска
    if normalized_email and phone_parts:
        normalized_code, normalized_phone = phone_parts
        email_conditions = [
            func.lower(Candidate.email) == normalized_email,
        ]
        if contacts_email_column is not None:
            email_conditions.append(func.lower(contacts_email_column) == normalized_email)
        
        phone_conditions = [Candidate.phone == normalized_phone]
        if contacts_phone_column is not None:
            phone_conditions.append(contacts_phone_column == normalized_phone)
        
        # Сначала проверяем точное совпадение: email И телефон
        combined_conditions = [
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
            or_(*email_conditions),
            or_(*phone_conditions),
        ]
        
        if normalized_code:
            code_conditions = [Candidate.phone_country_code == normalized_code]
            if contacts_phone_code_column is not None:
                code_conditions.append(contacts_phone_code_column == normalized_code)
            combined_conditions.append(or_(*code_conditions))
        
        stmt = select(Candidate).where(*combined_conditions).limit(1)
        candidate = await session.scalar(stmt)
        if candidate:
            return candidate
    
    # Если указан email - проверяем по email
    if normalized_email:
        email_conditions = [
            func.lower(Candidate.email) == normalized_email,
        ]
        if contacts_email_column is not None:
            email_conditions.append(func.lower(contacts_email_column) == normalized_email)
        stmt = (
            select(Candidate)
            .where(
                Candidate.tenant_id == str(tenant_id),
                Candidate.deleted_at.is_(None),
                or_(*email_conditions),
            )
            .limit(1)
        )
        candidate = await session.scalar(stmt)
        if candidate:
            return candidate

    # Если указан телефон - проверяем по телефону
    if phone_parts:
        normalized_code, normalized_phone = phone_parts
        phone_conditions = [Candidate.phone == normalized_phone]
        if contacts_phone_column is not None:
            phone_conditions.append(contacts_phone_column == normalized_phone)
        stmt = (
            select(Candidate)
            .where(
                Candidate.tenant_id == str(tenant_id),
                Candidate.deleted_at.is_(None),
                or_(*phone_conditions),
            )
            .limit(1)
        )
        if normalized_code:
            code_conditions = [Candidate.phone_country_code == normalized_code]
            if contacts_phone_code_column is not None:
                code_conditions.append(contacts_phone_code_column == normalized_code)
            stmt = stmt.where(or_(*code_conditions))
        else:
            blank_conditions = [
                Candidate.phone_country_code.is_(None),
                Candidate.phone_country_code == "",
            ]
            if contacts_phone_code_column is not None:
                blank_conditions.append(contacts_phone_code_column.is_(None))
                blank_conditions.append(contacts_phone_code_column == "")
            stmt = stmt.where(or_(*blank_conditions))
        candidate = await session.scalar(stmt)
        if candidate:
            return candidate
    phone_digits_with_code = _normalize_phone_digits(phone_country_code, phone)
    phone_digits_without_code = _normalize_phone_digits(None, phone)
    phone_digits_options = [value for value in {phone_digits_with_code, phone_digits_without_code} if value]
    if phone_digits_options:
        coalesce_code_args = [Candidate.phone_country_code]
        if contacts_phone_code_column is not None:
            coalesce_code_args.append(contacts_phone_code_column)
        coalesce_code_args.append(literal(""))
        combined_code_expr = func.coalesce(*coalesce_code_args)
        coalesce_phone_args = [Candidate.phone]
        if contacts_phone_column is not None:
            coalesce_phone_args.append(contacts_phone_column)
        coalesce_phone_args.append(literal(""))
        combined_phone_expr = func.coalesce(*coalesce_phone_args)

        normalized_column = func.regexp_replace(
            func.concat(
                combined_code_expr,
                combined_phone_expr,
            ),
            r"[^0-9]",
            "",
            "g",
        )
        stmt = (
            select(Candidate)
            .where(
                Candidate.tenant_id == str(tenant_id),
                Candidate.deleted_at.is_(None),
            )
            .limit(1)
        )
        if len(phone_digits_options) == 1:
            stmt = stmt.where(normalized_column == phone_digits_options[0])
        else:
            stmt = stmt.where(normalized_column.in_(phone_digits_options))
        candidate = await session.scalar(stmt)
        if candidate:
            return candidate
        # Фоллбэк: если в базе сохранён телефон вместе с кодом страны,
        # а в анкете ввели только локальный номер (или наоборот) — пробуем
        # матчить по окончанию цифр без учёта префикса.
        suffix_conditions = []
        for value in phone_digits_options:
            if not value or len(value) < 6:
                continue
            suffix_conditions.append(normalized_column.like(f"%{value}"))
        if suffix_conditions:
            suffix_stmt = (
                select(Candidate)
                .where(
                    Candidate.tenant_id == str(tenant_id),
                    Candidate.deleted_at.is_(None),
                    or_(*suffix_conditions),
                )
                .limit(1)
            )
            candidate = await session.scalar(suffix_stmt)
            if candidate:
                return candidate
    return None


def _contact_value(contact_type: str, *, email: Optional[str], phone: Optional[tuple[Optional[str], str]]) -> Optional[str]:
    if contact_type == "email" and email:
        return _normalize_email(email)
    if contact_type == "phone" and phone:
        code, number = phone
        return f"{code or ''}|{number}"
    return None


async def _create_magic_link(
    session: AsyncSession,
    tenant_id: UUID,
    candidate: Candidate,
    *,
    contact_type: str,
    contact_value: str,
) -> MagicLink:
    await _assert_magic_link_limits(session, tenant_id, contact_type, contact_value)
    token = _generate_token()
    # Clean up expired links for same contact
    await session.execute(
        delete(MagicLink).where(
            MagicLink.contact_value == contact_value,
            MagicLink.contact_type == contact_type,
            MagicLink.tenant_id == str(tenant_id),
            MagicLink.expires_at < _now(),
        )
    )
    link = MagicLink(
        tenant_id=str(tenant_id),
        candidate_id=candidate.id,
        token=token,
        contact_type=contact_type,
        contact_value=contact_value,
        expires_at=_now() + timedelta(minutes=MAGIC_LINK_TTL_MINUTES),
    )
    session.add(link)
    return link


async def _assert_magic_link_limits(
    session: AsyncSession,
    tenant_id: UUID,
    contact_type: str,
    contact_value: str,
) -> None:
    now = _now()
    recent_stmt = (
        select(MagicLink)
        .where(
            MagicLink.tenant_id == str(tenant_id),
            MagicLink.contact_type == contact_type,
            MagicLink.contact_value == contact_value,
        )
        .order_by(MagicLink.created_at.desc())
        .limit(1)
    )
    recent = await session.scalar(recent_stmt)
    if recent:
        recent_created = _as_aware(recent.created_at)
        if (now - recent_created).total_seconds() < MIN_MAGIC_LINK_INTERVAL_SECONDS:
            raise HTTPException(status_code=429, detail="Ссылка уже отправлена, попробуйте чуть позже")

    day_ago = now - timedelta(days=1)
    count_stmt = (
        select(func.count())
        .where(
            MagicLink.tenant_id == str(tenant_id),
            MagicLink.contact_type == contact_type,
            MagicLink.contact_value == contact_value,
            MagicLink.created_at >= day_ago,
        )
    )
    count = await session.scalar(count_stmt)
    if count and count >= MAX_MAGIC_LINKS_PER_DAY:
        raise HTTPException(status_code=429, detail="Превышен лимит запросов за сутки")


async def _load_magic_link(
    session: AsyncSession,
    tenant_id: UUID,
    token: str,
) -> MagicLink:
    stmt = (
        select(MagicLink)
        .where(
            MagicLink.tenant_id == str(tenant_id),
            MagicLink.token == token,
        )
        .limit(1)
    )
    link = await session.scalar(stmt)
    if not link:
        raise HTTPException(status_code=404, detail="Magic link not found")
    if link.expires_at < _now():
        raise HTTPException(status_code=410, detail="Magic link expired")
    return link


def _candidate_document_download_url(candidate_id: str, document_id: str) -> str:
    return f"/api/v1/candidates/{candidate_id}/documents/{document_id}/file"


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _next_version(files: Sequence[Dict[str, Any]]) -> int:
    versions = [int(entry.get("version") or 0) for entry in files if isinstance(entry, dict)]
    return max(versions, default=0) + 1


def _build_storage_key(candidate: Candidate, filename: str) -> str:
    sanitized = sanitize_filename_via_contract(filename) or "document.bin"
    return str(
        Path(candidate.tenant_id)
        / "candidates"
        / str(candidate.id)
        / f"{uuid4().hex}_{sanitized}"
    )


def _build_draft_storage_key(tenant_id: str, owner_id: str, filename: str) -> str:
    sanitized = sanitize_filename_via_contract(filename) or "document.bin"
    return str(Path(tenant_id) / "leads" / str(owner_id) / f"{uuid4().hex}_{sanitized}")


def _resolve_storage_path(relative: str) -> Path:
    rel = Path(relative.strip().lstrip("/\\"))
    uploads_root = _UPLOADS_ROOT.resolve()
    candidate = (uploads_root / rel).resolve()
    if uploads_root not in candidate.parents and candidate != uploads_root:
        raise HTTPException(status_code=400, detail="Invalid storage path")
    return candidate


def _normalize_user_comment(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    comment = value.strip()
    return comment or None


def _ensure_user_comment(doc_type: str, comment: Optional[str]) -> None:
    if doc_type_requires_user_comment(doc_type) and not comment:
        raise HTTPException(
            status_code=422,
            detail="user_comment required for doc_type 'additional_document'",
        )


def _owner_context_from_state(state: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
    personal = state.get("personal") or {}
    extra = state.get("extra") or {}
    raw_docs = extra.get("documents") if isinstance(extra.get("documents"), dict) else {}
    docs_ctx = {
        str(key): bool(value)
        for key, value in raw_docs.items()
        if isinstance(value, bool)
    }
    has_adr = personal.get("has_adr")
    if has_adr is None:
        has_adr = extra.get("has_adr")
    ctx = {
        "candidate_id": candidate_id,
        "citizenship": normalize_inbound_citizenship_alpha2(personal.get("citizenship")),
        "residency_status": extra.get("poland_stay_basis") or personal.get("residency_status") or None,
        "has_adr": has_adr if isinstance(has_adr, bool) else None,
        "documents": docs_ctx,
    }
    return {k: v for k, v in ctx.items() if v is not None}


async def _save_public_document_upload(
    session: AsyncSession,
    candidate: Candidate,
    doc_type_hint: str,
    *,
    upload_file: Optional[UploadFile],
    storage_key: Optional[str],
    user_comment: Optional[str] = None,
) -> Document:
    if not upload_file and not storage_key:
        raise HTTPException(status_code=422, detail="Either file or storage_key must be provided")

    if storage_key:
        target_path = _resolve_storage_path(storage_key)
        rel_path = storage_key
        original_name = os.path.basename(storage_key)
    else:
        uploads_root = _UPLOADS_ROOT
        rel_dir = Path(str(candidate.tenant_id)) / "candidates" / str(candidate.id)
        target_dir = uploads_root / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename_via_contract(upload_file.filename if upload_file else "document")
        stored_name = f"{uuid4().hex}_{safe_name}"
        target_path = target_dir / stored_name

        try:
            with target_path.open("wb") as fh:
                while True:
                    chunk = await upload_file.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
        finally:
            await upload_file.close()

        rel_path = target_path.relative_to(uploads_root).as_posix()
        original_name = upload_file.filename if upload_file and upload_file.filename else stored_name

    guessed = auto_fill_from_file(str(target_path), hinted_key=doc_type_hint)
    defaults = get_doc_type_defaults(guessed.get("key") or doc_type_hint)
    doc_type = defaults.doc_type
    kind = defaults.kind
    requested_from = defaults.requested_from
    process_type = defaults.process_type

    g_number = guessed.get("number")
    g_issued = guessed.get("issued_at")
    g_expires = guessed.get("expires_at")
    resolved_title = guessed.get("title") or (original_name or doc_type)
    custom_name = resolved_title if doc_type == "other" else None

    stmt = (
        select(Document)
        .where(
            Document.candidate_id == str(candidate.id),
            Document.tenant_id == str(candidate.tenant_id),
            Document.doc_type == doc_type,
            Document.deleted_at.is_(None),
        )
        .limit(1)
    )
    existing = await session.scalar(stmt)
    doc_id = existing.id if existing else str(uuid4())
    download_url = _candidate_document_download_url(str(candidate.id), doc_id)

    existing_meta_comment = None
    if existing and isinstance(existing.meta, dict):
        meta_comment = existing.meta.get("user_comment")
        if isinstance(meta_comment, str):
            existing_meta_comment = _normalize_user_comment(meta_comment)
    normalized_comment = _normalize_user_comment(user_comment)
    final_comment = normalized_comment if normalized_comment is not None else (
        getattr(existing, "user_comment", None) or existing_meta_comment
    )
    _ensure_user_comment(doc_type, final_comment)

    current_files: List[Dict[str, Any]] = []
    if existing and isinstance(existing.files, list):
        for entry in existing.files:
            if isinstance(entry, dict):
                current_files.append(dict(entry))

    next_version = _next_version(current_files)
    try:
        upload_size = int(os.path.getsize(target_path))
    except OSError:
        upload_size = 0
    primary_entry = {
        "name": original_name or os.path.basename(rel_path),
        "url": download_url,
        "uploaded_at": datetime.utcnow().isoformat(),
        "source": "public-upload",
        "storage_path": rel_path,
        "version": next_version,
        "size": upload_size,
        "mime": (
            upload_file.content_type
            if upload_file and upload_file.content_type
            else mimetypes.guess_type(original_name or os.path.basename(rel_path))[0]
        ),
    }
    if final_comment:
        primary_entry["user_comment"] = final_comment

    current_files = [entry for entry in current_files if isinstance(entry, dict)]
    current_files.append(primary_entry)

    tid = str(candidate.tenant_id)
    prev_doc_b = sum_file_entries_bytes(existing.files if existing else [])
    next_doc_b = sum_file_entries_bytes(current_files)
    if not existing:
        await ensure_tenant_document_quota(session, tid)
    await ensure_tenant_storage_bytes_fits(
        session,
        tid,
        previous_doc_attribution_bytes=prev_doc_b,
        next_doc_attribution_bytes=next_doc_b,
    )

    meta_payload: Dict[str, Any] = {
        "title": resolved_title,
        "number": g_number,
        "doc_type": doc_type,
        "files": {"primary": primary_entry},
        "source": "public-upload",
    }
    if final_comment:
        meta_payload["user_comment"] = final_comment

    issue_date = _parse_date(g_issued)
    expire_date = _parse_date(g_expires)

    if existing:
        doc = existing
        doc.custom_name = custom_name
        doc.kind = kind
        doc.requested_from = requested_from
        doc.process_type = process_type
        doc.number = g_number
        doc.filename = original_name
        doc.path = rel_path
        doc.issue_date = issue_date
        doc.expire_date = expire_date
        doc.status = DocumentStatus.submitted
        doc.files = current_files
        doc.meta = meta_payload
        doc.owner_type = "candidate"
        doc.owner_id = str(candidate.id)
        doc.user_comment = final_comment
        doc.updated_at = _now()
    else:
        doc = Document(
            id=doc_id,
            tenant_id=str(candidate.tenant_id),
            owner_type="candidate",
            owner_id=str(candidate.id),
            candidate_id=str(candidate.id),
            doc_type=doc_type,
            custom_name=custom_name,
            kind=kind,
            requested_from=requested_from,
            process_type=process_type,
            number=g_number,
            filename=original_name,
            path=rel_path,
            issue_date=issue_date,
            expire_date=expire_date,
            reminder_days_before=60,
            files=current_files,
            meta=meta_payload,
            status=DocumentStatus.submitted,
            user_comment=final_comment,
        )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    await reminders_service.schedule_document_expiry_reminders(
        session,
        tenant_id=str(candidate.tenant_id),
        document=doc,
    )
    await session.commit()
    return doc


async def _save_lead_draft_document_upload(
    session: AsyncSession,
    lead: Lead,
    doc_type_hint: str,
    *,
    upload_file: Optional[UploadFile],
    storage_key: Optional[str],
    user_comment: Optional[str] = None,
) -> dict[str, Any]:
    from backend.app.entity_profile.public_intake_draft_session import (
        get_public_intake_draft_block,
        set_public_intake_draft_block,
    )

    if not upload_file and not storage_key:
        raise HTTPException(status_code=422, detail="Either file or storage_key must be provided")

    defaults = get_doc_type_defaults(doc_type_hint)
    doc_type = defaults.doc_type
    normalized_comment = _normalize_user_comment(user_comment)
    _ensure_user_comment(doc_type, normalized_comment)

    if storage_key:
        target_path = _resolve_storage_path(storage_key)
        rel_path = storage_key.strip().lstrip("/\\")
        original_name = os.path.basename(rel_path)
    else:
        rel_dir = Path(str(lead.tenant_id)) / "leads" / str(lead.id)
        target_dir = _UPLOADS_ROOT / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename_via_contract(upload_file.filename if upload_file else "document")
        stored_name = f"{uuid4().hex}_{safe_name}"
        target_path = target_dir / stored_name

        try:
            with target_path.open("wb") as fh:
                while True:
                    chunk = await upload_file.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
        finally:
            await upload_file.close()

        rel_path = target_path.relative_to(_UPLOADS_ROOT).as_posix()
        original_name = upload_file.filename if upload_file and upload_file.filename else stored_name

    allowed_prefix = f"{lead.tenant_id}/leads/{lead.id}/"
    if not rel_path.startswith(allowed_prefix):
        raise HTTPException(status_code=403, detail="Storage key does not belong to draft session")

    block = get_public_intake_draft_block(lead)
    pending = [
        entry
        for entry in list(block.get("pending_documents") or [])
        if isinstance(entry, dict) and str(entry.get("doc_type") or "") != doc_type
    ]
    doc_id = str(uuid4())
    entry: dict[str, Any] = {
        "id": doc_id,
        "doc_type": doc_type,
        "status": "submitted",
        "has_files": True,
        "storage_path": rel_path,
        "filename": original_name,
        "uploaded_at": _now().isoformat(),
    }
    if normalized_comment:
        entry["user_comment"] = normalized_comment
    pending.append(entry)
    block["pending_documents"] = pending
    set_public_intake_draft_block(lead, block)
    await session.flush()
    return entry


def _storage_allowed_prefix_for_session(public_session, tenant_id: UUID) -> str:
    if public_session.kind == "lead_draft" and public_session.lead_id:
        return f"{tenant_id}/leads/{public_session.lead_id}/"
    if public_session.candidate is not None:
        candidate = public_session.candidate
        return f"{candidate.tenant_id}/candidates/{candidate.id}/"
    raise HTTPException(status_code=404, detail="Invalid intake token")


def _serialize_contacts(candidate: Candidate, state: Dict[str, Any]) -> IntakeContacts:
    contacts = dict(state.get("contacts") or {})
    data = IntakeContacts(
        phone_country_code=candidate.phone_country_code or contacts.get("phone_country_code"),
        phone=candidate.phone or contacts.get("phone"),
        email=_coerce_optional_email(candidate.email or contacts.get("email")),
        preferred_messenger=contacts.get("preferred_messenger"),
    )
    return data


def _serialize_personal(candidate: Candidate, state: Dict[str, Any]) -> IntakePersonal:
    personal_data = state.get("personal") or {}
    full_name = personal_data.get("full_name")
    if not full_name:
        full_name = f"{candidate.first_name} {candidate.last_name}".strip()
    # Также проверяем extra для обратной совместимости
    extra = candidate._get_extra()
    citizenship_raw = personal_data.get("citizenship") or extra.get("citizenship")
    return IntakePersonal(
        full_name=full_name.strip(),
        citizenship=normalize_inbound_citizenship_alpha2(citizenship_raw),
        residency_status=personal_data.get("residency_status"),
        in_poland=personal_data.get("in_poland") if personal_data.get("in_poland") is not None else extra.get("in_poland"),
        birth_date=personal_data.get("birth_date") or extra.get("birth_date"),
        current_location=personal_data.get("current_location") or extra.get("current_location"),
        frigo_experience=personal_data.get("frigo_experience") if personal_data.get("frigo_experience") is not None else extra.get("frigo_experience"),
        has_adr=personal_data.get("has_adr") if personal_data.get("has_adr") is not None else extra.get("has_adr"),
    )


def _serialize_experience(state: Dict[str, Any]) -> IntakeExperience:
    experience = state.get("experience") or {}
    return IntakeExperience(
        years_ce=experience.get("years_ce"),
        intl_experience=experience.get("intl_experience"),
        trailer_types=list(experience.get("trailer_types") or []),
        route_types=list(experience.get("route_types") or []),
    )


def _serialize_client_company(state: Dict[str, Any]) -> Optional[IntakeClientCompany]:
    payload = state.get("client_company")
    if not isinstance(payload, dict):
        return None
    return IntakeClientCompany(**payload)


def _serialize_employments(rows: List[CandidateEmployment]) -> List[IntakeEmployment]:
    serialized: List[IntakeEmployment] = []
    for row in rows[:MAX_EMPLOYMENTS]:
        serialized.append(
            IntakeEmployment(
                id=row.id,
                employer_name=row.employer_name,
                country=_coerce_iso3166_alpha2(row.country),
                position=row.position,
                start_date=row.start_date,
                end_date=row.end_date,
                trailer_types=list(row.trailer_types or []),
                route_types=list(row.route_types or []),
                truck_brands=list(row.truck_brands or []) if row.truck_brands else None,
                eu_routes=row.eu_routes,
                reason_for_leaving=row.reason_for_leaving,
                reference_contact=row.reference_contact,
            )
        )
    return serialized


def _employment_state_payload(entry: IntakeEmployment) -> Dict[str, Any]:
    """Convert employment entry to JSON-serializable payload (dates -> ISO strings)."""
    return {
        "id": entry.id,
        "employer_name": entry.employer_name,
        "country": entry.country,
        "position": entry.position,
        "start_date": entry.start_date.isoformat() if entry.start_date else None,
        "end_date": entry.end_date.isoformat() if entry.end_date else None,
        "trailer_types": list(entry.trailer_types or []),
        "route_types": list(entry.route_types or []),
        "truck_brands": entry.truck_brands,
        "eu_routes": entry.eu_routes,
        "reason_for_leaving": entry.reason_for_leaving,
        "reference_contact": entry.reference_contact,
    }


def _serialize_agreements(state: Dict[str, Any]) -> IntakeAgreements:
    agreements = state.get("agreements") or {}
    return IntakeAgreements(
        general=bool(agreements.get("general") or agreements.get("privacy")),
        employer_share=bool(agreements.get("employer_share") or agreements.get("contact")),
        terms_acceptance=bool(agreements.get("terms_acceptance")),
        cookies_accepted=bool(agreements.get("cookies_accepted")),
        privacy=bool(agreements.get("privacy")),
        contact=bool(agreements.get("contact")),
    )


def _consent_version_for_code(code: str, versions: ConsentDocumentsVersion) -> str:
    if code == "terms_acceptance":
        return versions.terms
    return versions.privacy


async def _log_consent_snapshot(
    session: AsyncSession,
    tenant_id: UUID,
    candidate_id: str,
    payload: PublicIntakeSubmitRequest,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> None:
    timestamp = _now()
    versions = payload.documents_version
    base_payload = {"documents_version": versions.model_dump(), "source": "public_form"}
    active_docs = await list_active_for_tenant(session, str(tenant_id))
    if active_docs.get("rodo_clause"):
        base_payload["rodo_version_id"] = active_docs["rodo_clause"].version_id
    if active_docs.get("privacy_policy"):
        base_payload["privacy_version_id"] = active_docs["privacy_policy"].version_id
    consent_map = payload.consents.model_dump()
    entries: List[CandidateConsent] = []

    for code, accepted in consent_map.items():
        entries.append(
            CandidateConsent(
                tenant_id=str(tenant_id),
                candidate_id=candidate_id,
                consent_code=code,
                text_version=_consent_version_for_code(code, versions),
                accepted=bool(accepted),
                ip_address=client_ip,
                user_agent=user_agent,
                payload=base_payload,
                accepted_at=timestamp,
            )
        )
    entries.append(
        CandidateConsent(
            tenant_id=str(tenant_id),
            candidate_id=candidate_id,
            consent_code="cookies",
            text_version=versions.cookies,
            accepted=payload.cookies_accepted,
            ip_address=client_ip,
            user_agent=user_agent,
            payload=base_payload,
            accepted_at=timestamp,
        )
    )
    session.add_all(entries)


async def _list_employments(session: AsyncSession, tenant_id: UUID, candidate_id: str) -> List[CandidateEmployment]:
    stmt = (
        select(CandidateEmployment)
        .where(
            CandidateEmployment.tenant_id == str(tenant_id),
            CandidateEmployment.candidate_id == candidate_id,
        )
        .order_by(CandidateEmployment.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _state_to_data(candidate: Candidate, employments: List[CandidateEmployment]) -> IntakeData:
    state = _ensure_intake_state(candidate)
    lf_raw = state.get("lead_form")
    lf = lf_raw if isinstance(lf_raw, dict) else None
    ak = _coerce_intake_application_kind(str(state.get("application_kind")))
    return IntakeData(
        contacts=_serialize_contacts(candidate, state),
        personal=_serialize_personal(candidate, state),
        experience=_serialize_experience(state),
        employments=_serialize_employments(employments),
        agreements=_serialize_agreements(state),
        lead_form=lf,
        client_company=_serialize_client_company(state),
        application_kind=ak,
    )


def _build_timeline_entries(
    candidate: Candidate,
    data: IntakeData,
    checklist: Dict[str, Any],
    documents_payload: Dict[str, Any],
) -> List[PublicTimelineEntry]:
    created_at = getattr(candidate, "intake_token_created_at", None)
    required_types: List[str] = list(checklist.get("requiredTypes") or [])
    required_total = len(required_types)
    doc_entries = documents_payload.get("documents") or []
    entries_by_type: Dict[str, Dict[str, Any]] = {}
    for entry in doc_entries:
        doc_type = str(entry.get("doc_type") or entry.get("type") or "").strip()
        if not doc_type:
            continue
        entries_by_type.setdefault(doc_type, entry)

    ready_required = 0
    missing_required: List[str] = []
    for code in required_types:
        payload = entries_by_type.get(code)
        if payload and payload.get("has_files"):
            ready_required += 1
        else:
            missing_required.append(code)
    summary_required = ((documents_payload.get("summary") or {}).get("required") or {})
    summary_ready = summary_required.get("ready")
    if isinstance(summary_ready, (int, float)):
        ready_required = int(summary_ready)
    summary_total = summary_required.get("total")
    if isinstance(summary_total, (int, float)):
        required_total = int(summary_total)
    summary_missing = summary_required.get("missing") or summary_required.get("missing_types")
    if isinstance(summary_missing, (list, tuple)):
        cleaned_missing: List[str] = []
        for entry in summary_missing:
            code = str(entry or "").strip()
            if code:
                cleaned_missing.append(code)
        if cleaned_missing:
            missing_required = cleaned_missing

    contacts = data.contacts
    contacts_ready = bool((contacts.phone_country_code and contacts.phone) or contacts.email)
    personal_ready = bool(data.personal.full_name or data.personal.citizenship)
    experience_ready = bool(data.experience.years_ce or data.experience.trailer_types or data.employments)
    profile_ready = contacts_ready and (personal_ready or experience_ready)
    documents_ready = required_total == 0 or ready_required >= required_total
    submitted_at = candidate.intake_submitted_at

    raw_entries = [
        {
            "key": "intake_created",
            "title": "Анкета создана",
            "done": bool(created_at),
            "completed_at": created_at,
            "description": "Черновик сохранён, можно вернуться по ссылке",
        },
        {
            "key": "profile_data",
            "title": "Данные заполнены",
            "done": profile_ready,
            "completed_at": created_at if profile_ready else None,
            "description": "Контакты и опыт заполнены",
        },
        {
            "key": "documents_upload",
            "title": "Документы загружены",
            "done": documents_ready,
            "completed_at": created_at if documents_ready else None,
            "description": "Обязательные документы готовы",
            "meta": {
                "ready_required": ready_required,
                "required_total": required_total,
                "missing_required": missing_required,
            },
        },
        {
            "key": "submitted",
            "title": "Анкета отправлена",
            "done": bool(submitted_at),
            "completed_at": submitted_at,
            "description": "Передана рекрутеру",
        },
    ]

    timeline: List[PublicTimelineEntry] = []
    pending_locked = False
    for item in raw_entries:
        status = "done" if item.get("done") else "pending"
        if status != "done":
            if not pending_locked:
                status = "current"
                pending_locked = True
            else:
                status = "pending"
        timeline.append(
            PublicTimelineEntry(
                key=item["key"],
                title=item["title"],
                status=status,
                description=item.get("description"),
                completed_at=item.get("completed_at"),
                meta=item.get("meta", {}),
            )
        )
    return timeline


def _build_state_components(
    candidate: Candidate,
    employments: List[CandidateEmployment],
    checklist: Dict[str, Any],
    documents: Dict[str, Any],
) -> Tuple[IntakeData, List[PublicTimelineEntry]]:
    data_payload = _state_to_data(candidate, employments)
    timeline = _build_timeline_entries(candidate, data_payload, checklist, documents)
    return data_payload, timeline


def _serialize_doc_types(codes: Sequence[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for code in codes:
        defaults = get_doc_type_defaults(code)
        doc_type = defaults.doc_type
        if doc_type in payload:
            continue
        payload[doc_type] = {
            "doc_type": doc_type,
            "title": copy.deepcopy(defaults.title),
            "i18n_key": defaults.i18n_key,
            "required_files": copy.deepcopy(defaults.required_files),
            "metadata_schema": copy.deepcopy(defaults.metadata_schema),
            "required_meta": list(defaults.required_meta),
            "kind": defaults.kind.value if hasattr(defaults.kind, "value") else str(defaults.kind),
            "requested_from": defaults.requested_from.value
            if hasattr(defaults.requested_from, "value")
            else str(defaults.requested_from),
            "process_type": defaults.process_type.value
            if hasattr(defaults.process_type, "value")
            else str(defaults.process_type),
            "orderable": defaults.orderable,
            "requires_custom_name": defaults.requires_custom_name,
            "duplicate_policy": defaults.duplicate_policy.value
            if hasattr(defaults.duplicate_policy, "value")
            else str(defaults.duplicate_policy),
            "expiry_rule": copy.deepcopy(defaults.expiry_rule),
        }
    return payload


def _collect_doc_type_codes(
    checklist: Dict[str, Any],
    documents: Sequence[Dict[str, Any]],
) -> List[str]:
    codes: List[str] = []
    seen: set[str] = set()
    for key in ("requiredTypes", "optionalTypes"):
        for entry in checklist.get(key) or []:
            doc_type = str(entry).strip()
            if doc_type and doc_type not in seen:
                seen.add(doc_type)
                codes.append(doc_type)
    for doc in documents:
        doc_type = str(doc.get("doc_type") or doc.get("type") or "").strip()
        if doc_type and doc_type not in seen:
            seen.add(doc_type)
            codes.append(doc_type)
    # добавляем эквивалентные типы (например, driver_license_code95), чтобы их можно было выбрать
    for equivalent, parents in (list_equivalent_satisfaction_map_via_contract() or {}).items():
        if not parents:
            continue
        normalized_parents = [str(parent).strip() for parent in parents if str(parent).strip()]
        if not normalized_parents:
            continue
        if equivalent in seen:
            continue
        if all(parent in seen for parent in normalized_parents):
            seen.add(equivalent)
            codes.append(equivalent)
    return codes


async def _build_checklist_and_docs(
    session: AsyncSession,
    tenant_id: UUID,
    candidate: Candidate,
    *,
    download_scope: str = "apply",
    download_token: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    state = _ensure_intake_state(candidate)
    oc = getattr(candidate, "own_company_id", None)
    own_company_id = str(oc).strip() if oc else None
    ruleset_version = await ensure_ruleset_seed_via_contract(
        session,
        tenant_id=str(tenant_id),
        ruleset_payload=load_default_ruleset(),
        own_company_id=own_company_id,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    owner_context = _owner_context_from_state(state, candidate.id)
    checklist = compute_candidate_checklist_via_contract(owner_context, ruleset_payload)
    checklist = _ensure_checklist_defaults(checklist, ruleset_payload)
    checklist = _ensure_checklist_defaults(checklist, ruleset_payload)

    docs = await list_candidate_documents_via_contract(
        session,
        tenant_id=str(tenant_id),
        candidate_id=candidate.id,
        include_deleted=False,
        active_own_company_id=own_company_id,
    )
    serialized_docs: List[Dict[str, Any]] = []
    for doc in docs:
        status_value = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
        has_files = bool(getattr(doc, "files", None) or getattr(doc, "path", None))
        download_url = None
        token_for_download = download_token if download_token is not None else candidate.intake_token
        if has_files and token_for_download:
            if download_scope == "status":
                download_url = f"/api/v1/public/status/{token_for_download}/documents/{doc.id}/file"
            else:
                download_url = f"/api/v1/public/apply/{token_for_download}/documents/{doc.id}/file"
        requested_from_value = (
            doc.requested_from.value
            if hasattr(doc, "requested_from") and hasattr(doc.requested_from, "value")
            else getattr(doc, "requested_from", None)
        )
        process_type_value = (
            doc.process_type.value
            if hasattr(doc, "process_type") and hasattr(doc.process_type, "value")
            else getattr(doc, "process_type", None)
        )
        serialized_docs.append(
            {
                "id": doc.id,
                "type": doc.doc_type,
                "doc_type": doc.doc_type,
                "status": status_value,
                "expires_at": getattr(doc, "expire_date", None),
                "has_files": has_files,
                "download_url": download_url,
                "requested_from": requested_from_value,
                "process_type": process_type_value,
                "ordered_at": getattr(doc, "ordered_at", None),
                "valid_from": getattr(doc, "valid_from", None),
                "user_comment": getattr(doc, "user_comment", None),
            }
        )
    summary = compute_owner_summary_via_contract(owner_context, ruleset_payload, serialized_docs)
    synthetic = [
        entry.model_dump()
        for entry in build_synthetic_documents_via_contract(
            str(tenant_id), UUID(candidate.id), checklist, serialized_docs
        )
    ]
    doc_entries = serialized_docs + synthetic
    doc_type_codes = _collect_doc_type_codes(checklist, doc_entries)
    if not doc_type_codes:
        catalog = await list_document_types_via_contract(session, tenant_id=str(tenant_id))
        doc_type_codes = [getattr(row, "code", None) or getattr(row, "key", None) or "" for row in catalog]
        doc_type_codes = [code for code in doc_type_codes if code]
    documents_payload = {
        "summary": summary,
        "documents": doc_entries,
        "doc_types": _serialize_doc_types(doc_type_codes),
    }
    return checklist, documents_payload


def _response_payload(
    candidate: Candidate,
    employments: List[CandidateEmployment],
    checklist: Dict[str, Any],
    documents: Dict[str, Any],
    *,
    lead_id: Optional[str] = None,
) -> PublicIntakeState:
    data_payload, timeline = _build_state_components(candidate, employments, checklist, documents)
    return PublicIntakeState(
        token=candidate.intake_token or "",
        candidate_id=candidate.id,
        lead_id=lead_id,
        status=candidate.intake_status or ("submitted" if candidate.intake_submitted_at else "draft"),
        stage=candidate.stage,
        created_at=getattr(candidate, "intake_token_created_at", None),
        expires_at=candidate.intake_token_expires_at,
        submitted_at=candidate.intake_submitted_at,
        data=data_payload,
        checklist=checklist,
        documents=documents,
        timeline=timeline,
        status_share_token=candidate.status_share_token,
    )


def _status_response_payload(
    candidate: Candidate,
    employments: List[CandidateEmployment],
    checklist: Dict[str, Any],
    documents: Dict[str, Any],
) -> PublicStatusState:
    data_payload, timeline = _build_state_components(candidate, employments, checklist, documents)
    name = " ".join(part for part in [candidate.first_name, candidate.last_name] if part).strip() or None
    return PublicStatusState(
        candidate_id=candidate.id,
        lead_id=None,
        status=candidate.intake_status or ("submitted" if candidate.intake_submitted_at else "draft"),
        stage=candidate.stage,
        created_at=getattr(candidate, "intake_token_created_at", None),
        expires_at=candidate.status_share_token_expires_at or candidate.intake_token_expires_at,
        submitted_at=candidate.intake_submitted_at,
        candidate_name=name,
        contacts=data_payload.contacts.model_dump(),
        checklist=checklist,
        documents=documents,
        timeline=timeline,
    )


def _status_response_payload_from_lead_session(
    public_session,
    checklist: Dict[str, Any],
    documents: Dict[str, Any],
) -> PublicStatusState:
    from backend.app.entity_profile.public_intake_draft_session import (
        get_public_intake_draft_block,
        session_created_at,
        session_expires_at,
        session_intake_state,
        session_intake_status,
        session_submitted_at,
    )

    state = session_intake_state(public_session)
    contacts_raw = dict(state.get("contacts") or {})
    personal = dict(state.get("personal") or {})
    name = str(personal.get("full_name") or "").strip() or None
    block = get_public_intake_draft_block(public_session.lead) if public_session.lead else {}
    expires_raw = block.get("intake_token_expires_at")
    expires_at = session_expires_at(public_session)
    if expires_raw and not expires_at:
        try:
            expires_at = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        except ValueError:
            expires_at = None
    data_payload = _intake_data_from_state_dict(state)
    timeline = _build_timeline_entries_for_draft(public_session, data_payload, checklist, documents)
    return PublicStatusState(
        candidate_id=None,
        lead_id=public_session.lead_id,
        status=session_intake_status(public_session),
        stage=getattr(public_session.lead, "stage", None) if public_session.lead else None,
        created_at=session_created_at(public_session),
        expires_at=expires_at,
        submitted_at=session_submitted_at(public_session),
        candidate_name=name,
        contacts=contacts_raw or None,
        checklist=checklist,
        documents=documents,
        timeline=timeline,
    )


async def _upsert_employments(
    session: AsyncSession,
    tenant_id: UUID,
    candidate_id: str,
    entries: List[IntakeEmployment],
) -> None:
    await session.execute(
        delete(CandidateEmployment).where(
            CandidateEmployment.tenant_id == str(tenant_id),
            CandidateEmployment.candidate_id == candidate_id,
        )
    )
    for entry in entries[:MAX_EMPLOYMENTS]:
        session.add(
            CandidateEmployment(
                id=entry.id or str(uuid4()),
                tenant_id=str(tenant_id),
                candidate_id=candidate_id,
                employer_name=entry.employer_name,
                country=entry.country,
                position=entry.position,
                start_date=entry.start_date,
                end_date=entry.end_date,
                trailer_types=entry.trailer_types,
                route_types=entry.route_types,
                truck_brands=entry.truck_brands,
                eu_routes=entry.eu_routes,
                reason_for_leaving=entry.reason_for_leaving,
                reference_contact=entry.reference_contact,
            )
        )


def _update_candidate_from_data(candidate: Candidate, payload: IntakeData) -> None:
    from backend.app.constants.catalog_utils import country_by_dial
    
    contacts = payload.contacts
    personal = payload.personal
    experience = payload.experience
    existing_state = _ensure_intake_state(candidate)
    existing_contacts = dict(existing_state.get("contacts") or {})
    existing_personal = dict(existing_state.get("personal") or {})
    existing_experience = dict(existing_state.get("experience") or {})
    existing_agreements = dict(existing_state.get("agreements") or {})
    existing_employments = list(existing_state.get("employments") or [])

    # Обновляем основные поля контактов
    if contacts.phone_country_code:
        candidate.phone_country_code = contacts.phone_country_code
    if contacts.phone:
        candidate.phone = contacts.phone
    if contacts.email:
        candidate.email = contacts.email

    # Сохраняем preferred_messenger в contacts для совместимости
    contacts_payload = candidate._get_contacts()
    contacts_payload.update(
        {
            "preferred_messenger": contacts.preferred_messenger,
        }
    )
    candidate._set_contacts(contacts_payload)

    # Обновляем имя
    if personal.full_name:
        first_name, last_name = _full_name_parts(personal.full_name)
        candidate.first_name = first_name or candidate.first_name
        candidate.last_name = last_name or candidate.last_name

    # Обновляем personal_data (для совместимости, но основное хранилище - extra)
    personal_dict = candidate._get_personal_data()
    if personal.citizenship:
        personal_dict["citizenship"] = normalize_inbound_citizenship_alpha2(personal.citizenship)
    if personal.in_poland is not None:
        personal_dict["in_poland"] = personal.in_poland
    if personal.birth_date:
        personal_dict["birth_date"] = personal.birth_date
    # Сохраняем current_location, frigo_experience, has_adr даже если они пустые строки или False
    if personal.current_location is not None:
        personal_dict["current_location"] = personal.current_location
    if personal.frigo_experience is not None:
        personal_dict["frigo_experience"] = personal.frigo_experience
    if personal.has_adr is not None:
        personal_dict["has_adr"] = personal.has_adr
    residency = _auto_residency_status(personal_dict.get("citizenship"), personal.residency_status)
    if residency:
        personal_dict["residency_status"] = residency
    merged_years_ce = experience.years_ce if experience.years_ce is not None else existing_experience.get("years_ce")
    merged_intl_experience = (
        experience.intl_experience
        if experience.intl_experience is not None
        else existing_experience.get("intl_experience")
    )
    merged_trailer_types = experience.trailer_types or existing_experience.get("trailer_types") or []
    merged_route_types = experience.route_types or existing_experience.get("route_types") or []
    personal_dict["experience"] = {
        "years_ce": merged_years_ce,
        "intl_experience": merged_intl_experience,
        "trailer_types": merged_trailer_types,
        "route_types": merged_route_types,
    }
    candidate._set_personal_data(personal_dict)

    state = _ensure_intake_state(candidate)
    state["contacts"] = {
        **existing_contacts,
        **{k: v for k, v in contacts.model_dump().items() if v not in (None, "", [], {})},
    }
    state["personal"] = {
        **existing_personal,
        **{k: v for k, v in personal.model_dump().items() if v not in (None, "", [], {})},
        "residency_status": residency or existing_personal.get("residency_status"),
    }
    state["experience"] = {
        **existing_experience,
        **{k: v for k, v in experience.model_dump().items() if v not in (None, "", [], {})},
        "years_ce": merged_years_ce,
        "intl_experience": merged_intl_experience,
        "trailer_types": merged_trailer_types,
        "route_types": merged_route_types,
    }
    merged_agreements = existing_agreements.copy()
    for key, val in payload.agreements.model_dump().items():
        # согласия прилипают: случайные автосохранения с False не затирают уже принятую отметку
        if val is True or key not in merged_agreements:
            merged_agreements[key] = val
    state["agreements"] = merged_agreements
    new_employments = [_employment_state_payload(entry) for entry in payload.employments]
    state["employments"] = new_employments or existing_employments
    if payload.lead_form is not None:
        state["lead_form"] = payload.lead_form
    elif existing_state.get("lead_form") is not None:
        state["lead_form"] = existing_state.get("lead_form")
    if payload.client_company is not None:
        state["client_company"] = {
            **dict(existing_state.get("client_company") or {}),
            **{k: v for k, v in payload.client_company.model_dump().items() if v not in (None, "", [], {})},
        }
    elif existing_state.get("client_company") is not None:
        state["client_company"] = existing_state.get("client_company")

    if payload.application_kind is not None:
        ak = str(payload.application_kind).strip().lower()
        state["application_kind"] = ak if ak in ("candidate", "client") else "candidate"
    elif existing_state.get("application_kind"):
        state["application_kind"] = existing_state["application_kind"]
    else:
        state["application_kind"] = "candidate"

    # Обновляем extra - основное хранилище для карточки кандидата
    extra = candidate._get_extra()
    
    # Маппинг phone_country_code в phone_country и phone_prefix
    if contacts.phone_country_code:
        dial_code = contacts.phone_country_code.strip()
        if not dial_code.startswith("+"):
            dial_code = f"+{dial_code}"
        # Находим страну по dial code
        countries = country_by_dial(dial_code)
        if countries:
            # Берем первую найденную страну (обычно одна)
            extra["phone_country"] = countries[0][0]
            extra["phone_prefix"] = dial_code
        else:
            # Если не нашли страну, сохраняем только префикс
            extra["phone_prefix"] = dial_code
    
    # Preferred contact
    if contacts.preferred_messenger:
        extra["preferred_contact"] = contacts.preferred_messenger
    
    # Personal data - сохраняем в extra (основное хранилище для карточки)
    if personal.citizenship:
        extra["citizenship"] = normalize_inbound_citizenship_alpha2(personal.citizenship)
    if personal.in_poland is not None:
        extra["in_poland"] = personal.in_poland
    if personal.birth_date:
        extra["birth_date"] = personal.birth_date
    # Сохраняем current_location, frigo_experience, has_adr в extra даже если они пустые строки или False
    if personal.current_location is not None:
        extra["current_location"] = personal.current_location
    if personal.frigo_experience is not None:
        extra["frigo_experience"] = personal.frigo_experience
    if personal.has_adr is not None:
        extra["has_adr"] = personal.has_adr
    
    # Residency basis
    basis = _map_residency_status_to_poland_basis(residency)
    if basis:
        extra["poland_stay_basis"] = basis
    
    # Experience data
    if merged_years_ce is not None:
        extra["experience_eu_years"] = merged_years_ce
    if merged_intl_experience is not None:
        extra["intl_experience"] = merged_intl_experience
    extra["trailer_types"] = _normalize_string_list(merged_trailer_types)
    extra["route_types"] = _normalize_string_list(merged_route_types)
    
    candidate._set_extra(extra)
    candidate.intake_state = state


@router.get(
    "/intake/lead-forms",
    response_model=list[PublicLeadFormListItem],
    summary="List active public lead forms",
    description=(
        "Returns forms that have a published slug. "
        "Pass **public_slug** or **lead_form_id** to resolve the tenant without **X-Tenant-Id**; "
        "otherwise send **X-Tenant-Id** to list all published forms for that workspace."
    ),
    responses={
        422: {"description": "Both **public_slug** and **lead_form_id** query parameters were sent."},
    },
)
async def list_public_intake_lead_forms(
    public_slug: Optional[str] = Query(
        default=None,
        description="Globally unique published slug; resolves the form owner's tenant (no **X-Tenant-Id** needed).",
    ),
    lead_form_id: Optional[str] = Query(
        default=None,
        description="Active lead form id; resolves the owner's tenant when **public_slug** is omitted.",
    ),
    tenant_id_header: Optional[str] = Header(
        default=None,
        alias="X-Tenant-Id",
        description="Workspace UUID when listing by tenant without **public_slug** / **lead_form_id**.",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[PublicLeadFormListItem]:
    """Active tenant lead forms with a public slug. Pass public_slug to resolve tenant; else X-Tenant-Id for one tenant's list."""
    slug_q = (public_slug or "").strip()
    fid_q = (lead_form_id or "").strip()
    if slug_q and fid_q:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "lead_form_reference_ambiguous",
                "message": "Send only one of public_slug or lead_form_id query parameters.",
            },
        )
    if slug_q:
        pair = await resolve_lead_form_tenant_and_id_by_slug(db, slug_q)
        if not pair:
            return []
        await bind_tenant_context_to_session(db, UUID(pair[0]))
        row = (
            await db.execute(
                select(TenantLeadForm).where(
                    TenantLeadForm.tenant_id == pair[0],
                    TenantLeadForm.id == pair[1],
                    TenantLeadForm.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row is None or not (row.public_slug or "").strip():
            return []
        return [
            PublicLeadFormListItem(
                id=row.id,
                title=row.title or "",
                public_slug=str(row.public_slug or "").strip(),
            )
        ]

    if fid_q:
        pair = await resolve_lead_form_tenant_and_id_by_form_id(db, fid_q)
        if not pair:
            return []
        await bind_tenant_context_to_session(db, UUID(pair[0]))
        row = (
            await db.execute(
                select(TenantLeadForm).where(
                    TenantLeadForm.tenant_id == pair[0],
                    TenantLeadForm.id == pair[1],
                    TenantLeadForm.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return []
        return [
            PublicLeadFormListItem(
                id=row.id,
                title=row.title or "",
                public_slug=str(row.public_slug or "").strip() if row.public_slug else "",
            )
        ]

    raw = (tenant_id_header or "").strip()
    if not raw:
        return []
    try:
        tenant_uuid = UUID(raw)
    except Exception:
        return []
    await bind_tenant_context_to_session(db, tenant_uuid)
    rows = await list_active_lead_forms_with_public_slug(db, str(tenant_uuid))
    return [
        PublicLeadFormListItem(id=r.id, title=r.title or "", public_slug=str(r.public_slug or "").strip())
        for r in rows
        if (r.public_slug or "").strip()
    ]


@router.post(
    "/intake",
    response_model=PublicIntakeCreateResponse,
    summary="Create or reuse public intake session",
    description=(
        "Creates a lead-first intake draft session (or reuses by contact / legacy candidate draft) "
        "in the workspace resolved from **lead_form_slug** / **lead_form_id** "
        "or from **X-Tenant-Id** (non-demo). Returns an **apply** token and URLs. "
        "Candidate rows are created only after submit when Decision Layer returns ``create_candidate``."
    ),
    responses={
        400: {
            "description": "Tenant routing: `intake_tenant_required` or `intake_default_tenant_forbidden` (see response JSON `detail.code`)."
        },
        404: {
            "description": "Referenced lead form missing, inactive, or slug not published (`lead_form_not_found`)."
        },
        422: {
            "description": "Invalid body: contacts missing, both lead form references set, or invalid `lead_form_slug` format."
        },
    },
)
async def create_public_intake(
    payload: PublicIntakeCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PublicIntakeCreateResponse:
    await enforce_rate_limit(request, rate_limits().public_intake, scope="public:intake")
    await require_turnstile(request, token=payload.turnstile_token)
    contacts = payload.contacts
    if not contacts.has_contact():
        raise HTTPException(status_code=422, detail="phone or email is required")
    tenant_uuid = await resolve_tenant_uuid_for_public_intake_create(
        db,
        x_tenant_id_header=request.headers.get("X-Tenant-Id"),
        lead_form_id=payload.lead_form_id,
        lead_form_slug=payload.lead_form_slug,
    )
    await bind_tenant_context_to_session(db, tenant_uuid)
    tenant_id = tenant_uuid

    lf = await load_active_lead_form_for_public_intake(
        db,
        str(tenant_id),
        lead_form_id=payload.lead_form_id,
        lead_form_slug=payload.lead_form_slug,
    )
    wants_lead_form = bool((payload.lead_form_id or "").strip() or (payload.lead_form_slug or "").strip())
    if wants_lead_form and lf is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "lead_form_not_found",
                "message": "Lead form not found, inactive, or slug is not published.",
            },
        )

    resolved_vacancy_id = await _resolve_public_intake_vacancy_id(
        db,
        tenant_id=str(tenant_id),
        vacancy_uuid=payload.vacancy_id,
    )

    # ADR-013 / Form Constructor (C1): bound lead forms always use Lead-first draft (P5C).
    # Legacy candidate-token reuse applies only to unbound public intake (no TenantLeadForm).
    use_legacy_candidate_session = lf is None

    candidate = None
    if use_legacy_candidate_session:
        candidate = await _find_candidate_by_contact(
            db,
            tenant_id,
            email=contacts.email,
            phone_country_code=contacts.phone_country_code,
            phone=contacts.phone,
        )
    now = _now()
    expires_at = now + timedelta(days=INTAKE_TOKEN_TTL_DAYS)

    if use_legacy_candidate_session and candidate:
        state = _ensure_intake_state(candidate)
        if payload.application_kind is not None:
            state["application_kind"] = _coerce_intake_application_kind(str(payload.application_kind))
        stored_contacts = dict(state.get("contacts") or {})
        for key, value in contacts.model_dump(exclude_none=True).items():
            stored_contacts[key] = value
        state["contacts"] = stored_contacts
        if payload.client_company is not None:
            state["client_company"] = {
                **dict(state.get("client_company") or {}),
                **{k: v for k, v in payload.client_company.model_dump().items() if v not in (None, "", [], {})},
            }
        if lf is not None:
            state["lead_form"] = lead_form_meta_for_intake_state(lf)
        candidate.intake_state = state
        if contacts.phone_country_code and not candidate.phone_country_code:
            candidate.phone_country_code = contacts.phone_country_code
        if contacts.phone and not candidate.phone:
            candidate.phone = contacts.phone
        if contacts.email and not candidate.email:
            candidate.email = contacts.email
        candidate.intake_status = candidate.intake_status or "draft"
        candidate.stage = candidate.stage or "docs_wait"
        if not candidate.intake_token:
            candidate.intake_token = _generate_token()
        candidate.intake_token_created_at = now
        candidate.intake_token_expires_at = expires_at
        _ensure_status_share_token(candidate)
        if resolved_vacancy_id is not None:
            candidate.vacancy_id = resolved_vacancy_id
        await log_public_event(
            db,
            tenant_id=str(tenant_id),
            action="intake_link_reused",
            target_id=candidate.id,
            payload={
                "contacts": contacts.model_dump(exclude_none=True),
                "source": normalize_candidate_source(payload.source),
                **({"lead_form_id": lf.id} if lf is not None else {}),
                **({"vacancy_id": resolved_vacancy_id} if resolved_vacancy_id else {}),
                **({"client_company": state.get("client_company")} if state.get("client_company") else {}),
            },
        )
        await db.commit()
        return PublicIntakeCreateResponse(
            apply_url=f"/public/apply/{candidate.intake_token}",
            token=candidate.intake_token or "",
            candidate_id=candidate.id,
            lead_id=None,
            expires_at=expires_at,
        )

    from backend.app.entity_profile.public_intake_draft_session import create_or_reuse_public_intake_lead_draft

    ak = _coerce_intake_application_kind(str(payload.application_kind) if payload.application_kind is not None else None)
    lf_meta = lead_form_meta_for_intake_state(lf) if lf is not None else None
    client_company = None
    if payload.client_company is not None:
        client_company = {
            k: v for k, v in payload.client_company.model_dump().items() if v not in (None, "", [], {})
        }
    try:
        lead, token, expires_at = await create_or_reuse_public_intake_lead_draft(
            db,
            tenant_id=str(tenant_id),
            contacts=contacts.model_dump(exclude_none=True),
            intake_source=normalize_candidate_source(payload.source),
            vacancy_id=resolved_vacancy_id,
            application_kind=ak,
            lead_form_meta=lf_meta,
            client_company=client_company,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await log_public_event(
        db,
        tenant_id=str(tenant_id),
        action="intake_lead_draft_created",
        target_id=lead.id,
        payload={
            "contacts": contacts.model_dump(exclude_none=True),
            "source": normalize_candidate_source(payload.source),
            **({"lead_form_id": lf.id} if lf is not None else {}),
            **({"vacancy_id": resolved_vacancy_id} if resolved_vacancy_id else {}),
        },
    )
    await db.commit()
    return PublicIntakeCreateResponse(
        apply_url=f"/public/apply/{token}",
        token=token,
        candidate_id=None,
        lead_id=lead.id,
        expires_at=expires_at,
    )


@router.get("/apply/{token}", response_model=PublicIntakeState)
async def get_public_intake(
    token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_apply_session),
) -> PublicIntakeState:
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    if public_session.kind == "questionnaire_invite" and public_session.invite is not None and public_session.lead is not None:
        from backend.app.modules.leads.lead_questionnaire_invite import mark_invite_opened

        await mark_invite_opened(
            db,
            invite=public_session.invite,
            lead=public_session.lead,
        )
        await db.commit()
    if public_session.kind == "legacy_candidate" and public_session.candidate is not None:
        if _ensure_status_share_token(public_session.candidate):
            await db.commit()
    checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
    return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)


@router.post(
    "/magic-link/request",
    response_model=PublicMagicLinkRequestResponse,
    summary="Request magic link for public intake",
    description=(
        "If a candidate with the same **email** or **phone** exists in the resolved tenant, creates a short-lived magic link "
        "(redeem via **GET /public/magic-link/{token}**). "
        "Prefer **intake_token** when the user is already on `/public/apply/{token}` so the correct workspace is used regardless of **X-Tenant-Id**."
    ),
    responses={
        400: {
            "description": "Tenant routing: `intake_tenant_required` or `intake_default_tenant_forbidden` (when **intake_token** is omitted)."
        },
        404: {"description": "Unknown **intake_token** (only evaluated when **intake_token** is sent)."},
        422: {
            "description": "Validation error: missing contact, or both **lead_form_id** and **lead_form_slug**, or invalid slug."
        },
        429: {"description": "Cooldown or daily cap for this contact in the tenant."},
    },
)
async def request_public_magic_link(
    payload: PublicMagicLinkRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PublicMagicLinkRequestResponse:
    await enforce_rate_limit(request, rate_limits().magic_link, scope="public:magic_link")
    it = (payload.intake_token or "").strip()
    if it:
        tid_str = await resolve_intake_token_tenant_id(db, it)
        if not tid_str:
            raise HTTPException(status_code=404, detail="Invalid intake token")
        tenant_id = UUID(tid_str)
        await bind_tenant_context_to_session(db, tenant_id)
    else:
        tenant_id = await resolve_tenant_uuid_for_public_intake_create(
            db,
            x_tenant_id_header=request.headers.get("X-Tenant-Id"),
            lead_form_id=payload.lead_form_id,
            lead_form_slug=payload.lead_form_slug,
        )
        await bind_tenant_context_to_session(db, tenant_id)
    candidate = await _find_candidate_by_contact(
        db,
        tenant_id,
        email=payload.email,
        phone_country_code=payload.phone_country_code,
        phone=payload.phone,
    )
    contact_type = "email" if payload.email else "phone"
    phone_parts = _normalize_phone_parts(payload.phone_country_code, payload.phone)
    contact_value = _contact_value(
        contact_type,
        email=payload.email,
        phone=phone_parts,
    )
    if candidate and contact_value:
        _ensure_status_share_token(candidate)
        _ensure_intake_token(candidate)
        link = await _create_magic_link(
            db,
            tenant_id,
            candidate,
            contact_type=contact_type,
            contact_value=contact_value,
        )
        magic_url = f"/public?magic={link.token}"
        logger.info(
            "Magic link issued for candidate=%s contact=%s value=%s url=%s",
            candidate.id,
            contact_type,
            contact_value,
            magic_url,
        )
        await log_public_event(
            db,
            tenant_id=str(tenant_id),
            action="magic_link_requested",
            target_id=candidate.id,
            payload={
                "contact_type": contact_type,
                "contact_value": contact_value,
                "magic_token": link.token,
            },
            ip=request.client.host if request and request.client else None,
            ua=request.headers.get("user-agent") if request else None,
        )
    elif it and contact_value:
        from backend.app.entity_profile.public_intake_draft_session import (
            find_lead_draft_by_intake_token,
            get_public_intake_draft_block,
        )

        lead = await find_lead_draft_by_intake_token(db, tenant_id=str(tenant_id), token=it)
        if lead is not None:
            await _assert_magic_link_limits(db, tenant_id, contact_type, contact_value)
            block = get_public_intake_draft_block(lead)
            link = MagicLink(
                tenant_id=str(tenant_id),
                candidate_id=None,
                token=_generate_token(),
                contact_type=contact_type,
                contact_value=contact_value,
                expires_at=_now() + timedelta(minutes=MAGIC_LINK_TTL_MINUTES),
                meta={"lead_id": str(lead.id), "intake_token": it},
            )
            db.add(link)
            await log_public_event(
                db,
                tenant_id=str(tenant_id),
                action="magic_link_requested",
                target_id=str(lead.id),
                payload={
                    "contact_type": contact_type,
                    "contact_value": contact_value,
                    "magic_token": link.token,
                    "lead_draft": True,
                },
                ip=request.client.host if request and request.client else None,
                ua=request.headers.get("user-agent") if request else None,
            )
    await db.commit()
    return PublicMagicLinkRequestResponse(
        cooldown_seconds=MIN_MAGIC_LINK_INTERVAL_SECONDS,
        daily_limit=MAX_MAGIC_LINKS_PER_DAY,
    )


@router.get("/magic-link/{token}", response_model=PublicMagicLinkRedeemResponse)
async def redeem_public_magic_link(
    token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_magic_link_redeem_session),
) -> PublicMagicLinkRedeemResponse:
    db, tenant_id = db_tenant
    link = await _load_magic_link(db, tenant_id, token)
    if not link.candidate_id:
        meta = dict(link.meta or {}) if isinstance(link.meta, dict) else {}
        intake_token = str(meta.get("intake_token") or "").strip()
        lead_id = str(meta.get("lead_id") or "").strip() or None
        if not intake_token:
            raise HTTPException(status_code=404, detail="Candidate not attached to link")
        from backend.app.entity_profile.public_intake_draft_session import (
            find_lead_draft_by_intake_token,
            get_public_intake_draft_block,
        )

        lead = await find_lead_draft_by_intake_token(db, tenant_id=str(tenant_id), token=intake_token)
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead draft not found")
        block = get_public_intake_draft_block(lead)
        expires_raw = block.get("intake_token_expires_at")
        expires_at = _now() + timedelta(days=INTAKE_TOKEN_TTL_DAYS)
        if expires_raw:
            try:
                expires_at = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
            except ValueError:
                pass
        link.redeemed_at = _now()
        await db.commit()
        return PublicMagicLinkRedeemResponse(
            token=intake_token,
            apply_url=f"/public/apply/{intake_token}",
            status_share_token=str(block.get("status_share_token") or "") or None,
            expires_at=expires_at,
            candidate_id=None,
            lead_id=lead_id or str(lead.id),
            cooldown_seconds=MIN_MAGIC_LINK_INTERVAL_SECONDS,
            daily_limit=MAX_MAGIC_LINKS_PER_DAY,
        )
    stmt = (
        select(Candidate)
        .where(
            Candidate.id == link.candidate_id,
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    candidate = await db.scalar(stmt)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    _ensure_intake_token(candidate)
    _ensure_status_share_token(candidate)
    link.redeemed_at = _now()
    await db.commit()
    return PublicMagicLinkRedeemResponse(
        token=candidate.intake_token or "",
        apply_url=f"/public/apply/{candidate.intake_token}",
        status_share_token=candidate.status_share_token,
        expires_at=candidate.intake_token_expires_at or (_now() + timedelta(days=INTAKE_TOKEN_TTL_DAYS)),
        candidate_id=candidate.id,
        cooldown_seconds=MIN_MAGIC_LINK_INTERVAL_SECONDS,
        daily_limit=MAX_MAGIC_LINKS_PER_DAY,
    )


@router.get("/status/{share_token}", response_model=PublicStatusState)
async def get_public_status(
    share_token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_status_session),
) -> PublicStatusState:
    db, tenant_id = db_tenant
    candidate_stmt = (
        select(Candidate)
        .where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.status_share_token == share_token,
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    candidate = await db.scalar(candidate_stmt)
    if candidate is not None:
        expires_at = getattr(candidate, "status_share_token_expires_at", None)
        if expires_at and expires_at < _now():
            raise HTTPException(status_code=410, detail="Status link expired")
        employments = await _list_employments(db, tenant_id, candidate.id)
        checklist, documents = await _build_checklist_and_docs(
            db,
            tenant_id,
            candidate,
            download_scope="status",
            download_token=share_token,
        )
        return _status_response_payload(candidate, employments, checklist, documents)

    from backend.app.entity_profile.public_intake_draft_session import (
        PublicIntakeSession,
        find_lead_draft_by_status_share_token,
        get_public_intake_draft_block,
    )

    lead = await find_lead_draft_by_status_share_token(
        db,
        tenant_id=str(tenant_id),
        share_token=share_token,
    )
    if lead is None:
        raise HTTPException(status_code=404, detail="Invalid status token")
    block = get_public_intake_draft_block(lead)
    if isinstance(block, dict):
        expires_raw = block.get("intake_token_expires_at")
        if expires_raw:
            try:
                exp = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
                if exp < _now():
                    raise HTTPException(status_code=410, detail="Status link expired")
            except ValueError:
                pass
    token = str(block.get("intake_token") or "") if isinstance(block, dict) else ""
    public_session = PublicIntakeSession(
        kind="lead_draft",
        tenant_id=str(tenant_id),
        token=token,
        lead=lead,
    )
    checklist, documents = await _build_checklist_and_docs_for_session(
        db,
        tenant_id,
        public_session,
        download_scope="status",
        download_token=share_token,
    )
    return _status_response_payload_from_lead_session(public_session, checklist, documents)


@router.post("/status/{share_token}/rotate", response_model=PublicStatusRotateResponse)
async def rotate_public_status_token(
    share_token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_status_session),
) -> PublicStatusRotateResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    _ensure_status_share_token(candidate)
    await db.commit()
    return PublicStatusRotateResponse(
        status_share_token=candidate.status_share_token or "",
        expires_at=candidate.status_share_token_expires_at or (_now() + timedelta(days=INTAKE_TOKEN_TTL_DAYS)),
    )



def _merge_intake_payload_into_state(state: Dict[str, Any], payload: IntakeData) -> Dict[str, Any]:
    """Merge IntakeData into intake_state dict (lead-first draft sessions)."""
    contacts = payload.contacts
    personal = payload.personal
    experience = payload.experience
    existing_contacts = dict(state.get("contacts") or {})
    existing_personal = dict(state.get("personal") or {})
    existing_experience = dict(state.get("experience") or {})
    existing_agreements = dict(state.get("agreements") or {})
    existing_employments = list(state.get("employments") or [])
    residency = _auto_residency_status(
        personal.citizenship or existing_personal.get("citizenship"),
        personal.residency_status,
    )
    merged_years_ce = experience.years_ce if experience.years_ce is not None else existing_experience.get("years_ce")
    merged_intl_experience = (
        experience.intl_experience
        if experience.intl_experience is not None
        else existing_experience.get("intl_experience")
    )
    merged_trailer_types = experience.trailer_types or existing_experience.get("trailer_types") or []
    merged_route_types = experience.route_types or existing_experience.get("route_types") or []
    state["contacts"] = {
        **existing_contacts,
        **{k: v for k, v in contacts.model_dump().items() if v not in (None, "", [], {})},
    }
    state["personal"] = {
        **existing_personal,
        **{k: v for k, v in personal.model_dump().items() if v not in (None, "", [], {})},
        "residency_status": residency or existing_personal.get("residency_status"),
    }
    state["experience"] = {
        **existing_experience,
        **{k: v for k, v in experience.model_dump().items() if v not in (None, "", [], {})},
        "years_ce": merged_years_ce,
        "intl_experience": merged_intl_experience,
        "trailer_types": merged_trailer_types,
        "route_types": merged_route_types,
    }
    merged_agreements = existing_agreements.copy()
    for key, val in payload.agreements.model_dump().items():
        if val is True or key not in merged_agreements:
            merged_agreements[key] = val
    state["agreements"] = merged_agreements
    new_employments = [_employment_state_payload(entry) for entry in payload.employments]
    state["employments"] = new_employments or existing_employments
    if payload.lead_form is not None:
        state["lead_form"] = payload.lead_form
    if payload.client_company is not None:
        state["client_company"] = {
            **dict(state.get("client_company") or {}),
            **{k: v for k, v in payload.client_company.model_dump().items() if v not in (None, "", [], {})},
        }
    if payload.application_kind is not None:
        ak = str(payload.application_kind).strip().lower()
        state["application_kind"] = ak if ak in ("candidate", "client") else "candidate"
    if payload.presentation_values is not None:
        from backend.app.entity_profile.public_intake_presentation_bridge import apply_presentation_values_to_state

        apply_presentation_values_to_state(state, dict(payload.presentation_values))
    return state


async def _finalize_public_client_lead_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    intake_state: dict[str, Any],
) -> None:
    if _coerce_intake_application_kind(str(intake_state.get("application_kind"))) != "client":
        return
    personal = dict(intake_state.get("personal") or {})
    contacts = dict(intake_state.get("contacts") or {})
    client_company = dict(intake_state.get("client_company") or {})
    full_name = str(personal.get("full_name") or "").strip()
    lead.stage = "questionnaire_submitted"
    lead.status = "new"
    normalized = dict(lead.normalized or {})
    normalized.update(
        {
            "email": contacts.get("email"),
            "phone": contacts.get("phone"),
            "full_name": full_name or None,
            "company_name": str(client_company.get("name") or "").strip() or None,
            "intake_application_kind": "client",
        }
    )
    lead.normalized = {k: v for k, v in normalized.items() if v is not None}
    lead.payload = {
        **(lead.payload if isinstance(lead.payload, dict) else {}),
        "intake": True,
        "contacts": contacts,
        "personal": personal,
        "client_company": client_company,
    }
    display_name = full_name or str(client_company.get("name") or "").strip() or str(lead.id)
    await emit_event(
        db,
        tenant_id=tenant_id,
        event_type="lead_public_intake_client",
        payload={
            "lead_id": str(lead.id),
            "candidate_id": None,
            "candidate_name": display_name,
            "href": spa_paths.spa_lead(str(lead.id)),
        },
        audience=EventAudience(roles=(Role.manager, Role.recruiter)),
        entity_type="lead",
        entity_id=str(lead.id),
    )
    await db.flush()


@router.put("/apply/{token}", response_model=PublicIntakeState)
async def update_public_intake(
    token: str,
    payload: PublicIntakeUpdateRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_apply_session),
) -> PublicIntakeState:
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    if public_session.kind == "questionnaire_invite" and public_session.invite is not None and public_session.lead is not None:
        from backend.app.entity_profile.public_intake_draft_session import (
            session_intake_state,
            write_session_intake_state,
        )
        from backend.app.modules.leads.lead_questionnaire_invite import (
            mark_invite_in_progress,
            merge_presentation_into_sales_summary,
        )

        state = session_intake_state(public_session)
        state = _merge_intake_payload_into_state(state, payload.data)
        write_session_intake_state(public_session, state)
        merge_presentation_into_sales_summary(public_session.lead, state, submitted=False)
        await mark_invite_in_progress(
            db,
            invite=public_session.invite,
            lead=public_session.lead,
        )
        await db.commit()
        checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
        return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)

    if public_session.kind == "lead_draft" and public_session.lead is not None:
        from backend.app.entity_profile.public_intake_draft_session import (
            session_intake_state,
            write_session_intake_state,
        )

        state = session_intake_state(public_session)
        state = _merge_intake_payload_into_state(state, payload.data)
        write_session_intake_state(public_session, state)
        normalized = dict(public_session.lead.normalized or {})
        contacts = dict(state.get("contacts") or {})
        if contacts.get("email"):
            normalized["email"] = contacts.get("email")
        if contacts.get("phone"):
            normalized["phone"] = contacts.get("phone")
        public_session.lead.normalized = normalized
        public_session.lead.payload = {
            **(public_session.lead.payload if isinstance(public_session.lead.payload, dict) else {}),
            "intake_state": state,
        }
        await db.commit()
        checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
        return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)

    candidate = public_session.candidate
    assert candidate is not None
    _update_candidate_from_data(candidate, payload.data)
    state = _ensure_intake_state(candidate)
    state["employments"] = [_employment_state_payload(entry) for entry in payload.data.employments] or state.get("employments") or []
    if payload.data.employments:
        await _upsert_employments(db, tenant_id, candidate.id, payload.data.employments)
    await db.commit()
    employments = await _list_employments(db, tenant_id, candidate.id)
    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    return _response_payload(candidate, employments, checklist, documents)


@router.post("/apply/{token}/submit", response_model=PublicIntakeState)
async def submit_public_intake(
    token: str,
    payload: PublicIntakeSubmitRequest,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_apply_session),
) -> PublicIntakeState:
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    if public_session.kind == "questionnaire_invite" and public_session.invite is not None and public_session.lead is not None:
        from backend.app.entity_profile.public_intake_draft_session import (
            session_intake_state,
            write_session_intake_state,
        )
        from backend.app.entity_profile.public_intake_presentation_bridge import (
            resolve_public_session_form_presentation,
            validate_presentation_required_fields,
        )
        from backend.app.modules.leads.lead_questionnaire_invite import mark_invite_submitted

        if not payload.has_all_required():
            raise HTTPException(status_code=422, detail="Required consents must be accepted before submit")
        state = session_intake_state(public_session)
        state["agreements"] = {
            "general": payload.consents.general,
            "employer_share": payload.consents.employer_share,
            "terms_acceptance": payload.consents.terms_acceptance,
            "cookies_accepted": payload.cookies_accepted,
        }
        write_session_intake_state(public_session, state)
        form_presentation = await resolve_public_session_form_presentation(
            db,
            tenant_id=str(tenant_id),
            intake_state=state,
        )
        if form_presentation:
            missing = validate_presentation_required_fields(form_presentation, state)
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "presentation_required_fields",
                        "message": "Required presentation fields are missing",
                        "missing": missing,
                    },
                )
        await mark_invite_submitted(
            db,
            invite=public_session.invite,
            lead=public_session.lead,
            intake_state=state,
        )
        await db.commit()
        checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
        return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)

    if public_session.kind == "lead_draft" and public_session.lead is not None:
        from backend.app.entity_profile.public_intake_draft_session import (
            mark_session_submitted,
            session_intake_state,
            session_intake_status,
            submit_public_intake_lead_draft,
            write_session_intake_state,
        )

        if not payload.has_all_required():
            raise HTTPException(status_code=422, detail="Required consents must be accepted before submit")
        if session_intake_status(public_session) == "submitted":
            checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
            return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        state = session_intake_state(public_session)
        state["agreements"] = {
            "general": payload.consents.general,
            "employer_share": payload.consents.employer_share,
            "terms_acceptance": payload.consents.terms_acceptance,
            "cookies_accepted": payload.cookies_accepted,
        }
        write_session_intake_state(public_session, state)
        from backend.app.entity_profile.public_intake_presentation_bridge import (
            resolve_public_session_form_presentation,
            validate_presentation_required_fields,
        )

        form_presentation = await resolve_public_session_form_presentation(
            db,
            tenant_id=str(tenant_id),
            intake_state=state,
        )
        if form_presentation:
            missing = validate_presentation_required_fields(form_presentation, state)
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "presentation_required_fields",
                        "message": "Required presentation fields are missing",
                        "missing": missing,
                    },
                )
        mark_session_submitted(public_session)
        application_kind = str(state.get("application_kind") or "candidate").strip().lower()
        form_presentation_code = (
            str(form_presentation.get("presentation_code") or "") if form_presentation else None
        )
        if application_kind == "client":
            from backend.app.intake_platform.intake_submit_service import submit_client_public_intake_with_policy

            decision, created_candidate_id, _effective = await submit_client_public_intake_with_policy(
                db,
                tenant_id=str(tenant_id),
                draft_lead=public_session.lead,
                intake_state=state,
                presentation_code=form_presentation_code,
            )
        else:
            decision, created_candidate_id = await submit_public_intake_lead_draft(
                db,
                tenant_id=str(tenant_id),
                lead=public_session.lead,
                intake_state=state,
            )
        if created_candidate_id:
            await _log_consent_snapshot(db, tenant_id, created_candidate_id, payload, client_ip, user_agent)
            employments_payload = state.get("employments") or []
            if employments_payload:
                parsed = _intake_data_from_state_dict(state).employments
                if parsed:
                    await _upsert_employments(db, tenant_id, created_candidate_id, parsed)
        await _finalize_public_client_lead_draft(
            db,
            tenant_id=str(tenant_id),
            lead=public_session.lead,
            intake_state=state,
        )
        await db.commit()
        checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
        return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)

    candidate = public_session.candidate
    assert candidate is not None
    state = _ensure_intake_state(candidate)
    state["agreements"] = {
        "general": payload.consents.general,
        "employer_share": payload.consents.employer_share,
        "terms_acceptance": payload.consents.terms_acceptance,
        "cookies_accepted": payload.cookies_accepted,
    }
    if not payload.has_all_required():
        raise HTTPException(status_code=422, detail="Required consents must be accepted before submit")
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    employments = await _list_employments(db, tenant_id, candidate.id)
    oc = getattr(candidate, "own_company_id", None)
    own_company_id = str(oc).strip() if oc else None
    docs = await list_candidate_documents_via_contract(
        db,
        tenant_id=str(tenant_id),
        candidate_id=candidate.id,
        include_deleted=False,
        active_own_company_id=own_company_id,
    )
    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    missing_required = [
        doc_type
        for doc_type in checklist.get("requiredTypes") or []
        if not has_ready_document(docs, doc_type)
    ]
    intake_state = _ensure_intake_state(candidate)
    _lf = intake_state.get("lead_form")
    _ak = _coerce_intake_application_kind(str(intake_state.get("application_kind")))
    intake_payload = IntakeData(
        contacts=IntakeContacts(**(intake_state.get("contacts") or {})),
        personal=IntakePersonal(**(intake_state.get("personal") or {})),
        experience=IntakeExperience(**(intake_state.get("experience") or {})),
        employments=intake_state.get("employments") or [],
        agreements=IntakeAgreements(**(intake_state.get("agreements") or {})),
        lead_form=_lf if isinstance(_lf, dict) else None,
        client_company=IntakeClientCompany(**(intake_state.get("client_company") or {}))
        if isinstance(intake_state.get("client_company"), dict)
        else None,
        application_kind=_ak,
    )
    _update_candidate_from_data(candidate, intake_payload)
    state["employments"] = [_employment_state_payload(entry) for entry in intake_payload.employments] or state.get("employments") or []
    if intake_payload.employments:
        await _upsert_employments(db, tenant_id, candidate.id, intake_payload.employments)
    candidate.stage = "questionnaire_submitted"
    candidate.intake_status = "submitted"
    candidate.intake_submitted_at = _now()
    await _log_consent_snapshot(db, tenant_id, candidate.id, payload, client_ip, user_agent)

    from backend.app.entity_profile.ingest_runtime import (
        prepare_public_intake_runtime,
        resolve_public_intake_source_profile_id,
    )

    _lf_meta = intake_state.get("lead_form") if isinstance(intake_state.get("lead_form"), dict) else {}
    lead_form_id = str(_lf_meta.get("id") or "").strip() or None
    public_slug = str(_lf_meta.get("public_slug") or "").strip() or None
    intake_source_profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=lead_form_id,
        public_slug=public_slug,
    )
    envelope, _profile_view, _validation = await prepare_public_intake_runtime(
        db,
        tenant_id=str(tenant_id),
        intake_state=intake_state,
        intake_source_profile_id=intake_source_profile_id,
        candidate_profile_id=None,
        vacancy_id=str(candidate.vacancy_id) if getattr(candidate, "vacancy_id", None) else None,
    )
    state["ingest_envelope_v1"] = envelope.to_dict()
    if envelope.entity_profile_code:
        state["entity_profile_code"] = envelope.entity_profile_code

    from backend.app.entity_profile.decision_layer import (
        DecisionInput,
        IngestDecisionContext,
        evaluate_ingest_decision,
    )
    from backend.app.entity_profile.public_intake_bridge import ensure_public_intake_lead_record

    flat_normalized = dict(envelope.normalized_payload or {})
    flat_normalized["ingest_envelope_v1"] = envelope.to_dict()
    if envelope.entity_profile_code:
        flat_normalized["entity_profile_code"] = envelope.entity_profile_code
    decision_input = DecisionInput.from_normalized(
        tenant_id=str(tenant_id),
        source="public_intake",
        normalized=flat_normalized,
        vacancy_id=str(candidate.vacancy_id) if getattr(candidate, "vacancy_id", None) else None,
        company_id=str(getattr(candidate, "company_id", None) or "") or None,
        existing_candidate_id=str(candidate.id),
    )
    decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=IngestDecisionContext(vacancy_resolved=bool(getattr(candidate, "vacancy_id", None))),
        email=getattr(candidate, "email", None),
        phone=getattr(candidate, "phone", None),
    )
    state["decision_input_v1"] = decision_input.to_dict()
    state["decision_result_v1"] = decision.to_dict()
    state["decision_result_v1"]["entity_profile_code"] = decision_input.entity_profile_code
    try:
        await ensure_public_intake_lead_record(
            db,
            tenant_id=str(tenant_id),
            candidate=candidate,
            intake_state=state,
            envelope_dict=envelope.to_dict(),
            decision_input=decision_input,
            decision=decision,
        )
    except ValueError:
        pass

    candidate.intake_state = state

    notify_user_ids: List[str] = []
    manager_id = str(candidate.manager) if _looks_like_uuid(getattr(candidate, "manager", None)) else None
    if manager_id:
        notify_user_ids.append(manager_id)
    recruiter_raw = getattr(candidate, "recruiter_id", None)
    recruiter_id = str(recruiter_raw) if _looks_like_uuid(recruiter_raw) else None
    if recruiter_id:
        notify_user_ids.append(recruiter_id)

    full_name = " ".join(part for part in [candidate.first_name, candidate.last_name] if part).strip()
    candidate_name = full_name or candidate.first_name or candidate.last_name or candidate.id

    await emit_event(
        db,
        tenant_id=str(tenant_id),
        event_type="candidate.intake_submitted",
        payload={
            "candidate_id": candidate.id,
            "candidate_name": candidate_name,
            "stage": candidate.stage,
            "manager_id": manager_id,
            "recruiter_id": recruiter_id,
        },
        audience=EventAudience(
            user_ids=notify_user_ids or None,
            roles=None if notify_user_ids else (Role.manager, Role.recruiter),
        ),
        entity_type="candidate",
        entity_id=candidate.id,
    )
    await _maybe_create_client_lead_from_public_intake(
        db, str(tenant_id), candidate, client_ip=client_ip, user_agent=user_agent
    )
    await db.commit()

    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    return _response_payload(candidate, employments, checklist, documents)


@router.post("/apply/{token}/documents/presign", response_model=PublicPresignResponse)
async def presign_public_document_upload(
    token: str,
    payload: PublicPresignRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_apply_session),
) -> PublicPresignResponse:
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    filename = payload.filename.strip() or f"{payload.doc_type}.bin"
    if public_session.kind == "lead_draft" and public_session.lead_id:
        key = _build_draft_storage_key(str(tenant_id), public_session.lead_id, filename)
        owner_id = public_session.lead_id
        candidate_id = None
    else:
        candidate = public_session.candidate
        if candidate is None:
            raise HTTPException(status_code=404, detail="Invalid intake token")
        key = _build_storage_key(candidate, filename)
        owner_id = str(candidate.id)
        candidate_id = str(candidate.id)
    url = f"/api/v1/public/uploads/{token}/{key}"
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
        result="success",
        severity="info",
        source="http:public_intake:presign_apply",
        tenant_id=str(tenant_id),
        document_id=None,
        access_kind=None,
        document_class=payload.doc_type.strip(),
        candidate_id=candidate_id,
        upload_presign=True,
        intake_channel="apply_token",
    )
    return PublicPresignResponse(
        key=key,
        url=url,
        method="PUT",
        headers={"Content-Type": "application/octet-stream"},
        fields={},
    )


@router.post("/status/{share_token}/documents/access", response_model=PublicStatusDocumentsAccessResponse)
async def get_public_documents_access(
    share_token: str,
    payload: PublicStatusDocumentsAccessRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_status_session),
) -> PublicStatusDocumentsAccessResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    if not _candidate_contact_matches(
        candidate,
        email=payload.email,
        phone_country_code=payload.phone_country_code,
        phone=payload.phone,
    ):
        raise HTTPException(status_code=403, detail="Contact verification failed")
    _ensure_intake_token(candidate)
    await db.commit()
    expires_at = candidate.intake_token_expires_at or (_now() + timedelta(days=INTAKE_TOKEN_TTL_DAYS))
    return PublicStatusDocumentsAccessResponse(
        verified=True,
        upload_url=f"/public/apply/{candidate.intake_token}?mode=documents",
        questionnaire_url=f"/public/apply/{candidate.intake_token}",
        expires_at=expires_at,
    )


@router.post("/status/{share_token}/documents/presign", response_model=PublicPresignResponse)
async def presign_status_document_upload(
    share_token: str,
    payload: PublicStatusPresignRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_status_session),
) -> PublicPresignResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    if not _candidate_contact_matches(
        candidate,
        email=payload.email,
        phone_country_code=payload.phone_country_code,
        phone=payload.phone,
    ):
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:public_intake:presign_status",
            tenant_id=str(tenant_id),
            document_id=None,
            access_kind=None,
            document_class=payload.doc_type.strip(),
            candidate_id=str(candidate.id),
            reason="contact_verification_failed",
            intake_channel="status_share",
        )
        raise HTTPException(status_code=403, detail="Contact verification failed")
    filename = payload.filename.strip() or f"{payload.doc_type}.bin"
    key = _build_storage_key(candidate, filename)
    url = f"/api/v1/public/uploads/{share_token}/{key}"
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
        result="success",
        severity="info",
        source="http:public_intake:presign_status",
        tenant_id=str(tenant_id),
        document_id=None,
        access_kind=None,
        document_class=payload.doc_type.strip(),
        candidate_id=str(candidate.id),
        upload_presign=True,
        intake_channel="status_share",
    )
    return PublicPresignResponse(
        key=key,
        url=url,
        method="PUT",
        headers={"Content-Type": "application/octet-stream"},
        fields={},
    )


@router.post("/apply/{token}/documents/upload", response_model=PublicIntakeState)
async def upload_public_document(
    token: str,
    doc_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    storage_key: Optional[str] = Form(None),
    user_comment: Optional[str] = Form(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_apply_session),
) -> PublicIntakeState:
    if not doc_type.strip():
        raise HTTPException(status_code=422, detail="doc_type is required")
    if not file and not storage_key:
        raise HTTPException(status_code=422, detail="file or storage_key is required")
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    doc_type_clean = doc_type.strip()
    if public_session.kind == "lead_draft" and public_session.lead is not None:
        await _save_lead_draft_document_upload(
            db,
            public_session.lead,
            doc_type_clean,
            upload_file=file,
            storage_key=storage_key,
            user_comment=user_comment,
        )
        await db.commit()
        checklist, documents = await _build_checklist_and_docs_for_session(db, tenant_id, public_session)
        return await _response_payload_from_session(db, tenant_id, public_session, checklist, documents)

    candidate = public_session.candidate
    if candidate is None:
        raise HTTPException(status_code=404, detail="Invalid intake token")
    await _save_public_document_upload(
        db,
        candidate,
        doc_type_clean,
        upload_file=file,
        storage_key=storage_key,
        user_comment=user_comment,
    )
    try:
        await send_candidate_documents_progress_telegram(
            db,
            tenant_id=str(tenant_id),
            candidate=candidate,
            source_doc_type=doc_type_clean,
        )
    except Exception:
        logger.exception(
            "public intake upload telegram progress notify failed tenant=%s candidate=%s",
            str(tenant_id),
            candidate.id,
        )
    try:
        promoted = await sync_candidate_ready_for_handoff_gate(
            db,
            tenant_id=str(tenant_id),
            candidate=candidate,
            source="public_intake_upload",
        )
        if promoted:
            await db.commit()
    except Exception:
        logger.exception(
            "public intake upload auto-ready-for-handoff sync failed tenant=%s candidate=%s",
            str(tenant_id),
            candidate.id,
        )
    employments = await _list_employments(db, tenant_id, candidate.id)
    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    return _response_payload(candidate, employments, checklist, documents)


@router.post("/status/{share_token}/documents/upload", response_model=PublicStatusState)
async def upload_status_document(
    share_token: str,
    doc_type: str = Form(...),
    email: Optional[str] = Form(None),
    phone_country_code: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    storage_key: Optional[str] = Form(None),
    user_comment: Optional[str] = Form(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_status_session),
) -> PublicStatusState:
    if not doc_type.strip():
        raise HTTPException(status_code=422, detail="doc_type is required")
    if not file and not storage_key:
        raise HTTPException(status_code=422, detail="file or storage_key is required")
    if not (email or phone):
        raise HTTPException(status_code=422, detail="email or phone is required")

    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    if not _candidate_contact_matches(
        candidate,
        email=email,
        phone_country_code=phone_country_code,
        phone=phone,
    ):
        raise HTTPException(status_code=403, detail="Contact verification failed")

    await _save_public_document_upload(
        db,
        candidate,
        doc_type.strip(),
        upload_file=file,
        storage_key=storage_key,
        user_comment=user_comment,
    )
    employments = await _list_employments(db, tenant_id, candidate.id)
    checklist, documents = await _build_checklist_and_docs(
        db,
        tenant_id,
        candidate,
        download_scope="status",
        download_token=share_token,
    )
    return _status_response_payload(candidate, employments, checklist, documents)


@router.get("/apply/{token}/documents/{doc_id}/file")
async def download_public_document_file(
    token: str,
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_apply_session),
) -> FileResponse:
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    doc_id_str = str(doc_id)

    if public_session.kind == "lead_draft" and public_session.lead is not None:
        from backend.app.entity_profile.public_intake_draft_session import get_public_intake_draft_block

        pending = list(get_public_intake_draft_block(public_session.lead).get("pending_documents") or [])
        entry = next(
            (row for row in pending if isinstance(row, dict) and str(row.get("id") or "") == doc_id_str),
            None,
        )
        if not entry or not entry.get("storage_path"):
            raise HTTPException(status_code=404, detail="Document not found")
        file_path = _resolve_storage_path(str(entry["storage_path"]))
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        filename = str(entry.get("filename") or file_path.name)
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return FileResponse(str(file_path), media_type=media_type, filename=filename)

    candidate = public_session.candidate
    if candidate is None:
        raise HTTPException(status_code=404, detail="Invalid intake token")
    stmt = (
        select(Document)
        .where(
            Document.id == str(doc_id),
            Document.candidate_id == candidate.id,
            Document.tenant_id == str(tenant_id),
            Document.deleted_at.is_(None),
        )
        .limit(1)
    )
    doc = await db.scalar(stmt)
    if not doc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:public_intake:download_apply",
            tenant_id=str(tenant_id),
            document_id=str(doc_id),
            access_kind=None,
            candidate_id=str(candidate.id),
            reason="document_not_found",
            intake_channel="apply_token",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        file_path, media_type, filename = resolve_document_file(doc)
    except FileNotFoundError:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:public_intake:download_apply",
            tenant_id=str(tenant_id),
            document_id=str(doc_id),
            access_kind=None,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(candidate.id),
            reason="file_not_found",
            intake_channel="apply_token",
        )
        raise HTTPException(status_code=404, detail="File not found") from None
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_FILE_DOWNLOADED,
        result="success",
        severity="info",
        source="http:public_intake:download_apply",
        tenant_id=str(tenant_id),
        document_id=str(doc_id),
        access_kind=None,
        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
        candidate_id=str(candidate.id),
        response_mode="file_stream",
        intake_channel="apply_token",
    )
    return FileResponse(str(file_path), media_type=media_type, filename=filename)


@router.get("/status/{share_token}/documents/{doc_id}/file")
async def download_status_document_file(
    share_token: str,
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_status_session),
) -> FileResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    stmt = (
        select(Document)
        .where(
            Document.id == str(doc_id),
            Document.candidate_id == candidate.id,
            Document.tenant_id == str(tenant_id),
            Document.deleted_at.is_(None),
        )
        .limit(1)
    )
    doc = await db.scalar(stmt)
    if not doc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:public_intake:download_status",
            tenant_id=str(tenant_id),
            document_id=str(doc_id),
            access_kind=None,
            candidate_id=str(candidate.id),
            reason="document_not_found",
            intake_channel="status_share",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        file_path, media_type, filename = resolve_document_file(doc)
    except FileNotFoundError:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:public_intake:download_status",
            tenant_id=str(tenant_id),
            document_id=str(doc_id),
            access_kind=None,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(candidate.id),
            reason="file_not_found",
            intake_channel="status_share",
        )
        raise HTTPException(status_code=404, detail="File not found") from None
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_FILE_DOWNLOADED,
        result="success",
        severity="info",
        source="http:public_intake:download_status",
        tenant_id=str(tenant_id),
        document_id=str(doc_id),
        access_kind=None,
        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
        candidate_id=str(candidate.id),
        response_mode="file_stream",
        intake_channel="status_share",
    )
    return FileResponse(str(file_path), media_type=media_type, filename=filename)


@router.put("/uploads/{token}/{storage_key:path}", status_code=204)
async def upload_public_storage_object(
    token: str,
    storage_key: str,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(public_intake_storage_upload_session),
) -> Response:
    db, tenant_id = db_tenant
    public_session = await _load_public_intake_session(db, tenant_id, token)
    allowed_prefix = _storage_allowed_prefix_for_session(public_session, tenant_id)
    normalized_key = storage_key.strip().lstrip("/\\")
    if not normalized_key.startswith(allowed_prefix):
        raise HTTPException(status_code=403, detail="Storage key does not belong to intake session")
    target_path = _resolve_storage_path(normalized_key)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as fh:
        async for chunk in request.stream():
            fh.write(chunk)
    return Response(status_code=204)
def _ensure_checklist_defaults(checklist: Dict[str, Any], ruleset: Dict[str, Any]) -> Dict[str, Any]:
    candidate_cfg = (ruleset.get("candidate") or {}).get("defaults") or {}
    fallback_cfg = _DEFAULT_CANDIDATE_DEFAULTS
    required = checklist.get("requiredTypes")
    optional = checklist.get("optionalTypes")
    if not required:
        checklist["requiredTypes"] = list(
            candidate_cfg.get("requiredTypes")
            or fallback_cfg.get("requiredTypes")
            or []
        )
    if not optional:
        checklist["optionalTypes"] = list(
            candidate_cfg.get("optionalTypes")
            or fallback_cfg.get("optionalTypes")
            or []
        )
    return checklist
