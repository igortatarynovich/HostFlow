# Activity & Notification Operating Layer (canon)

**Status:** canon. Источник истины для всех модулей HostFlow по теме «что нужно сделать», «когда», «кому», «почему» и «как пользователь об этом узнаёт». Решение и rationale — [`ADR-012`](ADR-012-activity-notification-operating-layer.md). Этот документ фиксирует **поля, инварианты и маппинг текущего кода** на целевую модель; он живёт вместе с кодом и обновляется при каждом изменении логики Activity или Notification.

**Не путать с:**

- [`modules/scheduler.md`](../modules/scheduler.md) — booking услуг (медосмотры, психотесты, обучение); другой домен.
- [`workflows/communications-workspace-research.md`](../workflows/communications-workspace-research.md) — communications/inbox; они **публикуют** Activity / Notification, но не владеют этим слоем.
- Compliance-логи (`final_no_contact_notifications`, `rodo_notifications`) и исходящие webhooks — отдельный delivery-слой, в этот канон не входят.

**Связанные документы:**

- [`operational-event-boundaries.md`](operational-event-boundaries.md) — events / consumers / side-effects / command-flow ownership.
- [`platform-architecture-principles.md`](platform-architecture-principles.md) §6 — shared capability «Activity & Notification Operating Layer».
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0 — карта Core / Platform.
- [`../operations-loop.md`](../operations-loop.md) — as-built карта подсистем и G-1…G-10 (закрываемые этим каноном).
- [`../manager-assignment.md`](../manager-assignment.md) — owner-поля; `assigned_to_user_id` — каноник для Activity.
- [`../workflows/activities.md`](../workflows/activities.md) — workflow-спека (создание, lifecycle, lifecycle-hooks).
- [`../workflows/activities-sla-matrix.md`](../workflows/activities-sla-matrix.md) — SLA / эскалации.

---

## 1. Главный принцип

`Task` / `Reminder` / `Todo` / `Planned action` / `Follow-up` / `Calendar item` — это **разные формы одной сущности**:

```
Activity
```

`Notification` — это **не** задача. Это сообщение о событии, риске или требуемом внимании.

| Концепт | Что это | Где живёт |
|---|---|---|
| **Activity** | Работа, которую нужно выполнить | `activities` table |
| **Notification** | Сообщение о том, что произошло или требует внимания | `notifications` table |
| **Reminder** | Временной триггер, напоминающий об Activity или событии | поведение `Activity.reminder_at` + порождённый `Notification` |
| **Todo** | Простая Activity без сложного контекста | `Activity` с `type='task'`, `related_entity_type='custom'` |
| **Task Manager** | Интерфейс управления Activity | view над `activities` |
| **Planner / Today** | Представление Activity во времени | view над `activities` (`due_at` / `starts_at`) |
| **Calendar** | Календарный вид Activity + integrated mirror | view над `activities` ⊕ `calendar_items` |

**Правило (UX-инвариант):** каждый элемент UI этого слоя должен отвечать на 5 вопросов:

1. Что произошло?
2. Что мне нужно сделать?
3. До какого срока?
4. К кому или чему это относится?
5. Что будет, если я это проигнорирую?

Если элемент не отвечает на эти вопросы — это баг, не легитимная строка.

---

## 2. Activity — модель

### 2.1 Поля

```
activities
  -- identity
  id                       uuid PK
  tenant_id                uuid NOT NULL, indexed
  company_id               uuid nullable, indexed
                           -- nullable, потому что system-tasks (например automation-rule warmup)
                           -- могут не иметь company-scope; но для всего operational stream
                           -- backfill пишет company через related_entity

  -- categorisation
  type                     activity_type NOT NULL  -- закрытый enum, см. §2.2
  status                   activity_status NOT NULL DEFAULT 'planned'  -- см. §2.3
  priority                 activity_priority NOT NULL DEFAULT 'normal'  -- см. §2.4

  -- description
  title                    varchar(256) NOT NULL
  description              text nullable

  -- ownership
  assigned_to_user_id      uuid nullable, FK users.id ON DELETE SET NULL, indexed
  created_by_user_id       uuid nullable, FK users.id ON DELETE SET NULL

  -- domain link
  related_entity_type      varchar(64) NOT NULL   -- см. §2.5
  related_entity_id        varchar(120) NOT NULL  -- '0' / 'custom' для type='custom'
  source_module            varchar(32) NOT NULL   -- см. §2.6

  -- time
  starts_at                timestamptz nullable   -- для timed events (meeting, call, shift)
  due_at                   timestamptz NOT NULL
  reminder_at              timestamptz nullable   -- триггер для NOTIFICATION
  duration_minutes         int nullable
  snoozed_until            timestamptz nullable
  completed_at             timestamptz nullable
  cancelled_at             timestamptz nullable

  -- SLA
  sla_due_at               timestamptz nullable
  sla_status               activity_sla_status nullable  -- ok|warning|breached

  -- automation
  recurrence_json          jsonb nullable
  metadata                 jsonb nullable

  -- delivery channel hint (для cross-channel дублей; не путать с notification.channel)
  channel                  varchar(32) nullable DEFAULT 'internal'

  created_at               timestamptz NOT NULL
  updated_at               timestamptz NOT NULL

INDEX ix_activities_tenant_due (tenant_id, due_at)
INDEX ix_activities_entity (tenant_id, related_entity_type, related_entity_id)
INDEX ix_activities_assignee_due (tenant_id, assigned_to_user_id, due_at)
INDEX ix_activities_assignee_remind (tenant_id, assigned_to_user_id, reminder_at)
INDEX ix_activities_status_due (tenant_id, status, due_at)
INDEX ix_activities_sla (tenant_id, sla_status, sla_due_at)  -- новый
```

### 2.2 `type` (закрытый enum)

| Значение | Назначение |
|---|---|
| `call` | Звонок (Activity с `starts_at`) |
| `message` | Сообщение в тред / мессенджер |
| `email` | Email-исходящее |
| `meeting` | Встреча (Activity с `starts_at` + `duration_minutes`) |
| `task` | Простая работа без специальной семантики |
| `follow_up` | Повторное обращение через интервал |
| `document_request` | Запросить документ у кандидата / клиента |
| `document_check` | Проверить документ (compliance) |
| `candidate_review` | Просмотреть нового кандидата / лида |
| `client_follow_up` | Поработать с клиентом-компанией |
| `vacancy_action` | Действие по вакансии |
| `work_permit_action` | Действие по разрешению на работу |
| `arrival_action` | Подтвердить приезд кандидата |
| `custom` | Пользовательская задача (`related_entity_type='custom'`, `related_entity_id='0'`) |

Расширение enum — только через PR с обновлением этого файла.

### 2.3 `status`

| Значение | Смысл | Допустимые переходы |
|---|---|---|
| `planned` | Создана, но не начата | → `in_progress`, `done`, `cancelled`, `overdue` |
| `in_progress` | Пользователь работает | → `done`, `cancelled`, `overdue` |
| `done` | Завершена | (terminal) |
| `cancelled` | Отменена / больше не нужна | (terminal) |
| `overdue` | `due_at < now AND status NOT IN (done, cancelled)` — пересчитывается фоновым job-ом | → `done`, `cancelled` |

### 2.4 `priority`

`low | normal | high | urgent`. Default — `normal`. Поднимается:

- автоматически при превышении `sla_due_at` (`normal → high`, `high → urgent`);
- вручную через PATCH;
- по правилу автоматизации.

### 2.5 `related_entity_type` (закрытый enum)

| Значение | Owner-домен |
|---|---|
| `candidate` | Recruitment |
| `lead` | Recruitment |
| `client` / `company` | Companies |
| `vacancy` | Recruitment |
| `document` | Document Hub |
| `document_step` | Document Hub (workflow-шаг) |
| `order` | Services |
| `service` | Services |
| `invoice` | Finance |
| `communication_thread` | Communications |
| `workforce_employee` | HR |
| `workforce_onboarding_task` | HR (см. ADR-012 §D7) |
| `custom` | — |

### 2.6 `source_module`

| Значение | Кто создаёт |
|---|---|
| `leads` | lead lifecycle / lead distribution |
| `candidates` | candidate lifecycle / handoff |
| `documents` | Document Hub (expiry, workflow) |
| `comms` | communications scheduler / SLA |
| `workforce` | HR onboarding / lifecycle (D7) |
| `automation` | `automation_rules` engine |
| `user` | ручное создание оператором |

### 2.7 Инварианты

1. **Каждое Activity имеет владельца действия.** `assigned_to_user_id IS NULL` допустимо **только** в состоянии «требует распределения» (lead-distribution в процессе); в этом случае `priority='high'` И обязателен `Notification` с `type='activity_assigned'` целевой группе менеджеров. Длительное состояние unassigned считается багом.
2. **Каждое Activity имеет домен.** `related_entity_type IS NOT NULL`. `custom` допустим только для `type='custom'`.
3. **Каждое Activity имеет источник.** `source_module IS NOT NULL` — иначе автоматизации и метрики теряют атрибуцию.
4. **Activity завершается явно.** Удаления нет. Только `done` или `cancelled` (и поля `completed_at` / `cancelled_at`).
5. **`due_at` обязателен.** Если для concept-а нет дедлайна — это либо `meeting` с `starts_at` (тогда `due_at = starts_at + duration_minutes`), либо `Notification`, не Activity.
6. **`starts_at` ≤ `due_at`** при наличии обоих.
7. **`reminder_at` ≤ `due_at`** если задан.
8. **SLA-инвариант:** `sla_due_at` (если задан) обновляется только при создании Activity или при changes в её владельце/типе. SLA — снимок политики на момент назначения; пересчёт допустим только при reassignment.

### 2.8 Activity vs Calendar item

`Activity` — источник истины для **всего**, что создал пользователь HostFlow.
`CalendarItem` — mirror внешнего provider-а (Google / Outlook / Slack / Teams):

- Импортированное событие → новая `CalendarItem` без соответствующего Activity (если оператор не «втянул» его в HostFlow).
- HostFlow-Activity, синхронизированная наружу → `CalendarItem` создаётся как mirror; `calendar_item_links` хранит provider-id.
- Отмена Activity → cancel в provider через mirror-link; удаление CalendarItem не удаляет Activity.

UI календарь рендерит **объединение** activities (HostFlow) + calendar_items без HostFlow-Activity (внешние).

---

## 3. Notification — модель

### 3.1 Поля

```
notifications
  id                    uuid PK
  tenant_id             uuid NOT NULL, indexed
  user_id               uuid NOT NULL, indexed

  type                  notification_type NOT NULL  -- см. §3.2
  title                 varchar(256) NOT NULL
  body                  text nullable
  severity              notification_severity NOT NULL  -- info|warning|critical

  related_entity_type   varchar(64) nullable
  related_entity_id     varchar(120) nullable
  activity_id           uuid nullable, FK activities.id ON DELETE SET NULL, indexed

  channel               varchar(16) NOT NULL DEFAULT 'in_app'
  priority              varchar(16) nullable
  payload               jsonb nullable
  is_read               bool NOT NULL DEFAULT false
  delivered_at          timestamptz nullable
  read_at               timestamptz nullable

  created_at            timestamptz NOT NULL
  updated_at            timestamptz NOT NULL

INDEX ix_notifications_tenant_user_read (tenant_id, user_id, is_read)
INDEX ix_notifications_activity (activity_id)
INDEX ix_notifications_entity (tenant_id, related_entity_type, related_entity_id)
```

### 3.2 `type` (закрытый enum)

| Значение | Когда |
|---|---|
| `activity_assigned` | На пользователя назначена Activity |
| `activity_due_soon` | До `due_at` осталось `reminder_at` минут |
| `activity_overdue` | `due_at < now`, Activity ещё не закрыта |
| `document_expiring` | Документ истекает (Document Hub) |
| `document_expired` | Документ истёк |
| `candidate_status_changed` | Кандидат сменил стадию |
| `lead_received` | Пришёл новый лид |
| `message_received` | Новое сообщение в треде, требующее внимания |
| `sla_warning` | `sla_due_at` приближается (Activity или Thread) |
| `sla_breached` | `sla_due_at` пропущен |
| `system` | Системное сообщение (платёж, аккаунт, миграция) |

### 3.3 `severity`

| Значение | Семантика | Bell visual |
|---|---|---|
| `info` | Информация | стандартный цвет |
| `warning` | Требует внимания, не критично | amber pill |
| `critical` | Срочное / SLA breach / документ истёк | rose pill, всегда unread даже после открытия панели до явного `mark_read` |

### 3.4 Инварианты

1. **Notification без Activity или сущности — баг.** Должно быть заполнено **минимум одно** из: `activity_id`, (`related_entity_type`, `related_entity_id`).
2. **Notification не подменяет Activity.** Если требуется действие — паблишится **и** Activity, **и** Notification со ссылкой `activity_id`.
3. **Закрытие Activity → автоматический `mark_read` соответствующих Notification.** Снимок текущего поведения G-9 переходит сюда как контракт: при `complete` / `snooze` / `cancel` Activity все unread `notifications` с её `activity_id` становятся `is_read=true` с `payload.auto_closed = {reason, at}`.
4. **Дедупликация:** в окне `dedupe_window_minutes` (default 15) повторный `Notification` с тем же `(user_id, type, activity_id)` либо тем же `payload.dedupe_key` подавляется.
5. **Bell visual count = панель count.** На колокольчике никогда не должно отображаться число, отличающееся от количества видимых строк в раскрытой панели (G-9 inv-3).

### 3.5 Что НЕ Notification

- Audit-логи (`audit_events`) — не Notification.
- Compliance-сообщения, ушедшие наружу (`final_no_contact_notifications`, `rodo_notifications`) — отдельный delivery audit, не bell.
- Webhook-исходящие (`services/notifications.py`) — outbound delivery, может быть **stat-but-not-row** в `notifications` (delivery-only).
- Email-доставка — отдельная queue (`email_dispatch`); `notifications.channel='email'` хранится только если соответствующий Notification был создан как UI-row.

---

## 4. Reminder — поведение

`Reminder` как сущность БД **отсутствует**. Концепт «напомни мне за 30 минут до встречи» реализован двумя полями + одним порождением:

```
Activity.due_at = 2026-05-10 12:00
Activity.reminder_at = 2026-05-10 11:30   -- триггер

Background job at 2026-05-10 11:30:
  CREATE Notification (
    type        = 'activity_due_soon',
    severity    = 'info' | 'warning' (от priority Activity),
    title       = activity.title,
    body        = "Through 30 minutes",
    activity_id = activity.id,
    user_id     = activity.assigned_to_user_id
  )
  UPDATE activities SET sent_at = now() WHERE id = ...   -- защита от повтора
```

Если `activity_due_soon` Notification ещё unread, но Activity уже сменилась — старый Notification помечается `is_read` через invariant 3.4-3.

**Рекуррентность:** `recurrence_json` (RFC 5545 RRULE-like) хранится на Activity; cron raises `next_occurrence` после `done` — каждый occurrence — отдельный `Activity` (linked через `metadata.parent_activity_id`).

---

## 5. Views — что показывает UI

| View | Frontend файл (целевой Phase 3) | URL | Источник |
|---|---|---|---|
| **Task Manager** | `pages/ActivitiesPage.tsx` (rename из `RemindersPage.tsx`) | `/app/work/tasks` | `GET /activities` |
| **Today / Planner panel** | `modules/workHub/MyActivitiesPanel.tsx`, `modules/workHub/TodayPanel.tsx` | `/app/work` секции | `GET /activities` с фильтром по дате |
| **Calendar** | `pages/CalendarPage.tsx` (rename из `CommunicationsCalendarPage.tsx`) | `/app/calendar` | `GET /activities` ⊕ `GET /calendar/items` |
| **Notification Center** | `pages/NotificationsCenterPage.tsx` (новый) | `/app/notifications` | `GET /notifications` |
| **Bell drawer** | `components/nav/Topbar.tsx` | overlay | `GET /notifications` (60s poll, severity-grouped) |

### 5.1 Task Manager — фильтры (Phase 3)

| Фильтр | Реализация |
|---|---|
| **My tasks** | `assignee_scope=mine` |
| **Today** | `due_to=<end-of-day-local>` |
| **Overdue** | `status=overdue` |
| **Upcoming** | `due_from=now` |
| **High priority** | `priority IN (high, urgent)` |
| **SLA risk** | `sla_status IN (warning, breached)` |
| **Unassigned** | `assigned_to_user_id IS NULL` |
| **Completed** | `status=done` |
| **Cancelled** | `status=cancelled` |

### 5.2 Колонки

`Status, Priority, Title, Related entity (with link), Assigned user, Due date, SLA status, Source module, Created date`.

### 5.3 Действия

`mark as done, reschedule, reassign, cancel, open related entity, add note, create follow-up`.

### 5.4 Notification Center — группы

`Urgent (severity=critical, unread), Tasks (type IN activity_*), Messages (type=message_received), Documents (type IN document_*), System (type=system)`.

---

## 6. Automation: Event → Rule → Activity / Notification

Слой автоматизации (`backend/app/services/automation_rules.py`) после Phase 2 переименовывает actions:

```
actions.create_activity(payload)   -- было create_reminder
actions.create_notification(payload)
```

| Event | Default rule | Side effect |
|---|---|---|
| `lead.created` | recruiter assigned via `recruiter_assignment` | `Activity { type='candidate_review', source_module='leads', priority='high', sla_due_at=now+15min }` + `Notification` с `type='activity_assigned'` |
| `candidate.stage_changed` → `Ожидаем документы` | document checklist evaluator | `Activity { type='document_request', source_module='candidates' }` |
| `candidate.stage_changed` → `Документы получены` | document hub validator | `Activity { type='document_check', source_module='candidates' }` |
| `candidate.stage_changed` → `Планируем приезд` | arrival flow | `Activity { type='arrival_action' }` |
| `document.expiring (T-14d)` | document expiry rule | `Activity { type='document_check' }` + `Notification { type='document_expiring', severity='warning' }` |
| `document.expired` | document expiry rule | `Notification { type='document_expired', severity='critical' }` (Activity создаётся уже была на T-14) |
| `message.received` | comms inbox | `Notification { type='message_received' }`; если требуется ответ — `Activity { type='message', sla_due_at=channel_sla }` |
| `vacancy.created` | sourcing rule | `Activity { type='vacancy_action', title='Start sourcing candidates' }` |
| `client.inactive (N days)` | client lifecycle | `Activity { type='client_follow_up' }` |
| `thread.sla_due` | comms scheduler | `Activity { type='message', priority='urgent', sla_status='warning' }` + `Notification { type='sla_warning' }` |
| `thread.sla_breached` | comms scheduler | `Notification { type='sla_breached', severity='critical' }` (на ранее созданной Activity повышается priority) |

### 6.1 Confidence бар для NBA

| Confidence | Поведение |
|---|---|
| **High (≥ 0.9)** | Activity создаётся **автоматически**; `next-actions` отдаёт `activity_id` |
| **Medium (0.5–0.9)** | NBA отдаёт `recommended_activity_payload`; пользователь нажимает «Accept» → `POST /activities` |
| **Low (< 0.5)** | NBA скрывает рекомендацию |

`confidence` хранится в `automation_rules.metadata` или вычисляется на лету в `_nba.py`.

---

## 7. Маппинг: текущий код → канон

### 7.1 Backend модели

| Сегодня | Phase 1 | Действие |
|---|---|---|
| `models/reminder.py::Reminder` | `models/activity.py::Activity` | rename + add `company_id`, `starts_at`, `sla_due_at`, `sla_status`; rename `assignee_id → assigned_to_user_id`, `created_by → created_by_user_id`, `entity_type → related_entity_type`, `entity_id → related_entity_id`, `source → source_module`, `remind_at → reminder_at`, `payload → metadata` |
| `models/reminder_event.py::ReminderEvent` | `models/activity_event.py::ActivityEvent` | rename |
| `models/user_notification.py::UserNotification` | `models/notification.py::Notification` | rename + add `title`, `body`, `severity`, `activity_id`; rename `event_type → type` |
| `models/candidate_children.py::CandidateTask` | **поглощено Phase 2.1 (2026-05-09)** | Backfill `alembic 202607150004_pti` спроецировал строки в `activities` с `metadata.legacy_source='candidate_tasks'`; backend HTTP-роуты `/api/v1/candidates/{id}/tasks` удалены; ORM-класс остаётся в коде до Phase 3 cleanup, физический `DROP TABLE` — за soft-gate `HOSTFLOW_PHASE_2_1_DROP_OK=1` (`alembic 202607150005_dptt`). |
| `models/communication.py::CommunicationPlannerEvent` | **поглощено Phase 2.1 (2026-05-09)** | Backfill `alembic 202607150004_pti` (kind=task/followup → type=task/follow_up; kind=meeting/call/shift → type=meeting/call/task с `starts_at`; `metadata.legacy_source='communication_planner_events'` + `metadata.planner.kind` сохраняет оригинальный `kind` для load-bucketing). Backend HTTP-роуты `/api/v1/communications/planner/events*` удалены; FE shim в `hostflow-frontend/src/api/communications.ts` дёргает `/api/v1/activities` с remap'ом полей. ORM-класс и `ensure_communications_schema.py` остаются до Phase 3 cleanup; физический `DROP TABLE` — за soft-gate `HOSTFLOW_PHASE_2_1_DROP_OK=1` (`alembic 202607150005_dptt`). |
| `models/calendar_integration.py::CalendarItem` | без изменений (mirror) | роль уточнена в §2.8 |
| `models/calendar_integration.py::CalendarConnection / Channel / SyncCursor / SyncJob` | без изменений | connector layer |

### 7.2 Backend API

| Сегодня | Phase 2 | Действие |
|---|---|---|
| `/api/v1/reminders` (`reminders_v2.py`) | удалить | контракт переходит на `/api/v1/activities` |
| `/api/v1/activities` (`activities_v1.py`) | расширить | становится единственным CRUD; добавить `GET /activities/{id}/notifications`, фильтры из §5.1 |
| `/api/v1/notifications` | расширить | новые поля `title/body/severity/activity_id` в response |
| `/api/v1/communications/planner/events` | **удалено Phase 2.1 (2026-05-09)** | HTTP-роуты сняты; FE shim в `hostflow-frontend/src/api/communications.ts` (`*PlannerEvent*` функции) транслирует legacy вызовы в `/api/v1/activities` с remap'ом полей до Phase 3. |
| `/api/v1/candidates/{id}/tasks` | **удалено Phase 2.1 (2026-05-09)** | HTTP-роуты сняты; единственный CRUD задач — `/api/v1/activities`. |
| `/api/v1/calendar/items` | сохранить | роль mirror'а (§2.8) |
| `/api/v1/next-actions` | переписать | recommendation layer (§D5 ADR-012); DTO добавляет `activity_id?` и `recommended_activity_payload?` |
| `/api/v1/reminders` (старый `reminders.py`, не подключён) | удалить | мёртвый код |

### 7.3 Backend services

| Сегодня | Phase 1/2 | Действие |
|---|---|---|
| `services/reminder_tasks.py` | `services/activity_tasks.py` | rename + adapt |
| `services/user_notifications.py` | `services/notifications_inapp.py` | rename |
| `services/reminders.py` (legacy doc-expiry) | поглотить в `services/activity_tasks.py` или Document Hub | depending on what домен реально owner-ит |
| `services/draft_reminders.py` | удалить | legacy admin endpoint |
| `services/reminder_ops_counts.py` | `services/activity_ops_counts.py` | rename |
| `services/automation_rules.py` (`actions.create_reminder`) | `actions.create_activity` | rename action |
| `services/next_action.py` | сохранить + дополнить | recommendation layer |
| `services/communications_scheduler.py` | подправить импорты | сейчас создаёт reminders → создаёт activities |
| `services/candidate_lifecycle.py`, `lead_lifecycle.py`, `handoff.py`, `events.py`, `imports/leads.py`, `uos_auto_activities.py`, `communications/_helpers/sla.py` | подправить импорты | один rename-сweep |
| `services/notifications.py` (исходящие webhooks) | без изменений | другой делivery-слой |
| `services/activity.py` | переименовать или поглотить | сегодня это **public audit** (`log_public_event`) — имя вводит в заблуждение, в Phase 1 переезжает в `services/audit.py` или становится `services/public_event_log.py` |

### 7.4 Frontend

| Сегодня | Phase 3 | Действие |
|---|---|---|
| `pages/RemindersPage.tsx` | `pages/ActivitiesPage.tsx` | rename + смена API |
| `pages/ActivitiesPage.tsx` (старая, мёртвая) | удалить | не подключена к роуту |
| `pages/CommunicationsPlannerPage.tsx` | удалить | мёртвый код, lazy-import сломан |
| `pages/CommunicationsCalendarPage.tsx` | `pages/CalendarPage.tsx` | упростить; единый источник `listActivities` + `listCalendarItems` |
| `pages/WorkOrganizerPage.tsx` | удалить | поглощено `WorkHubPage` |
| `pages/WorkHubPage.tsx` | сохранить | единственный work hub |
| `pages/NotificationsCenterPage.tsx` | создать | новый |
| `api/client.ts` `listReminders / createReminder / ...` | удалить | заменено `listActivities / ...` |
| `api/client.ts` `listActivities / ...` | оставить + дополнить | единственный API |
| `api/communications.ts` `*PlannerEvent*` | удалить | data в `activities` |
| `api/calendarIntegrations.ts` | сохранить | mirror layer |
| `api/nextActions.ts` | расширить DTO | добавить `activity_id?` / `recommended_activity_payload?` |
| `hooks/useActivities.ts` | создать | новый |
| `hooks/useNotifications.ts` | создать | новый |
| `components/nav/Topbar.tsx` | обновить | render severity / title / body |
| `i18n/{en,pl,ru}.json` | обновить | namespace переименовать `reminders.* → activity.*`; `communications.planner.* → activity.calendar.*` |

### 7.5 Alembic

Phase 1 — две ревизии:

```
202607XX0001_activity_layer_v1
  - RENAME TABLE reminders → activities
  - RENAME COLUMN: assignee_id → assigned_to_user_id, created_by → created_by_user_id,
    entity_type → related_entity_type, entity_id → related_entity_id,
    source → source_module, remind_at → reminder_at, payload → metadata
  - ADD COLUMN: company_id, starts_at, sla_due_at, sla_status
  - status mapping: 'pending'|'new'|'sent' → 'planned'; остальное по таблице §2.3
  - backfill company_id JOIN-ом по related_entity_type/_id
  - RENAME TABLE user_notifications → notifications
  - RENAME COLUMN: event_type → type
  - ADD COLUMN: title, body, severity, activity_id
  - backfill title/body/severity из payload + i18n template для известных типов

202607XX0002_activity_absorb_planner_and_candidate_tasks
  - INSERT INTO activities SELECT … FROM candidate_tasks (mapping: type='task',
    related_entity_type='candidate', source_module='candidates')
  - INSERT INTO activities SELECT … FROM communication_planner_events
    (kind=task → type=task, kind=followup → type=follow_up,
     kind=meeting → type=meeting WITH starts_at,
     kind=call → type=call WITH starts_at,
     kind=shift → type=task WITH starts_at)
  - DROP TABLE candidate_tasks
  - DROP TABLE communication_planner_events
```

Plus Phase 1 Stage 0:

```
202607XX0000_calendar_tables_explicit
  - CREATE TABLE calendar_connections / channels / items / item_links / sync_cursors / sync_jobs / integration_action_logs
    (если нет в alembic; сегодня поднимается через Base.metadata.create_all / ensure_calendar_schema)
```

---

## 8. Lifecycle hooks (закрывает G-1 / G-2 из operations-loop)

Канонический сервис `services/activity_lifecycle.py` (Phase 2) при изменении статуса связанной сущности:

| Trigger | Side effect на activities | Side effect на notifications |
|---|---|---|
| `candidate.stage_changed → terminal` | `UPDATE activities SET status='cancelled', cancelled_at=now() WHERE related_entity_type='candidate' AND related_entity_id=cand.id AND status IN (planned, in_progress, overdue)` | `UPDATE notifications SET is_read=true, read_at=now() WHERE related_entity_type='candidate' AND related_entity_id=cand.id AND is_read=false` |
| `candidate.deleted` | то же | то же |
| `lead.terminal` | то же для `related_entity_type='lead'` | то же |
| `document.deleted` | то же для `related_entity_type='document'` и `document_step` (см. §2.5) | то же |
| `thread.archived` / `thread.deleted` | то же для `related_entity_type='communication_thread'` | то же |

Lifecycle hooks вызываются из owner-команды (см. `operational-event-boundaries.md` инвариант 3 — cross-domain mutation требует canonical command), не из consumer-а напрямую.

---

## 9. UX-правило (вход в каждое окошко UI)

Каждый рендер любого элемента Activity или Notification обязан включать:

1. **Заголовок** — что произошло (`title`).
2. **Краткое объяснение** — `body` (для Notification) или `description` first-line (для Activity).
3. **Ссылку на связанную сущность** — кликабельная кнопка «Open candidate / lead / document / thread».
4. **Ссылку на Activity** — для Notification, если `activity_id IS NOT NULL`.
5. **Срок** — `due_at` для Activity, `created_at + ttl_hint` для Notification.
6. **SLA-индикатор** — если `sla_status IN (warning, breached)`.
7. **Read/unread** — для Notification.
8. **Severity** — для Notification.
9. **Кнопку primary action** — для Activity: «Mark done / Snooze / Reassign»; для Notification: «Open» (либо Activity, либо related entity).

Если рендер не включает 1-5 — это баг.

---

## 10. Документация

При любом изменении кода Activity или Notification обязательно обновлять:

- этот canon-документ (поля, инварианты),
- `workflows/activities.md` (lifecycle),
- `workflows/activities-sla-matrix.md` (SLA-числа),
- `operations-loop.md` (as-built карта),
- `glossary.md` (если меняется термин),
- `manager-assignment.md` (если меняется owner-поле),
- `operational-metrics.md` (если меняется dashboard-counter),
- `personas.md` (если меняется UX-поверхность роли).

При изменении enum-ов (`type`, `status`, `priority`, `severity`, `related_entity_type`, `source_module`) — сначала ADR-update, потом миграция, потом код.

---

## 11. Acceptance — слой работает

Слой считается «работающим», если:

1. **Один inbox.** В `/app/work/tasks` пользователь видит все свои задачи — нет «параллельных» списков (planner / candidate-tasks / activities), и галочка «mark done» закрывает строку везде синхронно.
2. **Один календарь.** В `/app/calendar` рендерятся `activities` (HostFlow) + `calendar_items` (mirror внешних). Drag-to-reschedule работает на обоих типах.
3. **Один центр уведомлений.** Bell + `/app/notifications` показывают одни и те же `notifications`. Bell visual count = панель count (G-9 inv-3).
4. **SLA в строке.** `sla_due_at`/`sla_status` — колонки таблицы, а не проекция API.
5. **Lifecycle hooks работают.** Reject кандидата → за ≤ 1с tasks/calendar/bell не показывают связанные строки (G-1).
6. **NBA — рекомендация, не задача.** В `/app/work` блок «Recommended next actions» содержит карточки с CTA «Accept → create Activity» или открывает существующую Activity.
7. **Нет мёртвого кода.** `WorkOrganizerPage`, старая `ActivitiesPage`, `CommunicationsPlannerPage` удалены. `Reminder = Activity` алиас удалён в Phase 4.

---

## 12. История

- 2026-05-09: Phase 0 — первичная фиксация canon-а; ADR-012 принят; решения Q1–Q5 зафиксированы; D1–D10 контракт; маппинг текущего кода (§7) — основа для Phase 1.
- 2026-05-09: **Phase 2.1 закрыт (engineering).** `candidate_tasks` и `communication_planner_events` поглощены `Activity`: backfill (`alembic 202607150004_pti`) применён, backend services переведены на чтение/запись `activities`, HTTP-роуты `/api/v1/candidates/{id}/tasks` и `/api/v1/communications/planner/events*` удалены, FE shim в `src/api/communications.ts` транслирует legacy вызовы. §7.1 / §7.2 mapping table обновлены. Физический `DROP TABLE` — за soft-gate `HOSTFLOW_PHASE_2_1_DROP_OK=1` (`alembic 202607150005_dptt`); ждёт canary. Подробности — [`phase-2-1-planner-tasks-into-activities.md`](phase-2-1-planner-tasks-into-activities.md). Transitional поля на `ReminderUpdateRequest` (`status`, `type`, `entity_type`, `entity_id`, `payload`) добавлены **только** для shim'а — Phase 3 удаляет их вместе со shim'ом; `payload` wholesale-replace из планерных семантик не должен закрепляться как долгосрочная модель PATCH'а Activity.
