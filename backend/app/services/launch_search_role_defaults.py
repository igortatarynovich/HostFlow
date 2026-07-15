"""Default candidate funnels and profiles per launch-search role (driver / warehouse / office / other)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    DRIVER_CE_PROFILE_CODE,
    WAREHOUSE_WORKER_PROFILE_CODE,
)

OFFICE_WORKER_PROFILE_CODE = "recruitment.candidate.office_worker"
GENERAL_CANDIDATE_PROFILE_CODE = "recruitment.candidate.general"
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.seed_candidate_profiles import (
    DRIVER_CE_DEFAULT_CODE,
    DRIVER_CE_DEFAULT_FUNNEL_NAME,
    DRIVER_CE_DEFAULT_FUNNEL_STAGES,
    FULL_DOCUMENT_CONFIGS,
    FULL_FIELD_CONFIGS,
)
from backend.app.services.recruitment_funnel_bootstrap import resolve_first_operating_company_id
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY

StageRow = tuple[str, str, str, bool]

WAREHOUSE_WORKER_DEFAULT_CODE = "warehouse_worker_default"
OFFICE_WORKER_DEFAULT_CODE = "office_worker_default"
GENERAL_CANDIDATE_DEFAULT_CODE = "general_candidate_default"

WAREHOUSE_FUNNEL_NAME = "Warehouse (default)"
OFFICE_FUNNEL_NAME = "Office (default)"
GENERAL_FUNNEL_NAME = "General hiring (default)"

GENERIC_FIELD_CONFIGS: list[dict[str, Any]] = [
    {"field_key": "first_name", "field_type": "text", "label": "Имя", "required": False, "visible": True, "order": 1},
    {"field_key": "last_name", "field_type": "text", "label": "Фамилия", "required": False, "visible": True, "order": 2},
    {"field_key": "phone", "field_type": "text", "label": "Телефон", "required": False, "visible": True, "order": 3},
    {"field_key": "email", "field_type": "text", "label": "Email", "required": False, "visible": True, "order": 4},
    {"field_key": "citizenship", "field_type": "text", "label": "Гражданство", "required": False, "visible": True, "order": 5},
    {"field_key": "birth_date", "field_type": "date", "label": "Дата рождения", "required": False, "visible": True, "order": 6},
    {"field_key": "current_location", "field_type": "text", "label": "Текущее местоположение", "required": False, "visible": True, "order": 7},
]

OFFICE_FIELD_CONFIGS: list[dict[str, Any]] = [
    *GENERIC_FIELD_CONFIGS,
    {"field_key": "years_similar_role", "field_type": "text", "label": "Опыт на похожей должности", "required": False, "visible": True, "order": 8},
    {"field_key": "poland_stay_basis", "field_type": "text", "label": "Документ на пребывание", "required": False, "visible": True, "order": 9},
]

WAREHOUSE_FIELD_CONFIGS: list[dict[str, Any]] = [
    *GENERIC_FIELD_CONFIGS,
    {"field_key": "poland_stay_basis", "field_type": "text", "label": "Документ на пребывание", "required": False, "visible": True, "order": 8},
    {"field_key": "forklift_license", "field_type": "boolean", "label": "Разрешение на погрузчик", "required": False, "visible": True, "order": 9},
]

BASIC_IDENTITY_DOCUMENT_CONFIGS: list[dict[str, Any]] = [
    {"document_type_id": "identity_document", "required": True},
]

WAREHOUSE_FUNNEL_STAGES: list[StageRow] = [
    ("new", "Nowy", "new", False),
    ("contacted", "Kontakt", "in_progress", False),
    ("questionnaire_submitted", "Screening", "in_progress", False),
    ("docs_wait", "Dokumenty", "in_progress", False),
    ("docs_got", "Dokumenty OK", "in_progress", False),
    ("employment_pending", "Oferta", "in_progress", False),
    ("employed", "Zatrudniony", "hired", True),
    ("rejected", "Odrzucony", "declined_rejected", True),
]

OFFICE_FUNNEL_STAGES: list[StageRow] = [
    ("new", "Nowy", "new", False),
    ("contacted", "Kontakt", "in_progress", False),
    ("questionnaire_submitted", "Screening", "in_progress", False),
    ("docs_got", "Rozmowa", "in_progress", False),
    ("employment_pending", "Oferta", "in_progress", False),
    ("employed", "Zatrudniony", "hired", True),
    ("rejected", "Odrzucony", "declined_rejected", True),
]

GENERAL_FUNNEL_STAGES: list[StageRow] = list(OFFICE_FUNNEL_STAGES)


@dataclass(frozen=True)
class LaunchSearchRoleSpec:
    role: str
    candidate_profile_code: str
    entity_profile_code: str
    funnel_name: str
    profile_name: str
    profile_description: str
    field_configs: list[dict[str, Any]]
    document_configs: list[dict[str, Any]]
    funnel_stages: list[StageRow]


def _driver_funnel_stages() -> list[StageRow]:
    rows: list[StageRow] = []
    for code, label, is_terminal in DRIVER_CE_DEFAULT_FUNNEL_STAGES:
        if is_terminal:
            system_stage = "declined_rejected" if code in {"rejected", "declined"} else "hired"
        elif code == "new":
            system_stage = "new"
        else:
            system_stage = "in_progress"
        rows.append((code, label, system_stage, is_terminal))
    return rows


LAUNCH_SEARCH_ROLE_SPECS: tuple[LaunchSearchRoleSpec, ...] = (
    LaunchSearchRoleSpec(
        role="driver",
        candidate_profile_code=DRIVER_CE_DEFAULT_CODE,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
        funnel_name=DRIVER_CE_DEFAULT_FUNNEL_NAME,
        profile_name="Driver CE (default)",
        profile_description="Профиль по умолчанию для водителей CE.",
        field_configs=list(FULL_FIELD_CONFIGS),
        document_configs=list(FULL_DOCUMENT_CONFIGS),
        funnel_stages=_driver_funnel_stages(),
    ),
    LaunchSearchRoleSpec(
        role="warehouse",
        candidate_profile_code=WAREHOUSE_WORKER_DEFAULT_CODE,
        entity_profile_code=WAREHOUSE_WORKER_PROFILE_CODE,
        funnel_name=WAREHOUSE_FUNNEL_NAME,
        profile_name="Warehouse worker (default)",
        profile_description="Профиль по умолчанию для складских позиций.",
        field_configs=list(WAREHOUSE_FIELD_CONFIGS),
        document_configs=list(BASIC_IDENTITY_DOCUMENT_CONFIGS),
        funnel_stages=list(WAREHOUSE_FUNNEL_STAGES),
    ),
    LaunchSearchRoleSpec(
        role="office",
        candidate_profile_code=OFFICE_WORKER_DEFAULT_CODE,
        entity_profile_code=OFFICE_WORKER_PROFILE_CODE,
        funnel_name=OFFICE_FUNNEL_NAME,
        profile_name="Office worker (default)",
        profile_description="Профиль по умолчанию для офисных позиций.",
        field_configs=list(OFFICE_FIELD_CONFIGS),
        document_configs=list(BASIC_IDENTITY_DOCUMENT_CONFIGS),
        funnel_stages=list(OFFICE_FUNNEL_STAGES),
    ),
    LaunchSearchRoleSpec(
        role="other",
        candidate_profile_code=GENERAL_CANDIDATE_DEFAULT_CODE,
        entity_profile_code=GENERAL_CANDIDATE_PROFILE_CODE,
        funnel_name=GENERAL_FUNNEL_NAME,
        profile_name="General candidate (default)",
        profile_description="Универсальный профиль для прочих подборов.",
        field_configs=list(GENERIC_FIELD_CONFIGS),
        document_configs=list(BASIC_IDENTITY_DOCUMENT_CONFIGS),
        funnel_stages=list(GENERAL_FUNNEL_STAGES),
    ),
)

LAUNCH_SEARCH_ROLE_BY_CODE: dict[str, LaunchSearchRoleSpec] = {
    spec.role: spec for spec in LAUNCH_SEARCH_ROLE_SPECS
}


async def _ensure_named_candidate_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
    name: str,
    stages: list[StageRow],
) -> str:
    filters = [
        Funnel.tenant_id == tenant_id,
        Funnel.type == "candidate",
        Funnel.name == name,
    ]
    if company_id:
        filters.extend([Funnel.company_id == company_id, Funnel.module_key == RECRUITMENT_MODULE_KEY])
    else:
        filters.append(Funnel.company_id.is_(None))

    target = (await db.execute(select(Funnel).where(*filters).limit(1))).scalar_one_or_none()
    if target is None:
        target = Funnel(
            tenant_id=tenant_id,
            company_id=company_id,
            module_key=RECRUITMENT_MODULE_KEY if company_id else None,
            type="candidate",
            name=name,
            is_default=False,
        )
        db.add(target)
        await db.flush()

    existing_stages = (
        await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == target.id))
    ).scalars().all()
    if not existing_stages:
        for order, (code, label, system_stage, is_terminal) in enumerate(stages):
            db.add(
                FunnelStage(
                    funnel_id=target.id,
                    code=code,
                    label=label,
                    system_stage=system_stage,
                    order=order,
                    is_terminal=bool(is_terminal),
                )
            )
        await db.flush()

        from backend.app.process_engine.pipeline_mapping import ensure_funnel_stage_pe_mapping

        stage_rows = (
            await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == target.id))
        ).scalars().all()
        for stage in stage_rows:
            await ensure_funnel_stage_pe_mapping(
                db, stage, tenant_id=tenant_id, module=RECRUITMENT_MODULE_KEY
            )

    return str(target.id)


async def ensure_launch_search_role_funnels_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> dict[str, str]:
    """Ensure role-specific candidate funnels exist on a company. Returns funnel id by role."""
    out: dict[str, str] = {}
    for spec in LAUNCH_SEARCH_ROLE_SPECS:
        funnel_id = await _ensure_named_candidate_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            name=spec.funnel_name,
            stages=spec.funnel_stages,
        )
        out[spec.role] = funnel_id
    await db.flush()
    return out


async def _ensure_role_candidate_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    spec: LaunchSearchRoleSpec,
    funnel_id: str,
) -> str:
    if spec.role == "driver":
        return spec.candidate_profile_code

    existing = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.code == spec.candidate_profile_code,
            )
        )
    ).scalar_one_or_none()

    config = {
        "field_configs": list(spec.field_configs),
        "document_configs": list(spec.document_configs),
        "launch_search_role": spec.role,
        "entity_profile_code": spec.entity_profile_code,
    }

    if existing:
        existing.funnel_id = funnel_id
        merged = dict(existing.config or {})
        merged.update(config)
        existing.config = merged
        await db.flush()
        return str(existing.id)

    profile = CandidateProfile(
        id=str(uuid4()),
        tenant_id=tenant_id,
        code=spec.candidate_profile_code,
        name=spec.profile_name,
        description=spec.profile_description,
        client_id=None,
        funnel_id=funnel_id,
        config=config,
        is_active=True,
        is_system=True,
        owner_user_id=None,
        notes="Системный профиль для launch search. Создаётся автоматически.",
    )
    db.add(profile)
    await db.flush()
    return str(profile.id)


async def ensure_launch_search_role_defaults(db: AsyncSession, tenant_id: str) -> dict[str, Any]:
    """Seed role-specific funnels (operating company) and non-driver candidate profiles."""
    company_id = await resolve_first_operating_company_id(db, tenant_id=tenant_id)
    funnel_ids = {}
    profile_ids: dict[str, str] = {}

    if company_id:
        funnel_ids = await ensure_launch_search_role_funnels_for_company(
            db, tenant_id=tenant_id, company_id=company_id
        )
    else:
        for spec in LAUNCH_SEARCH_ROLE_SPECS:
            funnel_ids[spec.role] = await _ensure_named_candidate_funnel(
                db,
                tenant_id=tenant_id,
                company_id=None,
                name=spec.funnel_name,
                stages=spec.funnel_stages,
            )

    for spec in LAUNCH_SEARCH_ROLE_SPECS:
        if spec.role == "driver":
            continue
        funnel_id = funnel_ids.get(spec.role)
        if not funnel_id:
            continue
        profile_ids[spec.role] = await _ensure_role_candidate_profile(
            db,
            tenant_id=tenant_id,
            spec=spec,
            funnel_id=funnel_id,
        )

    await db.flush()
    return {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "funnel_ids": funnel_ids,
        "profile_ids": profile_ids,
    }
