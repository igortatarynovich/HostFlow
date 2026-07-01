from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
try:
    from pydantic import BaseModel, EmailStr, Field, field_validator
except ImportError:  # pragma: no cover - Pydantic < 2 compatibility
    from pydantic import BaseModel, EmailStr, Field, validator

    def field_validator(*fields, **kwargs):  # type: ignore[misc]
        decorator = validator(*fields, **kwargs)

        def _wrapper(func):
            if isinstance(func, classmethod):  # unwrap classmethod for pydantic v1
                func = func.__func__  # type: ignore[attr-defined]
            return decorator(func)

        return _wrapper
from datetime import date, datetime

from backend.app.api.v1.reminders_v2 import ReminderOut

class CandidateCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    languages: Optional[Union[List[str], str]] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    status_reason: Optional[List[str]] = None
    email: Optional[EmailStr] = None
    note: Optional[str] = None
    manager: Optional[str] = None
    manager_id: Optional[str] = None
    company_id: Optional[str] = None  # UUID as str
    vacancy_id: Optional[str] = None  # UUID as str
    extra: Optional[Dict[str, Any]] = None
    docs_progress: Optional[Dict[str, Any]] = None
    personal_data: Optional[Dict[str, Any]] = None
    contacts: Optional[Dict[str, Any]] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("must not be empty")
        return s

    @field_validator("languages")
    @classmethod
    def _normalize_langs(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            return [p.strip() for p in s.split(",") if p.strip()] if s else []
        raise TypeError("languages must be list[str] or str")

    @field_validator("phone_country_code")
    @classmethod
    def _normalize_dial_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        # if it's purely digits and has no leading '+', prefix it
        if s.isdigit() and not s.startswith('+'):
            return "+" + s
        return s

    @field_validator("extra", "docs_progress")
    @classmethod
    def _ensure_dicts(cls, v: Optional[Union[Dict[str, Any], str]]):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                j = json.loads(s)
                return j if isinstance(j, dict) else None
            except Exception:
                return None
        return None

class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    languages: Optional[Union[List[str], str, None]] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    status_reason: Optional[List[str]] = None
    email: Optional[EmailStr] = None
    note: Optional[str] = None
    manager: Optional[str] = None
    manager_id: Optional[str] = None
    company_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    docs_progress: Optional[Dict[str, Any]] = None
    personal_data: Optional[Dict[str, Any]] = None
    contacts: Optional[Dict[str, Any]] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _not_empty_when_present(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        if not s:
            raise ValueError("must not be empty")
        return s

    @field_validator("languages")
    @classmethod
    def _normalize_langs(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            return [p.strip() for p in s.split(",") if p.strip()] if s else []
        raise TypeError("languages must be list[str] or str or None")

    @field_validator("phone_country_code")
    @classmethod
    def _normalize_dial_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        # if it's purely digits and has no leading '+', prefix it
        if s.isdigit() and not s.startswith('+'):
            return "+" + s
        return s

    @field_validator("extra", "docs_progress")
    @classmethod
    def _ensure_dicts(cls, v: Optional[Union[Dict[str, Any], str]]):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                j = json.loads(s)
                return j if isinstance(j, dict) else None
            except Exception:
                return None
        return None

class CandidateOut(BaseModel):
    id: str
    tenant_id: str
    short_id: Optional[str] = None
    first_name: str
    last_name: str
    first_name_latin: Optional[str] = None
    last_name_latin: Optional[str] = None
    phone: Optional[str] = None           # raw number
    phone_display: Optional[str] = None   # pretty +XX NNN
    phone_country_code: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    stage: Optional[str] = None
    status_reason: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    note: Optional[str] = None
    manager: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    vacancy_id: Optional[str] = None
    vacancy_title: Optional[str] = None
    manager_short: Optional[str] = None
    manager_name: Optional[str] = None
    # Phase 2.6.G-5 Stage F — canonical owner columns exposed on the wire
    # alongside the legacy ``manager*`` fields. The runtime payload built
    # by ``_serialize_candidate_row`` has always carried them (joined from
    # ``users`` via ``Candidate.recruiter_id``); declaring them on the
    # Pydantic schema makes the OpenAPI contract match reality so the
    # generated TypeScript types stop falling back to ``any``/``unknown``.
    recruiter_id: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_short: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    city_latin: Optional[str] = None
    address_latin: Optional[str] = None
    birth_date: Optional[date] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    docs_progress: Dict[str, Any] = Field(default_factory=dict)
    personal_data: Dict[str, Any] = Field(default_factory=dict)
    contacts: Dict[str, Any] = Field(default_factory=dict)
    intake_status: Optional[str] = None
    intake_submitted_at: Optional[datetime] = None
    intake_contacts: Dict[str, Any] = Field(default_factory=dict)
    intake_personal: Dict[str, Any] = Field(default_factory=dict)
    intake_experience: Dict[str, Any] = Field(default_factory=dict)
    intake_agreements: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def _as_dict(cls, v: Any) -> Dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                j = json.loads(v)
                return j if isinstance(j, dict) else {}
            except Exception:
                return {}
        return {}

    @classmethod
    def from_model(
        cls,
        c: Any,
        *,
        company_name: Optional[str] = None,
        vacancy_title: Optional[str] = None,
        manager_short: Optional[str] = None,
        manager_name: Optional[str] = None,
        recruiter_short: Optional[str] = None,
        recruiter_name: Optional[str] = None,
    ) -> "CandidateOut":
        # normalize languages from model (list[str] | comma-separated str | None)
        langs = getattr(c, "languages", None)
        if isinstance(langs, list):
            languages: List[str] = [str(x).strip() for x in langs if str(x).strip()]
        elif isinstance(langs, str):
            s = langs.strip()
            languages = [p.strip() for p in s.split(",") if p.strip()] if s else []
        else:
            languages = []

        # Normalize tags from model
        tags: List[str] = getattr(c, "tags", []) or []
        if not isinstance(tags, list):
            tags = []
        
        # Get is_favorite from model
        is_favorite: bool = getattr(c, "is_favorite", False) or False

        # optional UUID-like fields rendered as str or None
        def _str_or_none(v: Any) -> Optional[str]:
            return str(v) if v else None

        # pull extra once for fallbacks
        extra_dict = cls._as_dict(getattr(c, "extra", None))

        def _fallback(name: str, current: Any) -> Any:
            if current is not None:
                return current
            # return value from extra if present
            return extra_dict.get(name)

        # resolve fields that might live in extra
        country_code_val = _fallback("country_code", getattr(c, "country_code", None))
        city_val = _fallback("city", getattr(c, "city", None))
        address_val = _fallback("address", getattr(c, "address", None))

        # birth_date may come as date or ISO string from extra
        birth_date_attr = getattr(c, "birth_date", None)
        if birth_date_attr is not None:
            birth_date_val = birth_date_attr
        else:
            _bd = extra_dict.get("birth_date")
            if isinstance(_bd, date):
                birth_date_val = _bd
            elif isinstance(_bd, str):
                try:
                    birth_date_val = date.fromisoformat(_bd)
                except Exception:
                    birth_date_val = None
            else:
                birth_date_val = None

        personal_payload = cls._as_dict(getattr(c, "personal_data", None))
        contacts_payload = cls._as_dict(getattr(c, "contacts", None))
        raw_intake_state = getattr(c, "intake_state", None)
        if not isinstance(raw_intake_state, dict):
            raw_intake_state = {}
        intake_contacts = cls._as_dict(raw_intake_state.get("contacts"))
        intake_personal = cls._as_dict(raw_intake_state.get("personal"))
        intake_experience = cls._as_dict(raw_intake_state.get("experience"))
        intake_agreements = cls._as_dict(raw_intake_state.get("agreements"))

        return cls(
            id=str(getattr(c, "id", "")),
            tenant_id=str(getattr(c, "tenant_id", "")),
            short_id=getattr(c, "short_id", None),
            first_name=str(getattr(c, "first_name", "")),
            last_name=str(getattr(c, "last_name", "")),
            first_name_latin=getattr(c, "first_name_latin", None),
            last_name_latin=getattr(c, "last_name_latin", None),
            phone=getattr(c, "phone", None),
            phone_display=getattr(c, "phone_display", None) if hasattr(c, "phone_display") else None,
            phone_country_code=getattr(c, "phone_country_code", None),
            languages=languages,
            tags=tags,
            is_favorite=is_favorite,
            stage=getattr(c, "stage", None),
            email=getattr(c, "email", None),
            note=getattr(c, "note", None),
            manager=getattr(c, "manager", None),
            company_id=_str_or_none(getattr(c, "company_id", None)),
            company_name=company_name,
            vacancy_id=_str_or_none(getattr(c, "vacancy_id", None)),
            vacancy_title=vacancy_title,
            manager_short=manager_short,
            manager_name=manager_name,
            # Phase 2.6.G-5 Stage F — always mirror the canonical
            # recruiter_id from the model onto the wire. ``manager`` column
            # is still populated (shadow-write per Stage D) but downstream
            # consumers should prefer ``recruiter_id`` going forward.
            recruiter_id=_str_or_none(getattr(c, "recruiter_id", None)),
            recruiter_name=recruiter_name,
            recruiter_short=recruiter_short,
            country_code=country_code_val,
            city=city_val,
            address=address_val,
            city_latin=getattr(c, "city_latin", None),
            address_latin=getattr(c, "address_latin", None),
            birth_date=birth_date_val,
            extra=extra_dict,
            docs_progress=cls._as_dict(getattr(c, "docs_progress", None)),
            personal_data=personal_payload,
            contacts=contacts_payload,
            intake_status=getattr(c, "intake_status", None),
            intake_submitted_at=getattr(c, "intake_submitted_at", None),
            intake_contacts=intake_contacts,
            intake_personal=intake_personal,
            intake_experience=intake_experience,
            intake_agreements=intake_agreements,
        )


class CandidateTimelineEventOut(BaseModel):
    at: datetime
    kind: str
    source: str
    title: Optional[str] = None
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class CandidateTimelineResponse(BaseModel):
    items: List[CandidateTimelineEventOut] = Field(default_factory=list)


class CandidateChangeLogItemOut(BaseModel):
    at: datetime
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class CandidateChangeLogResponse(BaseModel):
    items: List[CandidateChangeLogItemOut] = Field(default_factory=list)


# --- Work panel aggregate (R1.5 Phase D) ------------------------------------


class CandidateWorkPanelProfileOut(BaseModel):
    contact_policy_enabled: bool = False
    contact_attempt_count: int = 0
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    risk_drivers: List[str] = Field(default_factory=list)
    risk_updated_at: Optional[str] = None
    risk_version: Optional[str] = None


class CandidateWorkPanelCommsOut(BaseModel):
    messages_relative_url: str
    email_relative_url: str
    documents_relative_url: str


class CandidateWorkPanelDocumentsSummaryOut(BaseModel):
    """Subset of documents owner summary for list work-panel (readiness metrics only)."""

    percent_ready: int = 0
    status: Optional[str] = None
    missing: List[str] = Field(default_factory=list)
    problematic: List[str] = Field(default_factory=list)
    ready_types: List[str] = Field(default_factory=list)
    in_progress_types: List[str] = Field(default_factory=list)
    expiring_soon: List[Dict[str, Any]] = Field(default_factory=list)


class CandidateWorkPanelLinkedDocumentOut(BaseModel):
    document_id: Optional[str] = None
    document_type_code: Optional[str] = None
    status: Optional[str] = None


class CandidateWorkPanelRequirementRowOut(BaseModel):
    requirement_code: str
    public_name: Optional[str] = None
    fulfilled: bool = False
    evaluation_status: Optional[str] = None
    evidence_variant_code: Optional[str] = None
    evidence_status: Optional[str] = None
    linked_document: Optional[CandidateWorkPanelLinkedDocumentOut] = None


class CandidateWorkPanelRequirementsSummaryOut(BaseModel):
    all_fulfilled: bool = False
    pipeline_blockers: Dict[str, Any] = Field(default_factory=dict)
    items: List[CandidateWorkPanelRequirementRowOut] = Field(default_factory=list)


class CandidateWorkPanelPipelineOverrideOut(BaseModel):
    id: str
    doc_type_code: Optional[str] = None
    requirement_code: Optional[str] = None
    status: str
    requested_scope: str
    granted_scope: Optional[str] = None
    reason: str
    review_note: Optional[str] = None
    requested_by_user_id: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None


class CandidateWorkPanelPipelineOverridesOut(BaseModel):
    items: List[CandidateWorkPanelPipelineOverrideOut] = Field(default_factory=list)


class CandidateWorkPanelResponse(BaseModel):
    profile: CandidateWorkPanelProfileOut
    reminders: List[ReminderOut]
    timeline: CandidateTimelineResponse
    comms: CandidateWorkPanelCommsOut
    documents_summary: Optional[CandidateWorkPanelDocumentsSummaryOut] = None
    requirements_summary: Optional[CandidateWorkPanelRequirementsSummaryOut] = None
    pipeline_overrides: Optional[CandidateWorkPanelPipelineOverridesOut] = None


# --- Recruitment applications (intent layer read model) ----------------------


class RecruitmentApplicationOut(BaseModel):
    """One row of ``recruitment_applications`` for recruiter UI (read-only)."""

    id: str
    candidate_id: str
    lead_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    source: str = "meta"
    recruiter_id: Optional[str] = None
    applied_at: datetime
    status: str = "applied"
    application_cycle: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": False}
