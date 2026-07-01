# Manager Assignment — один концепт «кто ответственный»

**Назначение:** один справочник по полям «кому принадлежит / за кем закреплено» на всех entity-ах HostFlow (Candidate, Vacancy, Lead, Reminder, Planner, Thread, Company, Document) — как сегодня, какие конфликты, и каким должен быть канонический набор полей.

**Связанные документы:**

- `docs/specs/operations-loop.md` §G-5 (формулировка проблемы на верхнем уровне).
- `docs/HOSTFLOW_AUDIT_AND_PLAN.md` §2.5.G5 (план Phase 4, закрываемый этим документом).
- `docs/specs/vacancy-statuses.md` (образец «канонический enum + stage-wise migration», тот же паттерн применяется здесь).
- `backend/app/services/recruiter_assignment.py::assign_recruiter` (канонический роутер «кому назначить кандидата» — сохраняется).

**Краткое решение:**

- Канонический owner-FK на каждом entity: **`recruiter_id`** (Candidate, Lead) / **`manager`** (Vacancy, до stage F) / **`assignee_id`** (Reminder, Planner event, Communication thread/message) / **`owner_user_id`** (Company, DocumentPolicy, CandidateProfile).
- Все owner-колонки становятся **полноценными FK → `users.id` ON DELETE SET NULL** (сегодня часть из них — плоские `String` без ограничений).
- `Candidate.manager` **устраняется**: после миграции остаётся только `Candidate.recruiter_id`. UI-фильтр «Менеджер» переключается на `recruiter_id`, derived-поле `manager_short/manager_name` продолжает выдаваться через `users.id → users.short_id/full_name`.
- `Vacancy.manager` остаётся как primary-owner вакансии (single), `VacancyRecruiter` m2m — как пул для round-robin. Canonical resolver — `assign_recruiter`.
- Аудит-трейл переназначений: новая таблица `candidate_assignee_history` (append-only, `candidate_id, from_user_id, to_user_id, reason, actor_id, changed_at`).

---

## 1. Сегодняшняя модель (inventory)

### 1.1. Owner-поля на entity-ах

| Entity | Поле | Тип в БД | FK | Индекс | Роль |
|---|---|---|---|---|---|
| `Candidate` | `recruiter_id` | `String(36)` | **да** → `users.id` ON DELETE SET NULL | да | Канонический владелец (используется NBA, notifications, routing) |
| `Candidate` | `manager` | `String` (без длины) | **нет** (хранит user-UUID, но без FK) | да | **Дубль** — используется UI-фильтром «Менеджер», bulk-set-manager, вакансия-job-board |
| `Vacancy` | `manager` | `String` (без длины) | **нет** (хранит user-UUID, но без FK) | да | Primary-owner вакансии (single) |
| `Vacancy` | `recruiter_links` (m2m `VacancyRecruiter`) | FK `user_id → users.id` (в отдельной таблице) | да | да | Пул рекрутеров для round-robin; `weight`, `last_assigned_at` |
| `Lead` | **нет** (не хранится на строке) | — | — | — | Лид не имеет owner-а напрямую; назначение считается в момент конверсии в candidate (`_processing.py`) |
| `MetaLeadSettings` | `fallback_recruiter_id` | `String(36)` | **да** → `users.id` ON DELETE SET NULL | — | Tenant-wide дефолт «если не нашли никого — назначить этого» |
| `Reminder` | `assignee_id` | `String(36)` | **нет** (без FK) | нет | Операционный assignee (кому делать reminder) |
| `CommunicationPlannerEvent` | `assignee_id` | `String(36)` | **нет** (без FK) | да | Assignee календарного блока |
| `CommunicationThread` / `CommunicationMessage` | `assignee_id` | `String(36)` | **нет** (без FK) | да | Владелец треда/сообщения |
| `Company` | `owner_user_id` | `String(36)` | **нет** (без FK, см. `backend/app/models/company.py:28`) | нет | Основной ответственный по клиентской компании |
| `DocumentPolicy` | `owner_user_id` | `String(36)` | **нет** (без FK, см. `backend/app/models/document_policy.py:144`) | — | Владелец документа |
| `CandidateProfile` | `owner_user_id` | `String(36)` | **нет** (без FK, см. `backend/app/models/candidate_profile.py:96`) | — | Владелец профиля |

> 11 owner-полей на 8 моделях, **минимум 3 разных имени** (`recruiter_id`, `manager`, `assignee_id`, `owner_user_id`), **минимум 4 из 11 без FK** — референциальная целостность держится за счёт application-кода.

### 1.2. Конфликты и silent-bugs на сегодняшней модели

1. **`Candidate.manager` vs `Candidate.recruiter_id` — split-brain.** Оба хранят user-UUID, оба считаются «канон» разными участками кода:
   - `backend/app/api/v1/candidates/repo.py:507-509` — фильтр `?manager=` ходит в `Candidate.manager`.
   - `backend/app/services/next_action.py`, notifications, lead-processing — читают `Candidate.recruiter_id`.
   - `backend/app/modules/leads/service/_processing.py:845-846` — вручную синхронизирует одно в другое, но только на ветке `meta-lead → candidate conversion`. Все остальные точки записи (например `bulk_set_manager` — `backend/app/api/v1/candidates/service.py:1719`) пишут **только в `manager`**, `recruiter_id` остаётся устаревшим → UX-bug «назначил менеджера, но NBA/notifications считают старого».

2. **Silent dead-read `vacancy.recruiter_id`.** `backend/app/modules/leads/service/_processing.py:826, 831` делает `getattr(vacancy, "recruiter_id", None)` — у `Vacancy` такой колонки **не существует**, получается всегда `None`. Результат: все лиды, прошедшие этот путь, **пропускают** «взять рекрутера с вакансии» и валятся в tenant-wide `fallback_recruiter_hint`. Backlog: резолвить через `assign_recruiter` (которая умеет least_load + vacancy_owner) или через приватный vacancy-scoped resolver.

3. **`Reminder.assignee_id` / Planner / Threads без FK.** Удалённый user оставляет «сиротские» записи, которые показываются в `/app/tasks`, `/app/calendar`, bell, но при клике «открыть профиль assignee» падают. Сейчас закрывается application-логикой в `backend/app/services/comms_consistency.py` и ручной чисткой.

4. **`Vacancy.manager` vs `VacancyRecruiter` m2m — два разных смысла на одной сущности.**
   - `Vacancy.manager` — «кто отвечает за вакансию в целом» (primary).
   - `VacancyRecruiter` — «кого можно назначить кандидату на эту вакансию» (pool).
   - Канонический resolver `assign_recruiter` (`backend/app/services/recruiter_assignment.py:227-310`) уже совмещает их правильно: `least_load` через m2m → `vacancy_owner` через `manager` → `company_supervisor` → `tenant_admin`. **Оставляем как есть**, только оформляем stage-F как explicit contract.

5. **`owner_user_id` / `manager` / `assignee_id` — три имени одного понятия.** Сейчас это терпимо (разные сущности), но усложняет UI и доки. Stage F предлагает **публично** нормализовать на два имени:
   - `owner_user_id` — для «данных» (Company/Document/Profile — долгоживущая принадлежность)
   - `assignee_id` — для «действий» (Reminder/Planner/Thread — операционная работа)
   - `recruiter_id` — для «процесса» (Candidate/Lead — кто ведёт этого человека)
   - `manager` (строка) — **удалить из `Candidate`**, оставить только на `Vacancy` как краткое имя primary-owner-а (а потом, в stage G, переименовать в `primary_recruiter_id` для терминологической чистоты).

### 1.3. Что уже работает правильно (не трогаем)

- `assign_recruiter` (`backend/app/services/recruiter_assignment.py`) — канонический «кому назначить кандидата», корректно использует m2m + vacancy.manager + company-supervisor + tenant-admin с round-robin по least-load. Этот resolver **единственная точка истины**, которую будем переиспользовать во всех местах, где сегодня есть ad-hoc логика.
- `MetaLeadSettings.fallback_recruiter_id` — уже FK, семантика ясная («tenant-wide дефолт, когда никто не подошёл»). Остаётся.
- `VacancyRecruiter` — правильно спроектированная m2m с `weight`, `is_active`, `last_assigned_at`. Остаётся.

---

## 2. Целевая модель

### 2.1. Канонические имена полей

| Смысл | Канон | Где |
|---|---|---|
| «Кто ведёт человека» (процесс) | `recruiter_id` | Candidate, (future) Lead |
| «Primary-ответственный за вакансию» | `primary_recruiter_id` (был `manager`) | Vacancy |
| «Пул рекрутеров вакансии» | `recruiter_links` (m2m `VacancyRecruiter`) | Vacancy |
| «Кому делать действие» (операционный assignee) | `assignee_id` | Reminder, Planner event, Communication thread/message |
| «Кому принадлежит данные» (владение) | `owner_user_id` | Company, DocumentPolicy, CandidateProfile |
| Tenant-wide дефолт routing-а | `fallback_recruiter_id` | MetaLeadSettings |
| Аудит-трейл переназначений кандидата | `candidate_assignee_history` (новая таблица) | — |

### 2.2. Канонический resolver

Единственный путь «посчитать кому назначить кандидата» — `backend/app/services/recruiter_assignment.py::assign_recruiter(db, tenant_id, vacancy_id, company_id) -> AssignmentDecision`. Все call-site-ы, где сегодня есть ad-hoc ветвление («посмотри `vacancy.recruiter_id`, иначе `fallback`»), переключаются на этот resolver.

Для узкой задачи «только vacancy-scope, без company-supervisor / tenant-admin fallback-ов» вводится публичный helper **`resolve_vacancy_primary_recruiter(db, tenant_id, vacancy) -> Optional[str]`** в том же модуле. Возвращает ровно одно из:

- `least_load` pick из `VacancyRecruiter` m2m (если пул непустой);
- `vacancy.manager` (если вакансия без пула, но primary-owner задан);
- `None` — даёт caller-у возможность самому решить, чем fallback-ить (например, `MetaLeadSettings.fallback_recruiter_id`).

Этот helper заменяет silent-dead `getattr(vacancy, "recruiter_id", None)` в lead-processing.

### 2.3. Candidate.manager устраняется

**Stage F:** UI-фильтр «Менеджер», bulk-set-manager, `candidates/repo.py` фильтрация — переключаются на `Candidate.recruiter_id`. Колонка `Candidate.manager` **остаётся в БД** в режиме shadow-write: любая запись в `recruiter_id` также пишет в `manager` (для back-compat с внешними intgrations, если такие есть).

**Stage G:** миграция backfill-ит `recruiter_id = COALESCE(recruiter_id, manager)` где `recruiter_id IS NULL`. Затем `DROP COLUMN candidates.manager`. Shadow-write снимается. Backend читает derived `manager_short/manager_name` через join `users.id = candidates.recruiter_id`.

### 2.4. FK на все owner-колонки

Все 11 owner-колонок из §1.1 должны быть `FOREIGN KEY → users.id ON DELETE SET NULL` после миграций. Отсутствие FK — техдолг из ранних миграций, закрывается в stage E.

### 2.5. Аудит-трейл: `candidate_assignee_history`

Новая таблица (append-only, без updates):

```
candidate_assignee_history
  id              String(36)     PK
  tenant_id       String(36)     NOT NULL, index
  candidate_id    String(36)     NOT NULL, index, FK → candidates.id ON DELETE CASCADE
  from_user_id    String(36)     nullable, FK → users.id ON DELETE SET NULL
  to_user_id      String(36)     nullable, FK → users.id ON DELETE SET NULL
  reason          String(32)     NOT NULL   -- manual_bulk|lead_processing|rule|timeoff_reroute|admin|...
  actor_user_id   String(36)     nullable, FK → users.id ON DELETE SET NULL  -- кто инициировал
  actor_kind      String(16)     NOT NULL default 'user'  -- user|system|automation
  note            Text           nullable
  changed_at      DateTime(tz)   NOT NULL default now()
```

Все точки записи `Candidate.recruiter_id` оборачиваются в helper `record_candidate_reassignment(db, …)` который пишет историю и применяет изменение в одной транзакции. Помогает:

- G-8 explainability popover — «откуда этот assignee».
- Команда поддержки — «почему кандидата забрали у Ани».
- Аналитика load balancing / routing quality.

### 2.6. Что НЕ делаем в G-5

- Не трогаем `Candidate.owner_user_id` стиль на Lead (лид остаётся без owner-колонки на строке — owner всегда resolvable через vacancy/rules/fallback).
- Не объединяем `assignee_id` и `recruiter_id` в одно поле — у них разный смысл (операционный vs процессный).
- Не переименовываем `Company.owner_user_id` / `Document*.owner_user_id` — уже канон, правильное имя, меняем только FK-constraint.

---

## 3. Acceptance criteria (по завершении G-5 wave)

1. **Один канон на entity.** Нет точек записи `Candidate.manager` вне shadow-write helper-а; UI-фильтр «Менеджер» ходит в `recruiter_id`.
2. **Нет silent-dead-read-ов.** `vacancy.recruiter_id` не упоминается нигде в коде; все call-site-ы используют либо `assign_recruiter`, либо `resolve_vacancy_primary_recruiter`.
3. **Все owner-колонки — FK.** Альтер-миграции для `Reminder.assignee_id`, `CommunicationPlannerEvent.assignee_id`, `CommunicationThread.assignee_id`, `CommunicationMessage.assignee_id`, `Company.owner_user_id`, `DocumentPolicy.owner_user_id`, `CandidateProfile.owner_user_id` добавляют FK `→ users.id ON DELETE SET NULL`.
4. **Audit trail.** `candidate_assignee_history` существует и пишется из всех точек изменения `Candidate.recruiter_id` (minimum 5 call-sites: `bulk_set_manager`, `update_candidate`, lead-processing rules, lead-processing fallback, `assign_recruiter` endpoint).
5. **Контракт для Vacancy.** `Vacancy.manager` переименована в `primary_recruiter_id`; добавлен FK. Legacy-alias `manager` остаётся принимаемым в API-schemas (BC), маппится на `primary_recruiter_id` на входе/выходе.
6. **Тесты.** В `backend/tests/test_manager_assignment.py` и `backend/tests/test_candidate_assignee_history.py` покрыты: shadow-write parity (stage D), resolver fallback matrix (stage B), history row on each mutation path (stage C), FK constraint rejection (stage E).
7. **Docs.** Этот документ обновлён с прогрессом по каждой stage (`**DONE** — детали`).

---

## 4. План исполнения (stage A-G)

Паттерн тот же, что в `docs/specs/vacancy-statuses.md` §6.

### Stage A — Recon + spec doc + silent-dead-read fix

**DONE (этот документ, wave 1).**

- Написан canonical spec doc (`docs/specs/manager-assignment.md`).
- Добавлен helper `resolve_vacancy_primary_recruiter(db, tenant_id, vacancy) → Optional[str]` в `backend/app/services/recruiter_assignment.py`. Возвращает: round-robin pick из `VacancyRecruiter.is_active` m2m → `vacancy.manager` (валидируется что user активен в tenant) → `None`. **Не фоллбечит** на company-supervisor / tenant-admin — эту семантику оставляем за полноценным `assign_recruiter` (call-site сам решает, хочет ли дополнительный fallback).
- Переписан silent-dead path в `backend/app/modules/leads/service/_processing.py:822-840`: вместо `getattr(vacancy, "recruiter_id", None)` теперь `await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)`. Поведенческая разница — лиды, у которых у вакансии есть назначенный `manager` или активный `VacancyRecruiter`-пул, теперь реально получают рекрутера с вакансии вместо проваливания в `MetaLeadSettings.fallback_recruiter_id`.
- Тесты `backend/tests/test_vacancy_primary_recruiter_resolver.py` — резолвер: empty-pool-no-manager→None, manager-only→manager, active-pool-only→pool pick, pool+manager→pool wins, inactive-pool→manager, manager-for-inactive-user→None.

### Stage B — Canonical resolver everywhere

**DONE.**

Заменены все ad-hoc vacancy-owner reader-ы, обнаруженные в recon Stage A (`manager-assignment.md` §1.2), на `resolve_vacancy_primary_recruiter`. Audit показал **два** оставшихся vacancy-scoped call-site-а (помимо уже закрытого `_processing.py` в Stage A); остальные `candidates/service.py:466`, `recruiters/router.py:37-52` уже используют канонический `assign_recruiter` (Stage B no-op для них).

- **`backend/app/modules/leads/service/_reroute.py:201-217`** — зеркало Stage A fix: старое `getattr(target_vacancy, "recruiter_id", None) if target_vacancy else None` читало несуществующую колонку (всегда None), из-за чего любая manual re-route лида на другую вакансию **игнорировала** её recruiter-пул и проваливалась в `MetaLeadSettings.fallback_recruiter_id`. Теперь `await resolve_vacancy_primary_recruiter(db, tenant_id, target_vacancy)` резолвит pool → manager → None ДО `create_candidate_full` (чтобы не словить `MissingGreenlet` после внутреннего commit-а ORM).

- **`backend/app/services/uos_auto_activities.py:533-544`** (`ensure_vacancy_recruiting_follow_up_task`) — старый код читал ТОЛЬКО `getattr(vacancy, "manager", None)` и падал в `actor_id` (часто админ, который флипнул `status=open`), если `manager=NULL`. При этом VacancyRecruiter m2m-пул уже был заполнен через UI "рекрутеры на вакансию" → авто-задача «Vacancy pipeline: ...» падала на админа, а не на рекрутера-владельца сорсинга. Теперь тот же resolver: pool → manager → `act`. Специально **оставлен `act`-fallback на самом дне**, чтобы не оставить напоминание orphan-ным когда вакансия создана без owner-а — Reminder.assignee_id NOT NULL по контракту `create_reminder`.

- **Out-of-scope Stage B (оставлено сознательно):** `backend/app/services/next_action.py:612-620` (`compute_vacancy_next_action` ветка `vacancy_no_recruiter`) делает **presence-check** «можно ли раздать сюда candidates lead-distribution-ом», а не pick-assignee. Семантика другая: lead-distribution (`_prepare_vacancy_pool`) фильтрует по `role=recruiter` И `users.is_active=True`, а resolver-резултат-not-None будет true-positive для админа в `manager` — это привело бы к ложному «всё хорошо» когда distributor на самом деле пропустит вакансию. Этот callsite канонизируется отдельным тиклом под NBA-polish (tighten ветку до `_prepare_vacancy_pool`-eligible); не G-5 Stage B.

- **Out-of-scope Stage B (Candidate.manager shadow-read):** `uos_auto_activities.py:158-161, 471-474` читают `candidate.recruiter_id OR candidate.manager OR actor_id`. Эта форма намеренно оставлена — она является exact shadow-read-аналогом того, что Stage D превратит в shadow-write helper. Трогать до Stage D — увеличить диф.

- **Тесты** `backend/tests/test_uos_vacancy_follow_up_assignee.py` — 4 кейса на `ensure_vacancy_recruiting_follow_up_task`: (1) `manager=NULL` + активный пул → `assignee_id == pool_member` (regression-гард для центрального бага), (2) пустой пул + `manager` → `assignee_id == manager`, (3) без owner-а → `assignee_id == actor_id` (legacy fallback сохранён), (4) precedence гард pool beats manager. Регрессия: 93 зелёных теста в сумме (resolver Stage A — 8, uos Stage B — 4, lead distribution/next-action/vacancy-NBA/candidate-NBA/bell — 81).

### Stage C — Audit history table

**DONE.**

Append-only audit-trail для `Candidate.recruiter_id` — теперь один канонический path записи с обязательной history-row.

- **Модель** `backend/app/models/candidate_assignee_history.py` + регистрация в `backend/app/models/__init__.py` (класс `CandidateAssigneeHistory`). Все колонки из §2.5 реализованы: `id`, `tenant_id`, `candidate_id`, `from_user_id`, `to_user_id`, `reason (String(32))`, `actor_user_id`, `actor_kind (String(16), default 'user')`, `note (Text)`, `changed_at (DateTime tz, default now)`. FK на `candidates.id ON DELETE CASCADE` + на `users.id ON DELETE SET NULL` для `from_user_id`/`to_user_id`/`actor_user_id`. Индексы: `(tenant_id)`, `(candidate_id)`, `(changed_at)`, композитные `(tenant_id, candidate_id)` и `(tenant_id, changed_at)` — первый для explainability lookup по карточке кандидата, второй для аналитических витрин "кто перераспределял кого за период".

- **Alembic-миграция** `backend/alembic/versions/202604190001_candidate_assignee_history.py` (down_revision = `202604031200_vac_status_canon`, нынешний head). `heads` после миграции: `202604190001_candidate_assignee_history (head)`. Миграция не-destructive (только create_table + индексы); `downgrade()` обратим.

- **Helper** `backend/app/services/recruiter_assignment.py::record_candidate_reassignment(db, candidate, *, new_recruiter_id, reason, actor=None, actor_kind="user", note=None, skip_if_unchanged=True, write=True)`. Контракт:
  - `write=True` (default) — mutate `candidate.recruiter_id` + `await db.flush()` + `db.add(history_row)`. Используется всеми update-точками.
  - `write=False` — только history-row (candidate.recruiter_id уже выставлен INSERT-ом). Используется в `create_candidate_full` после `INSERT`, когда помечать `from == to` корректно, а UPDATE был бы бесcмысленным.
  - `skip_if_unchanged=True` (default) — no-op если `old == new`. Защита от шумного audit trail при идемпотентных routing-проходах.
  - Нормализация: `new_recruiter_id` с пустой/whitespace-строкой приводится к `None` (чтобы не нарушать FK `users.id`). `reason` клампуется до 32 символов, `actor_kind` — до 16.
  - Defensive: `candidate=None`, candidate без `id` или `tenant_id` → `return None` без raise (lead-processing может звать helper после failed-create).
  - **Не коммитит** — caller контролирует транзакционность (lead-processing делает `await db.commit()` один раз в конце pipeline).
  - Константа `CANDIDATE_REASSIGNMENT_REASONS` в том же модуле фиксирует словарь reason-кодов: `candidate_create`, `manual_single`, `manual_bulk`, `lead_vacancy`, `lead_rule`, `lead_fallback`, `lead_reroute_vacancy`, `lead_reroute_rule`, `lead_reroute_fallback`, `admin`, `timeoff_reroute`.

- **Обёрнутые write-точки** (все места, где сегодня пишется `Candidate.recruiter_id`):
  1. `backend/app/api/v1/candidates/service.py::create_candidate_full` — после `INSERT` + `commit`, `record_candidate_reassignment(..., write=False, skip_if_unchanged=False, reason="candidate_create")`. Explainability popover (G-10) читает эту row для «первое назначение, стратегия X».
  2. `backend/app/api/v1/candidates/service.py::update_candidate` — PATCH-payload с `recruiter_id` теперь снимает `recruiter_id_before` до `update(Candidate).values(**changes)`, а после `commit` + `refresh` добавляет history-row напрямую (inline, не через helper, чтобы не словить stale-ORM conflict на уже-refreshed candidate). `reason="manual_single"`, `actor_id` берётся из caller-scope.
  3. `backend/app/modules/leads/service/_processing.py:835-868` — три ветки (rule-stamped / vacancy-resolved / tenant-fallback) каждая со своим `reason` (`lead_rule` / `lead_vacancy` / `lead_fallback`), `actor_kind="system"`, `note=f"lead_id={lead.id}"` для traceability.
  4. `backend/app/modules/leads/service/_reroute.py:296-340` — две ветки (rule-stamped re-route / tenant-fallback re-route) с reason-ами `lead_reroute_rule` / `lead_reroute_fallback`. `vacancy_recruiter_id`-ветка сознательно не эмитит history — initial INSERT уже покрыт `candidate_create` row от `create_candidate_full`.

- **Out-of-scope Stage C (оставлено сознательно):**
  - `bulk_set_manager` пишет в `Candidate.manager`, не в `recruiter_id` — будет закрыт Stage D (shadow-write). Пока оставлен как есть, чтобы не создавать split-write до shadow-write helper-а.
  - Propagation `actor_id` в `_reroute.py` (сейчас `actor=None`, `actor_kind="system"`) — admin_service.reroute_lead не прокидывает actor. Follow-up тикет.

- **Тесты** `backend/tests/test_candidate_assignee_history.py` — 9 кейсов на `record_candidate_reassignment`:
  1. `skip_if_unchanged=True` + same value → no history (идемпотентность).
  2. old→new transition пишет candidate AND history-row с правильными `from_user_id`/`to_user_id`/`reason`/`actor`/`note`.
  3. `write=False` пишет history-row без UPDATE candidate (INSERT-time path).
  4. unassign (`new_recruiter_id=None`) пишет history с `to_user_id=NULL`.
  5. Defensive: `candidate=None` → `None`.
  6. Defensive: candidate без `tenant_id` → `None` + не персистит history.
  7. Reason и actor_kind clamp до column-length (String(32) / String(16)).
  8. Append-only: несколько переназначений → N отдельных row в правильном порядке `changed_at`.
  9. `new_recruiter_id="   "` нормализуется в `None` (защита от FK violation на `users.id`).

- **Регрессия:** 140 passed / 2 skipped на G-5 surface (helper 9 + resolver 8 + UOS follow-up 4 + lead/NBA/bell/vacancy-status 119). Pre-existing failures (`test_candidate_children.py`, `test_audit_events.py`, `test_candidate_short_id.py`, etc.) — все не связаны с recruiter-path, подтверждены как data-pollution / DNS-resolution artifacts в sandbox.

### Stage D — Shadow-write `Candidate.manager` ↔ `Candidate.recruiter_id` — **DONE**

Единый write-point — существующий helper `record_candidate_reassignment` (Stage C), расширен shadow-write-логикой: каждый раз, когда он мутирует `candidate.recruiter_id`, он зеркалит то же значение в `candidate.manager` (и наоборот — при `skip_if_unchanged=True` и drift-случае `manager != recruiter_id` делает self-heal без эмита history-строки). Таким образом инвариант «`manager == recruiter_id`» держится на уровне канонического writer-а, а не на уровне каждого call-site-а.

**Изменённые файлы:**

- `backend/app/services/recruiter_assignment.py::record_candidate_reassignment` — расширен shadow-write-блок: `candidate.manager = new_value` рядом с `candidate.recruiter_id = new_value`. Добавлен self-heal branch для `skip_if_unchanged` — reconciliate drift без emit-а history-строки (история — про reassignment, не про sync-repair).
- `backend/app/api/v1/candidates/service.py::bulk_update_manager` — переписан с bulk `UPDATE SET manager=...` на цикл с `record_candidate_reassignment(..., reason="manual_bulk")` per candidate. Trade-off — per-row flush вместо одного SQL-стейтмента; приемлемо (N < 100 в типичном selection). Бонус: `manual_bulk` history-строка на каждый изменённый кандидат, split-brain между `manager`/`recruiter_id` устранён.
- `backend/app/api/v1/candidates/service.py::update_candidate` (PATCH) — `manager` / `manager_id` / `recruiter_id` в payload слиты в единый `_assignment_value` pipeline: `recruiter_id` канон (когда оба переданы с разными значениями — выигрывает он), FK-валидация user-а применяется к обеим ветвям, `changes["recruiter_id"]` и `changes["manager"]` пишутся синхронно. Audit-строка (`manual_single`, Stage C) теперь также покрывает случай, когда payload прислал только `manager` (раньше — беззвучный split-brain).
- `backend/app/api/v1/candidates/service.py::create_candidate_full` — INSERT-time shadow-write: когда `assignment.assigned` (cascade от vacancy/tenant выбрал recruiter-а) или когда payload принёс валидный `manager_val`, и `recruiter_id`, и `manager` проставляются тем же значением. Добавлена FK-валидация `manager_val` против `users` (до Stage D — только UUID-валидация; теперь, раз мы mirror-им в `recruiter_id` с FK, нужно гарантировать существование). Audit-emit расширен: `candidate_create` history-строка теперь пишется и для payload-manager-only пути (reason-note `strategy=payload_manager`).
- `backend/app/api/v1/candidates/repo.py` — фильтр `filters["manager"]` расширен до `or_(Candidate.manager == v, Candidate.recruiter_id == v)`. Транзитивный — до Stage F, когда UI переключится на `?recruiter_id=`. Комментарий объясняет мотивацию (legacy-строки с `manager=NULL`, `recruiter_id=<user>` не должны пропадать из `?manager=<user>`).
- `backend/app/api/v1/candidates/router.py::active-candidates` list (`?manager_id=`) — тот же OR-мёрдж, чтобы фильтр вёл себя консистентно с основным list-эндпоинтом.
- `backend/app/modules/leads/service/_processing.py` — два inline shadow-write-а `if recruiter_id and not getattr(candidate, "manager", None): candidate.manager = recruiter_id` удалены (lines 143-145 и 882-884). Теперь helper делает это в момент своего write-а, дополнительная defensive-проверка не нужна.
- `backend/app/modules/leads/service/_reroute.py` — аналогичный inline shadow-write убран (line 338-340). В branch-е `vacancy_recruiter_id` (где Stage C намеренно не оборачивает в helper, потому что INSERT уже эмитит `candidate_create`) `manager` теперь тоже проставляется на INSERT-time shadow-write в `create_candidate_full`.

**Tests (`backend/tests/test_candidate_manager_shadow_write.py`, 6/6 passed):**

1. `test_helper_shadow_writes_manager_on_happy_path` — `A → B` флипает обе колонки.
2. `test_helper_shadow_writes_manager_on_unassign` — `A → None` зачищает обе.
3. `test_helper_self_heals_drifted_manager_on_noop` — legacy drift (`recruiter_id=A, manager=B`) + повтор reassignment `→ A` ресинкит `manager`, history не растёт.
4. `test_bulk_update_manager_syncs_recruiter_id_and_history` — bulk-set-manager пишет оба поля + one `manual_bulk` row per candidate с правильными `from/to`.
5. `test_bulk_update_manager_idempotent_on_same_value` — повторный bulk с тем же значением не добавляет строк (skip_if_unchanged default).
6. `test_repo_manager_filter_matches_recruiter_id_only` — кандидат с `manager=NULL, recruiter_id=X` возвращается фильтром `?manager=X`.

**Регрессия:**

- Stage D-specific: 6/6 passed.
- G-5 surface (Stage A/B/C + Stage D helper/bulk): 27/27 passed (6 + 9 Stage C + 8 resolver + 4 UOS).
- Broader candidate/lead sweep (`test_candidate_next_action`, `test_lead_next_action`, `test_lead_distribution_ingest`, `test_candidate_status_reason`, `test_candidate_employments`, `test_candidate_stage_visibility`, `test_leads_meta`, `test_leads_delete`, `test_lead_quota`, etc.): все failures (`test_candidate_status_reason::test_candidates_filter_by_status_reason`, `test_candidate_stage_visibility::*`, `test_leads_meta::*`) **воспроизводятся на baseline без Stage D** — pre-existing sandbox issues (DNS `Temporary failure in name resolution`, data-pollution на long-lived PG). Stage D регрессий не вносит.

**Out-of-scope (Stage E/F):**

- Helper `_set_candidate_recruiter(candidate, user_id)` как отдельная функция не вводился — `record_candidate_reassignment` уже выполняет эту роль (single write-point, audit-aware, идемпотентный). Альтернативный wrapper повторил бы её контракт без бенефита. Имя в спецификации оставлено исторически — см. §4 Stage D (рефакторинг под alias отложен до Stage G, где и будет финальный clean-up).
- Actor-propagation для lead-processing / reroute (`actor_kind="user"` вместо текущего `"system"`) — отложено до Stage E (требует протаскивания `actor_id` через `processing_context` и `reroute_lead_manual`).
- `uos_auto_activities.py` shadow-read `recruiter_id OR manager OR actor_id` — всё ещё читает обе колонки defensively; теперь это избыточно (Stage D гарантирует их равенство), но трогать до Stage F-G не будем, чтобы не увеличивать диф.

### Stage E — FK constraints на все owner-колонки **DONE**

Alembic-ревизия: `backend/alembic/versions/202604190002_owner_fk_set_null.py` (head после `202604190001_candidate_assignee_history`).

Реализованный скоуп (5 колонок, подтверждено live-интроспекцией PG):

1. `reminders.assignee_id` → `fk_reminders_assignee_id_users` `ON DELETE SET NULL`.
2. `communication_planner_events.assignee_id` → `fk_comm_planner_events_assignee_id_users` `ON DELETE SET NULL`.
3. `communication_threads.assignee_id` → `fk_comm_threads_assignee_id_users` `ON DELETE SET NULL`.
4. `document_policies.owner_user_id` → `fk_document_policies_owner_user_id_users` `ON DELETE SET NULL` + новый индекс `ix_document_policies_owner_user_id`.
5. `candidate_profiles.owner_user_id` → `fk_candidate_profiles_owner_user_id_users` `ON DELETE SET NULL` + новый индекс `ix_candidate_profiles_owner_user_id`.

Каждая точка закрыта и в БД (Alembic), и в ORM (`ForeignKey("users.id", ondelete="SET NULL")` в `backend/app/models/reminder.py`, `backend/app/models/communication.py`, `backend/app/models/document_policy.py`, `backend/app/models/candidate_profile.py`), чтобы SQLAlchemy metadata не расходилось с фактическим схема-состоянием.

Исходное состояние до миграции (разовая инвентаризация `information_schema`):
- `candidates.recruiter_id` — уже был FK `SET NULL` (legacy).
- `companies.owner_user_id` / `companies.manager_user_id` — уже были FK `SET NULL` (legacy; в спеке §1.1 помечены «нет FK» — инвентаризация оказалась устаревшей, FK поставили ранее в другой миграции).
- Остальные 5 колонок — `String(36)` без FK, referential integrity держалась application-кодом.

**Pre-migration orphan sweep.** Перед `ADD CONSTRAINT` на каждой из 5 таблиц выполняется `UPDATE … SET <col> = NULL WHERE <col> NOT IN (SELECT id FROM users)`. Без этого шага `ADD CONSTRAINT` на популированных таблицах упадёт на первой висящей строке. NULL — строго безопаснее «висящего UUID», поэтому `downgrade()` эту очистку осознанно **не откатывает**.

**Out-of-scope в Stage E:**
- `communication_allocation_audits.assignee_id` — forensic audit table; SET NULL потерял бы историческую фиксацию «кому allocate решил выдать», что обнуляет цель аудита. Оставили `VARCHAR(36)` без FK.
- `communication_messages` — колонки `assignee_id` на этой таблице фактически **нет** (только на `communication_threads`); §1.1 спеки на этот счёт был написан «на вырост» — сейчас скорректирован.
- `Candidate.manager` — к Stage G уйдёт в `DROP COLUMN`, FK добавлять бессмысленно.
- `Vacancy.manager` — Stage G переименует в `primary_recruiter_id` и проставит FK одним махом с rename-ом.

Round-trip verified: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` проходит чисто на production-шаблоне БД.

**Тесты:** `backend/tests/test_owner_fk_set_null.py` (5 тестов, по одному на каждую закрытую FK-колонку). Каждый тест создаёт изолированного `User` (чтобы `DELETE` не тронул seed-fixture-ы) + owner-entity, хард-удаляет пользователя через `DELETE FROM users WHERE id = …` (мягкий `is_active=false` FK-триггер не фиксирует) и убеждается, что parent row **жив**, а owner-column — `NULL`. Все 5 зелёные.

**Out-of-scope (to Stage G):** actor-propagation (`actor_kind="user"`) для lead-processing / reroute; rename `Vacancy.manager → primary_recruiter_id`; drop `Candidate.manager`.

### Stage F — Frontend → `recruiter_id` canon **DONE**

Закрыт в одну волну: бэкенд принимает `?recruiter_id=` как канонический query-param, фронт переведён на него же под feature-flag, `CandidateOut`-схема декларирует `recruiter_id`/`recruiter_name`/`recruiter_short`, а PATCH `/candidates/{id}` принимает `recruiter_id` наравне с legacy-именами.

**Backend:**

- `GET /api/v1/candidates` и `GET /api/v1/candidates/no-next-action` теперь обьявляют оба query-параметра: `recruiter_id` (канон) и `manager_id` (legacy alias). Оба воронкуются в один и тот же `filters["manager"]`, который в `candidates/repo.py::_build_conditions` превращается в `or_(Candidate.manager == v, Candidate.recruiter_id == v)` — гарантирует что legacy-строки с `manager=NULL, recruiter_id=<user>` видны обоим фильтрам. При одновременной передаче обоих — `recruiter_id` выигрывает (описано в `description=` параметра).
- PATCH `/api/v1/candidates/{id}` ­дополняет `allowed_fields` + `_candidate_patch_side_effect_fields` каноническим именем `recruiter_id`. Service-слой (Stage D) уже умеет сводить `manager` / `manager_id` / `recruiter_id` в один валидированный UUID через `record_candidate_reassignment`; роутер только перестаёт фильтровать новое имя.
- `CandidateOut` (Pydantic-схема) теперь декларирует `recruiter_id`, `recruiter_name`, `recruiter_short` — payload (`_serialize_candidate_row`) эти поля всегда строил, но OpenAPI-контракт о них не знал и TS-типы fallback-или до `any`. `from_model(...)` тоже проброшен, хотя он dead-code на текущий момент.

**Frontend:**

- Новый feature-flag `VITE_FEATURE_CANDIDATE_RECRUITER_CANON` (default ON, см. §5) в `hostflow-frontend/src/utils/featureFlags.ts`, helper `isCandidateRecruiterIdCanonEnabled()`.
- `hostflow-frontend/src/modules/candidates/hooks/useCandidatesTableData.ts` — outgoing `manager_id: …` в параметрах axios заменён на условный `{ recruiter_id }` / `{ manager_id }` в зависимости от флага.
- `hostflow-frontend/src/api/client.ts::listCandidatesNoNextAction` — добавлен параметр `recruiterId` (канон) наряду с legacy `managerId`; outgoing query-name тоже gated на флаге.
- `hostflow-frontend/src/modules/candidates/utils.ts::getCandidateRecruiterId` — новый helper-первой-инстанции (читает `recruiter_id`, fallback на `manager_id`/`manager`); `getCandidateManagerId` становится алиасом этого helper-а (оба теперь возвращают канонический id).
- `hostflow-frontend/src/pages/CandidateCard.tsx` — PATCH-body теперь включает `recruiter_id` в дополнение к `manager`/`manager_id`. Legacy-ключи сохранены unconditionally для rollback и на случай промежуточного deploy-состояния.
- `hostflow-frontend/src/pages/Pipeline.tsx` — bulk-PATCH (`api.patch('/candidates/:id', …)`) аналогично пишет оба поля; client-side manager-фильтр на Kanban-доске читает `recruiter_id` первым.
- `hostflow-frontend/src/modules/dashboard/types.ts` + `useDashboardDerivedAnalytics.ts` — `CandidateSnapshot` пополнен `recruiter_id`/`recruiter_name`/`recruiter_short`, manager-load drill-down переключён на канонические поля.

**Тесты:** `backend/tests/test_candidates_list_recruiter_id_filter.py` — 4 теста (signature-based): `list_candidates` / `list_candidates_no_next_action` декларируют `recruiter_id` как `UUID | None`; legacy `manager_id` не выпилен; `CandidateOut` содержит обе triplet-ы (manager/recruiter). E2E-smoke на реальный `GET /candidates?recruiter_id=…` намеренно не добавлялся: default-тенант в conftest — agency-тип, а agency-scope в list-endpoint возвращает кандидатов только связанных с client-tenant handoff-ами — такой танец с tenancy относится к отдельному fixture-ритиусу, а не к Stage F. Покрытие OR-фильтра на обеих колонках закрывается существующим `test_candidate_manager_shadow_write.test_repo_manager_filter_matches_recruiter_id_only` (Stage D) — Stage F воронкует новое имя в тот же `filters["manager"]`, так что SQL-OR не меняется.

**Pre-existing регресс в smoke-тестах** `test_pipeline_sync.py::test_stage_sync_smoke`, `test_candidate_children.py::*`, `test_recruiter_access.py::test_recruiter_can_create_candidate_in_accessible_company` — подтверждено stash-сравнением: присутствуют с той же частотой **без** Stage F-коммитов. Causes нашего wave не являются; фиксятся отдельным ticket-ом (статус 422 от `POST /companies/`, flake resolve-recruiter-assignment-а, DNS resolution noise в sandbox).

**Out-of-scope Stage F (переехало в Stage G):**

- DROP COLUMN `candidates.manager` — ждёт ≥ 7 дней shadow-write stability в prod (§5).
- Rename `Vacancy.manager → primary_recruiter_id` + FK с `ON DELETE SET NULL` — в одной Alembic-ревизии с DROP'ом выше.
- Выпил legacy-параметра `manager_id` из query-string (канон только `recruiter_id`) — пойдёт вместе с drop-колонкой: до этого момента оба имени живы ради одного релизного окна.

### Stage G — Drop `Candidate.manager` + rename `Vacancy.manager → primary_recruiter_id`

Alembic:

```sql
-- candidates
UPDATE candidates SET recruiter_id = COALESCE(recruiter_id, manager) WHERE recruiter_id IS NULL;
ALTER TABLE candidates DROP COLUMN manager;

-- vacancies
ALTER TABLE vacancies RENAME COLUMN manager TO primary_recruiter_id;
ALTER TABLE vacancies ADD CONSTRAINT fk_vacancies_primary_recruiter
  FOREIGN KEY (primary_recruiter_id) REFERENCES users(id) ON DELETE SET NULL;
```

Schemas: `VacancyIn.manager` → `VacancyIn.primary_recruiter_id`, со legacy-alias `manager` (Pydantic `Field(alias=...)`) для одного минорного релиза.

---

## 5. Back-compat / roll-out

- Stage A–E — **не ломают** ни API, ни БД-инвариантов. Можно мержить пачками.
- Stage F — фронт-релиз, покрыт feature-flag `VITE_FEATURE_CANDIDATE_RECRUITER_CANON` (default ON после стабилизации). Откат — флаг в OFF, фронт снова читает `manager`.
- Stage G — destructive (DROP COLUMN). Только после того, как все production-tenants отметились на prod-бекенде, в котором Stage D был активен **≥ 7 дней** (shadow-write стабилен). В alembic-ревизии оставить `downgrade()` с restore-логикой из `candidate_assignee_history` (последнее значение `to_user_id` как recover для `manager`-колонки, если потребуется roll-back).

---

## 6. Открытые вопросы

- **External integrations.** Нужно ли сохранять `Candidate.manager` в webhook-payload-ах (Meta/Indeed/HH) для BC? Сейчас ответ — **да** (stage G: derived-поле в serializer, построенное из `users.short_id`), но потребует аудита интеграционных тестов.
- **Lead.recruiter_id.** Вопрос оставлен открытым: нужен ли `recruiter_id` на самой `Lead`-строке, или достаточно резолвить при конверсии. Обсуждение — в `docs/specs/operations-loop.md` §G-5.X (будущий TODO).
