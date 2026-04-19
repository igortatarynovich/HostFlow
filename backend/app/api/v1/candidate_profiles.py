"""API endpoints for managing candidate profiles."""

from __future__ import annotations

from typing import List, Optional, Any, Dict
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.services import billing_restrictions
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.candidate_profile_history import CandidateProfileHistory
from backend.app.models.tenant import Tenant, TenantLink
from backend.app.models.user import Role
from backend.app.models.vacancy import Vacancy

router = APIRouter(prefix="/candidate-profiles", tags=["candidate-profiles"])


def _profile_to_dict(profile: CandidateProfile) -> Dict[str, Any]:
    """Convert profile to dictionary for history snapshot."""
    return {
        "id": profile.id,
        "code": profile.code,
        "name": profile.name,
        "description": profile.description,
        "client_id": profile.client_id,
        "funnel_id": getattr(profile, "funnel_id", None),
        "config": profile.config or {},
        "is_active": profile.is_active,
        "is_system": profile.is_system,
        "owner_user_id": profile.owner_user_id,
        "notes": profile.notes,
    }


def _compute_changes(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute changes between old and new profile data."""
    changes: Dict[str, Any] = {}
    
    for key in ["code", "name", "description", "client_id", "funnel_id", "is_active", "is_system", "owner_user_id", "notes"]:
        old_val = old_data.get(key)
        new_val = new_data.get(key)
        if old_val != new_val:
            changes[key] = {"old": old_val, "new": new_val}
    
    # Compare config (deep comparison for nested structures)
    old_config = old_data.get("config", {})
    new_config = new_data.get("config", {})
    if old_config != new_config:
        changes["config"] = {"old": old_config, "new": new_config}
    
    return changes


def _make_profile_history(
    tenant_id: str,
    profile_id: str,
    action: str,
    *,
    old_data: Optional[Dict[str, Any]] = None,
    new_data: Optional[Dict[str, Any]] = None,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    comment: Optional[str] = None,
) -> CandidateProfileHistory:
    """Create a profile history entry."""
    changes = None
    if old_data and new_data:
        changes = _compute_changes(old_data, new_data)
    
    return CandidateProfileHistory(
        id=str(uuid4()),
        tenant_id=tenant_id,
        profile_id=profile_id,
        action=action,
        old_data=old_data,
        new_data=new_data,
        changes=changes,
        actor_id=actor_id,
        actor_name=actor_name,
        comment=comment,
    )


class CandidateProfileIn(BaseModel):
    """Payload for creating/updating candidate profile."""

    code: str = Field(..., min_length=1, max_length=64, description="Уникальный код профиля")
    name: str = Field(..., min_length=1, max_length=255, description="Название профиля")
    description: Optional[str] = Field(None, description="Описание профиля")
    client_id: Optional[str] = Field(None, description="ID клиента (если профиль специфичен для клиента)")
    funnel_id: Optional[str] = Field(None, description="ID воронки (этапы берутся из воронки, не из config)")
    config: dict[str, Any] = Field(default_factory=dict, description="Конфигурация профиля (JSON)")
    owner_user_id: Optional[str] = Field(None, description="ID ответственного пользователя")
    notes: Optional[str] = Field(None, description="Заметки")


class CandidateProfileOut(BaseModel):
    """Response model for candidate profile."""

    id: str
    tenant_id: str
    code: str
    name: str
    description: Optional[str]
    client_id: Optional[str]
    funnel_id: Optional[str] = None
    config: dict[str, Any]
    is_active: bool
    is_system: bool
    owner_user_id: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str
    usage_count: Optional[int] = Field(None, description="Number of vacancies using this profile")

    @classmethod
    async def from_model_with_usage(
        cls, profile: CandidateProfile, db: AsyncSession, tenant_id: str
    ) -> "CandidateProfileOut":
        """Create from ORM model with usage count."""
        # Count vacancies using this profile
        vacancy_stmt = select(Vacancy).where(
            Vacancy.tenant_id == tenant_id,
            Vacancy.candidate_profile_id == profile.id,
        )
        usage_count = len((await db.execute(vacancy_stmt)).scalars().all())
        
        return cls(
            id=profile.id,
            tenant_id=profile.tenant_id,
            code=profile.code,
            name=profile.name,
            description=profile.description,
            client_id=profile.client_id,
            funnel_id=getattr(profile, "funnel_id", None),
            config=profile.config or {},
            is_active=profile.is_active,
            is_system=profile.is_system,
            owner_user_id=profile.owner_user_id,
            notes=profile.notes,
            created_at=profile.created_at.isoformat() if profile.created_at else "",
            updated_at=profile.updated_at.isoformat() if profile.updated_at else "",
            usage_count=usage_count,
        )
    
    @classmethod
    def from_model(cls, profile: CandidateProfile) -> "CandidateProfileOut":
        """Create from ORM model (without usage count, for backward compatibility)."""
        return cls(
            id=profile.id,
            tenant_id=profile.tenant_id,
            code=profile.code,
            name=profile.name,
            description=profile.description,
            client_id=profile.client_id,
            funnel_id=getattr(profile, "funnel_id", None),
            config=profile.config or {},
            is_active=profile.is_active,
            is_system=profile.is_system,
            owner_user_id=profile.owner_user_id,
            notes=profile.notes,
            created_at=profile.created_at.isoformat() if profile.created_at else "",
            updated_at=profile.updated_at.isoformat() if profile.updated_at else "",
            usage_count=None,
        )


class CandidateProfileFieldContractField(BaseModel):
    code: str
    section: str
    required: bool = False
    owner: str
    source_of_truth: str
    editable_by: List[str] = Field(default_factory=list)
    purpose: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)


class CandidateProfileFieldContractOut(BaseModel):
    profile_id: str
    profile_code: str
    profile_name: str
    contract_version: int = 1
    fields: List[CandidateProfileFieldContractField]


_FIELD_ALIAS_TO_CANONICAL: Dict[str, str] = {
    # Contacts
    "phone": "contacts.phone",
    "phone_country_code": "contacts.phone_country_code",
    "email": "contacts.email",
    "preferred_contact": "contacts.preferred_messenger",
    "preferred_messenger": "contacts.preferred_messenger",
    # Personal
    "birth_date": "personal.birth_date",
    "citizenship": "personal.citizenship",
    "country_code": "personal.country_code",
    "current_location": "personal.current_location",
    "residency_status": "personal.residency_status",
    "in_poland": "personal.in_poland",
    "frigo_experience": "personal.frigo_experience",
    "has_adr": "personal.has_adr",
    "languages": "personal.languages",
    "city": "personal.city",
    "address": "personal.address",
    # Experience
    "experience_eu_years": "experience.years_ce",
    "years_ce": "experience.years_ce",
    "intl_experience": "experience.intl_experience",
    "trailer_types": "experience.trailer_types[]",
    "route_types": "experience.route_types[]",
    # Employments
    "employment_history": "employments[]",
    "employments": "employments[]",
    "employments[]": "employments[]",
    # Agreements (legacy + new)
    "privacy": "agreements.general",
    "general": "agreements.general",
    "contact": "agreements.employer_share",
    "employer_share": "agreements.employer_share",
    "terms_acceptance": "agreements.terms_acceptance",
    "cookies_accepted": "agreements.cookies_accepted",
}

_FIELD_PURPOSES: Dict[str, str] = {
    "first_name": "identification",
    "last_name": "identification",
    "contacts.phone": "communication",
    "contacts.phone_country_code": "dialing_normalization",
    "contacts.email": "status_links_and_notifications",
    "contacts.preferred_messenger": "operator_routing",
    "personal.birth_date": "legal_checks",
    "personal.citizenship": "document_requirements",
    "personal.current_location": "relocation_logistics",
    "experience.years_ce": "qualification",
    "experience.intl_experience": "route_fit",
    "experience.trailer_types[]": "vacancy_matching",
    "experience.route_types[]": "vacancy_matching",
    "employments[]": "screening_and_verification",
    "agreements.general": "legal",
    "agreements.employer_share": "legal",
    "agreements.terms_acceptance": "legal",
    "documents.required_types[]": "policy_enforcement",
    "documents.uploaded[]": "candidate_dossier",
    "documents.review_status": "qc_compliance",
    "stage": "process_control",
    "assignee": "workload_routing",
    "tags": "triage_ops",
    "note": "context",
}

_SECTION_ORDER: Dict[str, int] = {
    "contacts": 1,
    "personal": 2,
    "experience": 3,
    "employments": 4,
    "agreements": 5,
    "documents": 6,
    "operations": 7,
    "general": 8,
}

_DEFAULT_CANONICAL_FIELDS: List[str] = [
    "first_name",
    "last_name",
    "contacts.phone_country_code",
    "contacts.phone",
    "contacts.email",
    "contacts.preferred_messenger",
    "personal.birth_date",
    "personal.citizenship",
    "personal.residency_status",
    "personal.current_location",
    "personal.in_poland",
    "experience.years_ce",
    "experience.intl_experience",
    "experience.trailer_types[]",
    "experience.route_types[]",
    "employments[]",
    "agreements.general",
    "agreements.employer_share",
    "agreements.terms_acceptance",
]


def _normalize_field_code(raw_code: str) -> str:
    code = str(raw_code or "").strip()
    if not code:
        return code
    if code in _FIELD_ALIAS_TO_CANONICAL:
        return _FIELD_ALIAS_TO_CANONICAL[code]
    lowered = code.lower()
    if lowered in _FIELD_ALIAS_TO_CANONICAL:
        return _FIELD_ALIAS_TO_CANONICAL[lowered]
    # Already namespaced in canonical intake shape.
    if lowered.startswith(("contacts.", "personal.", "experience.", "agreements.", "documents.")):
        return lowered
    if lowered.startswith("employments"):
        return "employments[]"
    return code


def _field_section(code: str) -> str:
    if code in {"first_name", "last_name"}:
        return "contacts"
    if code in {"stage", "assignee", "tags", "note"}:
        return "operations"
    if code.startswith("employments"):
        return "employments"
    head = str(code).split(".", 1)[0].strip().lower()
    if head in {"contacts", "personal", "experience", "agreements", "documents"}:
        return head
    return "general"


def _field_governance(code: str) -> tuple[str, str, List[str]]:
    # operations fields are managed by managers/system.
    if code in {"stage", "assignee", "tags", "note"}:
        return ("manager", "manager_card", ["manager", "system"])
    if code.startswith("documents.required_types"):
        return ("system", "system", ["system", "manager"])
    if code.startswith("documents.review_status"):
        return ("manager", "manager_card", ["manager"])
    if code.startswith("documents."):
        return ("candidate", "telegram_intake", ["candidate", "manager"])
    if code.startswith("agreements."):
        return ("candidate", "telegram_intake", ["candidate", "manager_with_reason"])
    section = _field_section(code)
    if section in {"contacts", "personal", "experience", "employments"}:
        return ("candidate", "telegram_intake", ["candidate", "manager"])
    return ("candidate", "telegram_intake", ["candidate", "manager"])


def _extract_contract_fields(config: Dict[str, Any]) -> List[CandidateProfileFieldContractField]:
    cfg = config or {}
    required_codes = {
        str(x).strip()
        for x in (cfg.get("required_fields") or [])
        if isinstance(x, str) and str(x).strip()
    }
    optional_codes = {
        str(x).strip()
        for x in (cfg.get("optional_fields") or [])
        if isinstance(x, str) and str(x).strip()
    }
    field_configs = cfg.get("field_configs") or []

    raw_codes: List[str] = []
    raw_codes.extend(sorted(required_codes))
    raw_codes.extend(sorted(optional_codes))
    for item in field_configs:
        if not isinstance(item, dict):
            continue
        candidate_key = item.get("field_key") or item.get("code") or item.get("key")
        if isinstance(candidate_key, str) and candidate_key.strip():
            raw_codes.append(candidate_key.strip())

    # Fallback for old profiles without explicit required/optional lists.
    if not raw_codes:
        raw_codes = list(_DEFAULT_CANONICAL_FIELDS)

    grouped: Dict[str, Dict[str, Any]] = {}
    for raw in raw_codes:
        canonical = _normalize_field_code(raw)
        if not canonical:
            continue
        row = grouped.setdefault(
            canonical,
            {
                "required": False,
                "aliases": set(),
            },
        )
        row["aliases"].add(raw)
        if raw in required_codes or canonical in required_codes:
            row["required"] = True

    # Merge explicit `required` flags from field_configs.
    for item in field_configs:
        if not isinstance(item, dict):
            continue
        candidate_key = item.get("field_key") or item.get("code") or item.get("key")
        if not (isinstance(candidate_key, str) and candidate_key.strip()):
            continue
        canonical = _normalize_field_code(candidate_key.strip())
        if not canonical:
            continue
        row = grouped.setdefault(
            canonical,
            {
                "required": False,
                "aliases": set(),
            },
        )
        row["aliases"].add(candidate_key.strip())
        if bool(item.get("required")):
            row["required"] = True

    fields: List[CandidateProfileFieldContractField] = []
    for canonical, meta in grouped.items():
        owner, source_of_truth, editable_by = _field_governance(canonical)
        fields.append(
            CandidateProfileFieldContractField(
                code=canonical,
                section=_field_section(canonical),
                required=bool(meta.get("required")),
                owner=owner,
                source_of_truth=source_of_truth,
                editable_by=editable_by,
                purpose=_FIELD_PURPOSES.get(canonical),
                aliases=sorted({str(x) for x in (meta.get("aliases") or set()) if str(x).strip()}),
            )
        )

    fields.sort(key=lambda f: (_SECTION_ORDER.get(f.section, 999), f.code))
    return fields


async def _resolve_profile_for_read(
    db: AsyncSession,
    tenant_id_str: str,
    profile_id: str,
    current_user: Any,
) -> CandidateProfile:
    # 1) Same-tenant profile
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.id == profile_id)
        .where(CandidateProfile.tenant_id == tenant_id_str)
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile:
        return profile

    # 2) Agency profile via tenant link for client roles
    stmt_any = select(CandidateProfile).where(CandidateProfile.id == profile_id)
    profile_any = (await db.execute(stmt_any)).scalar_one_or_none()
    if profile_any:
        role = (current_user.role or "").lower()
        if role in (Role.client_processor.value, Role.client_manager.value):
            link_stmt = (
                select(TenantLink)
                .where(TenantLink.client_tenant_id == tenant_id_str)
                .where(TenantLink.agency_tenant_id == profile_any.tenant_id)
            )
            link = (await db.execute(link_stmt)).scalar_one_or_none()
            if link:
                return profile_any

    # 3) Fallback default profile for tenant
    profile_default = (await db.execute(_get_default_profile_stmt(tenant_id_str))).scalar_one_or_none()
    if profile_default:
        return profile_default
    raise HTTPException(status_code=404, detail="Candidate profile not found")


@router.get("", response_model=List[CandidateProfileOut])
@router.get("/", response_model=List[CandidateProfileOut])
async def list_candidate_profiles(
    client_id: Optional[str] = Query(None, description="Deprecated: Filter by client ID (not used, profiles are linked to vacancies)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(
        Role.admin,
        Role.supervisor,
        Role.recruiter,
        Role.client_processor,
        Role.client_manager,
    )),
) -> List[CandidateProfileOut]:
    """List candidate profiles for the tenant.
    
    Note: Profiles are linked to vacancies, not clients. The client_id parameter is deprecated.
    """
    db, tenant_id = db_tenant
    stmt = select(CandidateProfile).where(CandidateProfile.tenant_id == str(tenant_id))

    # client_id filter is deprecated - profiles are linked to vacancies, not clients
    # if client_id:
    #     stmt = stmt.where(CandidateProfile.client_id == client_id)
    if is_active is not None:
        stmt = stmt.where(CandidateProfile.is_active == is_active)

    rows = (
        (await db.execute(stmt.order_by(CandidateProfile.created_at.desc())))
        .scalars()
        .all()
    )
    # Return profiles with usage count
    return [await CandidateProfileOut.from_model_with_usage(p, db, str(tenant_id)) for p in rows]


@router.post("", response_model=CandidateProfileOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CandidateProfileOut, status_code=status.HTTP_201_CREATED)
async def create_candidate_profile(
    payload: CandidateProfileIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> CandidateProfileOut:
    """Create a new candidate profile."""
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))

    # Check uniqueness
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.tenant_id == str(tenant_id))
        .where(CandidateProfile.code == payload.code)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Candidate profile with this code already exists")

    # Check profile limits
    from backend.app.services.profile_limits import check_profile_limit
    
    is_valid, limits_info, plan_name = await check_profile_limit(
        db, str(tenant_id), payload.config or {}
    )
    if not is_valid:
        # Build detailed error message
        errors = []
        if limits_info["simple"]["used"] > limits_info["simple"]["limit"]:
            errors.append(f"простых: {limits_info['simple']['used']}/{limits_info['simple']['limit']}")
        if limits_info["medium"]["used"] > limits_info["medium"]["limit"]:
            errors.append(f"средних: {limits_info['medium']['used']}/{limits_info['medium']['limit']}")
        if limits_info["resource"]["used"] > limits_info["resource"]["limit"]:
            errors.append(f"ресурсоемких: {limits_info['resource']['used']}/{limits_info['resource']['limit']}")
        if limits_info["total_custom"]["used"] > limits_info["total_custom"]["limit"]:
            errors.append(f"всего кастомных: {limits_info['total_custom']['used']}/{limits_info['total_custom']['limit']}")
        
        raise HTTPException(
            status_code=403,
            detail=f"Превышены лимиты ({plan_name}): {', '.join(errors)}"
        )

    from uuid import uuid4

    profile = CandidateProfile(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        client_id=payload.client_id,
        funnel_id=payload.funnel_id,
        config=payload.config,
        is_active=True,
        is_system=False,
        owner_user_id=payload.owner_user_id or current_user.sub,
        notes=payload.notes,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return await CandidateProfileOut.from_model_with_usage(profile, db, str(tenant_id))


DRIVER_CE_DEFAULT_CODE = "driver_ce_default"


@router.post("/fix-orphaned-vacancies", response_model=Dict[str, Any])
async def fix_orphaned_vacancies(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> Dict[str, Any]:
    """Set candidate_profile_id to driver_ce_default for vacancies that have none or reference a missing/inactive profile. Runs for all tenants that have driver_ce_default."""
    db, _tenant_id = db_tenant
    # All tenants that have driver_ce_default profile
    default_profiles = (
        await db.execute(
            select(CandidateProfile.tenant_id, CandidateProfile.id).where(
                CandidateProfile.code == DRIVER_CE_DEFAULT_CODE,
            )
        )
    ).all()
    if not default_profiles:
        raise HTTPException(
            status_code=404,
            detail="Default profile (driver_ce_default) not found. Run seed or migration.",
        )

    total_updated = 0
    for tid, default_id in default_profiles:
        tid_str = str(tid) if isinstance(tid, UUID) else tid
        try:
            result = await db.execute(
                text("""
                    UPDATE vacancies
                    SET candidate_profile_id = :default_id
                    WHERE tenant_id = :tid
                      AND (
                        candidate_profile_id IS NULL
                        OR candidate_profile_id NOT IN (
                          SELECT id FROM candidate_profiles
                          WHERE tenant_id = :tid AND is_active = true
                        )
                      )
                      AND (candidate_profile_id IS DISTINCT FROM :default_id)
                """),
                {"default_id": default_id, "tid": tid_str},
            )
            total_updated += result.rowcount if hasattr(result, "rowcount") else 0
        except Exception:
            # Fallback per-tenant with ORM
            null_stmt = select(Vacancy).where(
                Vacancy.tenant_id == tid_str,
                Vacancy.candidate_profile_id.is_(None),
            )
            null_vacancies = (await db.execute(null_stmt)).scalars().all()
            active_profile_ids = {
                p.id for p in (await db.execute(
                    select(CandidateProfile).where(
                        CandidateProfile.tenant_id == tid_str,
                        CandidateProfile.is_active == True,
                    )
                )).scalars().all()
            }
            for v in null_vacancies:
                v.candidate_profile_id = default_id
                total_updated += 1
            all_vacancies = (await db.execute(select(Vacancy).where(Vacancy.tenant_id == tid_str))).scalars().all()
            for v in all_vacancies:
                if not v.candidate_profile_id:
                    continue
                if v.candidate_profile_id not in active_profile_ids and v.candidate_profile_id != default_id:
                    v.candidate_profile_id = default_id
                    total_updated += 1

    await db.commit()
    default_id_first = default_profiles[0][1]
    return {"updated": total_updated, "default_profile_id": str(default_id_first)}


@router.get("/limits", response_model=Dict[str, Any])
async def get_profile_limits(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> Dict[str, Any]:
    """Get profile field limits for the tenant."""
    from backend.app.services.profile_limits import (
        get_tenant_plan,
        get_plan_limits,
        calculate_field_counts,
        FIELD_CATEGORIES,
    )

    db, tenant_id = db_tenant

    plan = await get_tenant_plan(db, str(tenant_id))
    simple_limit, medium_limit, resource_limit, total_custom_limit = get_plan_limits(plan)

    stmt = select(CandidateProfile).where(
        CandidateProfile.tenant_id == str(tenant_id),
        CandidateProfile.is_active == True,
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()

    total_simple = 0
    total_medium = 0
    total_resource = 0
    total_custom = 0
    for profile in profiles:
        s, m, r, t = calculate_field_counts(profile.config or {})
        total_simple += s
        total_medium += m
        total_resource += r
        total_custom += t

    return {
        "plan": plan or "free",
        "limits": {
            "simple": {"used": total_simple, "limit": simple_limit, "available": max(0, simple_limit - total_simple)},
            "medium": {"used": total_medium, "limit": medium_limit, "available": max(0, medium_limit - total_medium)},
            "resource": {"used": total_resource, "limit": resource_limit, "available": max(0, resource_limit - total_resource)},
            "total_custom": {"used": total_custom, "limit": total_custom_limit, "available": max(0, total_custom_limit - total_custom)},
        },
        "field_categories": FIELD_CATEGORIES,
    }


def _get_default_profile_stmt(tenant_id_str: str):
    return (
        select(CandidateProfile)
        .where(CandidateProfile.tenant_id == tenant_id_str)
        .where(CandidateProfile.code == DRIVER_CE_DEFAULT_CODE)
    )


@router.get("/{profile_id}/field-contract", response_model=CandidateProfileFieldContractOut)
async def get_candidate_profile_field_contract(
    profile_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(
        Role.admin,
        Role.supervisor,
        Role.recruiter,
        Role.client_processor,
        Role.client_manager,
    )),
) -> CandidateProfileFieldContractOut:
    """Get normalized field ownership contract for intake/card deduplication."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    profile = await _resolve_profile_for_read(db, tenant_id_str, profile_id, current_user)
    return CandidateProfileFieldContractOut(
        profile_id=profile.id,
        profile_code=profile.code,
        profile_name=profile.name,
        contract_version=1,
        fields=_extract_contract_fields(profile.config or {}),
    )


@router.get("/{profile_id}", response_model=CandidateProfileOut)
async def get_candidate_profile(
    profile_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(
        Role.admin,
        Role.supervisor,
        Role.recruiter,
        Role.client_processor,
        Role.client_manager,
    )),
) -> CandidateProfileOut:
    """Get a single candidate profile by ID (includes inactive, so vacancy references keep working).
    Same-tenant profile is returned; for client tenants, agency profile is allowed when linked via TenantLink.
    If the profile is missing or not allowed, returns driver_ce_default for this tenant so the card always loads.
    """
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    profile = await _resolve_profile_for_read(db, tenant_id_str, profile_id, current_user)
    return await CandidateProfileOut.from_model_with_usage(profile, db, tenant_id_str)


@router.patch("/{profile_id}", response_model=CandidateProfileOut)
async def update_candidate_profile(
    profile_id: str,
    payload: CandidateProfileIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> CandidateProfileOut:
    """Update an existing candidate profile."""
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))

    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.id == profile_id)
        .where(CandidateProfile.tenant_id == str(tenant_id))
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    if profile.is_system:
        raise HTTPException(
            status_code=403, detail="System profiles cannot be modified"
        )

    # Check if profile is used in any active vacancies
    vacancy_stmt = select(Vacancy).where(
        Vacancy.tenant_id == str(tenant_id),
        Vacancy.candidate_profile_id == profile_id,
    )
    used_vacancies = (await db.execute(vacancy_stmt)).scalars().all()
    if used_vacancies:
        vacancy_titles = [v.title for v in used_vacancies[:5]]  # Show first 5
        more_count = len(used_vacancies) - 5
        detail = f"Profile is used in {len(used_vacancies)} vacancy(ies): {', '.join(vacancy_titles)}"
        if more_count > 0:
            detail += f" and {more_count} more"
        detail += ". Consider creating a new profile instead."
        raise HTTPException(
            status_code=409,
            detail=detail
        )

    # Check profile limits (excluding current profile)
    from backend.app.services.profile_limits import check_profile_limit
    
    is_valid, limits_info, plan_name = await check_profile_limit(
        db, str(tenant_id), payload.config or {}, exclude_profile_id=profile_id
    )
    if not is_valid:
        # Build detailed error message
        errors = []
        if limits_info["simple"]["used"] > limits_info["simple"]["limit"]:
            errors.append(f"простых: {limits_info['simple']['used']}/{limits_info['simple']['limit']}")
        if limits_info["medium"]["used"] > limits_info["medium"]["limit"]:
            errors.append(f"средних: {limits_info['medium']['used']}/{limits_info['medium']['limit']}")
        if limits_info["resource"]["used"] > limits_info["resource"]["limit"]:
            errors.append(f"ресурсоемких: {limits_info['resource']['used']}/{limits_info['resource']['limit']}")
        if limits_info["total_custom"]["used"] > limits_info["total_custom"]["limit"]:
            errors.append(f"всего кастомных: {limits_info['total_custom']['used']}/{limits_info['total_custom']['limit']}")
        
        raise HTTPException(
            status_code=403,
            detail=f"Превышены лимиты ({plan_name}): {', '.join(errors)}"
        )

    # Save old data for history
    old_data = _profile_to_dict(profile)
    
    # Update fields (code should not change to avoid breaking references)
    profile.name = payload.name
    profile.description = payload.description
    profile.client_id = payload.client_id
    profile.funnel_id = payload.funnel_id
    profile.config = payload.config
    profile.owner_user_id = payload.owner_user_id
    profile.notes = payload.notes

    await db.commit()
    await db.refresh(profile)
    
    # Log update in history
    new_data = _profile_to_dict(profile)
    history_entry = _make_profile_history(
        tenant_id=str(tenant_id),
        profile_id=profile.id,
        action="updated",
        old_data=old_data,
        new_data=new_data,
        actor_id=current_user.sub,
        actor_name=current_user.email,
    )
    db.add(history_entry)
    await db.commit()
    
    return await CandidateProfileOut.from_model_with_usage(profile, db, str(tenant_id))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate_profile(
    profile_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> None:
    """Delete (deactivate) a candidate profile."""
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))

    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.id == profile_id)
        .where(CandidateProfile.tenant_id == str(tenant_id))
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    if profile.is_system:
        raise HTTPException(
            status_code=403, detail="System profiles cannot be deleted"
        )

    # Check if profile is used in any active vacancies
    vacancy_stmt = select(Vacancy).where(
        Vacancy.tenant_id == str(tenant_id),
        Vacancy.candidate_profile_id == profile_id,
    )
    used_vacancies = (await db.execute(vacancy_stmt)).scalars().all()
    if used_vacancies:
        vacancy_titles = [v.title for v in used_vacancies[:5]]  # Show first 5
        more_count = len(used_vacancies) - 5
        detail = f"Profile is used in {len(used_vacancies)} vacancy(ies): {', '.join(vacancy_titles)}"
        if more_count > 0:
            detail += f" and {more_count} more"
        detail += ". Cannot delete profile that is in use."
        raise HTTPException(
            status_code=409,
            detail=detail
        )

    # Save old data for history
    old_data = _profile_to_dict(profile)

    # Soft delete: set is_active=False
    profile.is_active = False
    await db.commit()
    await db.refresh(profile)

    # Log deactivation in history (non-fatal: FK actor_id may fail if user not in DB)
    try:
        new_data = _profile_to_dict(profile)
        history_entry = _make_profile_history(
            tenant_id=str(tenant_id),
            profile_id=profile.id,
            action="deactivated",
            old_data=old_data,
            new_data=new_data,
            actor_id=getattr(current_user, "sub", None),
            actor_name=getattr(current_user, "email", None),
        )
        db.add(history_entry)
        await db.commit()
    except Exception:
        await db.rollback()
        # Deactivation already committed; history is optional
        import logging
        logging.getLogger(__name__).warning(
            "delete_candidate_profile: failed to write history for profile_id=%s", profile_id
        )


@router.get("/{profile_id}/history", response_model=List[Dict[str, Any]])
async def get_profile_history(
    profile_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of history entries to return"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> List[Dict[str, Any]]:
    """Get history of changes for a candidate profile."""
    db, tenant_id = db_tenant

    # Verify profile exists
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.id == profile_id)
        .where(CandidateProfile.tenant_id == str(tenant_id))
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    # Get history entries
    history_stmt = (
        select(CandidateProfileHistory)
        .where(CandidateProfileHistory.profile_id == profile_id)
        .where(CandidateProfileHistory.tenant_id == str(tenant_id))
        .order_by(CandidateProfileHistory.created_at.desc())
        .limit(limit)
    )
    history_entries = (await db.execute(history_stmt)).scalars().all()

    # Convert to dict format
    return [
        {
            "id": entry.id,
            "action": entry.action,
            "old_data": entry.old_data,
            "new_data": entry.new_data,
            "changes": entry.changes,
            "comment": entry.comment,
            "actor_id": entry.actor_id,
            "actor_name": entry.actor_name,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        for entry in history_entries
    ]
