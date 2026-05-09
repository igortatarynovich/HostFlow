"""Таксономия событий для **взвешенной дневной нагрузки** (fallback выбора assignee).

Phase 2.1 (ADR-012, 2026-05-09): после поглощения
``communication_planner_events`` и ``candidate_tasks`` каноничной таблицей
``activities`` оба «потока» — это один и тот же ORM ``Activity``,
разделённый на ``starts_at IS NOT NULL`` (planner-style, calendar block) и
``starts_at IS NULL`` (reminder-style, deadline-only) — см.
``team_assignee_auto.compute_managers_weighted_day_load``.

Суммируются два **независимых потока** из БД (см. ``team_assignee_auto``)::

  1. **Planner-style** — ``Activity`` где ``starts_at IS NOT NULL``;
     ``kind`` берётся из ``metadata.planner.kind`` (для строк, перенесённых
     из ``communication_planner_events`` миграцией ``202607150004_pti``)
     или из ``Activity.type`` для нативно созданных активностей.
  2. **Reminder-style** — ``Activity`` где ``starts_at IS NULL``;
     ``type`` — это ``Activity.type`` (строка до 64; раньше ``reminders.type``).

Назначение разделения: **сначала зафиксировать полный набор лексики**, потом
подобрать веса так, чтобы порядок величин отражал продукт (SLA/операции > ручной to-do).
Неизвестные ``kind`` / ``type`` из будущих фич попадают в *default* (1.0) — при
добавлении нового системного типа **добавьте строку** в таблицу ниже.
"""

from __future__ import annotations

from typing import Final

from backend.app.models.reminder import ReminderStatus

# ---------------------------------------------------------------------------
# 1) Planner-style: ``Activity`` where ``starts_at IS NOT NULL``.
#    ``kind`` is read from ``metadata.planner.kind`` (preserved by
#    ``202607150004_pti`` for rows backfilled from
#    ``communication_planner_events``) with a fallback to ``Activity.type``
#    for natively created calendar blocks.
#    UI: ``CommunicationsCalendarPage`` — same vocabulary + matching labels.
# ---------------------------------------------------------------------------
PLANNER_EVENT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "meeting",
        "call",
        "task",
        "followup",
        "shift",
    }
)

# База относительных единиц (тай-брейк нагрузки: встреча > звонок > task).
# Неизвестный kind (опечатка / новая фича) — как task-level (1.0).
DEFAULT_UNKNOWN_PLANNER_KIND_WEIGHT: Final[float] = 1.0
PLANNER_KIND_BASE_WEIGHT: Final[dict[str, float]] = {
    "meeting": 4.0,  # блок времени, внешние участники, фасилитация
    "shift": 3.5,  # смена / дежурство
    "call": 2.5,
    "followup": 1.6,  # follow-up в календаре (отдельно от ``Reminder.type == "followup"``)
    "task": 1.0,
}

# ---------------------------------------------------------------------------
# 2) Reminder-style: ``Activity.type`` (String 64) on rows where
#    ``starts_at IS NULL`` — **широкий** набор.
#
#    Группы (для читаемости; вес задаётся **по конкретному** ``type``):
#    * **SLA / планировщик** — ``communications_scheduler``,
#      ``reminders_v2._SLA_REMINDER_TYPES`` (синхронизировать при изменении).
#    * **UoS** — ``uos_auto_activities`` (префикс ``uos_``).
#    * **Документы** — ``reminders.py`` (константы ``document_expiry`` …).
#    * **Пользовательские** — API default ``custom``, тесты ``manual`` / ``followup``.
# ---------------------------------------------------------------------------

# Подмножества (документация; не обязаны покрывать все ключи REMINDER_TYPE_BASE_WEIGHT).
REMINDER_TYPES_SLA_AND_OPS: Final[frozenset[str]] = frozenset(
    {
        "communications_sla_overdue",
        "communications_thread_escalated",
        "leads_no_next_action",
        "leads_stuck_stage",
        "invoice_overdue_payment",
    }
)
REMINDER_TYPES_UOS: Final[frozenset[str]] = frozenset(
    {
        "uos_order_confirm",
        "uos_invoice_follow_payment",
        "uos_candidate_call",
        "uos_inbound_reply",
        "uos_client_intro",
        "uos_client_stage_follow_up",
        "uos_candidate_stage_follow_up",
        "uos_vacancy_recruiting_follow_up",
    }
)
REMINDER_TYPES_DOCUMENT: Final[frozenset[str]] = frozenset(
    {
        "document_expiry",
        "document_workflow_step",
    }
)
REMINDER_TYPES_USER_GENERIC: Final[frozenset[str]] = frozenset(
    {
        "custom",
        "manual",
        "followup",  # user reminder (не путать с planner kind followup)
    }
)

# Единая таблица: **каждый известный продуктовый type** с явным весом.
# Синхронизировать с ``_SLA_REMINDER_TYPES`` в ``reminders_v2.py`` (тест покрывает).
DEFAULT_UNKNOWN_REMINDER_TYPE_WEIGHT: Final[float] = 1.0
REMINDER_TYPE_BASE_WEIGHT: Final[dict[str, float]] = {
    # --- Ops / SLA (критичность реакции) ---
    "communications_sla_overdue": 3.2,
    "communications_thread_escalated": 2.8,
    "invoice_overdue_payment": 2.4,
    "leads_stuck_stage": 1.8,
    "leads_no_next_action": 1.7,
    # --- UoS (автонуджи; слегка разведены по срочности смысла) ---
    "uos_inbound_reply": 1.5,
    "uos_invoice_follow_payment": 1.4,
    "uos_candidate_call": 1.4,
    "uos_order_confirm": 1.3,
    "uos_client_intro": 1.2,
    "uos_client_stage_follow_up": 1.2,
    "uos_candidate_stage_follow_up": 1.2,
    "uos_vacancy_recruiting_follow_up": 1.2,
    # --- Документы (фон, но фиксированный SLA-контекст) ---
    "document_expiry": 1.2,
    "document_workflow_step": 1.2,
    # --- Пользовательский ввод (дефолт веса «обычной задачи») ---
    "custom": 1.0,
    "manual": 1.0,
    "followup": 1.0,
}

# Полный набор type, для которых заданы явные веса (остальные → default).
ALL_CATALOGED_REMINDER_TYPES: Final[frozenset[str]] = frozenset(REMINDER_TYPE_BASE_WEIGHT)

assert REMINDER_TYPES_SLA_AND_OPS <= ALL_CATALOGED_REMINDER_TYPES
assert REMINDER_TYPES_UOS <= ALL_CATALOGED_REMINDER_TYPES
assert REMINDER_TYPES_DOCUMENT <= ALL_CATALOGED_REMINDER_TYPES
assert REMINDER_TYPES_USER_GENERIC <= ALL_CATALOGED_REMINDER_TYPES
assert PLANNER_EVENT_KINDS == frozenset(PLANNER_KIND_BASE_WEIGHT.keys())


# Множители по полям, общие для planner и reminders, где применимо.
LOAD_PRIORITY_MULT: Final[dict[str, float]] = {
    "urgent": 1.6,
    "high": 1.35,
    "normal": 1.0,
    "low": 0.85,
}
# Planner-style: ``Activity.status`` on ``starts_at IS NOT NULL`` rows
# (Phase 2.1 absorbed legacy ``CommunicationPlannerEvent.status``;
# values are a subset of ``ActivityStatus``).
PLANNER_STATUS_LOAD_MULT: Final[dict[str, float]] = {
    "cancelled": 0.0,
    "done": 0.12,
    "planned": 1.0,
    "in_progress": 1.15,
}
# Reminder-style: ``Activity.status`` on ``starts_at IS NULL`` rows
# (legacy ``ReminderStatus`` constants are still importable; the values
# match ``ActivityStatus.*`` post-``activity_layer_v1``).
REMINDER_STATUS_LOAD_MULT: Final[dict[str, float]] = {
    ReminderStatus.cancelled: 0.0,
    ReminderStatus.done: 0.1,
    ReminderStatus.overdue: 1.45,
    ReminderStatus.new: 1.0,
    ReminderStatus.pending: 1.0,
    ReminderStatus.sent: 0.9,
}


def planner_kind_base_load(kind: str) -> float:
    k = str(kind or "task").strip().lower()
    return float(PLANNER_KIND_BASE_WEIGHT.get(k, DEFAULT_UNKNOWN_PLANNER_KIND_WEIGHT))


def reminder_type_base_load(rtype: str) -> float:
    rt = str(rtype or "custom").strip().lower()
    return float(REMINDER_TYPE_BASE_WEIGHT.get(rt, DEFAULT_UNKNOWN_REMINDER_TYPE_WEIGHT))
