from __future__ import annotations

from typing import Dict, List, Optional

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
    # Трудоустроен
    "employed": "Трудоустроен",
    "on_trip": "Выехал в рейс",
    # Прошёл ПП
    "probation_ok": "Прошёл пробный период",
    # Отклонён
    "rejected": "Отклонён",
    "declined": "Отказался",
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


__all__ = [
    "DEFAULT_STAGE_CODE",
    "STAGES_BY_GROUP",
    "LABELS",
    "STATUS_REASON_CHOICES",
    "KANBAN_COLUMN_OF",
    "ORDER",
    "PIPELINE_SEQUENCE",
    "TERMINAL_STATUSES",
    "STAGES",
    "STAGES_ORDER",
    "is_stage_code",
    "code_for_label",
    "pipeline_for_stage_code",
]
