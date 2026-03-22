from __future__ import annotations

import secrets
import mimetypes
import os
import copy
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Sequence
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import delete, select, func, literal, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_consent import CandidateConsent
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.document import Document
from backend.app.models.magic_link import MagicLink
from backend.app.modules.documents.crud import ensure_ruleset_seed, list_candidate_documents, list_document_types
from backend.app.modules.documents.owner_summary import compute_owner_summary, EQUIVALENT_SATISFACTION
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.services.document_orders import has_ready_document
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.document_catalog import (
    doc_type_requires_user_comment,
    get_doc_type_defaults,
)
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.modules.documents.router import _build_synthetic_documents  # type: ignore
from backend.app.services.document_files import resolve_document_file
from backend.app.modules.documents.storage import get_uploads_root, sanitize_filename
from backend.app.services.extractors import auto_fill_from_file
from backend.app.services import reminders as reminders_service
from backend.app.models.enums import DocumentStatus
from backend.app.services.activity import log_public_event
from backend.app.services.legal_documents import list_active_for_tenant
from backend.app.services.events import EventAudience, emit_event
from backend.app.models.user import Role
from backend.app.services.source_labels import normalize_candidate_source
from backend.app.services.candidate_telegram_notifications import (
    send_candidate_documents_progress_telegram,
    sync_candidate_ready_for_handoff_gate,
)


_UPLOADS_ROOT = get_uploads_root()

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


class PublicIntakeCreateRequest(BaseModel):
    contacts: IntakeContacts
    vacancy_id: Optional[UUID] = None
    locale: Optional[str] = None
    source: Optional[str] = None


class PublicIntakeCreateResponse(BaseModel):
    apply_url: str
    token: str
    candidate_id: str
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
    candidate_id: str
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


class PublicStatusState(BaseModel):
    candidate_id: str
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
    email: Optional[EmailStr] = None
    phone_country_code: Optional[str] = None
    phone: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_contact(cls, data: "PublicMagicLinkRequest") -> "PublicMagicLinkRequest":
        if not (data.email or data.phone):
            raise ValueError("email or phone is required")
        return data


class PublicMagicLinkRequestResponse(BaseModel):
    status: str = "ok"
    cooldown_seconds: int = MIN_MAGIC_LINK_INTERVAL_SECONDS
    daily_limit: int = MAX_MAGIC_LINKS_PER_DAY


class PublicMagicLinkRedeemResponse(BaseModel):
    token: str
    apply_url: str
    status_share_token: Optional[str] = None
    expires_at: datetime
    candidate_id: str
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
    sanitized = sanitize_filename(filename) or "document.bin"
    return str(
        Path(candidate.tenant_id)
        / "candidates"
        / str(candidate.id)
        / f"{uuid4().hex}_{sanitized}"
    )


def _resolve_storage_path(relative: str) -> Path:
    rel = Path(relative.strip().lstrip("/\\"))
    candidate = (_UPLOADS_ROOT / rel).resolve()
    uploads_root = _UPLOADS_ROOT.resolve()
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
        "citizenship": (personal.get("citizenship") or "").upper() or None,
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

        safe_name = sanitize_filename(upload_file.filename if upload_file else "document")
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
    primary_entry = {
        "name": original_name or os.path.basename(rel_path),
        "url": download_url,
        "uploaded_at": datetime.utcnow().isoformat(),
        "source": "public-upload",
        "storage_path": rel_path,
        "version": next_version,
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


def _serialize_contacts(candidate: Candidate, state: Dict[str, Any]) -> IntakeContacts:
    contacts = dict(state.get("contacts") or {})
    data = IntakeContacts(
        phone_country_code=candidate.phone_country_code or contacts.get("phone_country_code"),
        phone=candidate.phone or contacts.get("phone"),
        email=candidate.email or contacts.get("email"),
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
    return IntakePersonal(
        full_name=full_name.strip(),
        citizenship=personal_data.get("citizenship") or extra.get("citizenship"),
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


def _serialize_employments(rows: List[CandidateEmployment]) -> List[IntakeEmployment]:
    serialized: List[IntakeEmployment] = []
    for row in rows[:MAX_EMPLOYMENTS]:
        serialized.append(
            IntakeEmployment(
                id=row.id,
                employer_name=row.employer_name,
                country=row.country,
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
    return IntakeData(
        contacts=_serialize_contacts(candidate, state),
        personal=_serialize_personal(candidate, state),
        experience=_serialize_experience(state),
        employments=_serialize_employments(employments),
        agreements=_serialize_agreements(state),
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
    for equivalent, parents in (EQUIVALENT_SATISFACTION or {}).items():
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
    ruleset_version = await ensure_ruleset_seed(
        session,
        str(tenant_id),
        load_default_ruleset(),
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    owner_context = _owner_context_from_state(state, candidate.id)
    checklist = compute_candidate_checklist(owner_context, ruleset_payload)
    checklist = _ensure_checklist_defaults(checklist, ruleset_payload)
    checklist = _ensure_checklist_defaults(checklist, ruleset_payload)

    docs = await list_candidate_documents(
        session,
        str(tenant_id),
        candidate.id,
        include_deleted=False,
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
    summary = compute_owner_summary(owner_context, ruleset_payload, serialized_docs)
    synthetic = [
        entry.model_dump()
        for entry in _build_synthetic_documents(str(tenant_id), UUID(candidate.id), checklist, serialized_docs)
    ]
    doc_entries = serialized_docs + synthetic
    doc_type_codes = _collect_doc_type_codes(checklist, doc_entries)
    if not doc_type_codes:
        catalog = await list_document_types(session, str(tenant_id))
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
) -> PublicIntakeState:
    data_payload, timeline = _build_state_components(candidate, employments, checklist, documents)
    return PublicIntakeState(
        token=candidate.intake_token or "",
        candidate_id=candidate.id,
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
        personal_dict["citizenship"] = personal.citizenship.upper()
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
        extra["citizenship"] = personal.citizenship.upper()
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


@router.post("/intake", response_model=PublicIntakeCreateResponse)
async def create_public_intake(
    payload: PublicIntakeCreateRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicIntakeCreateResponse:
    contacts = payload.contacts
    if not contacts.has_contact():
        raise HTTPException(status_code=422, detail="phone or email is required")
    db, tenant_id = db_tenant

    candidate = await _find_candidate_by_contact(
        db,
        tenant_id,
        email=contacts.email,
        phone_country_code=contacts.phone_country_code,
        phone=contacts.phone,
    )
    now = _now()
    expires_at = now + timedelta(days=INTAKE_TOKEN_TTL_DAYS)

    if candidate:
        state = _ensure_intake_state(candidate)
        stored_contacts = dict(state.get("contacts") or {})
        for key, value in contacts.model_dump(exclude_none=True).items():
            stored_contacts[key] = value
        state["contacts"] = stored_contacts
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
        await log_public_event(
            db,
            tenant_id=str(tenant_id),
            action="intake_link_reused",
            target_id=candidate.id,
            payload={
                "contacts": contacts.model_dump(exclude_none=True),
                "source": normalize_candidate_source(payload.source),
            },
        )
        await db.commit()
        return PublicIntakeCreateResponse(
            apply_url=f"/public/apply/{candidate.intake_token}",
            token=candidate.intake_token or "",
            candidate_id=candidate.id,
            expires_at=expires_at,
        )

    token = _generate_token()
    intake_source = normalize_candidate_source(payload.source, default="Анкета")
    candidate = Candidate(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        first_name="Candidate",
        last_name="Draft",
        phone_country_code=contacts.phone_country_code,
        phone=contacts.phone,
        email=contacts.email,
        intake_token=token,
        intake_token_created_at=now,
        intake_token_expires_at=expires_at,
        intake_status="draft",
        stage="docs_wait",
        source=intake_source,
    )
    state = {
        "contacts": contacts.model_dump(),
        "personal": {},
        "experience": {},
        "agreements": {},
    }
    candidate.intake_state = state
    _ensure_status_share_token(candidate)

    db.add(candidate)
    await db.commit()

    return PublicIntakeCreateResponse(
        apply_url=f"/public/apply/{token}",
        token=token,
        candidate_id=candidate.id,
        expires_at=expires_at,
    )


@router.get("/apply/{token}", response_model=PublicIntakeState)
async def get_public_intake(
    token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicIntakeState:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
    if _ensure_status_share_token(candidate):
        await db.commit()
    employments = await _list_employments(db, tenant_id, candidate.id)
    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    return _response_payload(candidate, employments, checklist, documents)


@router.post("/magic-link/request", response_model=PublicMagicLinkRequestResponse)
async def request_public_magic_link(
    payload: PublicMagicLinkRequest,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicMagicLinkRequestResponse:
    db, tenant_id = db_tenant
    candidate = await _find_candidate_by_contact(
        db,
        tenant_id,
        email=payload.email,
        phone_country_code=payload.phone_country_code,
        phone=payload.phone,
    )
    if candidate:
        contact_type = "email" if payload.email else "phone"
        phone_parts = _normalize_phone_parts(payload.phone_country_code, payload.phone)
        contact_value = _contact_value(
            contact_type,
            email=payload.email,
            phone=phone_parts,
        )
        if contact_value:
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
    await db.commit()
    return PublicMagicLinkRequestResponse(
        cooldown_seconds=MIN_MAGIC_LINK_INTERVAL_SECONDS,
        daily_limit=MAX_MAGIC_LINKS_PER_DAY,
    )


@router.get("/magic-link/{token}", response_model=PublicMagicLinkRedeemResponse)
async def redeem_public_magic_link(
    token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicMagicLinkRedeemResponse:
    db, tenant_id = db_tenant
    link = await _load_magic_link(db, tenant_id, token)
    if not link.candidate_id:
        raise HTTPException(status_code=404, detail="Candidate not attached to link")
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicStatusState:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    employments = await _list_employments(db, tenant_id, candidate.id)
    checklist, documents = await _build_checklist_and_docs(
        db,
        tenant_id,
        candidate,
        download_scope="status",
        download_token=share_token,
    )
    return _status_response_payload(candidate, employments, checklist, documents)


@router.post("/status/{share_token}/rotate", response_model=PublicStatusRotateResponse)
async def rotate_public_status_token(
    share_token: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicStatusRotateResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    _ensure_status_share_token(candidate)
    await db.commit()
    return PublicStatusRotateResponse(
        status_share_token=candidate.status_share_token or "",
        expires_at=candidate.status_share_token_expires_at or (_now() + timedelta(days=INTAKE_TOKEN_TTL_DAYS)),
    )



@router.put("/apply/{token}", response_model=PublicIntakeState)
async def update_public_intake(
    token: str,
    payload: PublicIntakeUpdateRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicIntakeState:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicIntakeState:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
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
    docs = await list_candidate_documents(
        db,
        str(tenant_id),
        candidate.id,
        include_deleted=False,
    )
    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    missing_required = [
        doc_type
        for doc_type in checklist.get("requiredTypes") or []
        if not has_ready_document(docs, doc_type)
    ]
    intake_state = _ensure_intake_state(candidate)
    intake_payload = IntakeData(
        contacts=IntakeContacts(**(intake_state.get("contacts") or {})),
        personal=IntakePersonal(**(intake_state.get("personal") or {})),
        experience=IntakeExperience(**(intake_state.get("experience") or {})),
        employments=intake_state.get("employments") or [],
        agreements=IntakeAgreements(**(intake_state.get("agreements") or {})),
    )
    _update_candidate_from_data(candidate, intake_payload)
    state["employments"] = [_employment_state_payload(entry) for entry in intake_payload.employments] or state.get("employments") or []
    if intake_payload.employments:
        await _upsert_employments(db, tenant_id, candidate.id, intake_payload.employments)
    candidate.stage = "questionnaire_submitted"
    candidate.intake_status = "submitted"
    candidate.intake_submitted_at = _now()
    await _log_consent_snapshot(db, tenant_id, candidate.id, payload, client_ip, user_agent)

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
    await db.commit()

    checklist, documents = await _build_checklist_and_docs(db, tenant_id, candidate)
    return _response_payload(candidate, employments, checklist, documents)


@router.post("/apply/{token}/documents/presign", response_model=PublicPresignResponse)
async def presign_public_document_upload(
    token: str,
    payload: PublicPresignRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicPresignResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
    filename = payload.filename.strip() or f"{payload.doc_type}.bin"
    key = _build_storage_key(candidate, filename)
    url = f"/api/v1/public/uploads/{token}/{key}"
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicPresignResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_status_token(db, tenant_id, share_token)
    if not _candidate_contact_matches(
        candidate,
        email=payload.email,
        phone_country_code=payload.phone_country_code,
        phone=payload.phone,
    ):
        raise HTTPException(status_code=403, detail="Contact verification failed")
    filename = payload.filename.strip() or f"{payload.doc_type}.bin"
    key = _build_storage_key(candidate, filename)
    url = f"/api/v1/public/uploads/{share_token}/{key}"
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PublicIntakeState:
    if not doc_type.strip():
        raise HTTPException(status_code=422, detail="doc_type is required")
    if not file and not storage_key:
        raise HTTPException(status_code=422, detail="file or storage_key is required")
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
    await _save_public_document_upload(
        db,
        candidate,
        doc_type.strip(),
        upload_file=file,
        storage_key=storage_key,
        user_comment=user_comment,
    )
    try:
        await send_candidate_documents_progress_telegram(
            db,
            tenant_id=str(tenant_id),
            candidate=candidate,
            source_doc_type=doc_type.strip(),
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> FileResponse:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
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
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        file_path, media_type, filename = resolve_document_file(doc)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    return FileResponse(str(file_path), media_type=media_type, filename=filename)


@router.get("/status/{share_token}/documents/{doc_id}/file")
async def download_status_document_file(
    share_token: str,
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
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
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        file_path, media_type, filename = resolve_document_file(doc)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    return FileResponse(str(file_path), media_type=media_type, filename=filename)


@router.put("/uploads/{token}/{storage_key:path}", status_code=204)
async def upload_public_storage_object(
    token: str,
    storage_key: str,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Response:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, token)
    allowed_prefix = f"{candidate.tenant_id}/candidates/{candidate.id}/"
    normalized_key = storage_key.strip().lstrip("/\\")
    if not normalized_key.startswith(allowed_prefix):
        raise HTTPException(status_code=403, detail="Storage key does not belong to candidate")
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
