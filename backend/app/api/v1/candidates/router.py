import logging
from typing import List, Tuple
from uuid import UUID
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status, Body, Header
from fastapi import Query
from sqlalchemy import select, func, update, text, or_
from sqlalchemy import exists
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional
from typing import Any, Dict, Literal
from pydantic import BaseModel, Field

class BulkStageIn(BaseModel):
    candidate_ids: List[UUID] = Field(default_factory=list)
    stage: str = Field(min_length=1)
    status_reason: Optional[List[str]] = Field(default=None)

class BulkStageItemOut(BaseModel):
    candidate_id: str
    stage: str
    ok: bool
    error: Optional[str] = None

class BulkManagerIn(BaseModel):
    candidate_ids: List[UUID] = Field(default_factory=list)
    manager_id: UUID = Field(description="User id of manager")

class BulkManagerItemOut(BaseModel):
    candidate_id: str
    manager: Optional[str]
    ok: bool
    error: Optional[str] = None

class BulkDeleteIn(BaseModel):
    candidate_ids: List[UUID] = Field(default_factory=list)

class BulkDeleteItemOut(BaseModel):
    candidate_id: str
    ok: bool
    error: Optional[str] = None


class CandidateListAvailableStatusesOut(BaseModel):
    """Distinct pipeline stages and row-level status values visible to the current list scope (tenant + ACL)."""

    schema_version: Literal[1] = 1
    stages: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(
        default_factory=list,
        description="Distinct ``Candidate.status`` values (non-empty), if used by the tenant.",
    )


class CandidateUploadLinkOut(BaseModel):
    apply_url: str
    documents_url: Optional[str] = None
    status_url: Optional[str] = None
    intake_token: str
    status_share_token: Optional[str] = None
    expires_at: Optional[datetime] = None

# CreateCandidateIn model
class CreateCandidateIn(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    languages: Optional[list[str] | str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    birth_date: Optional[date | str] = None
    address: Optional[dict] = None
    stage: Optional[str] = None
    manager_id: Optional[UUID] = Field(default=None, description="User id of manager")
    manager: Optional[str] = Field(default=None, description="Alias: same as manager_id")
    company_id: Optional[UUID] = None
    vacancy_id: Optional[UUID] = None

from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx

from backend.app.api.v1.candidates import service as cand_service
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.api.v1.candidates import repo as cand_repo
from backend.app.models.candidate import Candidate
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.models.audit import ActivityLog
from backend.app.models.user import User
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.tenant import Tenant, TenantLicense, TenantLink
from backend.app.api.v1.candidates.acl import (
    CandidateACL,
    apply_agency_acl_filters,
    ensure_candidate_access,
    resolve_candidate_acl,
    candidate_acl_sql_or_clause,
)
from backend.app.auth.hiring_workspace_roles import (
    HIRING_CANDIDATE_MUTATE_ROLES,
    HIRING_CANDIDATE_VIEW_ROLES,
)
from backend.app.services.tenant_visibility import get_tenant_visibility
from backend.app.services.handoff import (
    is_client_tenant,
    is_client_tenant_for_list,
    get_pending_handoff,
    get_accepted_handoff,
    has_pending_handoff_for_client,
    client_has_accepted_handoff,
    can_agency_edit,
    can_client_edit,
)
from backend.app.services.recruitment_handoff_write_guard import agency_candidate_has_internal_hr_handoff_lane
from backend.app.api.public.intake import _ensure_intake_token, _ensure_status_share_token
from backend.app.services import billing_restrictions, portal_candidate_usage
from backend.app.core.settings import settings
from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.modules.documents import crud as documents_crud
from backend.app.services import candidate_notifications
from backend.app.services.audit import log_audit_event
from backend.app.services.risk_scoring import CandidateRisk, compute_candidate_risk_scores
from backend.app.api.v1.candidates.schemas import (
    CandidateTimelineResponse,
    CandidateChangeLogItemOut,
    CandidateChangeLogResponse,
    CandidateWorkPanelResponse,
    RecruitmentApplicationOut,
)
from backend.app.services.recruitment_application_lifecycle import normalize_application_status
from backend.app.services.recruitment_application_service import list_recruitment_applications_for_candidate
from backend.app.services.candidate_workforce_lock import is_candidate_locked_by_workforce
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    AgencyRecruitmentWriteBypass,
    is_recruitment_recruiter_write_locked_by_handoff,
)
from backend.app.services.candidate_timeline import fetch_candidate_timeline_events
from backend.app.services.candidate_work_panel import load_candidate_work_panel
from backend.app.constants.stages import is_candidate_operationally_terminal, is_pipeline_completed_stage
from backend.app.db.candidate_operational_sql import sql_candidate_active_operational_pipeline



router = APIRouter()

ALLOW_MANAGER_ROLES = HIRING_CANDIDATE_MUTATE_ROLES
CANDIDATE_VIEW_ROLES = HIRING_CANDIDATE_VIEW_ROLES

# Helpers to read profile fields from extra
from typing import Any as _Any
import json

def _extra_dict(obj: _Any) -> dict:
    """Safe dict from obj.extra. Supports dict or JSON-encoded string."""
    try:
        extra = getattr(obj, "extra", None)
        # Already a dict
        if isinstance(extra, dict):
            return extra
        # Sometimes JSON is stored as a string in SQLite
        if isinstance(extra, str):
            try:
                import json
                parsed = json.loads(extra)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    except Exception:
        pass
    return {}


def _tags_list(value: _Any) -> list[str]:
    """Ensure tags is returned as list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return sorted(list(set(str(v).strip() for v in value if str(v).strip())))
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            decoded = json.loads(s)
            if isinstance(decoded, (list, tuple, set)):
                tags = [str(v).strip() for v in decoded if str(v).strip()]
                return sorted(list(set(tags)))
            else:
                return sorted(list(set([str(decoded).strip()])))
        except Exception:
            parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
            return sorted(list(set(parts)))
    return []


def _status_reason_list(value: _Any) -> list[str]:
    """Ensure status_reason is returned as list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            parts = [p.strip() for p in s.split(",")]
            return [p for p in parts if p]
    return []


def _get_profile_field(obj: _Any, key: str):
    """Get field from extra.profile[key] if present, else None."""
    try:
        extra = _extra_dict(obj)
        profile = extra.get("profile") or {}
        return profile.get(key)
    except Exception:
        return None

def _docs_progress_dict(obj: _Any) -> dict:
    """Safe dict from obj.docs_progress (json stored as text)."""
    try:
        docs = getattr(obj, "docs_progress", None)
        if isinstance(docs, dict):
            return docs
        if isinstance(docs, str):
            try:
                parsed = json.loads(docs)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
    except Exception:
        pass
    return {}


def _intake_application_kind_from_model(c: _Any) -> Optional[str]:
    """`candidate` vs `client` from `intake_state.application_kind` (public intake)."""
    raw = getattr(c, "intake_state", None)
    if not isinstance(raw, dict):
        return None
    if "application_kind" not in raw:
        return None
    return "client" if str(raw.get("application_kind") or "").strip().lower() == "client" else "candidate"


def _serialize_candidate_row(row: Tuple[_Any, ...]) -> Dict[str, Any]:
    if not row:
        raise ValueError("Empty candidate row")

    padded = list(row) + [None] * (8 - len(row))
    c = padded[0]
    company_name = padded[1] or getattr(c, "company_id", None)
    manager_raw = padded[2] or getattr(c, "manager", None)
    manager_name = padded[3] or manager_raw
    vacancy_name = padded[4]
    recruiter_id = padded[5] or getattr(c, "recruiter_id", None)
    recruiter_name = padded[6]
    recruiter_short = padded[7]
    if manager_raw and manager_name and str(manager_name) == str(manager_raw):
        if recruiter_id and str(recruiter_id) == str(manager_raw):
            manager_name = recruiter_name or recruiter_short or manager_name

    label_primary = None
    label_secondary = None
    stage_label = None

    extra_payload = _extra_dict(c)
    personal_data = getattr(c, "personal_data", None)
    if not isinstance(personal_data, dict) or not personal_data:
        personal_data = extra_payload.get("personal_data", {}) if isinstance(extra_payload, dict) else {}
    contacts = getattr(c, "contacts", None)
    if not isinstance(contacts, dict) or not contacts:
        contacts = extra_payload.get("contacts", {}) if isinstance(extra_payload, dict) else {}

    languages = getattr(c, "languages", None) or personal_data.get("languages") or _get_profile_field(c, "languages")
    country_code = personal_data.get("country_code") or getattr(c, "country_code", None) or _get_profile_field(c, "country_code")
    city = personal_data.get("city") or getattr(c, "city", None) or _get_profile_field(c, "city")
    birth_date = personal_data.get("birth_date") or getattr(c, "birth_date", None) or _get_profile_field(c, "birth_date")
    address = personal_data.get("address") or getattr(c, "address", None) or _get_profile_field(c, "address")

    return {
        "id": str(c.id),
        "tenant_id": str(getattr(c, "tenant_id", "")) if getattr(c, "tenant_id", None) else None,
        "short_id": getattr(c, "short_id", None),
        "first_name": getattr(c, "first_name", None),
        "last_name": getattr(c, "last_name", None),
        "phone": contacts.get("phone") or getattr(c, "phone", None),
        "phone_country_code": contacts.get("phone_country_code") or getattr(c, "phone_country_code", None),
        "languages": languages,
        "country_code": country_code,
        "city": city,
        "birth_date": birth_date,
        "address": address,
        "email": contacts.get("email") or getattr(c, "email", None),
        "note": getattr(c, "note", None),
        "notes": getattr(c, "note", None),  # alias for legacy consumers
        "stage": getattr(c, "stage", None),
        "row_status": getattr(c, "status", None),
        "status": getattr(c, "status", None) or getattr(c, "stage", None),
        "stage_label": stage_label,
        "status_reason": _status_reason_list(getattr(c, "status_reason", None)),
        "tags": _tags_list(getattr(c, "tags", None)),
        "manager": manager_name or manager_raw or "",
        "manager_name": manager_name or manager_raw or "",
        "manager_id": manager_raw,
        "vacancy": vacancy_name or company_name or "",
        "vacancy_name": vacancy_name or company_name or "",
        "vacancy_title": vacancy_name or company_name or "",
        "labels": [x for x in [label_primary, label_secondary] if x],
        "company_id": getattr(c, "company_id", None),
        "company_name": company_name,
        "vacancy_id": getattr(c, "vacancy_id", None),
        "recruiter_id": recruiter_id,
        "recruiter_name": recruiter_name or recruiter_id or "",
        "recruiter_short": recruiter_short or "",
        "source": getattr(c, "source", None),
        "origin": getattr(c, "origin", None),
        "created_at": getattr(c, "created_at", None),
        "updated_at": getattr(c, "updated_at", None),
        "extra": extra_payload,
        "docs_progress": _docs_progress_dict(c),
        "personal_data": personal_data or {},
        "contacts": contacts or {},
        "intake_application_kind": _intake_application_kind_from_model(c),
    }


_CANDIDATE_OWNED_OVERRIDE_KEYS = {
    "first_name",
    "last_name",
    "email",
    "phone",
    "phone_country_code",
    "languages",
    "country_code",
    "city",
    "birth_date",
    "address",
    "personal_data",
    "contacts",
}


def _normalize_compare_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize_compare_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _normalize_compare_value(v) for k, v in value.items()}
    if isinstance(value, str):
        return value.strip()
    return value


def _candidate_value_for_key(candidate: Candidate, key: str) -> Any:
    personal_data = getattr(candidate, "personal_data", None)
    if not isinstance(personal_data, dict):
        personal_data = {}
    contacts_data = getattr(candidate, "contacts", None)
    if not isinstance(contacts_data, dict):
        contacts_data = {}
    if key == "first_name":
        return getattr(candidate, "first_name", None)
    if key == "last_name":
        return getattr(candidate, "last_name", None)
    if key == "email":
        return contacts_data.get("email") or getattr(candidate, "email", None)
    if key == "phone":
        return contacts_data.get("phone") or getattr(candidate, "phone", None)
    if key == "phone_country_code":
        return contacts_data.get("phone_country_code") or getattr(candidate, "phone_country_code", None)
    if key == "languages":
        return getattr(candidate, "languages", None)
    if key == "country_code":
        return personal_data.get("country_code") or getattr(candidate, "country_code", None)
    if key == "city":
        return personal_data.get("city") or getattr(candidate, "city", None)
    if key == "birth_date":
        return personal_data.get("birth_date") or getattr(candidate, "birth_date", None)
    if key == "address":
        return personal_data.get("address") or getattr(candidate, "address", None)
    if key == "personal_data":
        return personal_data
    if key == "contacts":
        return contacts_data
    return None


def _candidate_owned_value_is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _detect_candidate_override_changes(
    candidate: Candidate,
    incoming: Dict[str, Any],
) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    changed_fields: List[str] = []
    diff_payload: Dict[str, Dict[str, Any]] = {}
    for key in _CANDIDATE_OWNED_OVERRIDE_KEYS:
        if key not in incoming:
            continue
        new_val = _normalize_compare_value(incoming.get(key))
        old_val = _normalize_compare_value(_candidate_value_for_key(candidate, key))
        if old_val != new_val:
            changed_fields.append(key)
            diff_payload[key] = {"old": old_val, "new": new_val}
    return changed_fields, diff_payload


def _candidate_owned_corrections_requiring_override_reason(
    candidate: Candidate,
    incoming: Dict[str, Any],
) -> List[str]:
    """Owned-field updates that replace an already meaningful value (not first fill)."""
    correction_fields: List[str] = []
    for key in _CANDIDATE_OWNED_OVERRIDE_KEYS:
        if key not in incoming:
            continue
        new_val = _normalize_compare_value(incoming.get(key))
        old_val = _normalize_compare_value(_candidate_value_for_key(candidate, key))
        if old_val != new_val and _candidate_owned_value_is_meaningful(old_val):
            correction_fields.append(key)
    return correction_fields


def _candidate_patch_is_close_action(payload: Dict[str, Any]) -> bool:
    stage_raw = payload.get("stage")
    status_raw = payload.get("status")
    if stage_raw is not None and is_pipeline_completed_stage(str(stage_raw)):
        return True
    if status_raw is not None and is_pipeline_completed_stage(str(status_raw)):
        return True
    return False


def _mask_candidate_pre_handoff(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    RODO mask for client viewing candidates before handoff (no pending/accepted).
    Keep: short_id, citizenship, experience without employer names.
    Remove: PII (name, email, phone), documents, personal_data, contacts.
    Candidate must not be identifiable.
    """
    out = dict(d)
    # Remove PII — keep short_id
    # Принудительно удаляем все PII данные
    pii_keys = ("first_name", "last_name", "first_name_latin", "last_name_latin", "email",
                "phone", "phone_country_code")
    for key in pii_keys:
        # Сначала удаляем ключ если он существует
        if key in out:
            del out[key]
        # Затем устанавливаем в None для гарантии, что данные не будут отображаться
        # Это важно, потому что некоторые сериализаторы могут возвращать None как строку "None"
        out[key] = None
    
    # Дополнительная проверка: убеждаемся что ключи действительно None
    for key in pii_keys:
        if out.get(key) is not None and out.get(key) != "":
            logging.getLogger(__name__).warning(
                "_mask_candidate_pre_handoff: PII key %s still has value %s after masking, forcing None",
                key,
                out.get(key),
            )
            out[key] = None
    # Strip employer_name/company from experience (keep position, dates, country etc.)
    def _strip_employers(obj: Any) -> Any:
        if isinstance(obj, list):
            return [
                {k: v for k, v in (x if isinstance(x, dict) else {}).items()
                 if k not in ("employer_name", "company", "employer")}
                for x in obj
            ]
        return obj

    extra = out.get("extra")
    if isinstance(extra, dict):
        extra = dict(extra)
        for key in ("profile", "experience", "employments"):
            if key in extra:
                extra[key] = _strip_employers(extra[key])
        profile = extra.get("profile")
        if isinstance(profile, dict):
            profile = dict(profile)
            if "experience" in profile:
                profile["experience"] = _strip_employers(profile["experience"])
            extra["profile"] = profile
        out["extra"] = extra

    # Keep citizenship in extra_summary for pre-handoff view
    out["personal_data"] = {}
    out["contacts"] = {}
    out["docs_progress"] = {}
    return out


async def _apply_client_view_mask(
    db: AsyncSession,
    candidate_dict: Dict[str, Any],
    candidate_id: str,
    client_tenant_id: str,
) -> Dict[str, Any]:
    """
    For client tenant: full data when:
    1. Accepted handoff TO this tenant exists, OR
    2. Pending handoff TO this tenant exists (client needs to see data to make decision)
    
    All other candidates (including those belonging to client tenant itself) should be masked.
    
    IMPORTANT: For client tenants, ALL candidates should be masked unless:
    - Candidate has accepted handoff TO this client tenant, OR
    - Candidate has pending handoff TO this client tenant (for decision-making)
    
    This ensures that clients can see unmasked data for candidates that have been handed off to them
    (both pending and accepted), allowing them to make informed decisions.
    """
    if not candidate_dict:
        return candidate_dict
    cand_tenant = (candidate_dict.get("tenant_id") or "").strip() or None
    
    # Debug logging
    logger = logging.getLogger(__name__)
    logger.debug(
        "_apply_client_view_mask: candidate_id=%s cand_tenant=%s client_tenant_id=%s",
        candidate_id,
        cand_tenant,
        client_tenant_id,
    )
    
    # Check if there's an accepted handoff TO this client tenant
    has_accepted_handoff = await client_has_accepted_handoff(db, candidate_id, client_tenant_id)
    if has_accepted_handoff:
        candidate_dict["masked"] = False
        logger.info(
            "_apply_client_view_mask: candidate_id=%s has accepted handoff to client_tenant_id=%s, NOT masking",
            candidate_id,
            client_tenant_id,
        )
        return candidate_dict
    
    # Check if there's a pending handoff TO this client tenant
    # Client needs to see data to make decision (accept/reject/return)
    has_pending_handoff = await has_pending_handoff_for_client(db, candidate_id, client_tenant_id)
    if has_pending_handoff:
        candidate_dict["masked"] = False
        logger.info(
            "_apply_client_view_mask: candidate_id=%s has pending handoff to client_tenant_id=%s, NOT masking (client needs to see data for decision)",
            candidate_id,
            client_tenant_id,
        )
        return candidate_dict
    
    # ALL other cases = masked (including candidates belonging to client tenant itself)
    # This ensures that clients only see unmasked data for candidates that have been handed off to them
    logger.info(
        "_apply_client_view_mask: MASKING candidate_id=%s (cand_tenant=%s, client_tenant_id=%s, no accepted or pending handoff)",
        candidate_id,
        cand_tenant,
        client_tenant_id,
    )
    out = _mask_candidate_pre_handoff(candidate_dict)
    out["masked"] = True
    # Always set short_id for masked so list and Short ID column show a stable reference (never empty)
    out["short_id"] = (out.get("short_id") or "").strip() or (candidate_id or "")[:8]
    return out


def _format_actor_label(user: _Any | None, raw_actor: Optional[str]) -> Optional[str]:
    """Human-readable label for stage history actors."""
    if user is not None:
        full_name = str(getattr(user, "full_name", "") or "").strip()
        email = str(getattr(user, "email", "") or "").strip()
        short_id = str(getattr(user, "short_id", "") or "").strip()
        if full_name and email:
            return f"{full_name} ({email})"
        if full_name:
            return full_name
        if short_id and email:
            return f"{short_id} ({email})"
        if email:
            return email
        if short_id:
            return short_id
    return str(raw_actor) if raw_actor else None


# Compatibility GET list endpoint for frontend
@router.get("", dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))])
@router.get("/", include_in_schema=False, dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))])
async def list_candidates(
    response: Response,
    order_by: str = "created_at",
    desc: bool = True,
    limit: int = 50,
    offset: int = 0,
    # filters
    stage: str | None = None,
    stages: str | None = None,
    status: str | None = Query(
        default=None,
        description=(
            "Filter by ``Candidate.status`` (row-level application/business state). "
            "Does **not** imply ``Candidate.stage``; combine with ``stage`` / ``stages`` for both axes."
        ),
    ),
    statuses: str | None = Query(
        default=None,
        description="Comma-separated ``Candidate.status`` values (multi-select). Same semantics as ``status``.",
    ),
    status_reason: Optional[List[str]] = Query(
        default=None,
        description="Коды причин отказа/отклонения (через запятую или повтор param).",
    ),
    tags: Optional[List[str]] = Query(
        default=None,
        description="Теги/метки кандидата (через запятую или повтор param).",
    ),
    is_favorite: Optional[bool] = Query(
        default=None,
        description="Фильтр по избранным кандидатам.",
    ),
    manager_id: UUID | None = Query(
        default=None,
        description=(
            "Legacy filter name for the candidate assignee user id. "
            "Prefer ``recruiter_id`` (Phase 2.6.G-5 Stage F canon). Both names "
            "are accepted for one release cycle; if both are supplied, "
            "``recruiter_id`` wins."
        ),
    ),
    recruiter_id: UUID | None = Query(
        default=None,
        description=(
            "Canonical filter by the candidate assignee user id "
            "(``Candidate.recruiter_id``). Phase 2.6.G-5 Stage F — replaces "
            "``manager_id``; during the transition both names funnel into the "
            "same OR-match on ``Candidate.manager`` / ``Candidate.recruiter_id``."
        ),
    ),
    vacancy_id: UUID | None = Query(default=None, alias="vacancy_id"),
    # str (not UUID): frontend sends CSV for multi-select; handler splits below.
    vacancy: str | None = Query(default=None, alias="vacancy"),
    documents_ordered: str | None = Query(
        default=None,
        description="Filter candidates by presence of ordered documents (`ordered` or `not_ordered`).",
    ),
    handoff_status: str | None = Query(
        default=None,
        description="Filter by handoff status: none, pending, accepted, returned.",
    ),
    contact_attempts: str | None = Query(
        default=None,
        description="Filter by contact attempts: none, some, limit_reached (3+).",
    ),
    processor_id: UUID | None = Query(
        default=None,
        description="Filter by processor (accepted handoff assigned_to_user_id).",
    ),
    recruiter_unassigned: bool = Query(
        default=False,
        description="Candidates with no recruiter assigned (excludes terminal stages employed/rejected/declined/probation_ok).",
    ),
    shadow_bucket_start: str | None = Query(
        default=None,
        description="Restrict to candidates in risk_intel_entity_shadow for this hourly bucket (ISO-8601, UTC).",
    ),
    shadow_bucket_min_band: str | None = Query(
        default=None,
        description="Band floor with shadow_bucket_start (default high): low|medium|high|critical.",
    ),
    q: str | None = Query(default=None, description="Поиск по имени/фамилии/email/телефону"),
    intake_application_kind: str | None = Query(
        default=None,
        description="Фильтр по виду публичного intake: client (запрос клиента) или candidate (всё остальное).",
    ),
    created_from: date | None = None,
    created_to: date | None = None,
    compact: bool = Query(
        default=False,
        description="Return a compact payload for list views (omit heavy fields).",
    ),
    include_risk: bool = Query(
        default=False,
        description="Include candidate risk scoring fields in the list payload.",
    ),
    include_insights: bool = Query(
        default=False,
        description="Include aggregate counters (total, new, docs readiness buckets) for the current filter set, computed in one SQL query.",
    ),
    scope_tenant_id: UUID | None = Query(
        default=None,
        description="If set, scope the list to this tenant (e.g. from getCurrentTenant). Overrides X-Tenant-Id for scope only.",
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    """
    List endpoint с фильтрами и пагинацией. Возвращает: {"total": int, "items": [ ... ]}
    """
    db, tenant_id = db_tenant
    # Scope list by: query param > X-Tenant-Id header > JWT. So when UI sends X-Tenant-Id (e.g. Citronex), we use it even if user's JWT tenant is agency.
    scope_tenant = (
        str(scope_tenant_id) if scope_tenant_id
        else (str(tenant_id).strip() or str(current_user.tenant_id).strip() or str(tenant_id))
    )
    # Debug: log who и с каким scope_tenant запрашивает список
    logging.getLogger(__name__).info(
        "Candidates list request: user_email=%s role=%s header_tenant=%s scope_tenant=%s",
        getattr(current_user, "email", None),
        getattr(current_user, "role", None),
        str(tenant_id),
        scope_tenant,
    )
    # Scope source for debugging
    scope_source = "query" if scope_tenant_id else ("header" if (tenant_id and str(tenant_id).strip() == scope_tenant) else "jwt")
    # RLS uses app.tenant_id: set it to scope_tenant so client sees candidates for their linked vacancies/handoffs
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    visibility = get_tenant_visibility(db, scope_tenant)
    filters: dict[str, object] = {}
    # Client tenant scope is from tenant_links in repo, not from ACL; avoid returning 0 on empty ACL.
    client_tenant = await is_client_tenant_for_list(db, scope_tenant)
    # Do not scope the generic candidates list by own company.
    # The frontend currently sends X-Own-Company-Id globally from persisted
    # workspace state, which unintentionally shrinks the main tenant-wide list.
    
    # Debug logging для диагностики определения клиентского тенанта
    user_email = (getattr(current_user, "email", None) or "").lower().strip()
    logging.getLogger(__name__).info(
        "Client tenant check: user_email=%s scope_tenant=%s client_tenant=%s",
        user_email,
        scope_tenant,
        client_tenant,
    )
    
    filters["is_client_tenant"] = client_tenant
    # ВАЖНО: Для клиентских тенантов маскирование применяется ВСЕГДА, независимо от роли
    # Это гарантирует защиту PII данных клиентов
    # Исключение: только для суперадмина платформы (который работает от имени платформенного тенанта)
    user_role_lower = (current_user.role or "").lower()
    # Проверяем, является ли пользователь суперадмином платформы (не клиентского тенанта)
    is_platform_superadmin = user_role_lower == Role.superadmin.value and not client_tenant
    # Признак применения клиентского маскирования (PII)
    # Для клиентских тенантов маскирование применяется всегда, кроме суперадмина платформы
    apply_client_view = client_tenant and not is_platform_superadmin
    # Debug logging для диагностики маскирования
    logging.getLogger(__name__).info(
        "Masking check: user_email=%s role=%s scope_tenant=%s client_tenant=%s is_platform_superadmin=%s apply_client_view=%s",
        getattr(current_user, "email", None),
        user_role_lower,
        scope_tenant,
        client_tenant,
        is_platform_superadmin,
        apply_client_view,
    )
    # Debug headers so we can see in Network tab, что именно происходит
    response.headers["X-Is-Client-Tenant"] = "1" if client_tenant else "0"
    response.headers["X-Apply-Client-View"] = "1" if apply_client_view else "0"
    response.headers["X-User-Role"] = user_role_lower

    if not await apply_agency_acl_filters(db, scope_tenant, current_user, client_tenant, filters):
        return {"total": 0, "items": []}

    # Funnel position: ``Candidate.stage`` only (``?stage`` / ``?stages``).
    if stage:
        s = stage.strip()
        if s:
            filters["stage"] = s
            filters["stages"] = [s]

    if stages:
        arr = [x.strip() for x in stages.split(",") if x.strip()]
        if arr:
            filters["stages"] = arr

    # Row-level state: ``Candidate.status`` only — never mixed into ``stages`` (legacy quirk removed).
    cand_status_vals: list[str] = []
    if status:
        s = status.strip()
        if s:
            cand_status_vals.append(s)
    if statuses:
        cand_status_vals.extend(x.strip() for x in statuses.split(",") if x.strip())
    if cand_status_vals:
        seen_row: set[str] = set()
        filters["candidate_statuses"] = [x for x in cand_status_vals if x and (x not in seen_row and not seen_row.add(x))]

    if status_reason:
        reason_codes: List[str] = []
        for value in status_reason:
            if not value:
                continue
            parts = [part.strip() for part in value.split(",") if part and part.strip()]
            reason_codes.extend(parts)
        if reason_codes:
            unique_codes: List[str] = []
            seen_codes = set()
            for code in reason_codes:
                if code in seen_codes:
                    continue
                unique_codes.append(code)
                seen_codes.add(code)
            if unique_codes:
                filters["status_reason"] = unique_codes

    if tags:
        tag_values: List[str] = []
        for value in tags:
            if not value:
                continue
            parts = [part.strip() for part in value.split(",") if part and part.strip()]
            tag_values.extend(parts)
        if tag_values:
            unique_tags: List[str] = []
            seen_tags = set()
            for tag in tag_values:
                if tag in seen_tags:
                    continue
                unique_tags.append(tag)
                seen_tags.add(tag)
            if unique_tags:
                filters["tags"] = unique_tags

    if is_favorite is not None:
        filters["is_favorite"] = is_favorite

    # Phase 2.6.G-5 Stage F — ``recruiter_id`` is the new canonical query
    # name; ``manager_id`` stays as a BC alias for one release. When both
    # are sent, ``recruiter_id`` wins. Either way we funnel into
    # ``filters["manager"]`` so ``repo._build_conditions`` does the OR
    # across ``Candidate.manager`` and ``Candidate.recruiter_id`` (Stage D
    # invariant — the two columns are kept in lock-step by
    # ``record_candidate_reassignment``).
    _assignee_id = recruiter_id or manager_id
    if _assignee_id:
        mid = str(_assignee_id)
        filters["manager"] = mid
        filters["manager_id"] = mid  # compatibility with legacy consumers

    # фильтр по вакансии — поддерживаем оба ключа (vacancy_id и vacancy)
    # Если vacancy содержит запятые, это множественный выбор
    # Приоритет: vacancy (может быть CSV) > vacancy_id (одиночное значение)
    if vacancy:
        vacancy_str = str(vacancy).strip()
        if ',' in vacancy_str:
            # Множественный выбор через CSV
            vacancy_ids = [x.strip() for x in vacancy_str.split(",") if x.strip()]
            if len(vacancy_ids) > 0:
                filters["vacancy_ids"] = vacancy_ids
        else:
            # Одиночное значение
            filters["vacancy_id"] = vacancy_str
    elif vacancy_id:
        # Одиночное значение через vacancy_id
        filters["vacancy_id"] = str(vacancy_id)

    if documents_ordered:
        doc_filter = documents_ordered.strip().lower()
        if doc_filter in {"ordered", "not_ordered"}:
            filters["documents_ordered"] = doc_filter

    if handoff_status:
        hs = handoff_status.strip().lower()
        if hs in {"none", "pending", "accepted", "returned"}:
            filters["handoff_status"] = hs

    if contact_attempts:
        ca = contact_attempts.strip().lower()
        if ca in {"none", "some", "limit_reached"}:
            filters["contact_attempts"] = ca

    if processor_id:
        filters["processor_id"] = str(processor_id)

    if recruiter_unassigned:
        filters["recruiter_unassigned"] = True

    if shadow_bucket_start and str(shadow_bucket_start).strip():
        from backend.app.services.risk_intel_v1 import parse_shadow_bucket_iso

        buck = parse_shadow_bucket_iso(str(shadow_bucket_start).strip())
        if buck is not None:
            mb = str(shadow_bucket_min_band or "high").strip().lower()
            filters["risk_intel_shadow"] = {"bucket_start": buck, "min_band": mb}

    if q:
        q = q.strip()
        if q:
            filters["q"] = q

    if intake_application_kind:
        ak = intake_application_kind.strip().lower()
        if ak in ("client", "candidate"):
            filters["intake_application_kind"] = ak

    if created_from:
        filters["dt_from"] = datetime.combine(created_from, datetime.min.time())
    if created_to:
        filters["dt_to"] = datetime.combine(created_to, datetime.max.time())
    insights_payload: dict[str, int] | None = None
    if include_insights:
        try:
            insights_payload = await cand_repo.count_candidates_insights(
                db,
                tenant_id=scope_tenant,
                filters=filters,
                visibility=visibility,
            )
            total = int(insights_payload.get("total", 0))
        except Exception:
            logging.getLogger(__name__).exception("count_candidates_insights failed, falling back to count_candidates")
            insights_payload = None
            total = await cand_repo.count_candidates(
                db,
                tenant_id=scope_tenant,
                filters=filters,
                visibility=visibility,
            )
    else:
        total = await cand_repo.count_candidates(
            db,
            tenant_id=scope_tenant,
            filters=filters,
            visibility=visibility,
        )
    # Log scope used for count (align list total with analytics; diagnose 666 vs 524)
    if client_tenant and total > 0:
        logging.getLogger(__name__).debug(
            "Candidates list count scope_tenant=%s scope_source=%s is_client_tenant=True total=%s",
            scope_tenant,
            scope_source,
            total,
        )
    # For agency/superadmin: log linked tenants/companies to diagnose scope issues
    if not client_tenant and current_user.role in (Role.admin.value, Role.administrator.value, Role.superadmin.value):
        linked_tenants = await db.execute(
            select(TenantLink.client_tenant_id)
            .where(
                TenantLink.agency_tenant_id == scope_tenant,
                TenantLink.client_tenant_id.isnot(None),
            )
            .distinct()
        )
        linked_tenant_ids = [str(tid) for (tid,) in linked_tenants.all() if tid]
        linked_companies = await db.execute(
            select(TenantLink.client_company_id)
            .where(
                TenantLink.agency_tenant_id == scope_tenant,
                TenantLink.client_company_id.isnot(None),
            )
            .distinct()
        )
        linked_company_ids = [str(cid) for (cid,) in linked_companies.all() if cid]
        logging.getLogger(__name__).info(
            "Candidates agency scope: tenant=%s total=%s linked_client_tenants=%s linked_companies=%s",
            scope_tenant,
            total,
            linked_tenant_ids,
            linked_company_ids,
        )
    # Log when list is empty to diagnose client/scope issues
    if total == 0:
        logging.getLogger(__name__).info(
            "Candidates list total=0 scope_tenant=%s scope_source=%s client_tenant=%s",
            scope_tenant,
            scope_source,
            client_tenant,
        )
    if client_tenant and total == 0:
        # Diagnose: handoffs count and how many rows RLS allows on candidates
        handoff_count = 0
        candidates_visible_by_rls = -1
        try:
            r = await db.execute(
                select(func.count()).select_from(CandidateHandoff).where(
                    CandidateHandoff.client_tenant_id == scope_tenant,
                ),
            )
            handoff_count = int(r.scalar() or 0)
        except Exception:
            pass
        try:
            r2 = await db.execute(text("SELECT COUNT(*) FROM candidates"))
            candidates_visible_by_rls = int(r2.scalar() or 0)
        except Exception:
            pass
        logging.getLogger(__name__).warning(
            "Candidates list empty for client tenant scope_tenant_id=%s scope_source=%s "
            "handoffs_for_tenant=%s candidates_visible_by_rls=%s.",
            scope_tenant,
            scope_source,
            handoff_count,
            candidates_visible_by_rls,
        )
    response.headers["X-List-Tenant-Id"] = scope_tenant
    response.headers["X-Scope-Source"] = scope_source
    response.headers["X-Is-Client-Tenant"] = "1" if client_tenant else "0"
    response.headers["X-List-Total"] = str(total)

    # Client tenant: use list_candidates only (same scope as count), avoid fetch_candidates_with_labels
    # which can return 0 rows due to JOINs/RLS on users/companies/vacancies.
    if client_tenant:
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": scope_tenant},
            )
        except Exception:
            pass
        candidates = await cand_repo.list_candidates(
            db, scope_tenant, filters, order_by, desc, limit, offset, visibility
        )
        logging.getLogger(__name__).info(
            "Candidates list client path: list_candidates returned %s rows scope_tenant=%s offset=%s",
            len(candidates),
            scope_tenant,
            offset,
        )
        rows = [
            (
                c,
                None,
                getattr(c, "manager", None),
                getattr(c, "manager", None),
                None,
                getattr(c, "recruiter_id", None),
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
            for c in candidates
        ]
        response.headers["X-List-Rows"] = str(len(rows))
        response.headers["X-List-Source"] = "list"
    else:
        rows = await cand_repo.fetch_candidates_with_labels(
            db,
            tenant_id=scope_tenant,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            desc=desc,
            visibility=visibility,
        )
        if total > 0 and len(rows) == 0:
            rls_count = -1
            try:
                r2 = await db.execute(text("SELECT COUNT(*) FROM candidates"))
                rls_count = int(r2.scalar() or 0)
            except Exception:
                pass
            logging.getLogger(__name__).info(
                "Candidates list total=%s but fetch returned 0 rows scope_tenant=%s offset=%s rls_count=%s",
                total,
                scope_tenant,
                offset,
                rls_count,
            )
        response.headers["X-List-Rows"] = str(len(rows))
        response.headers["X-List-Source"] = "fetch"

    risk_map: Dict[str, Any] = {}
    if include_risk and rows:
        candidate_by_id: Dict[str, Candidate] = {}
        for row in rows:
            if not row:
                continue
            c = row[0]
            cid = str(getattr(c, "id", "") or "")
            if cid:
                candidate_by_id[cid] = c
        try:
            now = datetime.now(timezone.utc)
            if candidate_by_id and all(
                is_candidate_operationally_terminal(stage=getattr(c, "stage", None), status=getattr(c, "status", None))
                for c in candidate_by_id.values()
            ):
                risk_map = {
                    cid: CandidateRisk(
                        risk_score=0,
                        risk_band="low",
                        risk_updated_at=now,
                        risk_drivers=[],
                        risk_version="risk_model_v1",
                    )
                    for cid in candidate_by_id
                }
            else:
                risk_map = await compute_candidate_risk_scores(
                    db,
                    tenant_id=scope_tenant,
                    candidates_by_id=candidate_by_id,
                    now=now,
                )
        except Exception:
            logging.getLogger(__name__).exception("Failed to compute candidate risk scores")
            risk_map = {}

    items = []
    for row in rows:
        # "rows" can come in two shapes depending on repo implementation.
        # Shape A (older): (c, label_primary, label_secondary, stage_label, vacancy_title)
        # Shape B (newer): (c, company_name, manager_raw, manager_name, vacancy_title)
        c = row[0]
        company_name = None
        label_primary = None
        label_secondary = None
        stage_label = None
        manager_name = None
        manager_raw = getattr(c, "manager", None)
        vacancy_name = None
        recruiter_id = None
        recruiter_name = None
        recruiter_short = None

        if len(row) >= 5:
            # Try to detect Shape B by checking if 3rd element looks like UUID (manager_raw)
            possible_mgr_raw = row[2]
            try:
                # if it's a valid UUID, treat as Shape B
                from uuid import UUID as _UUID
                _ = _UUID(str(possible_mgr_raw))
                # Shape B
                manager_raw = str(possible_mgr_raw)
                manager_name = row[3]
                company_name = row[1]
                vacancy_name = row[4]
                recruiter_id = row[5] if len(row) > 5 else None
                recruiter_name = row[6] if len(row) > 6 else None
                recruiter_short = row[7] if len(row) > 7 else None
            except Exception:
                # Shape A
                label_primary = row[1]
                company_name = row[1]
                label_secondary = row[2]
                stage_label = row[3]
                vacancy_name = row[4]
                recruiter_id = row[5] if len(row) > 5 else None
                recruiter_name = row[6] if len(row) > 6 else None
                recruiter_short = row[7] if len(row) > 7 else None
        elif len(row) == 4:
            # very defensive fallback: assume last is vacancy
            vacancy_name = row[3]
        elif len(row) > 5:
            recruiter_id = row[5]
            recruiter_name = row[6] if len(row) > 6 else None
            recruiter_short = row[7] if len(row) > 7 else None

        if manager_raw and manager_name and str(manager_name) == str(manager_raw):
            if recruiter_id and str(recruiter_id) == str(manager_raw):
                manager_name = recruiter_name or recruiter_short or manager_name

        docs_readiness_state = None
        docs_readiness_rank = None
        docs_last_ordered_at = None
        docs_next_valid_from = None
        docs_has_files = None

        if len(row) >= 13:
            docs_readiness_state = row[8]
            docs_readiness_rank = row[9]
            docs_last_ordered_at = row[10]
            docs_next_valid_from = row[11]
            docs_has_files = bool(row[12]) if row[12] is not None else None

        extra_payload = _extra_dict(c)
        docs_progress = _docs_progress_dict(c)
        extra_summary = {
            "citizenship": extra_payload.get("citizenship"),
            "preferred_contact": extra_payload.get("preferred_contact"),
            "first_contact_at": extra_payload.get("first_contact_at"),
            "in_poland": extra_payload.get("in_poland"),
            "poland_stay_basis": extra_payload.get("poland_stay_basis"),
            "trailer_types": extra_payload.get("trailer_types"),
        }

        risk = risk_map.get(str(c.id)) if include_risk else None

        base_payload = {
            "id": str(c.id),
            "tenant_id": str(getattr(c, "tenant_id", "")) if getattr(c, "tenant_id", None) else None,
            "short_id": getattr(c, "short_id", None),
            "first_name": getattr(c, "first_name", None),
            "last_name": getattr(c, "last_name", None),
            "phone": getattr(c, "phone", None),
            "phone_country_code": getattr(c, "phone_country_code", None),
            "email": getattr(c, "email", None),
            "stage": getattr(c, "stage", None),
            "row_status": getattr(c, "status", None),
            "status": getattr(c, "status", None) or getattr(c, "stage", None),
            # Менеджер: отображаем красивое имя, а сырой id отдаём отдельно
            "manager": manager_name or manager_raw or "",
            "manager_name": manager_name or manager_raw or "",
            "manager_id": manager_raw,
            "recruiter_id": recruiter_id,
            "recruiter_name": recruiter_name or recruiter_id or "",
            "recruiter_short": recruiter_short or "",
            # Вакансия: человекочитаемое название, fallback to company name
            "vacancy": (vacancy_name or company_name or ""),
            "vacancy_name": (vacancy_name or company_name or ""),
            "vacancy_title": (vacancy_name or company_name or ""),
            "vacancy_id": getattr(c, "vacancy_id", None),
            "company_name": company_name,
            # метки, если есть в Shape A
            "labels": [x for x in [label_primary, label_secondary] if x],
            "status_reason": _status_reason_list(getattr(c, "status_reason", None)),
            "tags": _tags_list(getattr(c, "tags", None)),
            "is_favorite": bool(getattr(c, "is_favorite", False)),
            "created_at": getattr(c, "created_at", None),
            "updated_at": getattr(c, "updated_at", None),
            "docs_readiness_state": docs_readiness_state,
            "docs_readiness_rank": docs_readiness_rank,
            "docs_last_ordered_at": docs_last_ordered_at.isoformat() if getattr(docs_last_ordered_at, "isoformat", None) else docs_last_ordered_at,
            "docs_next_valid_from": docs_next_valid_from.isoformat() if getattr(docs_next_valid_from, "isoformat", None) else docs_next_valid_from,
            "docs_has_files": docs_has_files,
            "intake_application_kind": _intake_application_kind_from_model(c),
        }
        if include_risk:
            base_payload["risk_score"] = getattr(risk, "risk_score", None) if risk else None
            base_payload["risk_band"] = getattr(risk, "risk_band", None) if risk else None
            base_payload["risk_drivers"] = getattr(risk, "risk_drivers", None) if risk else None
            ru = getattr(risk, "risk_updated_at", None) if risk else None
            base_payload["risk_updated_at"] = ru.isoformat() if ru and hasattr(ru, "isoformat") else None
            base_payload["risk_version"] = getattr(risk, "risk_version", None) if risk else None

        if compact:
            item = {
                **base_payload,
                "extra_summary": extra_summary,
            }
        else:
            item = {
                **base_payload,
                "languages": getattr(c, "languages", None) or _get_profile_field(c, "languages"),
                "country_code": getattr(c, "country_code", None) or _get_profile_field(c, "country_code"),
                "city": getattr(c, "city", None) or _get_profile_field(c, "city"),
                "birth_date": getattr(c, "birth_date", None) or _get_profile_field(c, "birth_date"),
                "address": getattr(c, "address", None) or _get_profile_field(c, "address"),
                "note": getattr(c, "note", None),
                "notes": getattr(c, "note", None),  # alias for legacy consumers
                "extra": extra_payload,
                "docs_progress": docs_progress,
            }
        items.append(item)

    # Client view: mask PII for non-transferred candidates; add can_edit; always set masked for frontend
    processed_items = []
    logger = logging.getLogger(__name__)
    logger.info(
        "Processing %d items with apply_client_view=%s scope_tenant=%s",
        len(items),
        apply_client_view,
        scope_tenant,
    )
    for item in items:
        cid = item.get("id")
        if apply_client_view:
            # Debug: log tenant_id before masking
            logger.debug(
                "Before masking: candidate_id=%s tenant_id=%s scope_tenant=%s first_name=%s last_name=%s",
                cid,
                item.get("tenant_id"),
                scope_tenant,
                item.get("first_name"),
                item.get("last_name"),
            )
            item = await _apply_client_view_mask(db, item, str(cid), scope_tenant)
            item["can_edit"] = await can_client_edit(db, str(cid), scope_tenant)
            # _apply_client_view_mask sets item["masked"] True or False
            logger.debug(
                "After masking: candidate_id=%s masked=%s tenant_id=%s first_name=%s last_name=%s",
                cid,
                item.get("masked"),
                item.get("tenant_id"),
                item.get("first_name"),
                item.get("last_name"),
            )
            # Ensure masked flag is set - если apply_client_view=True, то masked должен быть True или False
            # Если функция маскирования не установила флаг, значит что-то пошло не так - принудительно маскируем
            if "masked" not in item or item.get("masked") is None:
                logger.warning("Masked flag not set for candidate_id=%s, forcing True and applying mask", cid)
                item = _mask_candidate_pre_handoff(item)
                item["masked"] = True
                item["short_id"] = (item.get("short_id") or "").strip() or (str(cid) or "")[:8]
            # Дополнительная проверка: если masked=True, убеждаемся что PII данные удалены
            if item.get("masked") is True:
                # Принудительно удаляем PII данные если они еще присутствуют
                if item.get("first_name") or item.get("last_name") or item.get("email") or item.get("phone"):
                    logger.warning(
                        "PII data still present for masked candidate_id=%s: first_name=%s last_name=%s email=%s phone=%s, removing",
                        cid,
                        item.get("first_name"),
                        item.get("last_name"),
                        item.get("email"),
                        item.get("phone"),
                    )
                    item = _mask_candidate_pre_handoff(item)
                    item["masked"] = True
                    item["short_id"] = (item.get("short_id") or "").strip() or (str(cid) or "")[:8]
                    # Дополнительная проверка после маскирования
                    if item.get("first_name") or item.get("last_name"):
                        logger.error(
                            "CRITICAL: PII data STILL present after masking for candidate_id=%s: first_name=%s last_name=%s",
                            cid,
                            item.get("first_name"),
                            item.get("last_name"),
                        )
                        # Принудительно устанавливаем в None
                        item["first_name"] = None
                        item["last_name"] = None
                        item["email"] = None
                        item["phone"] = None
        else:
            item["can_edit"] = await can_agency_edit(db, str(cid), scope_tenant)
            item["masked"] = False
        processed_items.append(item)

    # Debug headers: verify client view and mask applied (inspect in browser Network tab)
    if apply_client_view:
        masked_count = sum(1 for i in processed_items if i.get("masked") is True)
        response.headers["X-Client-View"] = "1"
        response.headers["X-Masked-Count"] = str(masked_count)
        response.headers["X-Mask-Policy"] = "accepted-only"
        # How many items have accepted handoff to this tenant (should be 2 after migration 202602080010)
        accepted_count = sum(
            1 for i in processed_items
            if i.get("masked") is False
        )
        response.headers["X-Accepted-Handoff-Count"] = str(accepted_count)
        # Number of companies linked via tenant_links (handoff_include_company_id); 0 = client sees only handoff/own
        linked = await db.execute(
            select(func.count(func.distinct(TenantLink.handoff_include_company_id))).where(
                TenantLink.client_tenant_id == scope_tenant,
                TenantLink.handoff_include_company_id.isnot(None),
            )
        )
        response.headers["X-Client-Linked-Companies"] = str(linked.scalar() or 0)

    # Финальная проверка: убеждаемся что все замаскированные кандидаты не содержат PII
    if apply_client_view:
        for item in processed_items:
            if item.get("masked") is True:
                if item.get("first_name") or item.get("last_name") or item.get("email") or item.get("phone"):
                    logger.error(
                        "CRITICAL: Masked candidate still has PII data before response: candidate_id=%s first_name=%s last_name=%s email=%s phone=%s",
                        item.get("id"),
                        item.get("first_name"),
                        item.get("last_name"),
                        item.get("email"),
                        item.get("phone"),
                    )
                    # Принудительно удаляем PII данные перед отправкой ответа
                    item["first_name"] = None
                    item["last_name"] = None
                    item["first_name_latin"] = None
                    item["last_name_latin"] = None
                    item["email"] = None
                    item["phone"] = None
                    item["phone_country_code"] = None
    
    response.headers["X-Items-Count"] = str(len(processed_items))
    if client_tenant and total > 0 and len(processed_items) != len(items):
        logging.getLogger(__name__).warning(
            "Candidates list length mismatch: items=%s processed_items=%s scope_tenant=%s",
            len(items),
            len(processed_items),
            scope_tenant,
        )
    # Финальное логирование для диагностики
    if apply_client_view:
        sample_masked = next((i for i in processed_items if i.get("masked") is True), None)
        if sample_masked:
            logger.info(
                "Sample masked candidate in response: id=%s masked=%s first_name=%s last_name=%s email=%s",
                sample_masked.get("id"),
                sample_masked.get("masked"),
                sample_masked.get("first_name"),
                sample_masked.get("last_name"),
                sample_masked.get("email"),
            )
    
    out: dict[str, Any] = {"total": total, "items": processed_items}
    if include_insights and insights_payload is not None:
        out["insights"] = insights_payload
    return out


@router.get(
    "/available-statuses",
    response_model=CandidateListAvailableStatusesOut,
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
)
async def candidates_available_statuses(
    scope_tenant_id: UUID | None = Query(
        default=None,
        description="Same as list: optional tenant scope override (e.g. superadmin workspace).",
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Distinct ``Candidate.stage`` / ``Candidate.status`` for the tenant list scope (ignores funnel-only meta).

    Options reflect rows the user could see on the candidates table (same scope + ACL as ``GET /candidates`` with no
    stage/status/q/vacancy filters), including terminal or handoff-related stages when present in the dataset.
    """
    db, tenant_id = db_tenant
    scope_tenant = (
        str(scope_tenant_id) if scope_tenant_id
        else (str(tenant_id).strip() or str(current_user.tenant_id).strip() or str(tenant_id))
    )
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    visibility = get_tenant_visibility(db, scope_tenant)
    client_tenant = await is_client_tenant_for_list(db, scope_tenant)
    filters: dict[str, object] = {"is_client_tenant": client_tenant}
    if not await apply_agency_acl_filters(db, scope_tenant, current_user, client_tenant, filters):
        return CandidateListAvailableStatusesOut(schema_version=1, stages=[], statuses=[])
    stages, statuses = await cand_repo.distinct_candidate_list_facets(
        db,
        scope_tenant,
        visibility=visibility,
        filters=filters,
    )
    return CandidateListAvailableStatusesOut(schema_version=1, stages=stages, statuses=statuses)


@router.get(
    "/no-next-action",
    summary="Operational view: candidates without an active next action (reminder).",
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
)
async def list_candidates_no_next_action(
    response: Response,
    limit: int = 50,
    offset: int = 0,
    stages: Optional[List[str]] = Query(default=None, description="Optional list of stage codes to include."),
    manager_id: UUID | None = Query(
        default=None,
        description=(
            "Legacy filter name for the candidate assignee user id. "
            "Prefer ``recruiter_id`` (Phase 2.6.G-5 Stage F canon)."
        ),
    ),
    recruiter_id: UUID | None = Query(
        default=None,
        description=(
            "Canonical filter by candidate assignee user id "
            "(``Candidate.recruiter_id``). Phase 2.6.G-5 Stage F — when both "
            "``recruiter_id`` and ``manager_id`` are sent, ``recruiter_id`` wins."
        ),
    ),
    intake_application_kind: str | None = Query(
        default=None,
        description="Same as GET /candidates: client | candidate (public intake).",
    ),
    assignee_id: UUID | None = Query(default=None, description="Assignee to check reminders for (defaults to current user)."),
    scope_tenant_id: UUID | None = Query(
        default=None,
        description="If set, scope the list to this tenant. Overrides X-Tenant-Id for scope only.",
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """
    Next action contract v1:
    - a candidate has a "next action" iff there exists an active reminder for (entity_type='candidate', entity_id=candidate.id)
      assigned to the selected assignee with status in {pending,new,overdue}.
    - Pipeline-completed candidates (by ``stage`` **or** row ``status`` matching completed codes) are never listed.
    """
    db, tenant_id = db_tenant
    scope_tenant = (
        str(scope_tenant_id) if scope_tenant_id else (str(tenant_id).strip() or str(current_user.tenant_id).strip() or str(tenant_id))
    )
    try:
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": scope_tenant})
    except Exception:
        pass

    assignee = str(assignee_id) if assignee_id else str(current_user.sub)
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)

    reminder_exists = (
        exists()
        .where(
            Reminder.tenant_id == scope_tenant,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == Candidate.id,
            Reminder.assignee_id == assignee,
            Reminder.status.in_(active_statuses),
        )
        .correlate(Candidate)
    )

    active_pipeline = sql_candidate_active_operational_pipeline(Candidate.stage, Candidate.status)
    where = [
        Candidate.tenant_id == scope_tenant,
        Candidate.deleted_at.is_(None),
        active_pipeline,
        ~reminder_exists,
    ]
    if stages:
        clean = [str(s).strip() for s in stages if str(s).strip()]
        if clean:
            where.append(Candidate.stage.in_(clean))
    # Phase 2.6.G-5 Stage F — accept both canonical ``recruiter_id`` and
    # legacy ``manager_id`` names; the OR on ``Candidate.manager`` /
    # ``Candidate.recruiter_id`` is kept for transitional data safety
    # even though Stage D guarantees the two columns are in sync.
    _assignee_id = recruiter_id or manager_id
    if _assignee_id:
        mid = str(_assignee_id)
        where.append(or_(Candidate.manager == mid, Candidate.recruiter_id == mid))

    if intake_application_kind:
        ak = intake_application_kind.strip().lower()
        if ak in ("client", "candidate"):
            ak_expr = func.lower(func.coalesce(Candidate.intake_state["application_kind"].as_string(), ""))
            if ak == "client":
                where.append(ak_expr == "client")
            else:
                where.append(ak_expr != "client")

    client_tenant_acl = await is_client_tenant_for_list(db, scope_tenant)
    acl_no_next = await resolve_candidate_acl(db, scope_tenant, current_user)
    if not acl_no_next.unrestricted:
        if not client_tenant_acl and acl_no_next.is_empty():
            return {"total": 0, "items": []}
        frag = candidate_acl_sql_or_clause(acl_no_next, client_tenant=client_tenant_acl)
        if frag is not None:
            where.append(frag)

    count_row = await db.execute(select(func.count()).select_from(Candidate).where(*where))
    total = int(count_row.scalar() or 0)
    response.headers["X-Total-Count"] = str(total)

    rows = await db.execute(
        select(Candidate)
        .where(*where)
        .order_by(Candidate.updated_at.desc(), Candidate.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = []
    for c in rows.scalars().all():
        items.append(
            {
                "id": str(c.id),
                "short_id": getattr(c, "short_id", None),
                "first_name": getattr(c, "first_name", None),
                "last_name": getattr(c, "last_name", None),
                "stage": getattr(c, "stage", None),
                "manager": getattr(c, "manager", None),
                "company_id": getattr(c, "company_id", None),
                "vacancy_id": getattr(c, "vacancy_id", None),
                "created_at": getattr(c, "created_at", None),
                "updated_at": getattr(c, "updated_at", None),
                "intake_application_kind": _intake_application_kind_from_model(c),
            }
        )

    return {"total": total, "items": items}


@router.get(
    "/debug-client-view",
    summary="[Debug] Client view: accepted handoffs to current tenant (same DB as list).",
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
)
async def debug_client_view(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    """Returns count of accepted handoffs with client_tenant_id = current tenant.
    Use to verify the DB used by this backend; if 5, run POST .../debug-client-view/force-two."""
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    is_client = await is_client_tenant_for_list(db, tid)
    r = await db.execute(
        select(func.count()).select_from(CandidateHandoff).where(
            CandidateHandoff.client_tenant_id == tid,
            CandidateHandoff.status == "accepted",
        )
    )
    count = r.scalar() or 0
    return {
        "is_client_tenant": is_client,
        "accepted_handoffs_to_tenant": count,
        "message": "Only 2 should have full PII; if >2 run POST .../debug-client-view/force-two",
    }


@router.post(
    "/debug-client-view/force-two",
    summary="[Debug] Force only 2 accepted handoffs to current tenant (same as migration 011).",
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
)
async def debug_force_two_handoffs(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    """Updates handoffs: keep 2 most recent (by reviewed_at), set rest to company-only. Idempotent."""
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    # Need a company_id for "company-only" (constraint: exactly one of client_company_id / client_tenant_id)
    link = await db.execute(
        select(TenantLink.handoff_include_company_id).where(
            TenantLink.client_tenant_id == tid,
            TenantLink.handoff_include_company_id.isnot(None),
        ).limit(1)
    )
    company_id = link.scalar_one_or_none()
    if not company_id:
        raise HTTPException(
            status_code=400,
            detail="No tenant_link with handoff_include_company_id for this tenant",
        )
    company_id = str(company_id)
    # Subquery: ids of handoffs to update (all but 2 most recent)
    subq = (
        select(CandidateHandoff.id)
        .where(
            CandidateHandoff.client_tenant_id == tid,
            CandidateHandoff.status == "accepted",
        )
        .order_by(
            CandidateHandoff.reviewed_at.desc().nulls_last(),
            CandidateHandoff.id.asc(),
        )
        .offset(2)
    )
    stmt = (
        update(CandidateHandoff)
        .where(CandidateHandoff.id.in_(subq))
        .values(client_tenant_id=None, client_company_id=company_id)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"updated": result.rowcount, "message": "Reload list; expect 2 full PII, rest masked."}


@router.post(
    "/bulk-stage",
    response_model=List[BulkStageItemOut],
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def bulk_update_stage(
    payload: BulkStageIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    s = (payload.stage or "").strip()
    if not s:
        raise HTTPException(status_code=422, detail="Stage must not be empty")

    acl_raw = await resolve_candidate_acl(db, str(tenant_id), current_user)
    acl = None if acl_raw.unrestricted else acl_raw

    results = await cand_service.bulk_update_stage(
        db=db,
        tenant_id=str(tenant_id),
        candidate_ids=[str(cid) for cid in payload.candidate_ids],
        stage=s,
        actor_id=current_user.sub,
        status_reason=payload.status_reason,
        acl=acl,
    )
    return results

@router.post(
    "/bulk-manager",
    response_model=List[BulkManagerItemOut],
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def bulk_update_manager(
    payload: BulkManagerIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    if not payload.candidate_ids:
        return []

    acl_raw = await resolve_candidate_acl(db, str(tenant_id), current_user)
    acl = None if acl_raw.unrestricted else acl_raw

    results = await cand_service.bulk_update_manager(
        db=db,
        tenant_id=str(tenant_id),
        candidate_ids=[str(cid) for cid in payload.candidate_ids],
        manager_id=str(payload.manager_id),
        actor_id=current_user.sub,
        acl=acl,
    )
    return results

@router.post(
    "/bulk-delete",
    response_model=List[BulkDeleteItemOut],
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def bulk_delete_candidates(
    payload: BulkDeleteIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    if not payload.candidate_ids:
        return []

    # Check permissions - same as single delete
    if current_user.role == Role.recruiter.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter cannot delete candidates. Create a delete-request instead.",
        )
    if current_user.role not in (
        Role.administrator.value,
        Role.supervisor.value,
        Role.superadmin.value,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    acl_raw = await resolve_candidate_acl(db, str(tenant_id), current_user)
    acl = None if acl_raw.unrestricted else acl_raw

    results = await cand_service.bulk_delete_candidates(
        db=db,
        tenant_id=str(tenant_id),
        candidate_ids=[str(cid) for cid in payload.candidate_ids],
        actor_id=current_user.sub,
        acl=acl,
    )
    return [
        BulkDeleteItemOut(
            candidate_id=r["candidate_id"],
            ok=r.get("ok", False),
            error=r.get("error"),
        )
        for r in results
    ]


# Create candidate
@router.post(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Create candidate",
)
@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def create_candidate(
    payload: CreateCandidateIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))

    visibility = get_tenant_visibility(db, str(tenant_id))

    data: Dict[str, Any] = payload.model_dump(exclude_none=True)

    data["first_name"] = payload.first_name.strip()
    data["last_name"] = payload.last_name.strip()

    for key in ("phone", "email", "phone_country_code", "stage", "status"):
        if key in data and isinstance(data[key], str):
            stripped = data[key].strip()
            data[key] = stripped or None

    langs_value = data.get("languages")
    if isinstance(langs_value, str):
        data["languages"] = [p.strip() for p in langs_value.split(",") if p.strip()]

    birth_date_val = data.get("birth_date")
    if isinstance(birth_date_val, str) and birth_date_val:
        try:
            data["birth_date"] = date.fromisoformat(birth_date_val)
        except Exception:
            data["birth_date"] = None

    if data.get("manager_id"):
        data["manager"] = str(data.pop("manager_id"))
    elif data.get("manager"):
        data["manager"] = str(data["manager"]).strip()

    for fk in ("company_id", "vacancy_id"):
        if data.get(fk) is not None:
            data[fk] = str(data[fk])

    acl_raw = await resolve_candidate_acl(db, str(tenant_id), current_user)
    acl = None if acl_raw.unrestricted else acl_raw

    created = await cand_service.create_candidate_full(
        db=db,
        tenant_id=str(tenant_id),
        payload=data,
        actor_id=current_user.sub,
        acl=acl,
    )

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(created.id),
        visibility=visibility,
    )
    if row is None:
        return {
            "id": str(created.id),
            "first_name": created.first_name,
            "last_name": created.last_name,
            "email": created.email,
            "phone": created.phone,
            "phone_country_code": created.phone_country_code,
            "languages": data.get("languages"),
            "stage": created.stage,
            "status": created.stage,
            "manager_id": data.get("manager"),
            "company_id": data.get("company_id"),
            "company_name": data.get("company_name"),
            "vacancy_id": data.get("vacancy_id"),
            "recruiter_id": getattr(created, "recruiter_id", None),
            "recruiter_name": "",
            "recruiter_short": "",
            "source": data.get("source"),
            "origin": data.get("origin"),
            "extra": _extra_dict(created),
            "docs_progress": _docs_progress_dict(created),
            "personal_data": data.get("personal_data") or {},
            "contacts": data.get("contacts") or {},
        }

    return _serialize_candidate_row(row)


# Get candidate by id
@router.get(
    "/{candidate_id}",
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
    summary="Get candidate by id",
)
async def get_candidate(
    candidate_id: UUID,
    response: Response,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(
        db,
        tenant_id_str,
        str(candidate_id),
        current_user,
    )
    # Determine whether this tenant is a "client" for scope purposes
    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    # ВАЖНО: Для клиентских тенантов маскирование применяется ВСЕГДА, независимо от роли
    # Это гарантирует защиту PII данных клиентов
    # Исключение: только для суперадмина платформы (который работает от имени платформенного тенанта)
    user_role_lower = (current_user.role or "").lower()
    # Проверяем, является ли пользователь суперадмином платформы (не клиентского тенанта)
    is_platform_superadmin = user_role_lower == Role.superadmin.value and not client_tenant
    # Признак применения клиентского маскирования (PII)
    # Для клиентских тенантов маскирование применяется всегда, кроме суперадмина платформы
    apply_client_view = client_tenant and not is_platform_superadmin
    # Debug logging для диагностики маскирования
    logging.getLogger(__name__).info(
        "Masking check (get_candidate): user_email=%s role=%s tenant_id=%s client_tenant=%s is_platform_superadmin=%s apply_client_view=%s",
        getattr(current_user, "email", None),
        user_role_lower,
        tenant_id_str,
        client_tenant,
        is_platform_superadmin,
        apply_client_view,
    )
    # Debug headers for detail endpoint as well
    response.headers["X-Is-Client-Tenant"] = "1" if client_tenant else "0"
    response.headers["X-Apply-Client-View"] = "1" if apply_client_view else "0"
    response.headers["X-User-Role"] = user_role_lower
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    out = _serialize_candidate_row(row)
    if apply_client_view:
        out = await _apply_client_view_mask(db, out, str(candidate_id), tenant_id_str)
        out["can_edit"] = await can_client_edit(db, str(candidate_id), tenant_id_str)
    else:
        agency_can = await can_agency_edit(db, str(candidate_id), tenant_id_str)
        if agency_can:
            out["can_edit"] = True
        elif user_role_lower == "hr_officer" and await agency_candidate_has_internal_hr_handoff_lane(
            db, agency_tenant_id=tenant_id_str, candidate_id=str(candidate_id)
        ):
            out["can_edit"] = True
        else:
            out["can_edit"] = False

    from backend.app.services.candidate_operational_write import build_candidate_operational_permissions

    out["permissions"] = await build_candidate_operational_permissions(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        client_tenant=client_tenant,
    )

    # Contact-attempt readiness for stage UI (plan: New → at least one attempt when policy on).
    cand_row = row[0]
    try:
        from backend.app.services.contact_attempts import (
            count_contact_attempts,
            get_effective_contact_policy,
        )

        pol = await get_effective_contact_policy(db, tenant_id_str, cand_row)
        out["contact_policy_enabled"] = bool(pol.get("enabled"))
        out["contact_attempt_count"] = await count_contact_attempts(db, str(cand_row.id))
    except Exception:
        logging.getLogger(__name__).exception("contact readiness enrich failed for candidate %s", candidate_id)
        out["contact_policy_enabled"] = False
        out["contact_attempt_count"] = 0

    try:
        now_r = datetime.now(timezone.utc)
        if is_candidate_operationally_terminal(
            stage=getattr(cand_row, "stage", None),
            status=getattr(cand_row, "status", None),
        ):
            r = {
                "risk_score": 0,
                "risk_band": "low",
                "risk_drivers": [],
                "risk_updated_at": now_r,
                "risk_version": "risk_model_v1",
            }
        else:
            from backend.app.services.risk_intel_v1 import compute_candidate_risk_map_for_ids

            rmap = await compute_candidate_risk_map_for_ids(db, tenant_id_str, [str(candidate_id)], now=now_r)
            r = rmap.get(str(candidate_id))
        if r:
            out["risk_score"] = r["risk_score"]
            out["risk_band"] = r["risk_band"]
            out["risk_drivers"] = r["risk_drivers"]
            ru = r.get("risk_updated_at")
            out["risk_updated_at"] = ru.isoformat() if ru and hasattr(ru, "isoformat") else None
            out["risk_version"] = r.get("risk_version")
    except Exception:
        logging.getLogger(__name__).exception("risk enrich failed for candidate %s", candidate_id)

    return out


@router.get(
    "/{candidate_id}/work-panel",
    response_model=CandidateWorkPanelResponse,
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
    summary="Work panel bundle (ops profile + reminders + timeline + comms links)",
)
async def get_candidate_work_panel(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    timeline_limit: int = Query(80, ge=20, le=200),
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CandidateWorkPanelResponse:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    cand_row = row[0]
    return await load_candidate_work_panel(
        db,
        tenant_id_str,
        str(candidate_id),
        current_user,
        cand_row,
        timeline_limit=timeline_limit,
        assignee_scope=assignee_scope,
        active_own_company_id=own_company_id,
    )


@router.get(
    "/{candidate_id}/timeline",
    response_model=CandidateTimelineResponse,
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
    summary="Get candidate unified timeline",
)
async def get_candidate_timeline(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    limit: int = Query(200, ge=20, le=500),
) -> CandidateTimelineResponse:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    # Ensure candidate exists in scope.
    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    events = await fetch_candidate_timeline_events(db, tenant_id_str, str(candidate_id), limit)
    return CandidateTimelineResponse(items=events)


@router.get(
    "/{candidate_id}/change-log",
    response_model=CandidateChangeLogResponse,
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
    summary="Get candidate change log (all updates)",
)
async def get_candidate_change_log(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    limit: int = Query(200, ge=20, le=500),
) -> CandidateChangeLogResponse:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    rows = (
        await db.execute(
            select(
                ActivityLog.action,
                ActivityLog.created_at,
                ActivityLog.actor_id,
                ActivityLog.payload,
                User.full_name,
            )
            .outerjoin(User, User.id == ActivityLog.actor_id)
            .where(
                ActivityLog.tenant_id == tenant_id_str,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == str(candidate_id),
                ActivityLog.action.in_(["candidate.updated"]),
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    items: list[CandidateChangeLogItemOut] = []
    for action, created_at, actor_id, payload, actor_name in rows:
        items.append(
            CandidateChangeLogItemOut(
                at=created_at,
                actor_id=str(actor_id) if actor_id else None,
                actor_name=str(actor_name) if actor_name else None,
                action=str(action or ""),
                payload=payload if isinstance(payload, dict) else {},
            )
        )
    return CandidateChangeLogResponse(items=items)


def _recruitment_application_to_out(row: RecruitmentApplication) -> RecruitmentApplicationOut:
    """Map ORM row → API; tolerate legacy NULL/odd JSON so list endpoint does not 500."""
    applied = getattr(row, "applied_at", None)
    if applied is None:
        applied = datetime.now(timezone.utc)

    raw_meta = getattr(row, "meta", None)
    meta: Dict[str, Any]
    if isinstance(raw_meta, dict):
        meta = dict(raw_meta)
    elif isinstance(raw_meta, str) and raw_meta.strip():
        try:
            parsed = json.loads(raw_meta)
            meta = dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            meta = {}
    else:
        meta = {}

    def _opt_id(val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        return s or None

    cyc_raw = getattr(row, "application_cycle", None)
    application_cycle: Optional[str] = None
    if cyc_raw is not None:
        application_cycle = str(cyc_raw).strip() or None

    return RecruitmentApplicationOut(
        id=str(getattr(row, "id", "") or "").strip(),
        candidate_id=str(getattr(row, "candidate_id", "") or "").strip(),
        lead_id=_opt_id(getattr(row, "lead_id", None)),
        vacancy_id=_opt_id(getattr(row, "vacancy_id", None)),
        source=str(getattr(row, "source", None) or "meta").strip() or "meta",
        recruiter_id=_opt_id(getattr(row, "recruiter_id", None)),
        applied_at=applied,
        status=normalize_application_status(getattr(row, "status", None)),
        application_cycle=application_cycle,
        meta=meta,
    )


@router.get(
    "/{candidate_id}/applications",
    response_model=List[RecruitmentApplicationOut],
    dependencies=[Depends(require_roles(*CANDIDATE_VIEW_ROLES))],
    summary="List recruitment applications (intent) for this candidate",
)
async def list_candidate_recruitment_applications(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> List[RecruitmentApplicationOut]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    apps = await list_recruitment_applications_for_candidate(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
    )
    return [_recruitment_application_to_out(a) for a in apps]


@router.post(
    "/{candidate_id}/upload-link",
    response_model=CandidateUploadLinkOut,
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Create or refresh public upload link for candidate",
)
async def create_candidate_upload_link(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CandidateUploadLinkOut:
    """Ensure intake/status tokens exist and return a public link for candidate self-upload."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    candidate = await cand_repo.get_candidate(
        db, tenant_id_str, str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    _ensure_intake_token(candidate)
    _ensure_status_share_token(candidate)
    tenant_row = await db.get(Tenant, tenant_id_str)
    if tenant_row is not None:
        lic_row = await tenant_service.get_tenant_license(db, tenant_id_str)
        plan_pc = portal_candidate_usage.resolve_plan_code_for_portal_cap(
            portal_candidate_usage.subscription_dict_from_tenant_settings(tenant_row),
            lic_row,
        )
        portal_candidate_usage.ensure_can_add_portal_candidate_month(
            tenant_row,
            str(candidate_id),
            at_utc=datetime.now(timezone.utc),
            plan_code=plan_pc,
        )
        portal_candidate_usage.record_active_portal_candidate_month(
            tenant_row, str(candidate_id), at_utc=datetime.now(timezone.utc)
        )
    await db.commit()

    apply_token = getattr(candidate, "intake_token", None) or ""
    status_token = getattr(candidate, "status_share_token", None)
    expires_at = (
        getattr(candidate, "intake_token_expires_at", None)
        or getattr(candidate, "status_share_token_expires_at", None)
    )

    return CandidateUploadLinkOut(
        apply_url=f"/public/apply/{apply_token}",
        documents_url=f"/public/documents/{status_token}" if status_token else None,
        status_url=f"/public/status/{status_token}" if status_token else None,
        intake_token=apply_token,
        status_share_token=status_token,
        expires_at=expires_at,
    )


class NotifyCandidateOut(BaseModel):
    sent: bool
    reason: Optional[str] = None


@router.post(
    "/{candidate_id}/notify",
    response_model=NotifyCandidateOut,
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Notify candidate to upload documents",
)
async def notify_candidate(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NotifyCandidateOut:
    """Send email to candidate with link to upload requested documents."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    candidate = await cand_repo.get_candidate(
        db, tenant_id_str, str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    to_email = (getattr(candidate, "email", None) or "").strip()
    if not to_email:
        return NotifyCandidateOut(sent=False, reason="no_email")

    _ensure_status_share_token(candidate)
    tenant_row = await db.get(Tenant, tenant_id_str)
    if tenant_row is not None:
        lic_row = await tenant_service.get_tenant_license(db, tenant_id_str)
        plan_pc = portal_candidate_usage.resolve_plan_code_for_portal_cap(
            portal_candidate_usage.subscription_dict_from_tenant_settings(tenant_row),
            lic_row,
        )
        portal_candidate_usage.ensure_can_add_portal_candidate_month(
            tenant_row,
            str(candidate_id),
            at_utc=datetime.now(timezone.utc),
            plan_code=plan_pc,
        )
        portal_candidate_usage.record_active_portal_candidate_month(
            tenant_row, str(candidate_id), at_utc=datetime.now(timezone.utc)
        )
    await db.commit()

    docs = await documents_crud.list_candidate_documents(
        db, tenant_id_str, str(candidate_id), status="requested"
    )
    requested_names = [
        candidate_notifications.get_document_display_name(getattr(d, "doc_type", None) or "")
        for d in docs
    ]

    base_url = (settings.frontend_url or "").strip().rstrip("/") or "https://hostflow.cc"
    status_token = getattr(candidate, "status_share_token", None) or getattr(candidate, "intake_token", None)
    status_url = f"{base_url}/public/status/{status_token}" if status_token else None

    sent = await candidate_notifications.send_documents_reminder_email_to_candidate(
        db,
        tenant_id=tenant_id_str,
        candidate=candidate,
        requested_doc_names=requested_names,
        status_url=status_url,
    )
    return NotifyCandidateOut(sent=sent, reason=None if sent else "send_failed")


# Stage history
@router.get(
    "/{candidate_id}/stage-history",
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Get candidate stage history",
)
async def get_candidate_stage_history(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    visibility = get_tenant_visibility(db, tenant_id)
    candidate_str = str(candidate_id)

    await ensure_candidate_access(
        db,
        tenant_id,
        candidate_str,
        current_user,
    )

    client_tenant = await is_client_tenant(db, tenant_id)
    candidate = await cand_repo.get_candidate(
        db, tenant_id, candidate_str,
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    history_tenant_id = getattr(candidate, "tenant_id", tenant_id)
    entries = await cand_repo.list_candidate_stage_history(db, history_tenant_id, candidate_str)
    history: List[Dict[str, Any]] = []
    for entry, actor_user in entries:
        history.append(
            {
                "id": entry.id,
                "from_code": entry.from_code,
                "to_code": entry.to_code,
                "reason": entry.reason,
                "actor": _format_actor_label(actor_user, entry.actor),
                "at": entry.at.isoformat() if entry.at else None,
            }
        )
    return history


# Partially update candidate
@router.patch(
    "/{candidate_id}",
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Partially update candidate",
)
async def patch_candidate(
    candidate_id: UUID,
    payload: Dict[str, Any] = Body(...),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(
        db,
        tenant_id_str,
        str(candidate_id),
        current_user,
    )
    acl_raw = await resolve_candidate_acl(db, tenant_id_str, current_user)
    acl: CandidateACL | None = None if acl_raw.unrestricted else acl_raw
    if acl and str(getattr(current_user, "role", "") or "").strip().lower() == "hr_officer":
        if await agency_candidate_has_internal_hr_handoff_lane(
            db, agency_tenant_id=tenant_id_str, candidate_id=str(candidate_id)
        ):
            acl = None

    # Handoff permissions: agency can edit only if no accepted handoff; client only with accepted
    client_tenant = await is_client_tenant(db, tenant_id_str)
    recruitment_locked = False
    recruitment_lock_reason: Optional[str] = None
    workforce_locked = False
    recruitment_lock_override_used = False

    if client_tenant:
        if not await can_client_edit(db, str(candidate_id), tenant_id_str):
            raise HTTPException(status_code=403, detail="Cannot edit: no accepted handoff")
    else:
        recruitment_locked, recruitment_lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
            db, agency_tenant_id=tenant_id_str, candidate_id=str(candidate_id)
        )
        workforce_locked = await is_candidate_locked_by_workforce(
            db, tenant_id=tenant_id_str, candidate_id=str(candidate_id)
        )
        operational_locked = recruitment_locked or workforce_locked
        if operational_locked:
            role_l = str(getattr(current_user, "role", "") or "").strip().lower()
            or_raw = (payload or {}).get("override_reason")
            if role_l in RECRUITMENT_LOCK_OVERRIDE_ROLES and str(or_raw or "").strip():
                recruitment_lock_override_used = True
            elif role_l == "hr_officer" and await agency_candidate_has_internal_hr_handoff_lane(
                db, agency_tenant_id=tenant_id_str, candidate_id=str(candidate_id)
            ):
                recruitment_lock_override_used = True
            else:
                lock_detail = (
                    recruitment_lock_reason
                    if recruitment_locked
                    else ("workforce_hr_ownership" if workforce_locked else "handoff")
                )
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Recruitment locked ({lock_detail}): cannot edit candidate"
                        if recruitment_locked
                        else "candidate_readonly"
                    ),
                )

    # Allow only known fields to be updated to avoid accidental overwrites
    allowed_fields = {
        "first_name",
        "last_name",
        "email",
        "phone",
        "phone_country_code",
        "languages",
        "tags",
        "is_favorite",
        "country_code",
        "city",
        "birth_date",
        "address",
        "stage",
        "status",
        "status_reason",
        "company_id",
        "vacancy_id",
        # Phase 2.6.G-5 Stage F — accept all three names for the assignee:
        #   * ``recruiter_id``: canonical column (FK to ``users.id``); what
        #     Stage-F-aware frontends will send.
        #   * ``manager``: legacy DB column (shadow-written in lock-step).
        #   * ``manager_id``: legacy frontend alias, mapped to ``manager``
        #     below. Service layer (``update_candidate_full``) merges the
        #     three into ``changes["manager"]`` + ``changes["recruiter_id"]``
        #     via ``record_candidate_reassignment`` — see
        #     ``docs/specs/manager-assignment.md`` §1.2.1.
        "manager",
        "manager_id",
        "recruiter_id",
        "notes",
        "note",
        "extra",
        "personal_data",
        "contacts",
        "override_reason",
        "source",
        "origin",
        "docs_progress",
    }

    # Start with only allowed keys
    raw: Dict[str, Any] = {k: v for k, v in payload.items() if k in allowed_fields}

    # Map aliases
    if "manager_id" in raw and raw.get("manager_id"):
        raw["manager"] = raw.pop("manager_id")
    if "notes" in raw:
        raw["note"] = raw.pop("notes")

    # Normalize/clean values; ignore empty strings so we don't wipe seeded data
    data: Dict[str, Any] = {}
    for k, v in raw.items():
        # Treat blank strings as "no change"
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                continue

        # birth_date can come as string "YYYY-MM-DD" — convert to date if possible
        if k == "birth_date" and isinstance(v, str):
            try:
                v = date.fromisoformat(v)
            except Exception:
                # if parsing fails, skip updating this field
                continue

        # languages can be a comma-separated string from UI
        if k == "languages" and isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            v = parts

        if k in {"stage", "status", "status_reason"} and isinstance(v, str):
            v = v.strip()

        # address — skip completely empty dicts
        if k == "address" and isinstance(v, dict):
            if not any(bool(x) for x in v.values()):
                continue

        data[k] = v

    override_reason = None
    if "override_reason" in data:
        override_reason_raw = data.pop("override_reason")
        if override_reason_raw is not None:
            override_reason = str(override_reason_raw).strip() or None

    if (
        not client_tenant
        and recruitment_lock_override_used
        and str(getattr(current_user, "role", "") or "").strip().lower() == "hr_officer"
        and not override_reason
    ):
        override_reason = "internal_hr_handoff_lane"

    if not data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    if "stage" in data:
        role_lane = str(getattr(current_user, "role", "") or "").strip().lower()
        if role_lane != "hr_officer":
            from backend.app.services.stage_meta_recruitment_filter import (
                enforce_agency_handoff_stage_change_allowed,
            )

            await enforce_agency_handoff_stage_change_allowed(
                db,
                tenant_id=tenant_id_str,
                user=current_user,
                new_stage_code=str(data["stage"]),
            )

    _candidate_patch_side_effect_fields = frozenset(
        {
            "stage",
            "status",
            "status_reason",
            "company_id",
            "vacancy_id",
            "manager",
            "manager_id",
            # Phase 2.6.G-5 Stage F — canonical assignee name MUST trigger
            # the same billing / side-effect gate as the legacy names.
            "recruiter_id",
            "override_reason",
        }
    )
    tenant_row = await db.get(Tenant, tenant_id_str)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id_str).limit(1))
    ).scalar_one_or_none()
    if billing_restrictions.tenant_billing_blocks_side_effect_writes(tenant_row, lic_row):
        if _candidate_patch_side_effect_fields.intersection(data.keys()):
            if _candidate_patch_is_close_action(data):
                billing_restrictions.ensure_billing_allows_action(
                    tenant_row,
                    lic_row,
                    action="candidate_close",
                )
            else:
                billing_restrictions.ensure_billing_allows_side_effects(tenant_row, lic_row)

    current_candidate = await cand_repo.get_candidate(
        db,
        tenant_id_str,
        str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if current_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    override_fields, override_diff = _detect_candidate_override_changes(current_candidate, data)
    correction_fields = _candidate_owned_corrections_requiring_override_reason(
        current_candidate, data
    )
    role_l_owned = str(getattr(current_user, "role", "") or "").strip().lower()
    if correction_fields and not override_reason:
        requires_override_reason = (
            recruitment_locked
            or workforce_locked
            or role_l_owned in RECRUITMENT_LOCK_OVERRIDE_ROLES
        )
        if requires_override_reason:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "override_reason_required",
                    "message": "override_reason is required for candidate-owned field updates",
                    "fields": correction_fields,
                },
            )

    agency_bypass: Optional[AgencyRecruitmentWriteBypass] = None
    if not client_tenant and recruitment_lock_override_used and override_reason:
        agency_bypass = AgencyRecruitmentWriteBypass(
            actor_role=str(getattr(current_user, "role", "") or ""),
            override_reason=override_reason,
        )

    updated = await cand_service.update_candidate_full(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        payload=data,
        actor_id=current_user.sub,
        actor_role=str(getattr(current_user, "role", "") or ""),
        acl=acl,
        agency_recruitment_bypass=agency_bypass,
    )

    # Return the same enriched view as GET /{id}
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
        )
    if row is None:
        # Update succeeded but scope didn't return row (e.g. cross-tenant handoff).
        # Serialize from the updated model so we never 404 after a successful PATCH.
        c = updated
        row = (
            c,
            getattr(c, "company_id", None),
            getattr(c, "manager", None),
            None,
            None,
            getattr(c, "recruiter_id", None),
            None,
            None,
        )
    response_payload = _serialize_candidate_row(row)

    if override_fields and override_reason:
        try:
            await log_audit_event(
                db,
                tenant_id=tenant_id_str,
                event_type="candidate_field_overridden",
                entity_type=AuditEntityType.candidate,
                entity_id=str(candidate_id),
                actor_id=current_user.sub,
                payload={
                    "reason": override_reason,
                    "fields": override_fields,
                    "changes": override_diff,
                    "source": "manager_card",
                },
            )
            await db.commit()
        except Exception:
            await db.rollback()
    return response_payload


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@router.delete(
    "/{candidate_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_candidate(
    candidate_id: UUID,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Response:
    if ctx.role == Role.recruiter.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter cannot delete candidates. Create a delete-request instead.",
        )
    if ctx.role not in (
        Role.administrator.value,
        Role.supervisor.value,
        Role.superadmin.value,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    tenant_row = await db.get(Tenant, tenant_id_str)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id_str).limit(1))
    ).scalar_one_or_none()
    billing_restrictions.ensure_billing_allows_side_effects(tenant_row, lic_row)
    await cand_service.delete_candidate_full(db, tenant_id_str, str(candidate_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


from backend.app.api.v1.candidates import pipeline_overrides_api as _pipeline_overrides_api  # noqa: E402
from backend.app.api.v1.candidates import next_action_api as _next_action_api  # noqa: E402

router.include_router(_pipeline_overrides_api.router)
router.include_router(_next_action_api.router)
