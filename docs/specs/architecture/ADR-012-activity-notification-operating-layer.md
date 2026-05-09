# ADR-012: Activity & Notification Operating Layer

## Status

**Accepted (architectural direction).** Имплементация **поэтапная**: Phase 0 (документация — этот ADR + canon-документ + правки спек), Phase 1 (backend модели и Alembic), Phase 2 (consolidation HTTP API), Phase 3 (frontend), Phase 4 (seeds + clean-up алиасов). Этот ADR фиксирует **архитектурный контракт**, до старта Phase 1 никакой код не меняется.

## Context

В коде сегодня сосуществуют **три параллельных «task»-мира** и **четыре источника операционных «событий пользователя»**:

| Сегодняшняя сущность | Таблица / API | Что показывает | Проблема |
|---|---|---|---|
| `Reminder` | `reminders` / `/api/v1/reminders` | Tasks / SLA / follow-up | Главный inbox, но имя сужает смысл до «напомнить» |
| `Activity` (фасад) | `/api/v1/activities` | То же `reminders` под другим именем | Двойственность API без разной модели данных |
| `CandidateTask` | `candidate_tasks` / `/api/v1/candidates/{id}/tasks` | TODO по кандидату | Параллельная сущность, не используется во frontend |
| `CommunicationPlannerEvent` | `communication_planner_events` / `/api/v1/communications/planner/events` | Слоты в календаре | Пересекается с `Reminder` (kind=task/followup) |
| `CalendarItem` | `calendar_items` / `/api/v1/calendar/items` | Mirror Google/Outlook | Используется и как «source of truth» для встреч, и как зеркало |
| `UserNotification` | `user_notifications` / `/api/v1/notifications` | Bell в Topbar | Близко к цели, но без полей `title` / `body` / `severity` / `activity_id` |
| `next_actions` (NBA) | `/api/v1/next-actions` | Рекомендации по лидам | Семантически — рекомендация, но в коде сегодня живёт рядом с задачами |

UX-эффекты этой фрагментации:

- Пользователь видит в `/app/tasks` одни строки, в `/app/calendar` — другие, в bell — третьи.
- Закрытие задачи в одном месте не всегда закрывает её в другом (см. `operations-loop.md` G-9 / §6).
- Напоминания приходят без понятного «что мне сделать», а уведомления — без действия и без срока.
- Параллельные таблицы дают одни и те же данные с разной идемпотентностью и разной FK-целостностью (часть owner-полей до Phase 4 G-5 не имела FK; см. `manager-assignment.md` §1.1).

В существующих spec-файлах эта тема уже разрезана между:

- `architecture/operational-event-boundaries.md` — словарь events/consumers/side-effects (Activity и Notification как два отдельных concept-а).
- `architecture/platform-architecture-principles.md` §6 — две capability `Notifications` и `Activity / Tasks`.
- `architecture/module-catalog-and-routing-map.md` §0 — те же две строки.
- `operations-loop.md` — as-built карта boltened-вместе подсистем.
- `workflows/reminders.md` + `reminders_matrix.md` + `reminders_rework.md` — три источника правды по reminders.
- `manager-assignment.md` — assignee-поля, Reminder/Planner/Thread в одном фрейме.
- `modules/scheduler.md` + `min/scheduler.min.md` — отдельный booking/services-домен, который продуктовая команда часто путает с «планировщиком работы рекрутёра».

Этот ADR **сводит** архитектурную часть в один контракт, после которого код становится rename-able без смены смысла.

Связанные ADR: [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md), [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md), [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md), [`ADR-005`](ADR-005-three-level-settings-hierarchy.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`ADR-010`](ADR-010-unified-resource-list-shell.md), [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md).

---

## Decision

Ввести **единый Activity & Notification Operating Layer** между бизнес-модулями HostFlow. Слой состоит из **двух** долгоживущих сущностей и нескольких **представлений**.

### D1. Activity — единая операционная сущность

`Activity` — единственная таблица для **всех** операционных действий: задач, напоминаний, follow-up, звонков, встреч, проверок документов, разовых TODO. Никаких параллельных task-таблиц.

| Свойство | Решение |
|---|---|
| Идентификация | `id`, `tenant_id`, `company_id` |
| Типизация | `type` (закрытый enum, см. canon §2.1) |
| Состояние | `status` ∈ `planned` \| `in_progress` \| `done` \| `cancelled` \| `overdue` |
| Приоритет | `priority` ∈ `low` \| `normal` \| `high` \| `urgent` |
| Описание | `title`, `description` |
| Назначение | `assigned_to_user_id` (FK `users.id` ON DELETE SET NULL), `created_by_user_id` |
| Связь с доменом | `related_entity_type`, `related_entity_id` (обязательны кроме `type='custom'`) |
| Происхождение | `source_module` (закрытый enum: `leads` \| `candidates` \| `documents` \| `comms` \| `workforce` \| `automation` \| `user`) |
| Время | `starts_at`, `due_at`, `reminder_at`, `completed_at`, `cancelled_at`, `snoozed_until` |
| SLA | `sla_due_at`, `sla_status` ∈ `ok` \| `warning` \| `breached` |
| Прочее | `recurrence_json`, `metadata`, `duration_minutes`, `channel`, `created_at`, `updated_at` |

Полный список полей и инварианты — в canon-документе [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md) §2.

### D2. Notification — только сигнал

`Notification` — единственная таблица для in-app сигналов пользователю (bell + Notification Center). Уведомление **никогда** не подменяет задачу: если требуется действие — публикуется и `Activity`, и `Notification`, со ссылкой `notification.activity_id`.

| Свойство | Решение |
|---|---|
| Идентификация | `id`, `tenant_id`, `user_id` |
| Тип | `type` (закрытый enum, см. canon §3.1) |
| Содержание | `title`, `body`, `severity` ∈ `info` \| `warning` \| `critical` |
| Связь | `related_entity_type`, `related_entity_id`, `activity_id` (FK `activities.id` ON DELETE SET NULL) |
| Доставка | `channel` ∈ `in_app` \| `email` \| `webhook` \| …, `delivered_at`, `is_read`, `read_at` |
| Прочее | `priority`, `payload`, `created_at`, `updated_at` |

Compliance-логи (`final_no_contact_notifications`, `rodo_notifications`) и исходящие webhooks (`services/notifications.py`) — **не часть** этого слоя; это отдельный delivery / audit-домен.

### D3. Reminder — поведение Activity, не сущность

`Reminder` как самостоятельная сущность БД **прекращает существование**. На уровне concept «напомни мне» = пара полей `activity.reminder_at` + автоматически созданный `Notification` с `type='activity_due_soon'` за `reminder_at` минут до `due_at`.

API `/api/v1/reminders` удаляется в Phase 2; обратной совместимости не предусмотрено (см. Q2 в журнале решений ниже).

### D4. Task / Todo / Planner / Calendar / Today — представления Activity

Все четыре «продуктовые поверхности» — это **views** над `Activity`, не разные сущности:

| View | URL | Фильтр над `activities` |
|---|---|---|
| **Task Manager** | `/app/work/tasks` | `status ∈ {planned, in_progress, overdue}`, `assigned_to_user_id = me` (и пресеты Today / Overdue / Upcoming / SLA risk / Unassigned) |
| **Today / Planner** | `/app/work` (секция) | `due_at ∈ today` ∨ `starts_at ∈ today` |
| **Calendar** | `/app/calendar` | `starts_at IS NOT NULL` ∨ `due_at IS NOT NULL`, по диапазону |
| **Notification Center** | `/app/notifications` | `notifications` сгруппированы по `type` (Urgent / Tasks / Messages / Documents / System) |

Никаких дополнительных таблиц `planner_items`, `todos`, `calendar_internal_events` не вводится.

### D5. NBA / Next Actions — recommendation layer над Activity

`/api/v1/next-actions` остаётся, но переосмысляется как **recommendation layer**: возвращает рекомендации, каждая ссылается на существующий `activity_id` ИЛИ предлагает payload для создания Activity.

- Если правило в `automation_rules` имеет высокий confidence (ниже см. canon §6) — Activity создаётся **автоматически**, и NBA отдаёт её `activity_id`.
- Если confidence ниже — NBA отдаёт payload-предложение; пользователь принимает «Accept recommendation» → `POST /activities`.

NBA не хранит собственные задачи, не имеет своего inbox-а и не дублирует Task Manager.

### D6. WorkHubPage — основной операционный экран `/app/work`

Канонический экран Work Hub — **`WorkHubPage`** (явный композит панелей). `WorkOrganizerPage` удаляется в Phase 3. URL `/app/work` обслуживает `WorkHubPage`. Календарь живёт на отдельном URL `/app/calendar`. Это решение фиксирует G-6 / §4 из `operations-loop.md`.

### D7. WorkforceOnboardingTask — отдельная HR-сущность с проекцией в Activity

`WorkforceOnboardingTask` **не поглощается** Activity:

- HR-домен сохраняет собственный onboarding-flow (lifecycle сотрудника, чек-листы, контракты).
- При создании `WorkforceOnboardingTask` HR-сервис **публикует** соответствующий `Activity` с `source_module='workforce'`, `related_entity_type='workforce_onboarding_task'` (или `'workforce_employee'`), который виден в общем Task Manager.
- Закрытие `Activity` не закрывает onboarding-task автоматически (HR — owner lifecycle, см. `operational-event-boundaries.md`); закрытие onboarding-task переводит проекцию-Activity в `done`.

### D8. Scheduler module — отдельный booking domain

`docs/specs/modules/scheduler.md` (`scheduler_events` / `scheduler_slots` / `scheduler_reminders` / `scheduler_sync`) — **booking услуг** (медосмотры, психотесты, обучение). Это **другой** домен, не operational layer:

- Scheduler **может** публиковать `Activity` (например, «подтверди приезд кандидата на медосмотр»), но **не** наоборот.
- Calendar UI слоя `Activity` показывает scheduler-события только если у tenant включён модуль Services и присутствует явная проекция — модулю-источнику разрешено, не обязательно.

### D9. Calendar integrations — connector / mirror layer

Таблицы `calendar_connections`, `calendar_channels`, `calendar_items`, `calendar_sync_cursors`, `calendar_sync_jobs`, `integration_action_logs` остаются как **connector layer** (Google / Outlook / Slack / Teams sync):

- Внешнее календарное событие импортируется как `CalendarItem` (mirror).
- Если оно создано пользователем внутри HostFlow — единственным источником истины является `Activity`; `CalendarItem` живёт как **зеркало для внешнего provider-а**.
- Удаление `CalendarItem` не удаляет `Activity`; удаление `Activity` снимает mirror-связь и пушит cancel в provider.

Эти таблицы **не** являются источником операционных задач; UI-календарь читает `activities` + `calendar_items` (для интегрированных событий) — два разных слоя одного экрана.

### D10. Это смена модели, а не косметический rename

Решение явно фиксирует, что переименование `reminders → activities` — **не** косметика:

- Параллельные task-сущности (`candidate_tasks`, `communication_planner_events.kind ∈ {task, followup}`, обёртка `activities_v1` над `reminders_v2`) **снимаются**.
- Уведомления без `Activity` или без понятной информации **не создаются**: каждый `Notification` обязан вести либо к информации, либо к действию (через `activity_id`).
- Каждое Activity обязано иметь: `assigned_to_user_id` (или явное `unassigned`-состояние), `due_at` (или `starts_at` для timed-event), `status`, `related_entity_*`, `source_module`. Activity без этих полей считается багом, не легитимной строкой.
- `next-actions` перестаёт быть параллельным task-менеджером.
- Frontend перестаёт иметь `WorkOrganizerPage`, `pages/ActivitiesPage.tsx` (старая, мёртвая), `pages/CommunicationsPlannerPage.tsx`.

---

## Consequences

### Положительные

1. Один operational layer — один inbox, один календарь, один центр уведомлений.
2. Реальный SLA (`sla_due_at`, `sla_status`) живёт в самой строке, а не как проекция API → drilldown integrity.
3. UX-правило «что произошло / что мне сделать / до какого срока / к чему относится / что будет если проигнорировать» — закрывается полями `Activity` и `Notification`.
4. Меньше FK-долга: один `assigned_to_user_id` FK вместо трёх разных owner-полей.
5. Простая ментальная модель для разработчиков и AI-агентов: «эта строка — Activity или Notification?» — третьего не дано.

### Отрицательные / стоимость

1. Phase 1+2 — breaking-change для backend: переименование `reminders → activities`, `user_notifications → notifications`. Согласовано как **one-shot** (см. журнал решений Q2). Frontend мигрируется одной волной.
2. Удаление `candidate_tasks` API и `communication_planner_events` API — потенциальные внешние интеграции (если есть) ломаются. На момент Phase 0 внешние потребители не зафиксированы.
3. Под `calendar_*` таблицы Alembic-ревизий нет; Phase 1 включает создание корректирующей миграции, чтобы DDL-расхождения с prod не размножались.
4. Документация: 25+ spec-файлов требуют синхронизации (см. canon §10 «Документация» и список в `Phase 0 — Что обновлено»).

### Нейтральные

1. `WorkforceOnboardingTask`, `CommunicationTimeOffRequest`, `CommunicationThread.sla_due_at` — **не** трогаем; они остаются за HR / availability / threads-доменами и публикуют `Activity` по необходимости.
2. Модуль `Scheduler` (booking услуг) развивается независимо.
3. Compliance-уведомления (`final_no_contact_notifications`, `rodo_notifications`) и исходящие webhooks остаются.

---

## Ограничения

- **Не** косметический rename. Если в Phase 1 кто-то предложит «просто переименовать таблицу», но оставить параллельные сущности — это **нарушение этого ADR**.
- **Не** добавляем новые «todo / planner / reminder» сущности до явного нового ADR, который пересмотрит этот.
- **Не** позволяем consumer-у Activity/Notification менять source-of-truth чужого домена (см. `operational-event-boundaries.md` главный инвариант: *Activity is work item, not source of truth*; *Notification is delivery, not state*). Activity может быть создана только через owner-команду (PATCH stage, upload document, message received и т.д.).

---

## Журнал решений (Phase 0)

Зафиксированы во время согласования плана между пользователем и архитектурой:

| # | Вопрос | Решение |
|---|---|---|
| Q1 | Стратегия БД-миграции: rename in place vs новая таблица + бэкфилл | **Rename in place**: `reminders → activities`, `user_notifications → notifications` |
| Q2 | API: deprecation period или one-shot | **One-shot**. `/api/v1/reminders`, `/api/v1/communications/planner/events`, `/api/v1/candidates/{id}/tasks` удаляются в Phase 2 без 410-period |
| Q3 | Два work-хаба (`WorkOrganizerPage` vs `WorkHubPage`) | **`WorkHubPage`** остаётся, `WorkOrganizerPage` удаляется в Phase 3 |
| Q4 | `WorkforceOnboardingTask` → Activity или отдельно | **Отдельно**, но HR-сервис публикует проекцию в Activity (см. D7) |
| Q5 | `/api/v1/next-actions` — отдельный продукт или recommendation layer | **Recommendation layer над Activity** (см. D5) |

---

## Implementation roadmap

| Phase | Скоуп | DOR / DOD |
|---|---|---|
| **0** (this ADR) | Документация: ADR-012 + canon + правки 25+ spec-файлов; superseded reminders-workflows | DOD: каждое из 10 решений (D1–D10) имеет однозначное определение в spec; противоречий между doc-файлами нет |
| **1** | Backend модели: `Activity`, `Notification`, `ActivityEvent`, Alembic rename + add columns + backfill `company_id` / `sla_due_at`; алиасы `Reminder = Activity` для transition | DOD: тесты модели зелёные, миграция up/down round-trip clean на staging Postgres |
| **2.1** ✅ DONE 2026-05-09 | Planner / candidate-tasks → Activity: backfill (`202607150004_pti`), service rewire (`timeoff_cleanup` / `lead_lifecycle` / `candidate_lifecycle` / `team_assignee_auto`), удаление backend routes (`/api/v1/candidates/{id}/tasks`, `/api/v1/communications/planner/events*`), FE shim в `src/api/communications.ts`, drop-revision (`202607150005_dptt`) подготовлен и soft-gated за `HOSTFLOW_PHASE_2_1_DROP_OK=1` | DOD: rg по backend не находит активных вызовов legacy таблиц/route'ов; FE не ходит на legacy URL; canary smoke + проверка «no new writes в legacy таблицы» — gate перед физическим drop |
| **2** (остаток) | Backend API consolidation: удаление `/api/v1/reminders`; `next-actions` переписан под D5 | DOD: все internal call-site переведены, OpenAPI отражает только новый контракт |
| **3** | Frontend: rename pages, единый API client, Notification Center, удаление мёртвого кода, `WorkHubPage` единственный, **выпил Phase 2.1 shim'а** (`src/api/communications.ts::*PlannerEvent*`) и transitional полей в `ReminderUpdateRequest` | DOD: type-check + Playwright прогон, UAT-чеклист (см. `journeys/*.md`) |
| **4** | Seeds + cleanup алиасов; deprecated копии удалены | DOD: `Reminder = Activity` алиас удалён, `make seed` зелёный, нет dead-imports |

Каждая фаза — отдельный PR с нелокальными тестами и прогоном `make lint && make test`. Между фазами — обязательный canary 24-48ч на staging.

---

## References

- [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md) — canon (поля, инварианты, маппинг)
- [`operational-event-boundaries.md`](operational-event-boundaries.md) — vocabulary, consumer contract, command/flow
- [`platform-architecture-principles.md`](platform-architecture-principles.md) — shared capabilities (объединённая capability)
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0 — карта platform / business modules
- [`../operations-loop.md`](../operations-loop.md) — as-built и G-1…G-10 (закрываемые этим ADR)
- [`../manager-assignment.md`](../manager-assignment.md) — owner-поля
- [`../workflows/activities.md`](../workflows/activities.md) — единая workflow-спека (созда­ётся Phase 0)
- [`../workflows/activities-sla-matrix.md`](../workflows/activities-sla-matrix.md) — SLA-матрица (Phase 0)
- [`../modules/scheduler.md`](../modules/scheduler.md) — booking услуг (другой домен)

---

## История

- 2026-05: первичная фиксация ADR-012; Phase 0 — только документация; Q1–Q5 решения; D1–D10 контракт; canon-документ создан параллельно.
- 2026-05-09 — **Phase 2.1 closed (planner / candidate-tasks → Activity)**. Backfill (`alembic 202607150004_pti`), backend service rewire, backend route removal (`/api/v1/candidates/{id}/tasks`, `/api/v1/communications/planner/events*`) и FE shim в `src/api/communications.ts` (legacy `*PlannerEvent*` функции теперь дёргают `/api/v1/activities` с remap'ом kind ↔ type, start_at ↔ due_at, end_at ↔ duration_minutes, all_day ↔ payload._planner_all_day, linked_*_id ↔ entity_*) — все DONE. Drop-tables (`alembic 202607150005_dptt`) **не применён физически**: ревизия soft-gated за `HOSTFLOW_PHASE_2_1_DROP_OK=1`, ждёт canary. Подробности — [`phase-2-1-planner-tasks-into-activities.md`](phase-2-1-planner-tasks-into-activities.md).
  - **Transitional BE addition (отметка для Phase 3):** `ReminderUpdateRequest` (`backend/app/api/v1/reminders_v2.py`) и `services/reminder_tasks.update_reminder` получили опциональные поля `status`, `type`, `entity_type`, `entity_id`, `payload`. Эти поля добавлены **исключительно** для FE shim, который мапит legacy `PATCH /communications/planner/events/{id}` → `PATCH /api/v1/activities/{id}`. **Phase 3 обязан** выпилить эти legacy planner-семантики из shim'а вместе с `Reminder`-алиасом; в частности **`payload` wholesale replace** (mirror планерных правил) допустим только как transition — он **не должен** становиться долгосрочной моделью обновления Activity (целевая модель — domain-specific PATCH полей, без замены blob'а).
