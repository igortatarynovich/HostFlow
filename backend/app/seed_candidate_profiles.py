"""Seed function to create base and default candidate profiles for each tenant."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.vacancy import Vacancy

DRIVER_CE_DEFAULT_CODE = "driver_ce_default"

# Все поля карточки кандидата «без профиля» — видимы, не обязательны (как при отсутствии профиля)
FULL_FIELD_CONFIGS: list[dict] = [
    {"field_key": "first_name", "field_type": "text", "label": "Имя", "required": False, "visible": True, "order": 1},
    {"field_key": "last_name", "field_type": "text", "label": "Фамилия", "required": False, "visible": True, "order": 2},
    {"field_key": "email", "field_type": "text", "label": "Email", "required": False, "visible": True, "order": 3},
    {"field_key": "phone", "field_type": "text", "label": "Телефон", "required": False, "visible": True, "order": 4},
    {"field_key": "preferred_contact", "field_type": "text", "label": "Предпочитаемый контакт", "required": False, "visible": True, "order": 5},
    {"field_key": "birth_date", "field_type": "date", "label": "Дата рождения", "required": False, "visible": True, "order": 6},
    {"field_key": "citizenship", "field_type": "text", "label": "Гражданство", "required": False, "visible": True, "order": 7},
    {"field_key": "country_code", "field_type": "text", "label": "Страна", "required": False, "visible": True, "order": 8},
    {"field_key": "languages", "field_type": "text", "label": "Языки", "required": False, "visible": True, "order": 9},
    {"field_key": "current_location", "field_type": "text", "label": "Текущее местоположение", "required": False, "visible": True, "order": 10},
    {"field_key": "experience_eu_years", "field_type": "number", "label": "Опыт в ЕС (лет)", "required": False, "visible": True, "order": 11},
    {"field_key": "experience_non_eu_years", "field_type": "number", "label": "Опыт вне ЕС (лет)", "required": False, "visible": True, "order": 12},
    {"field_key": "intl_experience", "field_type": "boolean", "label": "Международный опыт", "required": False, "visible": True, "order": 13},
    {"field_key": "trailer_types", "field_type": "text", "label": "Типы прицепов", "required": False, "visible": True, "order": 14},
    {"field_key": "route_types", "field_type": "text", "label": "Типы маршрутов", "required": False, "visible": True, "order": 15},
    {"field_key": "employment_history", "field_type": "text", "label": "История занятости", "required": False, "visible": True, "order": 16},
    {"field_key": "poland_stay_basis", "field_type": "text", "label": "Основание пребывания в Польше", "required": False, "visible": True, "order": 17},
    {"field_key": "eu_routes", "field_type": "boolean", "label": "Маршруты ЕС", "required": False, "visible": True, "order": 18},
    {"field_key": "frigo_experience", "field_type": "boolean", "label": "Опыт с холодильниками", "required": False, "visible": True, "order": 19},
    {"field_key": "has_adr", "field_type": "boolean", "label": "ADR", "required": False, "visible": True, "order": 20},
]

# Документы по умолчанию (driver): как в ruleset — required + optional
FULL_DOCUMENT_CONFIGS: list[dict] = [
    {"document_type_id": "identity_document", "required": True},
    {"document_type_id": "qualification_code95", "required": True},
    {"document_type_id": "tachograph_card", "required": False},
    {"document_type_id": "driver_license", "required": False},
    {"document_type_id": "swiadectwo_kierowcy", "required": False},
    {"document_type_id": "medical_certificate", "required": False},
]

DRIVER_CE_DEFAULT_STAGE_CONFIGS: list[dict] = [
    {"stage_code": "new", "stage_label": "Nowy", "order": 1, "active": True},
    {"stage_code": "no_answer", "stage_label": "Brak kontaktu", "order": 2, "active": True},
    {"stage_code": "contacted", "stage_label": "Kontakt nawiązany", "order": 3, "active": True},
    {"stage_code": "questionnaire_submitted", "stage_label": "Kwestionariusz wysłany", "order": 4, "active": True},
    {"stage_code": "docs_wait", "stage_label": "Czekamy na dokumenty", "order": 5, "active": True},
    {"stage_code": "docs_got", "stage_label": "Dokumenty otrzymane", "order": 6, "active": True},
    {"stage_code": "ready_for_handoff", "stage_label": "Gotowy do przekazania", "order": 7, "active": True},
    {"stage_code": "processing_by_client", "stage_label": "Procesowany przez zleceniodawcę", "order": 8, "active": True},
    {"stage_code": "docs_submitted_permit", "stage_label": "Złożono dokumenty na zezwolenie", "order": 9, "active": True},
    {"stage_code": "permit_received", "stage_label": "Otrzymano zezwolenie", "order": 10, "active": True},
    {"stage_code": "handoff_returned", "stage_label": "Zwrócony", "order": 11, "active": True},
    {"stage_code": "on_trip", "stage_label": "W trakcie zatrudnienia", "order": 12, "active": True},
    {"stage_code": "rejected", "stage_label": "Odrzucony", "order": 13, "active": True},
    {"stage_code": "declined", "stage_label": "Kandydat zrezygnował", "order": 14, "active": True},
    {"stage_code": "employed", "stage_label": "Zatrudniony", "order": 15, "active": True},
]

DRIVER_CE_DEFAULT_STAGE_CODES: list[str] = [
    "new",
    "no_answer",
    "contacted",
    "questionnaire_submitted",
    "docs_wait",
    "docs_got",
    "ready_for_handoff",
    "processing_by_client",
    "docs_submitted_permit",
    "permit_received",
    "handoff_returned",
    "on_trip",
    "rejected",
    "declined",
    "employed",
]

DRIVER_CE_DEFAULT_STAGE_COLUMNS: dict[str, list[str]] = {
    "new": ["new", "no_answer"],
    "interview": ["contacted", "questionnaire_submitted", "docs_wait", "docs_got"],
    "ready": ["ready_for_handoff"],
    "client_process": ["processing_by_client", "docs_submitted_permit", "permit_received"],
    "returned": ["handoff_returned"],
    "hiring": ["on_trip"],
    "rejected": ["rejected", "declined"],
    "employed": ["employed"],
}

DRIVER_CE_DEFAULT_COLUMN_ORDER: list[str] = [
    "new",
    "interview",
    "ready",
    "client_process",
    "returned",
    "hiring",
    "rejected",
    "employed",
]

DRIVER_CE_DEFAULT_STAGE_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "new": {
        "new": {"pl": "Nowy", "ru": "Новый", "en": "New"},
        "no_answer": {"pl": "Brak kontaktu", "ru": "Нет контакта", "en": "No contact"},
    },
    "interview": {
        "contacted": {"pl": "Kontakt nawiązany", "ru": "Контакт установлен", "en": "Contact made"},
        "questionnaire_submitted": {"pl": "Kwestionariusz wysłany", "ru": "Анкета отправлена", "en": "Questionnaire sent"},
        "docs_wait": {"pl": "Czekamy na dokumenty", "ru": "Ждем документы", "en": "Waiting for documents"},
        "docs_got": {"pl": "Dokumenty otrzymane", "ru": "Документы получены", "en": "Documents received"},
    },
    "ready": {
        "ready_for_handoff": {"pl": "Gotowy do przekazania", "ru": "Готов к передаче", "en": "Ready for handoff"},
    },
    "client_process": {
        "processing_by_client": {
            "pl": "Procesowany przez zleceniodawcę",
            "ru": "Процесс у заказчика",
            "en": "Processed by client",
        },
        "docs_submitted_permit": {
            "pl": "Złożono dokumenty na zezwolenie",
            "ru": "Документы поданы на разрешение",
            "en": "Documents submitted for permit",
        },
        "permit_received": {"pl": "Otrzymano zezwolenie", "ru": "Разрешение получено", "en": "Permit received"},
    },
    "returned": {
        "handoff_returned": {"pl": "Zwrócony", "ru": "Возвращен", "en": "Returned"},
    },
    "hiring": {
        "on_trip": {"pl": "W trakcie zatrudnienia", "ru": "В процессе трудоустройства", "en": "In employment process"},
    },
    "rejected": {
        "rejected": {"pl": "Odrzucony", "ru": "Отклонен", "en": "Rejected"},
        "declined": {"pl": "Kandydat zrezygnował", "ru": "Кандидат отказался", "en": "Candidate declined"},
    },
    "employed": {
        "employed": {"pl": "Zatrudniony", "ru": "Трудоустроен", "en": "Employed"},
    },
}

DRIVER_CE_DEFAULT_FUNNEL_NAME = "Driver CE (default)"

DRIVER_CE_DEFAULT_FUNNEL_STAGES: list[tuple[str, str, bool]] = [
    ("new", "Nowy", False),
    ("no_answer", "Brak kontaktu", False),
    ("contacted", "Kontakt nawiązany", False),
    ("questionnaire_submitted", "Kwestionariusz wysłany", False),
    ("docs_wait", "Czekamy na dokumenty", False),
    ("docs_got", "Dokumenty otrzymane", False),
    ("ready_for_handoff", "Gotowy do przekazania", False),
    ("processing_by_client", "Procesowany przez zleceniodawcę", False),
    ("docs_submitted_permit", "Złożono dokumenty na zezwolenie", False),
    ("permit_received", "Otrzymano zezwolenie", False),
    ("handoff_returned", "Zwrócony", False),
    ("on_trip", "W trakcie zatrudnienia", False),
    ("rejected", "Odrzucony", True),
    ("declined", "Kandydat zrezygnował", True),
    ("employed", "Zatrudniony", True),
]


def _driver_ce_default_stage_config() -> dict:
    return {
        "stage_configs": list(DRIVER_CE_DEFAULT_STAGE_CONFIGS),
        "stage_codes": list(DRIVER_CE_DEFAULT_STAGE_CODES),
        "stage_columns": dict(DRIVER_CE_DEFAULT_STAGE_COLUMNS),
        "column_order": list(DRIVER_CE_DEFAULT_COLUMN_ORDER),
        "stage_labels": dict(DRIVER_CE_DEFAULT_STAGE_LABELS),
    }


def _driver_ce_default_config() -> dict:
    return {
        "field_configs": list(FULL_FIELD_CONFIGS),
        "document_configs": list(FULL_DOCUMENT_CONFIGS),
        **_driver_ce_default_stage_config(),
    }


async def _ensure_driver_ce_default_funnel(db: AsyncSession, tenant_id: str) -> str:
    """Ensure tenant has the default candidate funnel used by driver_ce_default profile."""
    funnels = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.type == "candidate",
            )
        )
    ).scalars().all()

    target: Funnel | None = None
    for f in funnels:
        if f.is_default:
            target = f
            break
    if target is None:
        for f in funnels:
            if (f.name or "").strip() == DRIVER_CE_DEFAULT_FUNNEL_NAME:
                target = f
                break

    if target is None:
        target = Funnel(
            tenant_id=tenant_id,
            type="candidate",
            name=DRIVER_CE_DEFAULT_FUNNEL_NAME,
            is_default=True,
        )
        db.add(target)
        await db.flush()

    for f in funnels:
        f.is_default = (f.id == target.id)
    target.is_default = True
    target.name = DRIVER_CE_DEFAULT_FUNNEL_NAME

    await db.execute(delete(FunnelStage).where(FunnelStage.funnel_id == target.id))
    for idx, (code, label, is_terminal) in enumerate(DRIVER_CE_DEFAULT_FUNNEL_STAGES):
        db.add(
            FunnelStage(
                funnel_id=target.id,
                code=code,
                label=label,
                order=idx,
                is_terminal=is_terminal,
            )
        )
    await db.flush()
    return target.id


async def ensure_driver_ce_default_profile(db: AsyncSession, tenant_id: str) -> None:
    """Create driver_ce_default profile if missing. Full config = all fields + all driver docs (same as card without profile).
    Assign this profile to all vacancies that have no candidate_profile_id.
    """
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.tenant_id == tenant_id)
        .where(CandidateProfile.code == DRIVER_CE_DEFAULT_CODE)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    funnel_id = await _ensure_driver_ce_default_funnel(db, tenant_id)
    if existing:
        profile_id = existing.id
        cfg = dict(existing.config or {})
        # Дефолтный системный профиль всегда синхронизируем на актуальную воронку.
        if not (cfg.get("field_configs") or cfg.get("document_configs")):
            cfg["field_configs"] = list(FULL_FIELD_CONFIGS)
            cfg["document_configs"] = list(FULL_DOCUMENT_CONFIGS)
        cfg.update(_driver_ce_default_stage_config())
        existing.funnel_id = funnel_id
        existing.config = cfg
        await db.flush()
    else:
        profile = CandidateProfile(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=DRIVER_CE_DEFAULT_CODE,
            name="Driver CE (default)",
            description="Профиль по умолчанию для водителей CE. Все поля и документы как в карточке без профиля. Нельзя редактировать; можно создать копию.",
            client_id=None,
            funnel_id=funnel_id,
            config=_driver_ce_default_config(),
            is_active=True,
            is_system=True,
            owner_user_id=None,
            notes="Системный профиль по умолчанию. Создаётся автоматически.",
        )
        db.add(profile)
        await db.flush()
        profile_id = profile.id

    # Привязать вакансии без профиля к driver_ce_default
    await db.execute(
        update(Vacancy)
        .where(Vacancy.tenant_id == tenant_id)
        .where(Vacancy.candidate_profile_id.is_(None))
        .values(candidate_profile_id=profile_id)
    )
    await db.commit()


async def ensure_base_candidate_profile(db: AsyncSession, tenant_id: str) -> None:
    """Create base candidate profile if it doesn't exist for the tenant."""
    # Check if base profile already exists
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.tenant_id == tenant_id)
        .where(CandidateProfile.code == "base")
        .where(CandidateProfile.is_system == True)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    
    if existing:
        return  # Base profile already exists
    
    # Create base profile with minimal configuration
    from uuid import uuid4
    
    base_profile = CandidateProfile(
        id=str(uuid4()),
        tenant_id=tenant_id,
        code="base",
        name="Базовый профиль",
        description="Базовый профиль кандидата. Содержит только обязательные поля. Нельзя редактировать.",
        client_id=None,
        config={
            "field_configs": [
                {
                    "field_key": "first_name",
                    "field_type": "text",
                    "label": "Имя",
                    "required": True,
                    "visible": True,
                    "order": 1,
                    "is_system": True,
                },
                {
                    "field_key": "last_name",
                    "field_type": "text",
                    "label": "Фамилия",
                    "required": True,
                    "visible": True,
                    "order": 2,
                    "is_system": True,
                },
                {
                    "field_key": "email",
                    "field_type": "text",
                    "label": "Email",
                    "required": False,
                    "visible": True,
                    "order": 3,
                    "is_system": True,
                },
                {
                    "field_key": "phone",
                    "field_type": "text",
                    "label": "Телефон",
                    "required": False,
                    "visible": True,
                    "order": 4,
                    "is_system": True,
                },
            ],
            "document_configs": [],  # No documents by default
        },
        is_active=True,
        is_system=True,
        owner_user_id=None,
        notes="Системный базовый профиль. Создается автоматически для каждого тенанта.",
    )
    
    db.add(base_profile)
    await db.commit()
