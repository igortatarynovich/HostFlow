# Operations Loop — единый позвоночник работы рекрутёра

**Назначение:** один справочник для подсистем, которые в HostFlow обязаны работать как ЕДИНОЕ ЦЕЛОЕ — иначе пользователь не понимает, что делать дальше, и продукт ощущается перегруженным. Документ покрывает: уведомления (bell), напоминания/задачи (reminders / `/app/tasks`), planner / календарь, working hours / time-off / team availability, назначение менеджеров, входящие сообщения мессенджеров, Next-Best-Action (NBA), хаб работы (`/app/work`), а также как это всё ведёт себя на терминальных стадиях кандидата.

**Связанные документы:**

- `docs/SSOT.md` §2.10 (lead processing), §2.11 (reminders/SLA), §2.13 (comms), §2.16 (план-биллинг).
- `docs/specs/plans-matrix.md` — лимиты (channels, automation rules, funnel definitions).
- `docs/specs/personas.md` — кто на каком экране что должен видеть.
- `docs/HOSTFLOW_AUDIT_AND_PLAN.md` Phase 2 §2.5 (todo по этому документу).

**Принцип:** «один экран — одна цель, один следующий шаг» (см. `pipe.md`). Операционный позвоночник существует, чтобы пользователь, открыв любой экран, мог за ≤ 2 клика ответить «что мне делать сейчас и почему». Если хотя бы одна подсистема молчит, врёт или дублирует другую — позвоночник сломан.

---

## Phase 2.1 status (planner / candidate-tasks → Activity, 2026-05-09)

**Зафиксировано в этом документе как as-built:** §2.4 (Communications planner), §2.3 (Calendar), §3.2 / G-1 (lifecycle hooks) и счётчики (`planner_events_cancelled`) описывают **как было до Phase 2.1**. С 2026-05-09 продакшен-поведение изменилось:

- `/api/v1/candidates/{id}/tasks` и `/api/v1/communications/planner/events*` **удалены** из backend. Единственный CRUD задач — `/api/v1/activities` (см. ADR-012, `architecture/phase-2-1-planner-tasks-into-activities.md`).
- Backend-сервисы (`timeoff_cleanup`, `lead_lifecycle`, `candidate_lifecycle`, `team_assignee_auto`, `communications_scheduler`) больше не читают и не пишут `candidate_tasks` / `communication_planner_events` — все cancel / load / sweep пути идут через `Activity`. Имя счётчика `planner_events_cancelled` сохранено для compat-а; bucketing — `Activity.starts_at IS NULL` (deadline) vs `IS NOT NULL` (time-bound).
- Frontend оставлен «как есть» через **shim** в `hostflow-frontend/src/api/communications.ts`: `getCommunicationPlannerEvent` / `listCommunicationPlannerEvents` / `createCommunicationPlannerEvent` / `patchCommunicationPlannerEvent` сохраняют типы и подписи, но внутренне дёргают `/api/v1/activities` с remap'ом полей (`kind ↔ type`, `start_at ↔ due_at`, `end_at ↔ due_at + duration_minutes`, `all_day ↔ payload._planner_all_day`, `linked_*_id ↔ entity_*`, planner-статусы `new`/`pending`/`sent`/`overdue` → `planned` на чтении, `done` patch → `POST /activities/{id}/complete`). `CommunicationsCalendarPage`, `RemindersPage`, `MyTasksPanel`, `TodayPlannerPanel` работают через shim без переписывания.
- Физический `DROP TABLE candidate_tasks / communication_planner_events` (`alembic 202607150005_dptt`) **soft-gated** за `HOSTFLOW_PHASE_2_1_DROP_OK=1` — ждёт canary и проверки «нет новых записей в legacy таблицы». До открытия gate ORM `CommunicationPlannerEvent`, `CandidateTask` и `ensure_communications_schema.py` остаются в коде.
- Phase 3 удалит shim, native-переименует UI и снимет transitional поля (`status` / `type` / `entity_type` / `entity_id` / `payload`) с `ReminderUpdateRequest`, добавленные исключительно для shim'а.

Текст ниже намеренно сохраняет описание подсистем «до Phase 2.1» как археологию — чтобы читатель видел, что закрылось каким PR'ом. Свежие правки помечены маркером **(Phase 2.1)** в соответствующих секциях.

---

## 1. Понятийная карта

```
                       ┌────────────────────────────────────────────────┐
                       │                  Триггеры                       │
                       │  ─ Lead ingest (Meta / webhook / form / import)│
                       │  ─ Stage transition (lead, candidate)           │
                       │  ─ Document workflow (uploaded, expired, signed)│
                       │  ─ Inbound message (Gmail/Telegram/WhatsApp/…) │
                       │  ─ SLA scheduler (cron, periodic)               │
                       │  ─ User action (manual reminder / planner event)│
                       └──────────────────────┬─────────────────────────┘
                                              │
                                              ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │                    Reminder (SLA / task queue)                    │
        │  table reminders: type, entity_type/id, owner_id, assignee_id,    │
        │  due_at, remind_at, snoozed_until, status, channel, priority      │
        │  Создаётся: reminder_tasks.create_reminder + scheduler            │
        └────────────┬───────────────────────────────────┬──────────────────┘
                     │                                   │
                     ▼                                   ▼
        ┌────────────────────────────┐    ┌────────────────────────────────────┐
        │ deliver_due_reminders cron │    │       NBA (Next-Best-Action)        │
        │ → создаёт UserNotification │    │  _nba.py + count_candidates_*       │
        │   reminder_due/_overdue    │    │  Источники: lead pipeline + reminder│
        └─────────────┬──────────────┘    │  status + funnel-dwell             │
                      │                   └─────────────┬──────────────────────┘
                      ▼                                 │
              ┌─────────────────────┐                   │
              │  UserNotification   │                   │
              │  bell в Topbar      │                   │
              └──────────┬──────────┘                   │
                         │                              │
                         ▼                              ▼
              ┌────────────────────────────────────────────────────────┐
              │  Где видит пользователь:                                │
              │  ─ Bell (Topbar)               ─ /app/tasks              │
              │  ─ /app/work (хаб)             ─ Dashboard (счётчики)   │
              │  ─ Карточки кандидата/лида     ─ /app/calendar          │
              └────────────────────────────────────────────────────────┘
```

**Параллельная подсистема — Planner (legacy, поглощено Phase 2.1):**

```
   CommunicationsCalendarPage  ──┐  через FE shim (Phase 2.1)
   (drag-and-drop UI)            │  src/api/communications.ts
                                 ▼
            /api/v1/activities  ───── единый CRUD
            (Activity.starts_at = planner.start_at,
             Activity.due_at + duration_minutes = planner.end_at,
             metadata.planner.kind = legacy planner.kind для
             backfilled rows; новые task/followup пишутся
             как Activity.type='task'/'follow_up')

   ──── as-was (до Phase 2.1, 2026-05-09) ─────────────────
   communication_planner_events table — отдельная таблица
   (start_at, end_at, kind, status, assignee, entity); ORM
   остаётся в коде за `ensure_communications_schema.py`,
   физический DROP за soft-gate HOSTFLOW_PHASE_2_1_DROP_OK=1.
```

Planner ≠ reminder. Planner — это запланированный «слот в календаре» (звонок, встреча, follow-up). Reminder — это «надо что-то сделать к дедлайну». **(Phase 2.1)** На уровне БД оба теперь — строки в `activities`: разница в наличии `starts_at`. На уровне UI они всё ещё рендерятся раздельно (планер-плитки в календаре vs reminder-rows в `/app/tasks`), что закрыто G-7 (UX-объединение в `/app/tasks`). См. §6 «Гэп: дублирующиеся сущности» — основная часть гэпа теперь устранена; остался UI-rename Phase 3.

---

## 2. Подсистемы — текущее состояние (факты из кода)

### 2.1 Reminders / Tasks

- **Модель:** `backend/app/models/reminder.py` (`Reminder`), статусы `new | pending | sent | overdue | done | cancelled`, `type` — свободная строка.
- **Сервис:** `backend/app/services/reminder_tasks.py` (606 LOC) — `create_reminder`, `list_reminders`, `snooze_reminder`, `complete_reminder`, `deliver_due_reminders`.
- **API:** `backend/app/api/v1/reminders_v2.py` (388 LOC) → `POST /reminders`, `POST /reminders/{id}/complete`, `POST /reminders/{id}/snooze`, `GET /reminders`.
- **UI:** `pages/RemindersPage.tsx` (1623 LOC), маршрут `/app/tasks` (legacy `/app/reminders` redirect).
- **Кто создаёт:**
  - User вручную (через UI на карточке кандидата/лида).
  - Документы: `services/reminders.py` (721 LOC) — на expiry / workflow.
  - Comms SLA: `communications_scheduler.py` — `communications_sla_overdue`.
  - Lead SLA: `communications_scheduler.py` — `leads_no_next_action`, `leads_stuck_stage`.
  - Lead processing: `_pick_lead_assignee_id` создаёт reminder при assign-е.
- **Default assignee:** = текущий пользователь, если не передан.
- **Фильтры в UI:** search, status (`active|all|done`), entity type, priority, overdue-only, assignee scope (`mine|team`). **Нет фильтра по «kind/type»** — есть только entity type.

### 2.2 Notifications (bell)

- **Модель:** `backend/app/models/user_notification.py` — `event_type` строка, `is_read`, `entity_type/id`, `payload`. **Нет** колонки `status`.
- **Сервис:** `backend/app/services/user_notifications.py` (577 LOC).
- **API:** `backend/app/api/v1/notifications.py` (228 LOC).
- **Дедуп:** `dedupe_window_minutes` + `payload.dedupe_key` или совпадение entity.
- **UI:** колокольчик в `components/nav/Topbar.tsx` (1119 LOC), отдельной страницы нет — только `events`-вкладка в `RemindersPage`.
- **Reminder → Notification:** да, `deliver_due_reminders` создаёт `reminder_due` / `reminder_overdue` в bell.

### 2.3 Calendar (`/app/calendar`)

- **UI:** `pages/CommunicationsCalendarPage.tsx` (2278 LOC).
- **Источники событий (4 параллельных API):**
  1. `listCommunicationTimeOffRequests` — одобренные time-off.
  2. `listActivities` (= reminders, через `api/v1/activities_v1.py`).
  3. `listCommunicationPlannerEvents`.
  4. `getMyWorkingHours` (для проверки слотов).
- Унифицированный shape `UnifiedCalendarEvent` с `source: 'timeoff'|'reminder'|'planner'`.
- **Конфликты:** проверяются на клиенте (`findSchedulingConflict`) — backend этого не делает.
- **Drag-to-reschedule:** для planner-rows фронт зовёт `patchCommunicationPlannerEvent` — **(Phase 2.1)** shim теперь маршрутизирует это в `PATCH /api/v1/activities/{id}` с remap'ом `start_at → due_at`, сохраняя `duration_minutes` (производное `end_at`); reminders двигаются напрямую через `updateReminder` (`PATCH /reminders/{id}`).

### 2.4 Communications planner

> **(Phase 2.1, 2026-05-09)** Раздел описывает планер «как было». На данный момент:
>
> - HTTP-роуты `GET/POST/PATCH/DELETE /communications/planner/events*` удалены; единственный CRUD задач/событий — `/api/v1/activities`.
> - ORM `CommunicationPlannerEvent` остаётся в кодовой базе (за `ensure_communications_schema.py`) только до открытия soft-gate `HOSTFLOW_PHASE_2_1_DROP_OK=1`. Backend-сервисы больше **не читают и не пишут** эту таблицу.
> - Frontend `CommunicationsCalendarPage` / `TodayPlannerPanel` / `RemindersPage` (G-7) / `MyTasksPanel` ходят через shim в `hostflow-frontend/src/api/communications.ts` (`*PlannerEvent*` функции) — он транслирует вызовы в `/api/v1/activities` с remap'ом полей. Phase 3 удалит shim и переименует консьюмеры на native Activity API.
> - Working-hours валидация для planner-create/patch (G-4 stage 2) теперь выполняется на activity-PATCH (через те же helpers `_assert_within_working_hours_or_overridden`); параметр `allow_outside_hours` сохранён в shim'е через `payload._planner_allow_outside_hours`.

- **Модель (legacy as-built):** `CommunicationPlannerEvent` (`models/communication.py` 179–209) — `kind` (task/call/meeting/followup/shift), `status` (planned/in_progress/done/cancelled), `start_at/end_at`, `assignee_id`, `entity_type/id`.
- **API (legacy, удалено Phase 2.1):** `backend/app/api/v1/communications/routes/planner.py` ранее экспортировал `GET/POST/PATCH /communications/planner/events`; сейчас файл содержит только working-hours / availability / time-off endpoints.
- **Working hours:** проверяются ТОЛЬКО на фронте при batch-создании. Backend (`/api/v1/activities`) валидирует working-hours окна через G-4 stage 2 helper — см. §G-4 ниже.
- **Frontend page `CommunicationsPlannerPage.tsx`:** удалён в Phase 2 §2.3.B (был мёртвый код).

### 2.5 Working hours / Team availability / Time off

- **Working hours:** хранятся через `GET|PUT /communications/availability/working-hours` (нет отдельной таблицы в моделях; вероятно в `tenant.settings`).
- **Time-off:** модель `CommunicationTimeOffRequest` (`requester_user_id`, `approver_user_id`, `request_type`, `status`, `start_date/end_date`, `partial_day`).
- **UI:**
  - `MyAvailabilityPage.tsx` (425 LOC) — мои working hours + мои time-off.
  - `TimeOffRequestsPage.tsx` (218 LOC) — менеджер approve/reject.
  - `TeamAvailabilityPage.tsx` (219 LOC) — обзор команды + одобренные time-off.
- **Approval:** `POST /communications/time-off/requests/{id}/decision` — только `administrator`/`supervisor`.
- **Что зависит от availability:**
  - **`reminders` (due/remind времена):** ❌ НЕ учитываются. Reminder придёт в 03:00 ночи.
  - **Planner создание:** ✅ frontend-only валидация.
  - **Comms send-time:** ❌ нет реализации (scheduler смотрит только SLA-минуты).
  - **NBA:** ❌ нет учёта.
  - **Manager queue (только!):** ✅ approved time-off обновляет `tenant.settings.communications.managerQueue.availability.state` через `_sync_manager_queue_availability_from_time_off`.

### 2.6 Manager assignment

- **Candidate:** `Candidate.manager` (string user_id) + `Candidate.recruiter_id` (FK на users).
- **Назначение лида:** `_pick_lead_assignee_id` в lead processing pipeline.
- **Назначение кандидата:** `_rule_recruiter_id_from_normalized` → `vacancy.recruiter_id` → fallback. Описано в `_processing.py`.
- **Vacancy:** `Vacancy.recruiter_id`.
- **«Моя очередь» vs «команда»:** `assignee_scope = mine|team` для reminders; для кандидатов — URL params (`?recruiter_unassigned=true`, `?ops_mode=in_work`); для work hub — assignee-scoped счётчики из `ops_counters`.

### 2.7 Messenger / Inbox → operations

- **Inbound сообщение → reminder + notification:**
  - На входящем устанавливается `thread.sla_due_at` из channel SLA (`sla.py` 82–96).
  - При просрочке scheduler создаёт ОБА: `UserNotification` (`communications_sla_overdue`) и `Reminder` (`communications_sla_overdue`) для assignee.
- **Per-thread SLA:** хранится на `CommunicationThread.sla_due_at` + `thread_meta.sla_policy`.
- **Resolve:** `_resolve_thread_sla_alerts` — отменяет SLA reminder и помечает notification прочитанным.
- **Auto-reply / templates:** не enumerated в текущем аудите; есть `notification_templates` сервис, но это про template metadata, не про auto-reply на тред.

### 2.8 NBA (Next-Best-Action)

- **Backend:** `backend/app/modules/leads/service/_nba.py` (367 LOC), `backend/app/api/v1/next_actions.py` (38 LOC) → `GET /next-actions`.
- **Скоп:** per-tenant lead-buckets + per-actor candidate-buckets (если передан `actor_user_id`).
- **Сигналы:**
  - Lead: status/stage/next_action/pipeline_error counts; funnel weak-step и slow-dwell.
  - Candidate: «нет активного reminder» = нет next action; overdue reminders.
- **UI:** Используется в `LeadsPage` (`useNbaQuickBulkFlow`), `AnalyticsLeadConversionFunnelPage`. Компонент `NbaNextActionsChips.tsx` — мёртвый код (никем не импортируется).
- **Подавление для терминальных стадий:** ✅ candidate NBA-counts ИСКЛЮЧАЮТ кандидатов где `stage in PIPELINE_COMPLETED_STAGE_CODES = {rejected, declined, probation_ok, employed}`.

### 2.9 `/app/work` (Work Hub)

- **UI:** `pages/WorkHubPage.tsx` (513 LOC).
- **Секции (всегда одинаковые, не меняются по роли):**
  1. Header.
  2. Hero (для candidates only): «calm» vs «needs action», CTA.
  3. Critical list — что требует внимания.
  4. Bottlenecks list.
  5. Quick actions / leads-only CTA.
- **Источники данных:**
  - `getOpsCounters()` → `/analytics/ops-counters` (assignee-scoped для текущего пользователя).
  - `GET /candidates?limit=1&compact=true&include_insights=true`.
  - **Нет** прямого вызова `GET /next-actions`.
- **Permission-aware:** через `usePermissions().can('candidates.view'|'leads.view'|'notifications.view')`. **Не различает** admin/supervisor/recruiter/client_manager — все видят одинаковый layout.

---

## 3. Жизненный цикл кандидата и подавление шума

### 3.1 «Терминальные» стадии (что считается завершённым)

```python
# backend/app/constants/stages.py
TERMINAL_STATUSES = {"probation_ok", "rejected", "declined"}
PIPELINE_COMPLETED_STAGE_CODES = TERMINAL_STATUSES | {"employed"}
```

Только эти 4 кода официально считаются «завершённым путём». Стадии типа `processing_by_client`, `handoff_returned`, `ready_for_handoff`, `archived`, `cancelled`, `withdrew`, `hired_elsewhere` — НЕ в этом наборе и считаются активными для всех агрегатов.

### 3.2 Что происходит при переходе в терминальную стадию (текущий код)

| Вопрос | Ответ кода | Где |
|---|---|---|
| Pending reminders для этого кандидата отменяются? | **❌ Нет.** `cancel_entity_reminders` существует, но вызывается ТОЛЬКО при удалении документа (`candidate_documents.py` 1398–1403). Никаких вызовов из `candidates/service.py` при stage-transition. | grep `cancel_entity_reminders` — ноль матчей в candidate flow. |
| Open notifications помечаются прочитанными? | **❌ Нет.** `list_notifications` не имеет фильтра по candidate.stage; cleanup существует только для SLA-типов (thread + lead). | `user_notifications.py` 271–294, 313–410, 488–505. |
| NBA подавляются? | **✅ Да** — counts. Но конкретные reminders в task list — **НЕТ**. | `_listing.py` 344–347, 384–387 (counts only). |
| Bell дедупится для тред-связанных, но НЕ по candidate.stage. | — | `Topbar.tsx` 341–357. |
| Tasks page (`RemindersPage`) скрывает reminders rejected-кандидатов? | **❌ Нет.** `list_reminders` фильтрует только по assignee/status, не по `Candidate.stage`. | `reminder_tasks.py` 215–249. |
| Calendar скрывает их? | **❌ Нет.** Те же reminders, тот же планер. | `CommunicationsCalendarPage.tsx`. |

**Вывод по запросу пользователя:** «Чтобы по отменённым/отклонённым уведомления не светились» — **сейчас они светятся**. Это не одна точка фиксации, а целый класс работ — см. §7 «Target state и гэпы», G-1.

### 3.3 Handoff

- `accept_handoff` → ставит `Candidate.stage = "processing_by_client"` и `Candidate.status = "processing_by_client"`. Не отменяет reminders агентства, не помечает notifications прочитанными.
- `return_handoff` → ставит `Candidate.stage = "handoff_returned"`. То же.
- Handoff event → создаёт notification (`handoff_requested`/`handoff_accepted`) для нужной аудитории. Не reverse-ится автоматически.

### 3.4 Ops-counter cleanup vs UI-list cleanup

**Несимметрия:** ops-counters умнее, чем сами списки.

- Ops-counter `no_next_action_candidates` — корректно исключает PIPELINE_COMPLETED.
- Reminders SLA cleanup — корректно работает для thread/lead SLA.
- Но `/app/tasks` (UI list) и bell-dropdown (UI list) — НЕ синхронизированы с этой логикой. Поэтому **на дашборде «12 задач», в /app/tasks — 47, в bell — 23.** Доверие к продукту падает.

---

## 4. Ролевая дифференциация хаба `/app/work`

### 4.1 Что должны видеть разные роли (target — из `personas.md`)

| Роль | Главный вопрос «что мне делать сейчас?» | Источник данных |
|---|---|---|
| **administrator (Solo)** | «Что нового пришло, что застряло у меня — я единственный пользователь.» | ops_counters (полный) + первый лид + первая задача. |
| **administrator (Team+)** | «Где блокеры команды? Кто перегружен?» | ops_counters tenant-wide + manager-load + risk digest queue. |
| **supervisor** | «Чьи дела протухают, кому делегировать.» | ops_counters tenant-wide + risk digest + handoff queue + по recruiters. |
| **recruiter** | «Мой следующий шаг по кандидату X через 2 клика.» | ops_counters mine-scoped + my candidates list + my reminders + сегодняшний planner. |
| **client_manager** | «Что прислало агентство, что подписать.» | candidates handed-off to me + documents-to-sign + threads. |
| **client_processor** | «Кого мне сегодня обработать.» | my candidates (handed-off mine) + my reminders + handoff queue. |
| **viewer** | «Что в системе вообще происходит.» | read-only сводка без CTA. |

### 4.2 Текущее состояние

`WorkHubPage` рендерит ВСЕ блоки без различий по роли. Permission gate проверяет только наличие просмотра модулей. Нет per-role ветвления, нет per-role «hero» (recruiter не видит handoff queue ярко, supervisor не видит team-load ярко).

### 4.3 Target

Один компонент с per-role layout-presetами:

```
WorkHubPage
 ├─ AdministratorWorkLayout    (admin-team / admin-solo)
 ├─ SupervisorWorkLayout
 ├─ RecruiterWorkLayout
 ├─ ClientManagerWorkLayout
 ├─ ClientProcessorWorkLayout
 └─ ViewerWorkLayout
```

Эти layouts собирают одни и те же data-блоки (`MyTasksPanel`, `TodayPlannerPanel`, `RiskDigestPanel`, `ManagerLoadPanel`, `HandoffQueuePanel`, `MyCandidatesPanel`), но в разном порядке и с разной приоритизацией. Это закрывает запрос «страница `/app/work` должна показывать реальный план работ, соответствующий типу пользователя».

---

## 5. Drilldown integrity (где врёт счётчик)

Главная находка из аудита: **«stuck leads = 12»** на дашборде ≠ «stuck leads» в `/app/leads?status=processed&next_action=stuck`.

- **Dashboard `12`:** = `opsCounters.leads_sla_stuck_stage_reminders` = active reminders типа `leads_stuck_stage` для **текущего пользователя как assignee**.
- **`/app/leads` list:** строит фильтр через `_build_lead_list_filters` с `next_action=stuck` (last stage change > stuckAfterDays, default 7), **per-tenant scope, не per-assignee**.

Это ДВЕ разные метрики с похожим названием. Пользователь нажимает «12» и получает 47 (или 3) — теряет доверие.

**Аналогичные риски** надо проверить для:
- «Overdue reminders» (mine vs tenant).
- «Candidates no_next_action» (mine vs tenant).
- «Documents missing» (mine vs tenant).
- «Open vacancies without candidates» (количество vs список).

См. §7 G-3.

---

## 6. Гэп: дублирующиеся сущности и непонятные границы

| Сущность | Где живёт | Конфуз для пользователя |
|---|---|---|
| **Reminder** vs **Planner event** | ~~Две разные таблицы, два API.~~ → **(Phase 2.1, 2026-05-09)** одна таблица `activities`, один API `/api/v1/activities`; legacy таблица `communication_planner_events` пуста для записей и ждёт DROP за soft-gate. UI всё ещё рендерит раздельно (G-7 объединил в `/app/tasks`); финальный rename — Phase 3. | «Я создал событие в календаре — почему оно не в задачах?» — закрыто на уровне модели; UI закрыт G-7 (calendar drag → reminder, common list в `/app/tasks`). |
| **`reminder_due` notification** vs **сам Reminder** | Bell показывает notification, `/app/tasks` — reminder. Закрытие в одном месте не закрывает в другом автоматически в всех путях. | «Я нажал done в bell — почему задача висит в tasks?» |
| **`Tenant.type` (DB enum: agency/company/platform)** vs **`tenant.settings.business_type` (agency/employer/services)** | Две разные системы классификации. | Маркетинг говорит «employer plan», в БД — `Tenant.type=company` + settings `business_type=employer`. → Канонизировано в `docs/specs/tenant-types.md` (Phase 2.6.A + 2.6.E). |
| **`OwnCompany`** vs **`Company` extra.company_role='operating'`** | ORM vs CRM-row-with-flag. Для UI они оба «своя компания». | Что я редактирую — юр. лицо или CRM-карточку? → Канонизировано в `docs/specs/own-company-model.md` (Phase 2.6.B). Целевое: `OwnCompany` — single-source, CRM operating-row — deprecated read-mirror. |
| **`Lead.lead_type=client`** vs обычный лид | Существует, но почти нигде не используется. | Зачем я завёл лид-клиент, если для клиента есть Companies? → Канонизировано в `docs/specs/lead-types.md` (Phase 2.6.C). Решение: оставляем + достраиваем вертикаль (NBA + UI badge + conversion-path «client lead → new client company»). |
| **`Vacancy.status` form (`paused`)** vs **list/NBA (`on_hold`)** | Form редактирует одно значение, list/badge/NBA читают другое — пользовательские действия не отражаются. | «Я поставил Paused — почему badge серый и NBA не показывает idle?» → Канонизировано и реализовано в `docs/specs/vacancy-statuses.md` (Phase 2.6.D Stage A+B+C+D+F+G): Python enum `VacancyStatus = {open, on_hold, closed, filled, cancelled}` + `normalize_vacancy_status` (alias `paused → on_hold`); shared frontend `VACANCY_STATUSES`; NBA `_VACANCY_TERMINAL_STATUS_CODES = {closed, filled, cancelled}`; alembic `202604031200_vac_status_canon` backfill `paused → on_hold` и `archived-status → is_archived=true`; **Stage D** строгая transition matrix `validate_vacancy_status_transition` (router: `ValueError → HTTP 409`); **Stage G** `archive_vacancy` синхронизирует `status='closed' + is_active=false`, убрана запись `status='archived'`. Открыт только Stage E (auto-flip on hire — UX-вопрос). |

**Не призываю немедленно сливать модели** — там много исторических причин. Призываю **в UI стереть стыки**: один экран = одна сущность, переходы между «event» и «task» — автоматические или явно объяснённые. Phase 2.6 (см. таблицу выше) фиксирует канонические контракты для будущей миграции.

---

## 7. Target state — гэпы и todo

Каждый пункт ниже — будущая работа в Phase 2 §2.5 / Phase 4 (calendar/tasks). Ссылки на todo-IDs создаются в `HOSTFLOW_AUDIT_AND_PLAN.md`.

### G-1. Lifecycle hooks для кандидата (PRIORITY 1)

При переходе кандидата в любой не-активный (`PIPELINE_COMPLETED_STAGE_CODES` + handoff/withdrew/cancelled) state — централизованный hook должен:

1. Отменить (`cancel`) все pending reminders где `entity_type=candidate` AND `entity_id=cand.id` AND `status in (new, pending, sent, overdue)`.
2. Пометить read все unread `UserNotification` где `entity_type=candidate` AND `entity_id=cand.id`.
3. Удалить из planner predicate non-cancelled события с `entity_type=candidate`/`linked_candidate_id` где `start_at >= now`.
4. Логировать в `reminder_events` причину (`auto_cancelled_due_to_candidate_stage`, новое `event_type`).

Реализация: один сервис `services/candidate_lifecycle.py` + вызов из всех точек stage-transition (`candidates/service.set_stage`, `handoff.accept`, `handoff.return`, любой bulk handler).

**Расширить `PIPELINE_COMPLETED_STAGE_CODES`** концептом «активный путь окончен» — добавить `archived`, `cancelled`, `withdrew`, `hired_elsewhere` если они используются как stage. Сейчас они валидны как stage-strings, но не подавляются.

### G-2. UI list-фильтры по lifecycle

`list_reminders`, bell-feed и planner-list должны исключать сущности на завершённом пути:

- `/api/v1/reminders` accept-параметр `include_completed_entities=false` (default), который JOIN-ит candidate и фильтрует.
- `/api/v1/notifications` тот же параметр.
- ~~`/api/v1/communications/planner/events`~~ → **(Phase 2.1)** legacy роут удалён; planner-данные теперь читаются через `/api/v1/activities`, который применяет тот же `include_completed_entities=false` фильтр (см. `app/services/candidate_lifecycle.py` — list-предикат покрывает оба domain-маркера: `entity_type='candidate'` и `metadata.planner.linked_candidate_id`).
- Рекомендация: сделать default «hide», а пользователь может включить «Show all» переключателем.

### G-3. Symmetric metric definitions (drilldown integrity)

- Создать `docs/specs/operational-metrics.md` (один файл): для каждой метрики дашборда — определение, scope (mine/tenant), точка вычисления (backend), точка отображения (frontend), canonical drilldown URL и acceptance: «список по drilldown совпадает с числом ±0».
- Тест `tests/test_metric_drilldown_consistency.py`: для каждой метрики из реестра — задёргать API, перейти по drilldown, сверить.

### G-4. Working hours respected повсюду — DONE (все 5 sub-задач; G-4.5 закрыт отдельной волной)

Foundation, reminder-shift, planner-validation и time-off-cleanup закрыты в одной волне. Comms-scheduler outbound gate (G-4.5) закрыт отдельной волной — он трогал критический dispatch-loop и заслуживал изолированного roll-out plan.

- **DONE.** `backend/app/services/working_hours_window.py::next_working_window_after(extra, after_utc)` — новый чистый helper (рядом с существующим `is_within_working_hours`/`schedule_applies`). Контракт: возвращает earliest UTC datetime ≥ `after_utc`, попадающий в enabled окно `working_hours_v1`. Если schedule пустой/disabled — возвращает `after_utc` без изменений (callers трактуют "нет расписания" как "anytime is fine"). Если уже внутри окна — возвращает unchanged (preserves seconds/microseconds). Иначе — start следующего окна (same day later, либо first window of next enabled day; walks 14 дней forward, fallback = unchanged). Локальное время через `User.extra.working_hours_v1.tz` → `ZoneInfo`; возврат всегда tz-aware UTC. Тесты `backend/tests/test_working_hours_window.py` — 13 кейсов: inside-window, before-9am-shift-to-9am, after-17-skip-to-tomorrow, weekend-skip-to-monday, no-schedule-no-op, naive-input-utc, DST winter (CET) vs CEST, multi-window same-day (split 9-12 / 14-17), tz-aware return invariant.
- **DONE.** `backend/app/services/reminder_tasks.create_reminder` — opt-in shift `due_at` через tenant setting `tenant.settings["reminders"]["shift_due_at_outside_hours"]: bool` (default OFF, чтобы не ломать существующие tenants). Когда ON: helper `_maybe_shift_due_at_to_working_hours` лукапит assignee-User → `extra.working_hours_v1` → если schedule_applies И due_at вне окна → шифт через `next_working_window_after`, и `remind_at` шифтится на тот же delta (lead-time invariant). Diagnostic stash в `Reminder.payload._working_hours_shift = {original_due_at, shifted_due_at, delta_seconds, reason: 'outside_assignee_working_hours'}` для G-10 explainability popovers — оператор видит "auto-shifted from 03:00 → 09:00" вместо misterious change. Silent no-op когда: tenant-flag OFF, нет assignee, assignee без schedule, due_at уже внутри окна. Тесты `backend/tests/test_reminder_working_hours_shift.py` — 5 кейсов через service layer (no HTTP): off-no-shift, on+outside-shifts, on+inside-no-op, on+no-schedule-no-op, lead-time preserved.
- **DONE.** Planner POST/PATCH server-side validation. Tenant setting `tenant.settings["planner"]["enforce_working_hours"]: bool` (default OFF). Schemas `CommunicationPlannerEventCreate`/`Patch` получили поле `allow_outside_hours: bool = False` (per-event override; consumed in route handler, NOT persisted on row). Helper `_assert_within_working_hours_or_overridden` в `backend/app/api/v1/communications/routes/planner.py` проверяет ОБА `start_at` И `end_at` через `is_within_working_hours` — partial-out-of-hours (16:30 → 18:30 при 9-17) ловится с `field=end_at`. Raise: HTTP 422 `{code: outside_working_hours, field, message, hint}`. Silent no-op: enforcement-flag OFF, no assignee, assignee без schedule, override=True. PATCH revalidirует только если меняются `start_at`/`end_at`/`assignee_id` (fast-path для description-only patches). Тесты `backend/tests/test_planner_working_hours_validation.py` — 7 кейсов: off-no-enforce, blocks-start-outside, blocks-end-outside-when-start-inside, passes-when-both-inside, allow-overrides, no-assignee-skips, no-schedule-skips.
- **DONE.** Time-off approved → auto-cancel reminders/planner для assignee на time-off датах. Новый сервис `backend/app/services/timeoff_cleanup.py::cancel_assignee_schedule_during_timeoff(db, *, tenant_id, assignee_id, start_date, end_date, request_id)`. Контракт: cancel ТОЛЬКО `Reminder.status == pending` (не done/cancelled — не переписываем историю) и Planner-events с `lower(status) NOT IN {done, cancelled}`. Stash `payload._cancelled_reason = 'timeoff_approved'` + `_timeoff_request_id` для audit. Date-range timezone: дата-строки `YYYY-MM-DD` интерпретируются в локальной `working_hours_v1.tz` requestera (fallback UTC) — "Mon-Fri off" = Monday 00:00 local через Saturday 00:00 local (exclusive upper для clean SQL). Wired в `decide_time_off_request` (`backend/app/api/v1/communications/routes/planner.py`) только на `decision == 'approved'` ветке; best-effort внутри `try/except` — если cleanup падает, approval всё равно коммитится, оператор узнаёт через warning-log (`[communications:timeoff] auto-cancelled schedule request=X reminders=N planner_events=M`). Тесты `backend/tests/test_timeoff_cleanup.py` — 7 кейсов: pending-cancelled-with-payload-marker, done-not-touched, outside-window-survives, planner-active-cancelled, planner-done-not-touched, cross-user-safety (A's cleanup не трогает B's row), malformed-dates-no-crash. Per-row assertions (не total-count) — другие G-4 тесты сидят reminders для того же user на той же future Monday и legitimately попадают в окно.

**G-4.5 — comms scheduler outbound gate — DONE.** `dispatch_queued_messages` (`backend/app/api/v1/communications/routes/dispatch.py`) ранее гейтил только billing + retry timing — в окно «не отправлять ночью» не смотрел. Теперь есть opt-in per-tenant gate по working hours ассignee-рекрутера треда.

Контракт:

- **Tenant flag:** `tenant.settings["communications"]["defer_outside_working_hours"]: bool` (default OFF). На pre-existing tenants — zero behavioural change, поэтому roll-out без миграций.
- **Helper:** `backend/app/api/v1/communications/_helpers/dispatch.py::_maybe_defer_outbound_for_working_hours(db, *, tenant, thread, msg, now)` — возвращает `Optional[datetime]` (deferral target или None). Silent no-op когда: флаг OFF, у треда нет `assignee_id` (некого спросить чью schedule уважать), assignee без `working_hours_v1` (консистентно с G-4 stage 2 reminder-shift — «не настроил часы — работаем anytime»), или `now` уже внутри окна. Иначе — `next_working_window_after(extra, now)` → мутирует `msg.payload.dispatch`:
  - `status: "deferred_working_hours"`;
  - `next_retry_at: <next window start UTC iso>` — используется существующий key, который `dispatch_queued_messages` уже уважает (`if next_retry_at > now_ref: continue`), **новой ветки в loop не потребовалось**;
  - `deferred_until: <same iso>` + `deferral_reason: "outside_assignee_working_hours"` + `last_deferred_at: <now iso>` + `deferred_count: N+1` для explainability (G-10) и метрик.
  - **НЕ трогает `attempt_count`/`last_error_reason`** — deferral ≠ failed retry; `_schedule_dispatch_retry` через 5 попыток помечает `delivery_status="failed"`, и смешивание deferrals с retry-failures «отваливало» бы healthy сообщения после 5 ночных попыток.
  - `delivery_status` остаётся `queued`.
- **Wire-in:** в `dispatch_queued_messages` gate вызывается ПОСЛЕ retry-timing skip (`next_retry_at > now_ref: continue`), но ДО channel-dispatch (`_dispatch_*_via_*`). На deferred ветке: `items.append(... reason="deferred_outside_working_hours", dispatched=False ...)`, `continue` — без инкремента `attempted_count` (processed-счётчик в ответе отражает только реальные попытки отправки). `body.simulate_failure=True` обходит gate (тесты не хотят reschedule'ов).
- **Manual `POST /messages/{id}/dispatch`:** НЕ тронут — если оператор явно нажал «send», его intent побеждает. Gate применяется только к batch-loop (это путь scheduler'а/email-worker'а, которые работают без оператора).
- **Roll-out:** feature-flag per-tenant + opt-in → безопасно включать per-tenant во время QA, если вылезет edge-case (например DST-граница в `working_hours_v1`), откат — `tenant.settings.communications.defer_outside_working_hours = False`.

Тесты `backend/tests/test_dispatch_working_hours_gate.py` — 8 PASSED:
- `test_tenant_flag_reader_default_off` / `test_tenant_flag_reader_opt_in_on` — reader;
- `test_no_defer_when_flag_off` — default tenant config → no-op;
- `test_no_defer_when_thread_has_no_assignee` — skip silently;
- `test_no_defer_when_assignee_has_no_schedule` — mirrors reminder-shift policy;
- `test_no_defer_when_inside_window` — 12:00 Warsaw в 9-17 → send;
- `test_defers_when_outside_and_stashes_diag` — 01:00 UTC Monday (= 02:00/03:00 Warsaw) → deferral target ≥ 09:00 local, payload.dispatch diag-block полностью проверен, `attempt_count` остаётся 0, `delivery_status` остаётся `queued`;
- `test_defer_increments_counter_on_repeat` — двойной вызов → `deferred_count=2`, `attempt_count=0`.

Регрессы (G-4 working-hours suite — `test_working_hours_window.py` 13, `test_reminder_working_hours_shift.py` 5, `test_planner_working_hours_validation.py` 7, `test_timeoff_cleanup.py` 7) — 32 passed. 8 pre-existing failures в `test_communications_access.py` (email-OAuth / flow-and-sync-cursor suite) не связаны с G-4.5 — те же кейсы красные до stash'а моих изменений.

### G-5. Manager assignment is one concept

Сейчас `manager` (string) и `recruiter_id` (FK) сосуществуют на `Candidate`. Конфуз: что главное?

- Оставить ОДИН `recruiter_id` (FK). `manager` — derived (для backward compat можно оставить view).
- Audit-trail смены: `candidate_assignee_history` table.
- Аналогично для Lead, Vacancy, Reminder.

**Canonical spec + stage plan:** `docs/specs/manager-assignment.md` (Phase 2.6.G-5).

- **DONE Stage F (Frontend → `recruiter_id` canon).** Backend: `GET /candidates` и `GET /candidates/no-next-action` теперь принимают `recruiter_id` как канонический query-param наравне с legacy `manager_id` (оба воронкуются в `filters["manager"]`; при конфликте выигрывает `recruiter_id`). PATCH `/candidates/{id}` добавил `recruiter_id` в `allowed_fields` + `_candidate_patch_side_effect_fields`; service-слой Stage-D (`record_candidate_reassignment`) уже умел сводить три имени в один канонический UUID. `CandidateOut`-схема декларирует `recruiter_id`/`recruiter_name`/`recruiter_short` — payload-ы (`_serialize_candidate_row`) эти поля всегда строили, теперь они в OpenAPI-контракте. Frontend: feature-flag `VITE_FEATURE_CANDIDATE_RECRUITER_CANON` (default ON) гейтит переключатель; `hostflow-frontend/src/modules/candidates/hooks/useCandidatesTableData.ts` и `hostflow-frontend/src/api/client.ts::listCandidatesNoNextAction` шлют `recruiter_id` вместо `manager_id`; `CandidateCard.tsx` и `Pipeline.tsx` при PATCH/bulk пишут `recruiter_id` + legacy-ключи (последние — для rollback / промежуточных deploy-состояний); новый helper `getCandidateRecruiterId` в `modules/candidates/utils.ts` стал каноническим read-helper-ом, `getCandidateManagerId` — его alias. `CandidateSnapshot` (dashboard) пополнен recruiter-triplet-ом, manager-load drill-down переключён на канонические поля. Тесты: `backend/tests/test_candidates_list_recruiter_id_filter.py` (4 signature-based теста). Out-of-scope: выпил legacy `manager_id` и hard-rename (ждёт Stage G + DROP COLUMN).
- **DONE Stage E (FK users.id ON DELETE SET NULL на owner-колонках).** Alembic-ревизия `202604190002_owner_fk_set_null` (head после `202604190001_candidate_assignee_history`). 5 колонок, которые до миграции хранили user-UUID как плоский `VARCHAR(36)` без referential integrity, теперь закрыты FK с `ON DELETE SET NULL`: `reminders.assignee_id` (`fk_reminders_assignee_id_users`), `communication_planner_events.assignee_id` (`fk_comm_planner_events_assignee_id_users`), `communication_threads.assignee_id` (`fk_comm_threads_assignee_id_users`), `document_policies.owner_user_id` (`fk_document_policies_owner_user_id_users`, + новый индекс `ix_document_policies_owner_user_id`), `candidate_profiles.owner_user_id` (`fk_candidate_profiles_owner_user_id_users`, + новый индекс `ix_candidate_profiles_owner_user_id`). Каждая из пяти колонок mirror-ится в ORM через `ForeignKey("users.id", ondelete="SET NULL")` в `backend/app/models/reminder.py`, `backend/app/models/communication.py`, `backend/app/models/document_policy.py`, `backend/app/models/candidate_profile.py`, чтобы SQLAlchemy metadata не расходилась с фактической схемой. Pre-migration orphan-sweep (`UPDATE … SET col = NULL WHERE col NOT IN (SELECT id FROM users)`) per-table выполняется ПЕРЕД `ADD CONSTRAINT`, иначе миграция упала бы на первой висящей строке (`downgrade()` cleanup **не откатывает** — NULL строго безопаснее висящего UUID). Out-of-scope в Stage E: `communication_allocation_audits.assignee_id` (forensic audit — SET NULL уничтожит трейл), `communication_messages` (колонки `assignee_id` там фактически нет — §1.1 был написан на вырост), `Candidate.manager` (уходит в `DROP COLUMN` в Stage G), `Vacancy.manager` (rename → `primary_recruiter_id` + FK одним шагом в Stage G). Round-trip `upgrade → downgrade -1 → upgrade` проходит чисто на production-шаблоне PG. Поведенческая разница: хард-удаление пользователя больше не оставляет ghost-assignee-ов в `/app/tasks`, `/app/calendar`, bell-panel, documents admin, candidate-profile admin — колонка становится `NULL`, карточка жива и доступна для re-assign. Тесты `backend/tests/test_owner_fk_set_null.py` — 5 кейсов (по одному на каждую FK), каждый изолированно создаёт user + owner-entity, хард-удаляет пользователя через `DELETE FROM users WHERE id=…` и убеждается что row жив, колонка NULL. Все 5 зелёные.
- **DONE Stage D (shadow-write `Candidate.manager` ↔ `Candidate.recruiter_id`).** Канонический writer — расширенный `record_candidate_reassignment`: в момент `candidate.recruiter_id = new_value` также пишется `candidate.manager = new_value`; на `skip_if_unchanged=True` сделан self-heal-branch для legacy drift (`manager != recruiter_id`) без спама history-строк. `bulk_update_manager` (`/api/v1/candidates/bulk/manager`) переписан с bulk `UPDATE SET manager=...` на per-candidate helper-call с `reason="manual_bulk"` — сразу решает split-brain (было: `manager` обновлён, `recruiter_id` остался стар) + эмитит audit row per candidate. `update_candidate` PATCH: `manager`/`manager_id`/`recruiter_id` слиты в единый assignment-pipeline (при конфликте выигрывает `recruiter_id`), FK-валидация user-а применяется к обеим ветвям, `changes` пишет оба поля синхронно — + history-row `manual_single` теперь эмитится и когда PATCH прислал только `manager` (раньше — беззвучный split-brain). `create_candidate_full` INSERT-time тоже shadow-write-ит (при `assignment.assigned` или при payload-manager-val с валидным user-row) + emit `candidate_create` в обеих ветках. Repo-filter `?manager=<user>` и `router.py` active-candidates list расширены на `or_(Candidate.manager == v, Candidate.recruiter_id == v)` (транзитивный — до Stage F). Inline shadow-write-ы `candidate.manager = recruiter_id` в `_processing.py` (×2) и `_reroute.py` удалены — redundant-to-helper. Тесты `backend/tests/test_candidate_manager_shadow_write.py` — 6 кейсов: happy-path mirror, unassign mirror, drift self-heal (skip_if_unchanged hit), bulk parity + history row, bulk idempotent, repo OR-filter matches `recruiter_id`-only строки. Регрессия: G-5 surface 27/27 (Stage A+B+C+D), broader sweep не поломан (failures `test_leads_meta::*`, `test_candidate_status_reason::*`, `test_candidate_stage_visibility::*` — воспроизводятся на baseline без Stage D, pre-existing sandbox DNS/data-pollution).
- **DONE Stage C (audit history table).** Добавлена append-only таблица `candidate_assignee_history` (модель `backend/app/models/candidate_assignee_history.py` + Alembic-миграция `202604190001_candidate_assignee_history`, down_revision=`202604031200_vac_status_canon`). FK на `candidates.id ON DELETE CASCADE` + `users.id ON DELETE SET NULL` для `from_user_id`/`to_user_id`/`actor_user_id`. Добавлен canonical helper `record_candidate_reassignment(db, candidate, *, new_recruiter_id, reason, actor, actor_kind, note, skip_if_unchanged, write)` в `backend/app/services/recruiter_assignment.py` — единственный write-point для `Candidate.recruiter_id` с обязательной audit-row. Константа `CANDIDATE_REASSIGNMENT_REASONS` фиксирует словарь reason-кодов (`candidate_create`, `manual_single`, `manual_bulk`, `lead_vacancy`, `lead_rule`, `lead_fallback`, `lead_reroute_vacancy`, `lead_reroute_rule`, `lead_reroute_fallback`, `admin`, `timeoff_reroute`). Обёрнутые write-точки: `create_candidate_full` (INSERT-time, `write=False`, `reason=candidate_create`), `update_candidate` PATCH (`reason=manual_single`), `_processing.py` (три ветки routing cascade), `_reroute.py` (две ветки manual re-route). `bulk_set_manager` оставлен на Stage D (сейчас пишет `Candidate.manager`, не `recruiter_id`). Тесты `backend/tests/test_candidate_assignee_history.py` — 9 кейсов: idempotent no-op, happy-path old→new, write=False INSERT-path, unassign with `to_user_id=NULL`, defensive None-guards, reason/actor_kind clamping, append-only ordering, empty-string normalisation. Регрессия: 140 passed / 2 skipped на G-5 surface.
- **DONE Stage B (canonical resolver everywhere).** Заменены оставшиеся ad-hoc vacancy-owner reader-ы на `resolve_vacancy_primary_recruiter`: (a) `backend/app/modules/leads/service/_reroute.py:201-217` — зеркало Stage A fix, manual re-route лида на другую вакансию больше не игнорирует её recruiter-пул и не проваливается в tenant-wide fallback; (b) `backend/app/services/uos_auto_activities.py:533-544` (`ensure_vacancy_recruiting_follow_up_task`) — авто-задача «Vacancy pipeline: ...» больше не назначается на admin-actor-а в случае когда vacancy имеет m2m-пул но `manager=NULL` (до Stage B падала на того, кто флипнул статус в open). Candidate.manager shadow-read в том же файле (`:158-161, :471-474`) намеренно оставлен — это exact shadow-read-аналог того, что Stage D превратит в shadow-write helper. NBA presence-check `compute_vacancy_next_action` ветка `vacancy_no_recruiter` оставлен out-of-scope: семантика там — «может ли lead-distribution сюда раздать», не pick-assignee; канонизируется отдельным NBA-polish тиклом. Тесты `backend/tests/test_uos_vacancy_follow_up_assignee.py` — 4 кейса (pool-wins-over-actor-fallback, manager-when-no-pool, actor-fallback-when-no-owner, pool-beats-manager). Регрессия: 93 зелёных (Stage A 8 + Stage B 4 + lead/NBA/bell surface 81).
- **DONE Stage A (recon + silent-dead-read fix).** Написан spec-документ с inventory всех 11 owner-полей на 8 моделях и планом stage A-G. Добавлен helper `resolve_vacancy_primary_recruiter(db, tenant_id, vacancy) → Optional[str]` (`backend/app/services/recruiter_assignment.py`) — каскад: `VacancyRecruiter` m2m least-load pick → `vacancy.manager` (валидируется что user активен в tenant) → `None`. Помогает call-site-ам, которым нужен vacancy-scoped resolver без полного `assign_recruiter` fallback-а на company-supervisor/tenant-admin. Заменён silent dead-read `getattr(vacancy, "recruiter_id", None)` в `backend/app/modules/leads/service/_processing.py:822-840` (колонка `Vacancy.recruiter_id` никогда не существовала → старый путь всегда возвращал `None` → все лиды проваливались в `MetaLeadSettings.fallback_recruiter_id` мимо пула вакансии). Поведенческая разница: лиды теперь реально получают рекрутера с вакансии, если там есть `manager` или активный пул. Тесты `backend/tests/test_vacancy_primary_recruiter_resolver.py` — 8 кейсов: vacancy=None, empty-pool-no-manager→None, manager-only→manager, active-pool-only→pool, pool+manager→pool wins, inactive-pool→manager, manager-for-inactive-user→None, manager-non-recruiter-role→still resolves.

### G-6. Per-role `/app/work`

Реализовать §4.3 — per-role layouts с переиспользованием data-panels. Acceptance: каждая из 6 CRM-ролей за UAT-прогон 2.2.C–H говорит «вижу на этой странице ровно то, что мне нужно».

**Stage 1 — DONE.** Каноник 7 профилей (`admin_solo` / `admin_team` / `supervisor` / `recruiter` / `client_manager` / `client_processor` / `viewer`) + `resolveWorkHubProfile` + `WorkHubRoleStrip` + `HandoffQueuePanel` + `WorkHubPage.tsx` рендер через `profile.sections` loop — см. `hostflow-frontend/src/modules/workHub/`.

**Stage 2 — в процессе.**

- **DONE — `MyTasksPanel` (live preview сегодняшних reminders).** `hostflow-frontend/src/modules/workHub/MyTasksPanel.tsx` — панель «что у меня на плите сегодня» в Work Hub. Всегда `assignee_scope=mine` (независимо от `profile.defaultCounterScope`) — хаб отвечает на «что _мне_ делать?», смешивать team-scope тут нельзя, иначе размоется фрейминг. Fetch: `listReminders({ assigneeScope: 'mine', dueTo: <start-of-day-after-tomorrow local>, limit: 50 })` — клиент-сайд бакеты `overdue` / `today` / `tomorrow`, статус-гейт через собственный `isClosedStatus` (зеркало `RemindersPage.isClosedReminderStatus`, чтобы не тянуть `ReminderRecord & {_source}` машинерию G-7 сюда). Backend-статус-фильтр не используется (надо подхватывать и `overdue`, и `pending`/`new` одновременно — проще фильтровать клиент-сайд). Рендер: до 3 row-ов на бакет (overdue=rose, today=amber, tomorrow=slate), overflow-row «+N more in this bucket» с deep-link на `/app/tasks?tab=tasks&filter=overdue` (для overdue) или `/app/tasks` (для сегодня/завтра). Клик на row → `/app/tasks?t_id=<reminder.id>` — используем существующий focus-by-id handler в `RemindersPage.tsx:764` (scroll into view + auto-flip status-filter если row closed). Empty state: «Nothing scheduled for today or tomorrow. Good work.» Error state: row с retry-button. Time-label: `HH:mm` для today/tomorrow, `Xm ago` / `Xh ago` / `Xd ago` для overdue. Реактивность: listener на `window.addEventListener('reminder-updated', …)` — тот же event, который диспатчит `CommunicationsCalendarPage` после drag-and-drop и который уже дёргают tick-bumper-ы G-8 NextActionBadge-хуков. Completed/snoozed в любом месте приложения → hub-preview обновляется без hard-reload. Секция `myTasks` вставлена в `profile.sections`: `admin_solo` — после `critical`; `admin_team`/`supervisor` — после `handoffQueue` (team-scope primary); `recruiter` — сразу после `hero` (personal-focus); `client_manager`/`client_processor` — после `hero` (handoffQueue первее). Viewer-profile не получает секцию (read-only). В `WorkHubPage.renderSection` ветка `'myTasks'` гейтится через `showTasks` (`can('notifications.view')`) — без permission endpoint вернул бы 403 на каждую fetch, рендер error-card хуже чем silent-skip. Frontend `tsc --noEmit -p tsconfig.app.json` + ReadLints clean.
- **DONE — `TodayPlannerPanel` (сегодня на календаре + конфликты).** `hostflow-frontend/src/modules/workHub/TodayPlannerPanel.tsx` — спутник `MyTasksPanel`: отвечает на «какие _timed events_ у меня сегодня» (meetings/calls/shifts), а не «какие у меня задачи». Сплит принципиальный — mixing их в одну 8-строчную ленту размыл бы «что в слот 14:00?» vs «что без времени, но надо сделать сегодня?». Scope: `assignee_id=me` (берётся из `useAuth().me?.id ?? me?.sub`; если id неизвестен — панель скрывается, чтобы случайно не показать tenant-wide events). Window: today-local `[start-of-day, start-of-tomorrow)`. Fetch `listCommunicationPlannerEvents({ assignee_id: myId, from_at, to_at, limit: 100 })` — backend-param `kind` single-value, поэтому фильтр `kind ∈ {meeting, call, shift}` применяется клиент-сайд (`task`/`followup` исключаются — они уже показаны в `MyTasksPanel` через reminder↔planner merge G-7, double-render путал бы «почему click на одной не закрыл вторую»). Terminal-status gate `done`/`cancelled` — зеркало `RemindersPage._PLANNER_TERMINAL_STATUSES`. DST-safety: после клиентского маппинга ещё раз валидируем `start_at ∈ [todayStart, tomorrowStart)` на случай flip-а таймзоны между fetch и render. Conflict detection — pure-client sweep-line: sort timed (non-all-day) events по `startAt`, для каждой пары `i<j` пока `b.startAt < a.endAt` → оба помечены `hasConflict=true`. All-day (часто shifts полный день) НЕ триггерит конфликт — иначе каждый meeting конфликтовал бы со сменой, false-positive. Live-badge: event в процессе (`startAt ≤ now < endAt`, timed) → emerald-тон bar + «Now» pill. Conflict → rose bar + «Conflict» pill + в header `N conflict` счётчик. Kind-icon: meetings=Users, call=Phone, shift=Briefcase. Время: `HH:mm–HH:mm` для timed, «All day» label для all-day. Max 6 row-ов + overflow-row «+N more today» → `/app/calendar`. Deep-link row → `/app/calendar` (focus-by-id не реализован в CalendarPage — см. TODO ниже; title+time+kind в row дают достаточно контекста чтобы оператор нашёл плитку на grid-е). Реактивность: planner не диспатчит собственного window event (tenant-wide bus отсутствует), поэтому listener на `'focus'` — при возврате в таб после редактирования в CalendarPage выполняется refetch; reminder-only `'reminder-updated'` сюда не нужен (панель читает только planner). Wire-in: секция `'todayPlanner'` вставлена сразу после `'myTasks'` во всех action-taking профилях (recruiter/admin_solo — перед critical, admin_team/supervisor — после handoffQueue, client_manager/client_processor — после hero); viewer не получает. `WorkHubPage.renderSection` ветка `todayPlanner` гейтится через `showTasks` (`can('notifications.view')`) — planner-endpoint за тем же ACL, что и reminders. Frontend `tsc --noEmit -p tsconfig.app.json` + ReadLints clean.
- **DONE — focus-by-id на `/app/calendar` (G-6 Stage 2f).** Query: `?event_id=<uuid>` (alias `eventId`). Семантика UUID: сначала как **planner-source row** через FE shim `getCommunicationPlannerEvent` (после Phase 2.1 — `GET /api/v1/activities/{id}` с обратным remap'ом в `CommunicationPlannerEvent`-shape; до Phase 2.1 — `GET /api/v1/communications/planner/events/{id}`), иначе как **activity/reminder id** (`GET /api/v1/activities/{id}`). Реализация: `hostflow-frontend/src/pages/CommunicationsCalendarPage.tsx` — merge fetch в `focusInjectPlanner` / `focusInjectReminder` → `plannerEventsEffective` / `remindersEffective` → `unifiedEvents`; при матче: `viewMode=day`, `selectedDay=dateKey`, курсор month/week на день, сброс фильтров источника на `all`, `scrollIntoView` на элемент `id=hf-cal-ev-<unified.id>` (day-bucket card), для planner — `activePlannerMenuId` (quick-actions), кольцо highlight ~4.5s, `replace` strip query. `TodayPlannerPanel` row-link: `/app/calendar?event_id=<planner-id>`. Backend (после Phase 2.1): `backend/app/api/v1/activities_v1.py::get_activity` + `reminder_tasks.get_reminder_for_actor`; ранее также использовался удалённый `routes/planner.py::get_planner_event`. Тесты: `backend/tests/api/test_activity_get.py` (404 smoke); `backend/tests/api/test_planner_event_get.py` удалён в `p21-be-rm` как superseded.
- **DONE — `RiskDigestPanel` (G-6 Stage 2d).** `hostflow-frontend/src/modules/workHub/RiskDigestPanel.tsx` — strip для admin/supervisor: `GET /analytics/risk-intelligence/manager-digest-queue` (`min_band=high`, `limit_buckets=14`) + тот же снимок `OpsCounters`, что уже грузит Work Hub (`ops` prop — без второго round-trip на counters). Строки: (1) unread SLA-bucket count + объём последнего unread-бакета; (2) team overdue reminders → `/app/tasks?tab=tasks&filter=overdue`; (3) stale intake proxy `leads_new_untouched_24h + draft_intake_stale` → `/app/leads?filter=no_first_contact_24h`. Primary CTA → `/app/overview` («Unblock the team — open overview»). **Wire-in:** секция `'riskDigest'` в `admin_team` и `supervisor` сразу после `todayPlanner`, перед `managerLoad`; `WorkHubPage.renderSection` ветка `'riskDigest'` гейтится как Dashboard `canViewRiskOpsUi` (`role ∈ {superadmin, administrator, supervisor}`) и получает `ops` из существующего state. Skeleton + error/retry. Frontend `tsc --noEmit -p tsconfig.app.json` + ReadLints clean.
- **DONE — `ManagerLoadPanel` (team-распределение candidates).** `hostflow-frontend/src/modules/workHub/ManagerLoadPanel.tsx` — отвечает admin/supervisor на «кто перегружен, где перераспределить». До Stage 2c этот сигнал жил только на `/app/dashboard` за widget-picker-ом (почти никто не открывал) — подняли в хаб, один скролл от hero. **Data source — `/analytics/by-manager`, НЕ `/analytics/candidate-slices`:** slices возвращает полный snapshot (one-row-per-candidate, тяжёлый для hub-preview), by-manager агрегирует на БД и возвращает одну row на `(manager_raw | recruiter_id)` — дешевле и уже сортировано `total desc + label`. Backend-patch в этой же stage: `backend/app/api/v1/analytics.py::by_manager` теперь добавляет `recruiter_id: str | None` в каждый item (до этого был только дисплей-label `manager`) — без канонического UUID frontend не мог построить deterministic drill-down URL. Legacy-rows (только `Candidate.manager` free-text, без FK) → `recruiter_id=null`, UI падает на legacy-путь. **Drill-down precedence:** `recruiter_id` → `/app/candidates?recruiter_id=<uuid>` (канонично, G-5 Stage F); fallback → `/app/candidates?manager=<label>` (матчит `useCandidatesUrlSync`, признает оба имени). **URL-sync follow-up:** `hostflow-frontend/src/modules/candidates/hooks/useCandidatesUrlSync.ts:99` раньше парсил только `manager_id`/`manager`; тут добавили `recruiter_id` в precedence (`recruiter_id || manager_id || manager`) — internal filter-state остаётся single-string `managerFilter`, backend-param переводится в canonical `recruiter_id=` уже в `useCandidatesTableData` через feature-flag. **Render:** header `Team load` + sub-line «Candidates owned by each recruiter»; до 6 rows с progress-bar (linear scale `total / max(total)`), количеством `hired` и legacy-label-warning для rows без `recruiter_id`; overflow → `/app/candidates`. **Wire-in:** секция `'managerLoad'` вставлена в `admin_team` и `supervisor` профили (только — `admin_solo` имеет одного recruiter = сам себя, recruiter/processor — personal-focus уже закрыт `MyTasksPanel`/`TodayPlannerPanel`, `client_manager` про handoffs, не про agency-team), сразу после `myTasks`+`todayPlanner` (рhythm «mine → team»). `WorkHubPage.renderSection` ветка `managerLoad` гейтится через `showCandidates` (`can('candidates.view')`) — выравнивает с drill-down target: без list-access панель не показывается. **Backend coverage:** `backend/tests/api/test_analytics_by_manager_recruiter_id.py` — два теста: (1) каждый item имеет ключ `recruiter_id` (value is null | UUID string); (2) PATCH candidate → `recruiter_id=<my-uuid>` → row с этим UUID появляется в response. Frontend `tsc --noEmit -p tsconfig.app.json` + ReadLints clean.
- **DONE — `is_solo_admin` на `GET /users/me` (G-6 Stage 2e).** `backend/app/schemas/user.py::UserMeOut` + `backend/app/services/users.py::get_user_me` — поле верхнего уровня `is_solo_admin: bool` (default `False`). Логика: `_count_active_tenant_members` — число активных не-удалённых пользователей с membership в tenant (fallback на `User.tenant_id == tenant` если membership-rows ещё не бэкфиллены); `_is_owner_class_role` — `Role ∈ {administrator, superadmin}`; `is_solo_admin = owner-class ∧ count == 1`. Frontend: `WhoAmI` / `UserMe` в `hostflow-frontend/src/api/types.ts`, merge в `store/auth.tsx` (`is_solo_admin: meEnvelope.is_solo_admin ?? false`), `useWorkHubProfile` читает `me.is_solo_admin` → `resolveWorkHubProfile({ isSoloAdmin })` выбирает `admin_solo` vs `admin_team`. Тест: `backend/tests/api/test_users_me_solo_admin.py`.
- **Следующий гейт — ручной UAT 2.2.C–H** («каждая роль говорит: вижу план дня»). Инженерная часть G-6 Stage 2 закрыта; чеклисты: `docs/specs/journeys/README.md` и файлы по персонам. Зафиксировать PASS внизу каждого journey-файла. Сводка закрытия фаз: `docs/specs/phases-2-8-engineering-closure.md`.

### G-7. Reminder ↔ Planner unification (UX-only) — DONE

Без слияния таблиц — на UI два списка ходят как один поток:

- **DONE.** Любой Planner-event с `kind ∈ {task, followup}` отображается в `/app/tasks` рядом с reminders. Реализация: `hostflow-frontend/src/pages/RemindersPage.tsx` параллелит `Promise.all([listReminders(...), listCommunicationPlannerEvents({ limit: 200, assignee_id, include_completed_entities })])` (planner-промис обёрнут в `.catch` → fallback пустой список, чтобы выпавший planner-endpoint не сломал основной поток reminders). Адаптер `plannerEventToTaskRow(event)` синтезирует `ReminderRecord & { _source: 'planner', _plannerKind }` — `start_at → due_at`, `status` маппится `planned/in_progress → pending`, `done → done`, `cancelled → cancelled` (чтобы не сломать `isClosedReminderStatus`/`bucketReminderByDue`/`compareOpenTasksBySlaThenDue`). Filtering `kind ∈ {task, followup}` — клиент-сайд (planner-endpoint принимает только single-value `kind`, два круг-трипа не оправданы для пары значений; meeting/call/shift остаются календарь-only). Status-filter (`active`/`done`) применяется client-side к planner-rows для зеркала backend-фильтра по reminders. **Visual differentiator:** на planner-rows badge "Calendar" (violet) с тултипом `From Calendar planner ({kind})` — оператору видно, что мутация уйдёт в planner-таблицу и появится в `/app/calendar`.
- **DONE (no-op — уже было).** Любой Reminder с `due_at != null` отображается в Calendar как `UnifiedCalendarEvent { source: 'reminder' }` (`hostflow-frontend/src/pages/CommunicationsCalendarPage.tsx:54-73` + reducer `:400-476` через `listActivities` — тот же DB-row, alias-API). Спек ставил это как TODO, но фактически было реализовано раньше — никаких изменений не потребовалось.
- **DONE.** Drag в календаре по reminder теперь работает наравне с planner-events. **"Новый endpoint" из спека НЕ потребовался** — `PATCH /reminders/{id}` уже принимает `due_at` (`backend/app/api/v1/reminders_v2.py:79-90, :307-326`); используем его напрямую через `updateReminder` (`hostflow-frontend/src/api/client.ts:1147`). Реализация: `movePlannerEventToDateTime` в `CommunicationsCalendarPage.tsx` обобщён через дискриминатор `event.source === 'reminder'` vs `event.source === 'planner'`. **Conflict-check `findSchedulingConflict` пропускается на reminder-ветке** — у reminders нет `end_at` (zero-duration), нет surface для overlap. Helper `isCalendarEventDraggable(event)` гейтит drag во всех трёх местах (week grid, day timeline, day buckets) — операторы тащут любую плитку независимо от source. Resize остаётся planner-only (логика длительности). После reminder-drag диспатчится `window.dispatchEvent('reminder-updated', { detail: { reminderId } })` — Topbar bell + per-entity badges (G-8 surface) подхватывают изменение без явной шины.

**Edit-modal divergence:** для planner-source `submitEdit` ходит в `patchCommunicationPlannerEvent` (а не `updateReminder`), маппит `dueAtLocal → start_at` и сохраняет оригинальную длительность через `end_at` shift. UI скрывает поле `remind_at` для planner-rows (нет аналога в planner-таблице) и переименовывает label `Due → Start`. Snooze (`+15m`/`+1h`) тоже разветвлён: для planner — это `start_at += minutes` с сохранением длительности, для reminders — родной `snoozeReminder`.

**Counts parity:** `taskCounts` (бейджи total/active/overdue/done в шапке таба) теперь считаются по объединённому `reminderRows`, а не сырому `reminders` — иначе оператор видел бы N rows в списке, но (N − planner) в счётчике. Аналогично `entityTypeOptions` собираются по объединённому списку, чтобы dropdown содержал и planner-производные `entity_type`.

**Что НЕ сделано (out of scope этого G-7):** объединение DB-таблиц reminders/planner_events, общие SLA-поля на planner-events, drag-handler для рассинхронизации reminder-row и его `entity` reminder-explainability (бейдж explainability у planner-rows опирается на reminder-popover, который не понимает planner — корректно, но minimal). Эти инкременты остаются за G-7.1 / G-7.2 если возникнут.

### G-8. Что делать дальше — единый primary CTA per entity

Каждая карточка (lead, candidate, vacancy, document, thread) обязана показывать ровно ОДИН primary CTA «следующее действие» в правом верхнем углу:

- Если есть active reminder с минимальным due_at → CTA = «Сделать: {reminder.title} (через 2 ч)».
- Иначе если NBA suggests → CTA = «{NBA.title}».
- Иначе если стадия требует контакт-attempt → CTA = «Связаться».
- Иначе явно: «Ничего не нужно: ждём ответа клиента до {sla_due_at}».

«Иначе явно» — критично. Пустота без объяснения — это «не понятно, я что-то сломал?».

**Стадия 1a (backend, кандидат) — DONE.** `backend/app/services/next_action.py` реализует `compute_candidate_next_action(...)`. Precedence фактически реализован как:
`deleted_at → terminal stage → pending handoff (с разворотом для agency vs client) → earliest active reminder → no contact attempts on pre-contact stage → idle ("nothing to do right now")`.
NBA-ветки сейчас нет — `lead_next_actions_snapshot` работает только tenant-wide (см. `_nba.py`), per-candidate NBA добавим в стадии 2 одновременно с расширением на lead/vacancy/document/thread. DTO стабилен по форме во всех 6 ветках; `reason_code` (`reminder_overdue` / `no_contact_attempt` / `terminal_stage_employed` / `handoff_pending_client_decision` / `no_signal` / …) — машиночитаемое объяснение, которое будет потреблять G-10. Endpoint `GET /api/v1/candidates/{id}/next-action`. Покрытие — `backend/tests/test_candidate_next_action.py` (16 кейсов, 16 PASSED), включая регресс-гард на cancelled reminder из G-1.

**Стадия 1b (frontend, кандидат) — DONE.** `NextActionBadge` (`hostflow-frontend/src/components/candidate/NextActionBadge.tsx`) рендерится в `CandidateHeader` рядом со `StageTag`. Цвет по `priority`, иконка по `kind`, кликабелен только когда `href` есть и `kind ∉ {idle, done, handoff_await}`. Хук `useCandidateNextAction` (`hostflow-frontend/src/components/candidate/useCandidateNextAction.ts`) — imperative (codebase без React Query), guard от race conditions через `requestSeq`, listener на `candidate-updated` window event для stage transitions, явный `bumpNextActionTick` для reminder/handoff/contact_attempt мутаций (вызывается из `CandidateCard.tsx` в 4 местах). Tooltip склеивает `title + hint + [reason_code]` — это плейсхолдер для G-10 explainability popover.

**Стадия 2 (остальные сущности).** Lead / vacancy / document / thread получают свой `compute_*_next_action`, тот же DTO, тот же frontend-компонент.

- **Стадия 2.0 — Lead — DONE.** `backend/app/services/next_action.compute_lead_next_action(...)` со ladder `terminal_stage(converted|lost) → terminal_status(failed|duplicated) → status=needs_routing → earliest active reminder (entity_type='lead') → status=new (lead_unqualified) → idle (no_signal)` и reason-кодами `terminal_stage_*`/`terminal_status_*`/`lead_needs_routing`/`reminder_due|overdue`/`lead_unqualified`/`no_signal`/`lead_not_found`/`invalid_input`. Endpoint `GET /api/v1/leads/{id}/next-action` (`backend/app/modules/leads/next_action_api.py`) — гейтится `admin/manager/recruiter/viewer`, 404 на чужого/типнутого ID; sub-router включён в `leads/router.py` ДО `/{lead_id}` чтобы Starlette не съел префикс. На фронте DTO/types подняты в общий `hostflow-frontend/src/api/nextAction.ts` (`NextActionDTO`, `NextActionKind`, `NextActionPriority`); `api/candidates.ts.CandidateNextActionDTO` оставлен алиасом для back-compat; новый `api/leads.ts.getLeadNextAction`; `components/lead/useLeadNextAction.ts` — клон candidate-хука с listener на `lead-updated` window event; `NextActionBadge` обобщён под `NextActionDTO` (без логики кандидата); `NextActionExplainabilityPopover` принимает generic DTO + добавлены fallback-объяснения для `lead_*` reason кодов и для `terminal_status_*`. Badge врезан в title-row `LeadDetailPage` (`inverse=false`); tick-bumper `bumpNextActionTick` дёргается из `handleProcess` / `handleDetailStageChange` / `confirmLostStageFromModal`. Тесты: `backend/tests/test_lead_next_action.py` — 13 кейсов (6 веток ladder + cancelled-reminder регресс-гард + unknown-lead placeholder + HTTP smoke + 404). Регрессы (`test_candidate_next_action.py` 16 + `test_reminder_bell_hygiene.py` 3) зелёные после правки `_idle_dto(entity_type=...)`. Frontend `tsc --noEmit -p tsconfig.app.json` clean.
- **Стадия 2.1 — Vacancy — DONE.** `backend/app/services/next_action.compute_vacancy_next_action(...)` со ladder `is_archived → status='closed' → earliest active reminder (entity_type='vacancy') → status='paused' (vacancy_paused, IDLE) → status='open' & ноль активных recruiter-link (vacancy_no_recruiter, CONTACT/HIGH) → idle (no_signal)` и reason-кодами `terminal_archived`/`terminal_status_closed`/`reminder_due|overdue`/`vacancy_paused`/`vacancy_no_recruiter`/`no_signal`/`vacancy_not_found`/`invalid_input`. Vacancy сегодня НЕ имеет SLA-генератора (`communications_scheduler` фаерит только лиды), поэтому `reminder` ветка сейчас покрывает только manual + UOS auto-activities — каркас готов, новые SLA-типы поедут без правок surface. Endpoint `GET /api/v1/vacancies/{id}/next-action` (`backend/app/api/v1/vacancies/next_action_api.py`) — без явного `require_roles` (паритет с `GET /vacancies/{vacancy_id}` на котором тоже нет gate); sub-router включён в `vacancies/router.py` ДО `/{vacancy_id}` чтобы Starlette не съел литерал `next-action` UUID-валидацией. Фронт: `api/vacancies.ts.getVacancyNextAction` + `VacancyNextActionDTO` (alias над `NextActionDTO`); новый хук `components/vacancy/useVacancyNextAction.ts` — клон candidate/lead-хука с listener на `vacancy-updated` window event; badge врезан в title-row `VacancyDetail.tsx` (рядом со `StageTag`, `inverse=true` потому что header — gradient white-on-brand); tick-bumper дёргается из `submitVacancy` (после save/create) и `refresh()` (manual reload). `NextActionExplainabilityPopover` дополнен fallback-кодами `vacancy_*` (`vacancy_not_found`, `terminal_archived`, `vacancy_paused`, `vacancy_no_recruiter`). Тесты: `backend/tests/test_vacancy_next_action.py` — 13 кейсов (все 6 веток ladder + cancelled-reminder регресс-гард G-1 + archived-trumps-reminder precedence-гард + inactive-recruiter негатив + unknown-vacancy placeholder + HTTP smoke + 404). Регрессы (`test_lead_next_action.py` 13 + `test_candidate_next_action.py` 16 + `test_reminder_bell_hygiene.py` 3) — зелёные. Frontend `tsc --noEmit -p tsconfig.app.json` clean.
- **Стадия 2.2 — Document — DONE.** `backend/app/services/next_action.compute_document_next_action(...)` со ladder `deleted_at → status∈{cancelled,not_required} → status=overdue (CRITICAL) → status=expired (HIGH) → earliest active reminder (entity_type='document' OR entity_type='document_step' AND entity_id like '{doc_id}:%') → status∈{missing,rejected,to_prepare,to_register,submitted,uploaded} (HIGH, per-status reason) → resolved-bucket(verified/approved/...) WITH expire_date<today (HIGH, document_expired_by_date) → resolved-bucket WITH expire_date в окне 30 дней (NORMAL, document_expiring_soon, мирорит фронтовый `EXPIRING_SOON_THRESHOLD_DAYS`) → resolved-bucket OK (DONE) → status∈{requested,in_progress} (IDLE, document_awaiting_party) → idle (no_signal)`. Reason-коды: `terminal_deleted`/`terminal_status_<status>`/`document_overdue`/`document_expired`/`document_expired_by_date`/`document_expiring_soon`/`document_missing`/`document_rejected`/`document_to_prepare`/`document_to_register`/`document_needs_verification`/`document_awaiting_party`/`no_signal`/`document_not_found`/`invalid_input`. **Важная особенность для readers:** `DocumentStatus` Python-enum имеет 20 значений, а Postgres `document_status_enum_v2` — только 11 (live: `approved`, `completed`, `delivered`, `expired`, `in_progress`, `missing`, `overdue`, `received`, `rejected`, `requested`, `submitted`). Сервисные ветки для немигрированных значений (`cancelled`, `not_required`, `verified`, `registered`, `active`, `issued`, `to_prepare`, `to_register`, `uploaded`) — defensive: код заработает в момент когда миграция расширит enum, тесты для этих веток помечены `pytest.mark.skip` с явным reason. `today` в сервисе — injectable kwarg для детерминизма тестов; production вызовы НЕ передают его. Reminder-ветка покрывает оба `entity_type` (`document` от `services/reminders.schedule_document_expiry_reminders` + `document_step` workflow-степы из того же модуля, `entity_id="{doc_id}:{step_code}"`) — иначе step-нудж был бы скрыт за doc-IDLE. Endpoint `GET /api/v1/db/documents/{id}/next-action` (`backend/app/modules/documents/next_action_api.py`) — без явного `require_roles` (паритет с `GET /db/documents/{document_id}` `api_get_document` на котором тоже нет gate); sub-router включён в `documents/router.py` ДО `@router.get("/documents/{document_id}")` чтобы Starlette не съел префикс. **Soft-delete:** endpoint НЕ фильтрует `deleted_at IS NOT NULL` — сервис возвращает `terminal_deleted` DTO для удалённых, что честнее чем 404 (строка ещё в БД). Фронт: `api/documents/nextAction.ts.getDocumentNextAction` (использует `docsApi` который ходит на `/api/v1/db`) + `DocumentNextActionDTO` (alias над `NextActionDTO`); новый хук `components/document/useDocumentNextAction.ts` — клон candidate/lead/vacancy-хука с listener на `document-updated` window event и поддержкой `string | number` refreshKey (для doc fingerprint без отдельного tick-bumper). Badge врезан в `modules/documents/components/DocumentCard.tsx` рядом со status pill — **только для `variant=full`**, в `compact` скрыт (плотный list view, нет горизонтального места). Refresh идёт автоматически через fingerprint `${doc.status}|${doc.expire_date}|${doc.deleted_at}|${doc.has_files}` — без правок в `CandidateDocuments.tsx`. **Перф-нота:** одна `useDocumentNextAction(id)` per `DocumentCard`, для типичного N≤20 doc/candidate приемлемо; escape hatch (bulk endpoint) описан в JSDoc хука. `NextActionExplainabilityPopover` дополнен fallback-кодами `document_*` (12 reason-кодов, `terminal_deleted` переиспользует candidate-fallback, читается generic). Тесты: `backend/tests/test_document_next_action.py` — 19 active + 2 skipped (skip = не-мигрированные enum значения, документировано в файле). Покрытие: soft-delete (branch 1), HIGH-priority statuses (branch 6, 3 кейса для DB-valid + drop для немигрированных), overdue/expired (branches 3-4), reminder ветка (3 кейса: future/overdue/document_step + cancelled-reminder регресс-гард G-1), resolved×expire matrix (4 кейса: expired_by_date/expiring_soon/far/none), awaiting bucket (2 кейса), defensive (unknown doc), HTTP smoke + 404. Регрессы (`test_vacancy_next_action.py` 13 + `test_lead_next_action.py` 13 + `test_candidate_next_action.py` 16 + `test_reminder_bell_hygiene.py` 3) — зелёные (45 active + 2 skipped в текущем сете запусков, итого 64 active passed). Frontend `tsc --noEmit -p tsconfig.app.json` clean. ReadLints clean.
- **Стадия 2.3 — Thread — DONE.** `backend/app/services/next_action.compute_thread_next_action(...)` со ladder `is_archived (DONE, terminal_archived) → status.lower()='deleted' (DONE, terminal_status_deleted) → status.lower()∈{closed,resolved} (DONE, terminal_status_*) → sla_due_at<now (CONTACT/CRITICAL, thread_sla_overdue) → earliest active reminder (entity_type='communication_thread') → unread_count>0 (CONTACT/HIGH, thread_unread_inbound) → last_inbound_at>last_outbound_at (CONTACT/NORMAL, thread_awaiting_reply) → sla_due_at в окне 30 мин (CONTACT/NORMAL, thread_sla_due_soon) → status.lower()∈{snoozed,pending} (IDLE, thread_<status>) → idle (no_signal)`. Reason-коды: `terminal_archived`/`terminal_status_<status>`/`thread_sla_overdue`/`reminder_due|overdue`/`thread_unread_inbound`/`thread_awaiting_reply`/`thread_sla_due_soon`/`thread_<snoozed|pending>`/`no_signal`/`thread_not_found`/`invalid_input`. **Особенность:** `CommunicationThread.status` — **free `String(32)` колонка** с дефолтом `"open"`, а не Enum. Фронт сегодня распознаёт только `status.lower()=='deleted'` как terminal (`CommunicationsInboxCenterPage.tsx`). Сервис defensively добавляет `closed`/`resolved` (нет в live data) и `snoozed`/`pending` (приходят через `thread_meta.sla_policy` в patch_thread) — все на нижнем регистре, `status.strip().lower()`. **SLA источник истины:** прямое чтение `thread.sla_due_at` (не зависит от того, выстрелил ли уже scheduler-evictor `_run_sla_escalations_for_tenant` reminder с `entity_type='communication_thread'` и `type='communications_sla_overdue'`) — SLA breach surface'ится корректно даже до задержки scheduler'а. Reminder ветка ловит и SLA-эвакуированные, и manual reminders по тому же entity_type. **Unread vs awaiting_reply:** `unread_count>0` HIGH (срочно: даже не открыл), `last_inbound>last_outbound` NORMAL (открыл, не ответил). Двойная вилка — иначе read-but-not-replied нити уходили бы в IDLE после ручного "mark as read". Threshold `_THREAD_SLA_DUE_SOON_MINUTES=30` — половина типичного channel-SLA окна (60-180 мин per `services/communications/_helpers/sla.py`). `now` — injectable kwarg для тестов; production вызовы не передают. Endpoint `GET /api/v1/communications/threads/{thread_id}/next-action` (`backend/app/api/v1/communications/routes/threads_next_action.py`) — гейтинг **полностью зеркалит `GET /communications/threads/{thread_id}` `get_thread`** (tenant exists → thread exists → own_company scope `_ensure_thread_matches_own_company_scope` → channel-feature gate `assert_comm_feature_access(_feature_for_channel(thread.channel))`). Sub-router включён в `communications/__init__.py` смежно с `_threads_routes` (порядок не важен — у пути 2 segments после `/threads/`, `/{thread_id}` не может алиасить). Фронт: `api/communications/nextAction.ts.getThreadNextAction` (использует общий `api` client, baseURL `/api/v1`) + `ThreadNextActionDTO` (alias над `NextActionDTO`); новый хук `components/communications/useThreadNextAction.ts` — клон document-хука с listener на `thread-updated` window event и поддержкой `string|number` refreshKey. Badge врезан в `CommunicationsThreadWorkArea.tsx` для **обоих layouts** (`inboxCenter` — компактный header, `page` — full meta-row), рядом со status. Refresh fingerprint: `${status}|${is_archived?1:0}|${unread_count}|${sla_due_at}|${last_inbound_at}|${last_outbound_at}` — покрывает каждое поле, которое читает backend ladder, без правок в parent компонентах. `NextActionExplainabilityPopover` дополнен `thread_*` reason-кодами; `terminal_archived` обобщён ("Archived — no further action.") т.к. share между vacancy и thread, `terminal_deleted` переиспользует candidate-fallback, `terminal_status_*` ложится через `defaultExplanationFor`. Тесты: `backend/tests/test_thread_next_action.py` — **21 active кейс**: archived-trumps-everything precedence (regression guard), status_deleted (case-insensitive), closed/resolved parametrize, sla_overdue CRITICAL, reminder ветка (future/overdue/cancelled-G1-guard), unread (1/N + trumps-awaiting precedence), awaiting_reply (3 кейса: inbound>outbound / inbound only / outbound>inbound негатив), sla_due_soon (15 мин + far-future негатив), idle statuses (snoozed/pending), unknown thread, HTTP smoke 404. **Тест `_NOW`** anchored к real `datetime.now(timezone.utc)` (не historical date) — `_priority_from_due` сравнивает с реальным now, и historical anchor выводил бы reminder в CRITICAL. Регрессы (`test_document_next_action.py` 19+2skip + `test_vacancy_next_action.py` 13 + `test_lead_next_action.py` 13 + `test_candidate_next_action.py` 16 + `test_reminder_bell_hygiene.py` 3) — зелёные. **Итого по next-action surface: 85 active passed + 2 skipped.** Frontend `tsc --noEmit -p tsconfig.app.json` clean, ReadLints clean.

### G-9. Bell hygiene

- Убрать дубли `reminder_due` notification если соответствующий reminder уже в bell (или наоборот).
- Группировать `reminder_due` по entity (3 reminders по одному кандидату → 1 строка с раскрытием).
- Иконка bell должна светиться ТОЛЬКО для actionable (assignee=me, не read, не cancelled, candidate.stage active).

**Статус — DONE.** Сделано в три удара:

1. **Backend — bell перестаёт ныть, как только пользователь среагировал в `/app/tasks`.** Новый helper `services/user_notifications.mark_reminder_bell_notifications_read(reminder, reason)` находит все unread `reminder_due` / `reminder_overdue` `UserNotification`-строки, payload которых указывает на этот `reminder.id` (по полю `reminder_id` или подстроке в `dedupe_key`), и помечает их read. На прочитанные строки кладётся `payload.auto_closed = {reason: "reminder_completed|reminder_snoozed", at: <ts>}` — explainability сохраняется. Хук вызывается из `services/reminder_tasks.complete_reminder` и `snooze_reminder` (cancel-on-terminal уже покрыт G-1 через `_mark_candidate_notifications_read`). Тесты — `backend/tests/test_reminder_bell_hygiene.py` (3 кейса: complete, snooze, изоляция «соседнего» reminder).
2. **Frontend — bell drawer группирует reminder-строки по entity.** `Topbar.unifiedPanelRows` обогащён вариантом `notif_group { key, representative, items, count }`: все `reminder_due` / `reminder_overdue` items, у которых одинаковая пара `(entity_type, entity_id)` и оба заполнены, схлопываются в одну строку с бейджем «×N» и кнопкой «Clear all (N)» (вызывает `markNotificationsRead({ ids: <все ids группы> })`). Один reminder на сущность остаётся обычной `notif`-строкой — никакого визуального шума. Локали добавлены: `app.topbar.notifications.reminder_group_title` и `clear_group` (en/ru/pl).
3. **Frontend — badge считает строки, а не raw items.** В `fetchCount` итоговый `bellBadgeCount = allowedUnreadThreads.length + countNotifPanelRowsGrouped(dedupedUnreadNotifs)`. Helper `countNotifPanelRowsGrouped` использует ту же логику группировки, что и drawer, поэтому число на колокольчике точно равно тому, что пользователь увидит при клике (parity badge ↔ panel).

Не делалось дополнительно (намеренно, чтобы не раздуть PR): strict-by-key dedupe в `create_notification` — у `deliver_due_reminders` есть `Reminder.sent_at IS NULL` фильтр, поэтому одна и та же строка reminder-а второй раз не выстреливает. Когда появятся реальные кейсы повторных fire (rescheduling, multi-channel), вернёмся.

### G-10. Кнопка «Показать почему этот reminder» / explainability

На каждом reminder в `/app/tasks` — крошечная иконка «?» открывает popover «откуда этот reminder»:
- `Тип: leads_stuck_stage`
- `Создан: SLA scheduler 2026-04-19 09:14`
- `Источник: leads_next_action_sla_v1.stuckAfterDays=7`
- `Кандидат/лид: link`
- `Ссылка на политику: /app/settings/communications/sla`

Это снимает ощущение «продукт сам что-то делает за моей спиной».

**Статус — DONE.** Универсальный примитив `hostflow-frontend/src/components/explainability/ExplainabilityPopover.tsx` (свой минимальный popover — codebase без Radix/Headless/Floating UI: click-toggle, click-outside / Escape для закрытия, `<ExplainabilityRow>` для пар label/value/href). Два consumer:
- `ReminderExplainabilityPopover` (Type / Source / Created / Created by / Due / SLA deadline / SLA status / Linked entity / Policy — defensive чтение `payload`, fallback на полевые источники для `source`) — врезан в строку `/app/tasks` сразу после ссылки «Open entity».
- `NextActionExplainabilityPopover` (Kind / Priority / Reason code / Due + переведённое объяснение по `reason_code`, fallback bake-in для всех 8 кодов; `terminal_stage_*` склеены в один key с value `{stage}`) — рендерится sibling-элементом рядом с `NextActionBadge` на CandidateHeader, чтобы не ломать click-target самого badge.

Это также покрывает «explainability» для G-8 — оператор видит «почему именно эта рекомендация» прямо рядом с CTA.

---

## 8. Acceptance — операционный позвоночник работает

Считаем, что позвоночник «починен», если:

1. **Зеро-leak:** UAT-прогон отклоняет 5 кандидатов и 5 завершает hire → bell + tasks + calendar мгновенно (≤ 1 sec) НЕ показывают ничего по этим кандидатам. Баг G-1 закрыт.
2. **Drilldown integrity:** все числа на дашборде ведут на список с тем же количеством элементов (±0). Бэкенд-тест G-3 зелёный.
3. **Per-role хаб:** каждая из 6 CRM-ролей в UAT-прогоне говорит «вижу свой план дня». G-6 закрыт.
4. **Working hours:** уведомления / звонки / push-сообщения не приходят ночью локального времени assignee. G-4 закрыт.
5. **Bell hygiene:** колокольчик светится ≤ N раз в день для recruiter в среднем рабочем дне (метрика).
6. **Один primary CTA per карточке:** аудит показывает 100 % покрытия. G-8 закрыт.

---

## 9. Что делать в коде, чтобы дойти до §8

Порядок предложен:

1. **G-1 + G-2** одной волной — это самый громкий баг, фиксится за 2-3 дня.
2. **G-3** — каноник `operational-metrics.md` + тест → день.
3. **G-8** — primary CTA contract на 5 типах карточек → 3-4 дня (затрагивает компоненты).
4. **G-6** — per-role `/app/work` → 4-5 дней (но половина этого — UAT-прогоны 2.2.C–H, которые мы и так делаем).
5. **G-9** — bell hygiene → 2 дня.
6. **G-4** — working hours respected (большой по охвату, но низкий риск) → 5-7 дней. **DONE** (все 5 sub-задач, вкл. G-4.5 comms scheduler outbound gate — opt-in per-tenant setting `communications.defer_outside_working_hours`, gate в `dispatch_queued_messages` перед channel-dispatch, deferrals НЕ трогают `attempt_count` чтобы не отваливать healthy сообщения после 5 ночных попыток, manual `/messages/{id}/dispatch` не тронут — оператор intent побеждает).
7. **G-7** — reminder/planner UX unification → 3-5 дней.
8. **G-10** — explainability tooltip → 1 день.
9. **G-5** — manager → recruiter_id consolidation → Stage A+B+C+D+E+F готовы (spec + resolver helper + оба silent-dead-read fix-а + uos auto-follow-up canon + `candidate_assignee_history` audit-table + helper `record_candidate_reassignment` с shadow-write invariant + bulk/patch/insert/repo переведены на canonical writer + FK `users.id ON DELETE SET NULL` на 5 owner-колонках reminder/planner/thread/document_policy/candidate_profile + backend `?recruiter_id=` canonical query-param на обоих list endpoints + PATCH `allowed_fields` расширен + `CandidateOut` декларирует recruiter-triplet + FE под feature-flag `VITE_FEATURE_CANDIDATE_RECRUITER_CANON` шлёт `?recruiter_id=` и `{ recruiter_id, manager, manager_id }` на PATCH/bulk), остаётся только G (destructive `DROP COLUMN candidates.manager` + `RENAME Vacancy.manager → primary_recruiter_id` — после ≥ 7 дней стабильности shadow-write в prod) — см. `docs/specs/manager-assignment.md` §4.
