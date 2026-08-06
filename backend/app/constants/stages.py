from __future__ import annotations

from typing import Any, Dict, Final, List, Optional

# ----- Коды ↔ Метки -----
LABELS: Dict[str, str] = {
    # Новый
    "new": "Новый",
    "no_answer": "Не отвечает",
    # Интервью
    "contacted": "Контакт установлен",
    "questionnaire_submitted": "Анкета заполнена",
    "docs_wait": "Ожидаем документы",
    "docs_got": "Документы получены",
    # Трудоустройство
    "permit_ordered": "Заказ разрешения на работу",
    "permit_received": "Разрешение на работу получено",
    "visa": "Виза",
    "red_paper": "Красная бумага заказана",
    "trip_plan": "Планируем приезд",
    "at_client": "На базе клиента",
    "employment_pending": "На трудоустройстве",
    # Трудоустроен
    "employed": "Трудоустроен",
    "on_trip": "Выехал в рейс",
    # Прошёл ПП
    "probation_ok": "Прошёл пробный период",
    # Отклонён
    "rejected": "Отклонён",
    "declined": "Отказался",
    # Handoff flow
    "ready_for_handoff": "Готов к передаче",
    "processing_by_client": "Обработка заказчиком",
    "docs_submitted_permit": "Документы поданы на разрешение",
    "handoff_returned": "Возвращён",
    # Recruitment → HR (single-tenant / internal lane; ADR-002)
    "ready_for_hr": "Готов к передаче в HR",
    "processing_by_hr": "В обработке у HR",
    "hired": "Принят HR",
}

# ----- Метаданные этапов -----
#
# Используются для управления отображением и правами:
# - is_system: системный этап, который нельзя удалять/переименовывать на уровне конфигураций
# - visible_for_agency: этап участвует в пайплайне агентства
# - visible_for_client: этап показывается клиентским тенантам (в UI и аналитике клиента)
# - owner: семантический «владелец» этапа: agency | client | shared
#
# ВАЖНО:
# - По умолчанию любой неизвестный код считается visible_for_agency=True, visible_for_client=False, owner="agency"
STAGE_META: Dict[str, Dict[str, Any]] = {
    # Внутренний пайплайн агентства (до handoff)
    "new": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "no_answer": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "contacted": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "questionnaire_submitted": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "docs_wait": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "docs_got": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "permit_ordered": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "visa": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "red_paper": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "trip_plan": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "at_client": {
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "employment_pending": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },
    "probation_ok": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "ready_for_handoff": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "ready_for_hr": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "agency",
    },
    "processing_by_hr": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "shared",
    },
    "hired": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": False,
        "owner": "shared",
    },

    # Клиентский пайплайн (после handoff)
    "processing_by_client": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "client",
    },
    "docs_submitted_permit": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "client",
    },
    # Разрешение на работу получено — видно обеим сторонам
    "permit_received": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },
    # W trakcie zatrudnienia — для клиента и агентства
    "on_trip": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },
    # Zwrócony (возврат handoff с комментарием)
    "handoff_returned": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },

    # Терминальные статусы, общие для обеих сторон
    "employed": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },
    "rejected": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },
    "declined": {
        "is_system": True,
        "visible_for_agency": True,
        "visible_for_client": True,
        "owner": "shared",
    },
}

STATUS_REASON_CHOICES: Dict[str, List[Dict[str, str]]] = {
    "declined": [
        {"code": "schedule", "label": "Не подходит график работы"},
        {"code": "salary", "label": "Не устраивает зарплата"},
        {"code": "location", "label": "Не устраивает местоположение базы"},
        {"code": "trailer_type", "label": "Не устраивает тип полуприцепа"},
        {"code": "night_driving", "label": "Не устраивает ночная езда"},
        {"code": "bonus_scheme", "label": "Не устраивает способ премирования"},
        {"code": "cab_overnight", "label": "Не хочет ночевать в кабине"},
        {"code": "company_reviews", "label": "Плохие отзывы о компании"},
    ],
    "rejected": [
        {"code": "eu_exp_lt_1y", "label": "Опыт по ЕС менее 1 года"},
        {"code": "eu_exp_lt_6m", "label": "Опыт по ЕС менее 6 месяцев"},
        {"code": "awaiting_residence", "label": "Ожидает ВНЖ"},
        {"code": "language", "label": "Не говорит на русском/английском/польском"},
        {"code": "no_visa", "label": "Нет визы/ВНЖ"},
        {"code": "no_ce_experience", "label": "Нет опыта по СЕ"},
        {"code": "no_code95", "label": "Нет 95 кода"},
        {"code": "no_chip", "label": "Нет чипа"},
        {"code": "age", "label": "Возраст"},
        {"code": "blacklist", "label": "Ч/С"},
        {"code": "wrong_phone", "label": "Неверно указан номер"},
        {"code": "double_crew", "label": "Двойной экипаж"},
        {"code": "no_response", "label": "Не отвечает"},
        {"code": "recruitment_completed", "label": "Набор завершён"},
    ],
}

_LABEL_TO_CODE: Dict[str, str] = {v.lower(): k for k, v in LABELS.items()}

# ----- Колонки канбана -> коды -----
STAGES_BY_GROUP: Dict[str, List[str]] = {
    "new": ["new", "no_answer"],
    "interview": [
        "contacted",
        "questionnaire_submitted",
        "docs_wait",
        "docs_got",
    ],
    "hiring": [
        "permit_ordered",
        "permit_received",
        "visa",
        "red_paper",
        "trip_plan",
        "at_client",
        "employment_pending",
        "on_trip",
    ],
    "probation": [
        "probation_ok",
    ],
    "employed": [
        "employed",
    ],
    "rejected": [
        "rejected",
        "declined",
    ],
    "ready": ["ready_for_handoff", "ready_for_hr"],
    "internal_hr": [
        "processing_by_hr",
        "hired",
    ],
    "client_process": [
        "processing_by_client",
        "docs_submitted_permit",
        "permit_received",
        "employment_pending",
        "employed",
    ],
    "returned": ["handoff_returned"],
}

# код -> колонка
KANBAN_COLUMN_OF: Dict[str, str] = {
    code: group for group, codes in STAGES_BY_GROUP.items() for code in codes
}

# Плоский порядок
ORDER: List[str] = [code for group in STAGES_BY_GROUP.values() for code in group]

# Каноническая последовательность статусов пайплайна
PIPELINE_SEQUENCE: List[str] = ORDER.copy()

# Совместимый список словарей для старых вызовов (code + label)
STAGES: List[Dict[str, str]] = [{"code": code, "label": LABELS.get(code, code)} for code in ORDER]
STAGES_ORDER: List[str] = ORDER.copy()

# Терминальные статусы, из которых выход невозможен
# Финальные статусы: прошёл ПП или завершил работу (уволен/ушёл сам).
TERMINAL_STATUSES = {"probation_ok", "rejected", "declined"}

# Путь завершён (успех или отказ): нет операционных next-action / risk v1 и агрегатов активного пайплайна.
# Включает TERMINAL_STATUSES + «трудоустроен» (успешный финал воронки).
PIPELINE_COMPLETED_STAGE_CODES: frozenset[str] = frozenset(TERMINAL_STATUSES) | frozenset(
    {"employed", "ready_for_hr", "hired", "processing_by_hr"}
)

# Ops analytics overview «stuck» — only real ``LABELS`` / ``STAGES_BY_GROUP`` codes (not legacy pseudo-stages).
OVERVIEW_STUCK_AGENCY_STAGE: Final[str] = "docs_wait"
OVERVIEW_STUCK_EMPLOYER_STAGE_CODES: Final[tuple[str, ...]] = tuple(STAGES_BY_GROUP["interview"])

assert OVERVIEW_STUCK_AGENCY_STAGE in LABELS
assert all(c in LABELS for c in OVERVIEW_STUCK_EMPLOYER_STAGE_CODES)

# ----- Agency handoff lane (see ADR-002, stage_meta_recruitment_filter) -----
# Recruitment roles must not jump into HR/client terminal lanes when handoff is enabled.
# P0 (2026): recruitment *surface* shows only pre-employment / handoff-boundary work; all
# permit/trip/employment/HR-client processing tails are hidden from recruiter funnel UI.
RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES: Final[frozenset[str]] = frozenset(
    {
        "hired",
        "employed",
        "processing_by_hr",
        "processing_by_client",
        "docs_submitted_permit",
        "employment_pending",
        "on_trip",
        "probation_ok",
        "permit_ordered",
        "permit_received",
        "visa",
        "red_paper",
        "trip_plan",
        "at_client",
    }
)

# HR officer funnel: internal lane + shared downstream (excludes client-only first steps).
INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES: Final[frozenset[str]] = frozenset(
    {
        "processing_by_hr",
        "hired",
        "permit_received",
        "employment_pending",
        "on_trip",
        "employed",
        "handoff_returned",
        "rejected",
        "declined",
        "visa",
        "red_paper",
        "trip_plan",
        "at_client",
    }
)

# Client processor lane after agency→client handoff.
CLIENT_HANDOFF_VISIBLE_STAGE_CODES: Final[frozenset[str]] = frozenset(
    {
        "processing_by_client",
        "docs_submitted_permit",
        "permit_received",
        "employment_pending",
        "on_trip",
        "employed",
        "handoff_returned",
        "rejected",
        "declined",
    }
)

# По умолчанию
DEFAULT_STAGE_CODE: str = "new"


# ===== Утилиты =====


def is_stage_code(value: str) -> bool:
    return value in LABELS


def code_for_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return _LABEL_TO_CODE.get(value.strip().lower())


def pipeline_for_stage_code(stage_code: str) -> str:
    """
    Маппинг "тонкой" стадии кандидата -> агрегированная колонка канбана вакансии.
    Возвращает одно из: new | interview | hiring | employed | probation | rejected
    """
    return KANBAN_COLUMN_OF.get(stage_code, "new")


def is_pipeline_completed_stage(value: Optional[str]) -> bool:
    """True when `value` is a canonical pipeline-completed stage code (case-insensitive)."""
    s = (value or "").strip().lower()
    return bool(s) and s in PIPELINE_COMPLETED_STAGE_CODES


def is_candidate_operationally_terminal(
    *,
    stage: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    """True when neither funnel work nor reminders should treat the row as «in pipeline».

    Some flows set ``Candidate.status`` (row-level) to a completed code such as
    ``rejected`` without updating ``Candidate.stage`` — next-action and ops
    counters must still treat the candidate as closed.

    Only **canonical** codes in ``PIPELINE_COMPLETED_STAGE_CODES`` count; arbitrary
    row strings (e.g. ``returned_for_revision``) never match by accident.
    """
    if is_pipeline_completed_stage(stage):
        return True
    return is_pipeline_completed_stage(status)


__all__ = [
    "DEFAULT_STAGE_CODE",
    "STAGES_BY_GROUP",
    "LABELS",
    "STAGE_META",
    "STATUS_REASON_CHOICES",
    "KANBAN_COLUMN_OF",
    "ORDER",
    "PIPELINE_SEQUENCE",
    "PIPELINE_COMPLETED_STAGE_CODES",
    "OVERVIEW_STUCK_AGENCY_STAGE",
    "OVERVIEW_STUCK_EMPLOYER_STAGE_CODES",
    "TERMINAL_STATUSES",
    "STAGES",
    "STAGES_ORDER",
    "RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES",
    "INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES",
    "CLIENT_HANDOFF_VISIBLE_STAGE_CODES",
    "is_pipeline_completed_stage",
    "is_candidate_operationally_terminal",
    "is_stage_code",
    "code_for_label",
    "pipeline_for_stage_code",
]
