from __future__ import annotations

from typing import Optional


# нормализуем вход (рус/англ/разные регистры, пробелы)
def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    return s.strip().lower()


# карта соответствия: 14 подробных этапов кандидата -> 6 укрупнённых статусов вакансии
_STAGE_TO_STATUS = {
    # Новый
    "новый": "new",
    "new": "new",
    "не отвечает": "new",
    "no_answer": "new",
    # Интервью (Контакт установлен, Ожидаем документы, Документы получены)
    "интервью": "interview",
    "контакт установлен": "interview",
    "анкета заполнена": "interview",
    "ожидаем документы": "interview",
    "документы получены": "interview",
    "contacted": "interview",
    "docs_wait": "interview",
    "docs_got": "interview",
    "questionnaire_submitted": "interview",
    "awaiting docs": "interview",
    "docs received": "interview",
    # Трудоустройство (все бюрократические шаги + приезд/на базе)
    "трудоустройство": "hiring",
    "заказ разрешения на работу": "hiring",
    "разрешение на работу получено": "hiring",
    "виза": "hiring",
    "красная бумага заказана": "hiring",
    "планируем приезд": "hiring",
    "на базе клиента": "hiring",
    "work permit ordered": "hiring",
    "work permit received": "hiring",
    "visa": "hiring",
    "red paper ordered": "hiring",
    "arrival planned": "hiring",
    "on client site": "hiring",
    "permit_ordered": "hiring",
    "permit_received": "hiring",
    "red_paper": "hiring",
    "trip_plan": "hiring",
    "at_client": "hiring",
    "employment_pending": "hiring",
    "на трудоустройстве": "hiring",
    "on_trip": "hiring",
    "ready_for_handoff": "hiring",
    "ready_for_hr": "hiring",
    "processing_by_hr": "hiring",
    "processing_by_client": "hiring",
    # Трудоустроен
    "трудоустроен": "employed",
    "выехал в рейс": "employed",
    "employed": "employed",
    "dispatched": "employed",
    "hired": "employed",
    # Прошёл пробный период
    "прошёл пробный период": "probation",
    "passed probation": "probation",
    # Отклонен
    "отклонен": "rejected",
    "отклонён": "rejected",
    "rejected": "rejected",
    "отказался": "rejected",
    "declined": "rejected",
}


def stage_to_status(candidate_stage: Optional[str]) -> Optional[str]:
    key = _norm(candidate_stage)
    return _STAGE_TO_STATUS.get(key)
