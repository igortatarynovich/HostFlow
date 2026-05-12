# Activities — SLA & Escalation Matrix

**Status:** canon. Заменяет `workflows/reminders_matrix.md`.

**Связанные документы:**

- [`../architecture/ADR-012-activity-notification-operating-layer.md`](../architecture/ADR-012-activity-notification-operating-layer.md)
- [`../architecture/activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md) §2 (поля), §3 (Notification), §6 (automation)
- [`activities.md`](activities.md) — lifecycle Activity
- [`../operational-metrics.md`](../operational-metrics.md) — реестр счётчиков SLA-метрик
- [`../operations-loop.md`](../operations-loop.md) — G-4 (working hours), G-3 (drilldown)

---

## 1. Цель

Зафиксировать:

1. **Какие типы Activity / событий имеют SLA** и какие именно (T-минусы и T-плюсы).
2. **Какие каналы доставки** активируются на каждой стадии эскалации.
3. **Какие Notification создаются** (`type`, `severity`, получатель).
4. **Дедупликацию**, тишина в неработающие часы и обработку отмен.

Все числа в этом документе — defaults; tenant может override через `tenant.settings["activities"]["sla"]`.

---

## 2. Универсальный SLA-контракт

Для любой Activity с заполненным `sla_due_at`:

| Момент | Notification | Activity-эффект |
|---|---|---|
| `sla_due_at − T−24h` | `type='sla_warning'`, `severity='warning'` | — |
| `sla_due_at − T−4h` | `type='sla_warning'`, `severity='warning'` (повтор) | — |
| `sla_due_at` (T+0) | `type='sla_breached'`, `severity='critical'` | `sla_status` = `breached`; `priority` поднимается на 1 ступень |
| `sla_due_at + T+24h` | `type='sla_breached'`, `severity='critical'` (эскалация супервизору) | `priority='urgent'` |

Дедупликация: повторное событие с тем же `(activity_id, sla_stage)` в окне 15 минут подавляется (`metadata.last_sla_alert_at`).

---

## 3. SLA-чувствительные сценарии

### 3.1 Lead first contact (Recruitment)

| Trigger | Activity | SLA |
|---|---|---|
| `lead.created` (intake from form / Meta / webhook) | `type='candidate_review'`, `source_module='leads'`, `priority='high'` | `sla_due_at = created_at + 15min` |
| Эскалация T−5min | `Notification` recruiter `severity='warning'` |
| T+0 | `Notification` recruiter + supervisor `severity='critical'` |
| T+30min | `Notification` administrator |

### 3.2 Lead stuck stage

| Trigger | Activity | SLA |
|---|---|---|
| `lead.stage` без изменения > `stuckAfterDays` (default 7d) | `type='follow_up'`, `source_module='leads'` | `sla_due_at = stuck_threshold + 24h` |
| T−24h | `Notification` recruiter |
| T+0 | `Notification` supervisor |
| T+24h | `Notification` administrator |

### 3.3 Candidate follow-up (Ожидаем документы)

| Trigger | Activity | SLA |
|---|---|---|
| `candidate.stage_changed → Ожидаем документы` | `type='document_request'`, `source_module='candidates'` | `sla_due_at = created_at + 24h` |
| T−4h | `Notification` recruiter |
| T+0 | `Notification` recruiter + supervisor |

### 3.4 Document expiry

| Trigger | Activity | SLA |
|---|---|---|
| `document.expire_date − 14d` | `type='document_check'`, `source_module='documents'` | `due_at = expire_date − 14d` (без `sla_due_at` — дедлайн = `due_at`) |
| `document.expire_date − 7d` | `Notification` `type='document_expiring'`, `severity='warning'` | — |
| `document.expire_date − 1d` | `Notification` `type='document_expiring'`, `severity='warning'` (повтор) | — |
| `document.expire_date` (T+0) | `Notification` `type='document_expired'`, `severity='critical'` (owner + supervisor) | `Activity.priority='urgent'` |
| T+24h | `Notification` administrator | — |

См. также [`document_expiry.md`](document_expiry.md).

### 3.5 Process step due (документы workflow)

Похожи на 3.4, но `related_entity_type='document_step'`, `related_entity_id='{doc_id}:{step_code}'`.

### 3.6 Communication thread SLA

| Trigger | Activity | SLA |
|---|---|---|
| `message.received` (channel-specific SLA, default 60-180min) | `type='message'`, `source_module='comms'`, `related_entity_type='communication_thread'` | `sla_due_at = received_at + channel_sla` |
| T−15min | `Notification` recruiter (assignee) |
| T+0 | `Activity.sla_status='breached'`; `Notification` recruiter + supervisor |
| T+24h | `Notification` administrator |

`thread.sla_due_at` остаётся **источником истины** для треда; `Activity.sla_due_at` — снимок политики на момент создания (нужен для отображения в Task Manager).

### 3.7 Vacancy activation

| Trigger | Activity | SLA |
|---|---|---|
| `vacancy.status='open'` 30d без переходов | `type='vacancy_action'`, `source_module='leads'` (vacancy lifecycle живёт в Recruitment) | `sla_due_at = created_at + 7d` |
| T−1d | `Notification` recruiter |
| T+0 | `Notification` administrator |

### 3.8 Manual reminder / Custom

`type='custom'` или `task` без явного SLA — `sla_due_at` не заполняется, эскалаций нет; работает только `reminder_at` для personal nudge.

---

## 4. Каналы доставки

| Канал | Описание | Активируется при |
|---|---|---|
| **In-app (bell)** | Запись в `notifications` с `channel='in_app'`; bell в Topbar | Все случаи (default) |
| **Email** | Отдельная очередь `email_dispatch`; `notifications.channel='email'` хранит UI-факт | T−24h, T+0, T+24h в эскалации; user-preference через `notification_preferences` |
| **Webhook** | Out-of-band JSON POST с `event_id` | На критических событиях для tenants с `webhook_url` |
| **Telegram** | Через `services/candidate_telegram_notifications.py` | Только для кандидата (а не сотрудников tenant-а) |
| **Slack** | Через интеграцию | T+0 для process step due |

Все исходящие каналы — это **delivery layer**, не подменяет `Notification` в БД. Outbound webhooks (`services/notifications.py`) могут отправляться **без** записи в `notifications` (только delivery), если получатель — внешняя система.

---

## 5. Working hours respect

| Канал | Работает ночью |
|---|---|
| In-app bell | Да (показывается, не мигает) |
| Email — escalation | Да (queue не задерживается) |
| Push / Telegram / WhatsApp | **Нет**: задерживается до next working window assignee (через `services/working_hours_window.py::next_working_window_after`) |
| `Activity.due_at` shift | Опционально (per-tenant `tenant.settings.activities.shift_due_at_outside_hours`); сдвигает `due_at` и `reminder_at` |
| Outbound dispatch (`dispatch_queued_messages`) | Опционально (per-tenant `tenant.settings.communications.defer_outside_working_hours`) |

См. G-4 в `../operations-loop.md` для деталей реализации.

---

## 6. Дедупликация и отмена

### 6.1 Дедупликация Notification

В окне `dedupe_window_minutes` (default 15) повторный `Notification` с тем же `(user_id, type, activity_id)` или тем же `payload.dedupe_key` подавляется.

### 6.2 Отмена эскалации

| Событие | Эффект |
|---|---|
| `Activity.status → done` | Все pending escalations отменяются; unread `notifications` помечаются read |
| `Activity.status → cancelled` | То же |
| `Activity.snooze` | `due_at` сдвигается; будущие escalation-таймеры пересчитываются от нового `due_at` |
| Lifecycle hook (candidate terminal, document deleted, etc.) | Activity переводится в `cancelled`, escalations отменяются (см. [`activities.md`](activities.md) §5) |

### 6.3 Throttling

Per-user throttling: не более **N** notifications в час одного `type` (default 10). Превышение — батчится в одну строку «Y more notifications of type X». Контролируется в `services/notifications_inapp.py::create_notification`.

---

## 7. Получатели по RBAC

| Роль | Получает |
|---|---|
| `recruiter` (owner / assignee) | T−24h, T−4h, T+0, T+24h |
| `supervisor` (куратор команды owner-а) | T+0 (для критичных типов), T+24h |
| `administrator` (tenant admin) | T+24h, T+72h |
| Custom escalation rule | По `automation_rules` |

`Owner` Activity = `assigned_to_user_id` (FK на `users`, см. canon §2.1). Если `assigned_to_user_id IS NULL` — получатели из «requires distribution» Notification: все members с ролью recruiter в company-scope.

---

## 8. Шаблоны Notification

Хранятся в `services/notification_templates.py`. Шаблоны локализованы (en источник, ru/pl переводы). Обязательные placeholders:

```
{{user_name}}, {{entity_name}}, {{due_at}}, {{activity_title}},
{{related_entity_link}}, {{activity_link}}, {{severity}}
```

Webhook payload:

```json
{
  "event_id": "uuid",
  "type": "activity.sla_breached",
  "tenant_id": "uuid",
  "activity": {
    "id": "uuid",
    "type": "candidate_review",
    "title": "...",
    "due_at": "2026-05-10T12:00:00Z",
    "sla_due_at": "2026-05-10T11:45:00Z",
    "sla_status": "breached",
    "related_entity": {"type": "lead", "id": "uuid"}
  },
  "user_id": "uuid",
  "locale": "en"
}
```

---

## 9. Acceptance

SLA-движок считается «работающим», если:

1. Для каждого SLA-чувствительного типа в §3 цепочка T−*, T+0, T+24h автоматически генерирует ровно те `Notification`, которые описаны.
2. Завершение Activity (`done` / `cancelled` / lifecycle hook) отменяет все pending escalations за ≤ 1 секунду — никаких «ghost notifications» после mark done.
3. Working hours respected на push-каналах: ночью у assignee — отложено до открытия окна.
4. Дедупликация: повторный SLA-warning в 15-минутном окне в `notifications` не появляется.
5. Bell visual count = панель count (G-9 inv-3 из operations-loop).

---

## 10. История

- 2026-05-09: Phase 0 — создан как замена `reminders_matrix.md`; универсальный SLA-контракт §2; типизированные сценарии §3; working hours respect §5; throttling и дедуп §6.
