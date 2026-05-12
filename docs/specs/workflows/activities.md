# Activities — Workflow Specification

**Status:** canon. Workflow-спека для единого operational слоя HostFlow. Заменяет три устаревших файла:

- `workflows/reminders.md` — superseded by this document
- `workflows/reminders_matrix.md` — superseded by [`activities-sla-matrix.md`](activities-sla-matrix.md)
- `workflows/reminders_rework.md` — superseded by canon [`../architecture/activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md)

**Связанные документы:**

- [`../architecture/ADR-012-activity-notification-operating-layer.md`](../architecture/ADR-012-activity-notification-operating-layer.md) — решение
- [`../architecture/activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md) — canon (поля, инварианты, маппинг кода)
- [`../architecture/operational-event-boundaries.md`](../architecture/operational-event-boundaries.md) — events / consumers / command-flow ownership
- [`activities-sla-matrix.md`](activities-sla-matrix.md) — SLA / эскалации
- [`document_expiry.md`](document_expiry.md) — частный кейс: документы → Activity
- [`../operations-loop.md`](../operations-loop.md) — as-built и G-1…G-10
- [`../manager-assignment.md`](../manager-assignment.md) — owner-поля; `assigned_to_user_id` — canon Activity

---

## 1. Цель

Описать **жизненный цикл Activity** — единственной операционной сущности HostFlow для задач, напоминаний, follow-up, звонков, встреч, проверок документов, подтверждений приезда и любых других действий, которые должен выполнить пользователь.

Ключевое: **Activity ≠ Notification**. Activity — это **работа**. Notification — это **сигнал**. Если требуется и работа, и сигнал — публикуются обе сущности, со ссылкой `notification.activity_id`. Подробнее — canon §1.

---

## 2. Типы Activity

См. canon §2.2. Закрытый enum `type`:

| Группа | Типы |
|---|---|
| **Communication** | `call`, `message`, `email`, `meeting`, `follow_up` |
| **Generic work** | `task`, `custom` |
| **Documents** | `document_request`, `document_check` |
| **Recruitment** | `candidate_review`, `vacancy_action` |
| **Clients** | `client_follow_up` |
| **Workforce** | `work_permit_action`, `arrival_action` |

Расширение enum — только через PR с обновлением canon §2.2 и этого файла.

---

## 3. Создание Activity

### 3.1 Источники

Activity создаётся **тремя способами**:

1. **Автоматически** — `services/automation_rules.py::actions.create_activity` или специализированные lifecycle-сервисы (`candidate_lifecycle.py`, `lead_lifecycle.py`, `handoff.py`, `services/reminders.py` для документов, `communications_scheduler.py` для thread SLA).
2. **Из NBA** — пользователь принял рекомендацию через `POST /next-actions/{id}/accept` → создаётся Activity по `recommended_activity_payload`.
3. **Вручную** — пользователь нажал «Create activity» в карточке кандидата / лида / документа / треда; либо `POST /activities` напрямую.

### 3.2 Обязательные поля при создании

См. canon §2.7 (инварианты). Минимум:

- `tenant_id` (из контекста)
- `type` (из enum §2)
- `title`
- `due_at` (или `starts_at` для timed events; `due_at` тогда выводится из `starts_at + duration_minutes`)
- `related_entity_type` + `related_entity_id` (`'custom'` + `'0'` для свободного todo)
- `source_module` (`leads`, `candidates`, `documents`, `comms`, `workforce`, `automation`, `user`)
- `assigned_to_user_id` — либо явный, либо помечается «требует распределения» (`priority='high'` + создаётся Notification `type='activity_assigned'` группе менеджеров)

### 3.3 Default-значения

| Поле | Default |
|---|---|
| `status` | `planned` |
| `priority` | `normal` |
| `channel` | `internal` |
| `created_by_user_id` | `current_user.id` |
| `reminder_at` | `due_at − 15min` (если `reminder_at` явно не задан и не `meeting`/`call`); для `meeting`/`call` — `due_at − 30min` |
| `sla_due_at` / `sla_status` | по [`activities-sla-matrix.md`](activities-sla-matrix.md), если `type` ∈ SLA-types |
| `company_id` | резолвится через `related_entity` (если кандидат — его `company_id`, если лид — `null` до конверсии и т.д.) |

### 3.4 Идемпотентность

Создание Activity автоматизацией обязано быть идемпотентным:

- Ключ дедупликации: `(tenant_id, source_module, related_entity_type, related_entity_id, type, dedupe_key?)`.
- `dedupe_key` хранится в `metadata.dedupe_key` (например, `lead_no_first_contact_24h`).
- Повторное событие с теми же ключами не создаёт новую Activity, если предыдущая ещё `planned` / `in_progress` / `overdue`.

---

## 4. Lifecycle: переходы статусов

См. canon §2.3 для разрешённых переходов. Расширенная семантика:

```
planned ──[user starts work]──> in_progress ──[mark done]──> done
   │                                │                          ▲
   │                                │                          │
   │                                └──[mark done]─────────────┘
   │
   ├──[due_at < now]──> overdue ──[mark done]──> done
   │                       │
   │                       └──[cancel]──> cancelled
   │
   ├──[snooze]──> planned (с обновлённым due_at)
   │
   └──[cancel / lifecycle hook]──> cancelled
```

### 4.1 Snooze

`POST /activities/{id}/snooze`:

```json
{ "minutes": 30 }    // или
{ "new_due_at": "2026-05-10T15:00:00Z" }
```

Эффект:
- `due_at` сдвигается на `minutes` или становится равным `new_due_at`.
- `reminder_at` сдвигается на ту же дельту.
- `snoozed_until` обновляется.
- Соответствующие unread `notifications` (`type='activity_due_soon'/'activity_overdue'`) помечаются `is_read=true` (canon §3.4.3).

### 4.2 Reschedule

`PATCH /activities/{id}` с новым `starts_at` / `due_at`. То же закрытие `notifications`. Diagnostic stash `metadata._rescheduled = {old_due_at, new_due_at, by_user_id, at}`.

### 4.3 Reassign

`PATCH /activities/{id}` с новым `assigned_to_user_id`. Эффекты:

- Старому assignee — никаких уведомлений (он больше не отвечает).
- Новому — `Notification { type='activity_assigned' }`.
- Аудит — через `activity_events` (новая ревизия `activity_event.py`, аналог `reminder_events`).
- SLA пересчитывается, **только если** `metadata.sla_recompute_on_reassign = true` (по умолчанию SLA — снимок политики при создании, не пересчитывается).

### 4.4 Recurring activities

`recurrence_json` хранится на родительской Activity. После `done` cron-job создаёт следующую occurrence как **отдельный** `Activity` row, связанный через `metadata.parent_activity_id`. Нет «обновления родителя на месте» — нужен audit-trail каждого выполнения.

---

## 5. Lifecycle hooks (массовое закрытие при изменении домена)

Канонический сервис `services/activity_lifecycle.py` (Phase 2). Реализует G-1 / G-2 из `operations-loop.md`:

| Trigger | Side effect |
|---|---|
| `candidate.stage_changed → terminal` (`probation_ok`, `rejected`, `declined`, `employed`, `hired`, `ready_for_hr`, `archived`, `withdrew`, `cancelled`, `hired_elsewhere`) | `UPDATE activities SET status='cancelled', cancelled_at=now() WHERE related_entity_type='candidate' AND related_entity_id=cand.id AND status IN (planned, in_progress, overdue)`; mark unread notifications read |
| `candidate.deleted` (`deleted_at IS NOT NULL`) | то же |
| `lead.terminal` | то же для `related_entity_type='lead'` |
| `document.deleted` / `document.cancelled` / `document.not_required` | то же для `related_entity_type IN ('document', 'document_step')`; для step-ов matched по `related_entity_id LIKE '{document_id}:%'` |
| `thread.archived` / `thread.deleted` | то же для `related_entity_type='communication_thread'` |
| `vacancy.is_archived` / `vacancy.status='closed'` | то же для `related_entity_type='vacancy'` |

Hooks вызываются из **owner-команды** домена (см. [`../architecture/operational-event-boundaries.md`](../architecture/operational-event-boundaries.md) — cross-domain mutation требует canonical command). Consumer не имеет права закрыть чужие activities.

---

## 6. ACL и видимость

| Роль | Видит / может |
|---|---|
| `recruiter` | свои Activity (`assigned_to_user_id = self`) + Activity по своим кандидатам / лидам / вакансиям |
| `supervisor` | Activity своей команды (`assigned_to_user_id IN team`) |
| `administrator` | все Activity tenant-а |
| `client_manager` / `client_processor` | Activity по handed-off кандидатам, треды клиентского портала |
| `viewer` | read-only ленту, без mark-done |

Реализация — RLS по `tenant_id` + scope-фильтры в `services/activity_tasks.py::list_activities`.

---

## 7. Working hours integration

Реализация G-4 из `operations-loop.md` сохраняется и в новой модели:

- `services/activity_tasks.py::create_activity` опционально сдвигает `due_at` и `reminder_at` на ближайшее окно работы assignee, если `tenant.settings["activities"]["shift_due_at_outside_hours"] = true` (бывший `tenant.settings["reminders"]["shift_due_at_outside_hours"]`, переименован в Phase 1).
- Diagnostic stash в `metadata._working_hours_shift = {original_due_at, shifted_due_at, delta_seconds, reason: 'outside_assignee_working_hours'}`.
- Time-off approval → автоотмена future activities assignee на дни time-off (через `services/timeoff_cleanup.py`, target table — `activities`).

---

## 8. UI surface (см. canon §5)

| URL | Что показывает | Phase 3 файл |
|---|---|---|
| `/app/work/tasks` | Task Manager — все Activity с фильтрами My/Today/Overdue/Upcoming/SLA risk/… | `pages/ActivitiesPage.tsx` |
| `/app/work` | Work Hub — `MyActivitiesPanel` + `TodayPanel` + Risk digest + recommendations | `pages/WorkHubPage.tsx` |
| `/app/calendar` | Calendar — Activity (`starts_at` или `due_at`) + integrated mirror events | `pages/CalendarPage.tsx` |
| `/app/notifications` | Notification Center — все `notifications` с группами | `pages/NotificationsCenterPage.tsx` |
| Topbar bell | unread `notifications` (60s poll, severity grouping) | `components/nav/Topbar.tsx` |

---

## 9. Метрики

| Метрика | Источник | Drilldown |
|---|---|---|
| Total active activities (mine) | `count(*) WHERE status IN (planned, in_progress, overdue) AND assigned_to_user_id=me` | `/app/work/tasks?status=active&assignee_scope=mine` |
| Overdue (mine) | `count(*) WHERE status='overdue' AND assigned_to_user_id=me` | `/app/work/tasks?status=overdue&assignee_scope=mine` |
| SLA risk (tenant) | `count(*) WHERE sla_status IN (warning, breached)` | `/app/work/tasks?sla_status=warning,breached` |
| Avg time to complete (по type) | `avg(completed_at − created_at)` | — |
| Auto vs manual ratio | `count(source_module='automation') / count(*)` | — |

См. также [`../operational-metrics.md`](../operational-metrics.md) — канонический реестр; при изменении подсчёта обновлять и его.

---

## 10. Безопасность

- RLS обязателен по `tenant_id`.
- Activity **не удаляется** физически. Только `done` или `cancelled`.
- `assigned_to_user_id` — FK с `ON DELETE SET NULL`; удаление пользователя не оставляет ghost-rows.
- При удалении связанной сущности (через soft-delete) — Activity переводится в `cancelled` через lifecycle hook (§5), не удаляется.

---

## 11. AI Agent Notes

- Никогда не создавать новую таблицу типа `todos` / `planner_items` / `reminders` / `candidate_tasks`. Единственный source of truth — `activities`.
- При создании Activity всегда указывать `source_module`, `related_entity_type`, `related_entity_id`, `due_at`. Без этого — баг, не легитимная строка.
- При создании Notification всегда указывать `title`, `severity`. Если есть `activity_id` или `related_entity_*` — обязательно. Notification без действия и без сущности — мусор.
- При изменении статуса Activity — никогда не делать в БД напрямую; использовать `services/activity_tasks.py::complete_activity / snooze_activity / cancel_activity` (`update_reminder` после Phase 2 удаляется).
- При cross-domain side-effect — пройти через owner command (см. [`../architecture/operational-event-boundaries.md`](../architecture/operational-event-boundaries.md)), не писать чужой state из consumer-а.

---

## 12. История

- 2026-05-09: Phase 0 — создан как замена `reminders.md`; зафиксирован lifecycle, hooks, ACL, working-hours контракт.
