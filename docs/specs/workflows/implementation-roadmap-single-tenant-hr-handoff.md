# Дорожная карта: single-tenant контур Recruitment → Document Hub → HR

**Назначение:** зафиксировать **текущее состояние кода**, **определение готовности (DOD)** первого куска и **очередность фаз** до полного замыкания модулей.  
**Канон требований:** [first-operational-flow-recruitment-documents-hr.md](first-operational-flow-recruitment-documents-hr.md).  
**Контракт handoff и стадий (для агентов):** [handoff-contract.md](../architecture/handoff-contract.md) — маппинг `ready_for_hr` / `ready_for_handoff`, типы передачи, idempotent/forbidden.  
**Governance (events / consumers / command-flow / orchestration + чеклист ревью):** [operational-event-boundaries.md](../architecture/operational-event-boundaries.md).  
**Мастер-порядок этапов (0–10):** [module-separation-implementation-order.md](module-separation-implementation-order.md) — этот файл детализирует измеримый **первый контур** и AS-IS; не заменяет полную лестницу модулей.

**Правило фиксации прогресса:** в этом файле отмечаем **завершение логических блоков** (кусок контракта + код/тесты + при необходимости спека), а не каждый мелкий PR. Краткий перечень закрытых блоков — §2.1.

---

## 1. Определение готовности фазы 1 (единственная «точка завершения» первого куска)

Фаза 1 считается **закрытой**, когда одновременно выполнено:

1. **Функциональный чеклист** из контракта первого потока (8 пунктов в разделе «Критерии готовности») подтверждён сценариями **внутри одного tenant** и одного согласованного **company scope** (`own_company_id` / активная компания — по правилам продукта).
2. **Регрессия:** есть **автоматические тесты** (или минимум один сквозной integration test + чеклист для QA), которые фиксируют:
   - переход кандидата в **`ready_for_hr`** / **`hired`** (или согласованный код из воронки) создаёт **ровно одну** связку `WorkforceEmployee` для `candidate_id` (идемпотентность);
   - **нет второй записи `documents`** с тем же бинарным содержимым/файлом при handoff (проверка отсутствия копирования — по наличию одного `document.id` и того же storage ref);
   - пользователь с ролью **HR** может **читать** документы кандидата, необходимые для онбординга, в рамках текущей модели доступа (`dossier_zone` + роль, см. ниже).

   Референс в коде: `backend/tests/api/test_single_tenant_recruitment_hr_handoff_flow.py` (**recruiter** ставит `ready_for_hr`, **hr_officer** — `hired`; рекрутер не может `hired` при включённом handoff lane). Инварианты: [`docs/specs/architecture/invariants-recruitment-hr-document-hub.md`](../architecture/invariants-recruitment-hr-document-hub.md).
3. **Событие смены ответственности** фиксируется явно: в логе активности / событий есть связь «кандидат → сотрудник / handoff» (сейчас: `workforce.handoff_from_candidate` — при необходимости дополнить отдельным доменным событием handoff без дублирования смысла).
4. **Документация:** этот файл и [first-operational-flow…](first-operational-flow-recruitment-documents-hr.md) не противоречат поведению кода (или обновлены под фактическую MVP-модель «HR Case»).

Пока пункты 1–4 не зелёные — **не** считаем закрытым первый кусок и **не** переносим фокус на inter-tenant, portal, marketplace (см. §0 основного контракта).

---

## 2. Текущее состояние (AS-IS) — кратко по слоям

### 2.1 Зафиксированные логические блоки (завершено в коде / спеках)

| Блок | Суть | Где смотреть |
|------|------|--------------|
| **A. Handoff + Workforce + регрессия** | Стадии `ready_for_hr` / `hired` → идемпотентный `WorkforceEmployee`, HR читает те же документы без копии файла; рекрутер не переводит на `hired` при включённом handoff lane. | `test_single_tenant_recruitment_hr_handoff_flow.py`, `workforce_employees.py`, `invariants-recruitment-hr-document-hub.md` |
| **B. HR operational context** | Таблица **`workforce_hr_cases`**, связки **`document_entity_links`** (`reused_for_hr` → `workforce_employee`), `ensure` на handoff + ленивый backfill на `GET/POST` HR API; отдельная **HR-проверка** (`DocumentCheck` с `review_module=hr`) без смены `Document.status` от рекрутинга; UI на карточке сотрудника; тесты RBAC на `hr-review`. | `workforce_hr_operational_context.py`, `router.py` (`hr-operational-context`, `hr-review`), `test_hr_operational_context_after_handoff.py`, `HrEmployeeDocumentsSection.tsx` |
| **C. Документация P0 (стадии + single-tenant путь)** | Разведение **`ready_for_handoff` vs `ready_for_hr`** и канонический **stage-driven** handoff для internal tenant — зафиксированы в §3 ниже и в [first-operational-flow…](first-operational-flow-recruitment-documents-hr.md). | §3 GAP, first-operational-flow §3.1 / §5.2 |
| **D. Мост `ready_for_handoff` → Workforce** | Стадия **`ready_for_handoff`** (воронка/Telegram) материализует `WorkforceEmployee`, если на **tenant link** включён internal HR и выполняется одно из условий: **`handoff_to_client` выключен** (только internal lane), либо в `features_json` выставлено **`workforce_handoff_on_ready_for_handoff_stage: true`** (PATCH `TenantLinkUpdate`). Иначе — по-прежнему канон **`ready_for_hr`** или **CandidateHandoff** (agency). | `should_workforce_handoff_on_stage_change_resolved`, `candidates/service.py`, `candidate_profile.py`, `test_single_tenant_recruitment_hr_handoff_flow.py` |

### 2.2 Таблица по слоям

| Тема | Что есть в коде | Комментарий к контракту |
|------|-----------------|-------------------------|
| Кандидат (Recruitment) | CRUD, стадии, `Candidate` привязан к `tenant_id`, `own_company_id` | П.1 чеклиста закрыт базово. |
| Документы (Document Hub MVP) | `Document` + `candidate_id`, `dossier_zone`, `DocumentDossierShare` | П.2: хранение в Hub — да. **MVP link:** таблица **`document_entity_links`** (не полный ADR-009: документ по-прежнему «принадлежит» кандидату в строке `documents`, связь с сотрудником — через link). |
| Доступ HR к досье | `document_dossier_access.py` + `GET /workforce/employees/.../documents` | П.7: зоны/шаринг + workforce-scoped чтение. **Дополнительно:** отдельная запись проверки HR (`hr-review`) без перезаписи recruitment-статуса документа. |
| Стадии Ready for HR / Hired | `WORKFORCE_HANDOFF_STAGE_CODES`; ADR-002 | П.4: `ready_for_hr`, `hired`, `processing_by_hr`, … См. §3 про **`ready_for_handoff`**. |
| Employee + HR Case | `WorkforceEmployee` + спутники + **`WorkforceHrCase`** | П.5: **Employee** + **строка HR case** в БД; onboarding bundle как раньше. |
| Handoff-событие | `handoff_from_candidate` + `log_activity` при смене стадии | П.8: событие есть. **Single-tenant internal (зафиксировано):** материализация workforce + HR context опирается на **смену стадии** в `WORKFORCE_HANDOFF_STAGE_CODES` и при необходимости на **блок D §2.1** для `ready_for_handoff`. `CandidateHandoff(destination=internal_hr)` — для agency/client, **не обязательна** для появления сотрудника в internal контуре при включённом tenant link. |
| Копирование / reuse | Нет второго `Document` при handoff; **`document_entity_links`** для reuse в HR | П.6–7: без копии файла; линк employee↔document — **MVP (фаза 1)**. Полная унификация с ADR-009 — **фаза 2**. |

---

## 3. Разрывы (GAP) до DOD фазы 1

Приоритет **P0** (блокирует объявление фазы 1 завершённой):

1. ~~**Тестовый контур**~~ **→ закрыт (блок A §2.1):** `test_single_tenant_recruitment_hr_handoff_flow.py` + `test_hr_operational_context_after_handoff.py` (идемпотентность workforce, отсутствие второго документа, HR-доступ и отдельная HR-проверка).
2. ~~**`ready_for_handoff` vs `ready_for_hr`**~~ **→ зафиксировано для спеки/продукта + мост в коде (блок D §2.1):** **`ready_for_hr`** остаётся каноном ADR-002 / invariants. **`ready_for_handoff`** — код воронки/Telegram; для материализации Workforce без смены кода воронки оператор настраивает **tenant link** (`handoff_to_client: false` при internal-only **или** `workforce_handoff_on_ready_for_handoff_stage: true` через PATCH ссылки). Иначе по-прежнему нужны **`ready_for_hr`** или **CandidateHandoff** (agency).
3. ~~**Single-tenant путь handoff**~~ **→ зафиксировано:** для **internal single-tenant** по умолчанию достаточно **stage-driven** пути (`candidates/service.py` → `handoff_from_candidate` при стадиях из `WORKFORCE_HANDOFF_STAGE_CODES`). Запись **`CandidateHandoff`** с destination internal HR остаётся в контуре **agency/client**; для «чистого» single-tenant она **не является обязательным условием** появления `WorkforceEmployee`, если включены настройки tenant link и те же стадии. UI handoff-кнопок под agency — не блокер, пока стадии доступны рекрутеру.

**Остаётся по DOD §1:** ручной прогон на стенде — **§6** этого файла (функциональные 8 пунктов по [first-operational-flow…](first-operational-flow-recruitment-documents-hr.md) + governance-ревью + **журнал прогона §6.3**) + убедиться, что спека и UI не противоречат §3 (в т.ч. Telegram/воронка vs `ready_for_hr`).

Приоритет **P1** (после объявления фазы 1 или в начале фазы 2):

4. ~~**Термин «HR Case» в UI:**~~ **→ закрыто (copy):** подписи без отсылки к «миграции бэкенда»; «кейс» = operational record сотрудника в смысле строки `workforce_hr_cases`; `en` / `ru` / `pl` + `defaultValue` в `HrEmployeeDocumentsSection`.
5. **ADR-009 полный слой:** расширить MVP-линки до платформенной модели Hub (фаза 2 дорожной карты).

**Продуктовый долг (не блокер фазы 1):** политика **required document set для HR** поверх текущего «все активные документы кандидата» в `ensure`.

---

## 4. План по фазам (последовательно, с отдельной DOD на каждую)

### Фаза 1 — Single-tenant operational continuity (текущий фокус)

**Цель:** замкнуть контур из [first-operational-flow…](first-operational-flow-recruitment-documents-hr.md) без внешнего sharing.

**Работы (порядок):  
A.** Закрыть GAP P0 (тесты + стадии + выбор пути handoff в single-tenant).  
**B.** Пройти ручной чеклист 8 пунктов на стенде с одним tenant.  
**C.** Обновить при необходимости [first-operational-flow…](first-operational-flow-recruitment-documents-hr.md) («HR Case = MVP: WorkforceEmployee + …»).

**DOD:** раздел §1 этого файла.

---

### Фаза 2 — Зрелость Document Hub внутри tenant

**Цель:** приблизить модель к ADR-009: **Document Link**, при необходимости **`source_module` / `linked_entity_type=employee`**, отдельный **review context** поверх `workflow` в `meta` (если продукт требует).

**DOD:** документ можно связать с `WorkforceEmployee` без дублирования файла; политики доступа согласованы с ролями; миграции и тесты.

**Не начинать** до зелёной фазы 1.

---

### Фаза 3 — Company → company внутри одного tenant

**Цель:** тот же механизм handoff + links, но с **сменой operational company scope** (две компании в одном tenant).

**DOD:** спека + тесты на изоляцию `own_company_id` и корректные права.

---

### Фаза 4 — Agency → employer (существующая механика handoff)

**Цель:** использовать/упростить `CandidateHandoff`, client portal queue, блокировки recruitment — **без** ломки фазы 1.

**DOD:** сценарии agency приняты регрессией; контракт first-operational-flow остаётся валидным для internal tenant.

---

### Фаза 5 — Tenant → tenant, shared access, client portal

**Цель:** межтенантный обмен и внешние поверхности — только после стабильности фаз 1–4.

**DOD:** отдельные ADR/спеки + security review.

---

## 5. Модули продукта (параллельные треки после фазы 1)

По [ADR-004](../architecture/ADR-004-five-product-modules-and-billing-events.md) полное «завершение всех модулей» — не один поток, а набор треков:

| Модуль | Зависимость от фазы 1 | Примечание |
|--------|------------------------|------------|
| **Recruitment** | База для handoff | Уже несёт Candidate и стадии. |
| **HR (Workforce)** | Прямой потребитель handoff | Фокус фазы 1. |
| **Document Hub** | Общий слой | Фазы 1–2. |
| **Fleet** | После HR employee | Привязка к сотруднику/документам — отдельные эпики. |
| **Services** | Слабая связь с фазой 1 | Интеграции по мере необходимости. |
| **Finance / Billing** | Слабая связь | События биллинга — отдельный контур. |

После **DOD фазы 1** планирование «следующего куска» выбирается явно: либо **фаза 2 (Hub)**, либо **минимальный Fleet read-only к employee**, либо **долги Recruitment UI** — но не смешивать в одном PR.

---

## 6. Стенд: чеклисты фазы 1 и журнал прогона

**Цель:** закрыть DOD §1 п.1 (ручной прогон) и зафиксировать результат в одном месте.

**Не уходить снова в meta-архитектуру** на этом этапе: governance foundation достаточен; дальше — **проверка канона исполнением**, а не новые концепции.

### Цикл operational validation (зрелый engineering loop)

1. Запустить реальный flow (Recruitment → Document Hub → HR).  
2. Пройти стенд, заполнить **§6.1–6.2**, зафиксировать **§6.3**.  
3. При нарушении канона классифицировать: **код** / **UI** / **flow** / **semantics** / **сам governance** (редко).  
4. **Точечно** исправить; канон (спеки) менять **только после повторяющихся** operational contradictions, не «на опережение».

**На что смотреть в первую очередь:** hidden orchestration, duplicated triggers, обходы через Telegram/UI/automation, прямые записи в чужой домен, дублирование документов вместо links, устаревшие допущения старого монолита.

**Объём работ:** не «идеально разделить всё сразу» — удерживать **canonical boundaries**, не ломать **invariants**, постепенно выносить ownership из монолита через реальные прогоны.

**Статус блока (architecture / governance):** закрыт для текущей итерации. Канон не расширяем без фактов со стенда. **Рабочая формула:** *не расширяем канон — проверяем канон исполнением*; следующий шаг — **только** прогон flow и **§6.1–6.3**.

**Фаза:** переход из **architecture-definition** в **architecture-verification**. Следующие meaningful артефакты — не новые спеки, а **заполненный §6.3**, зафиксированный **violation**, **тикет**, **PR**, **regression test** или **подтверждённый clean flow**.

**Качество архитектуры сейчас** определяется не объёмом документации, а: качеством **operational validation**, дисциплиной **review**, устойчивостью **invariants** под давлением «быстрых фиксов» и скоростью обнаружения **hidden coupling**. Лучший ближайший шаг — **реальный прогон** Recruitment → Document Hub → HR и **первая честная строка в §6.3**.

**Любое изменение дальше — от факта:** что сломалось → где → какой invariant → баг (код / UI / Telegram / automation / спека) → минимальный фикс.

### 6.1 Функциональный чеклист (8 пунктов)

Критерии из [first-operational-flow… §3](first-operational-flow-recruitment-documents-hr.md#3-критерии-готовности-внутри-одного-tenant). На стенде (один tenant, согласованный company scope): пройти сценарий Recruitment → Document Hub → HR и отметить каждый пункт.

| # | Критерий (кратко) | Pass / Fail | Примечания (шаги, роли, URL) |
|---|-------------------|-------------|------------------------------|
| 1 | Recruitment создаёт Candidate | | |
| 2 | Document Hub хранит документы | | |
| 3 | Recruitment только линкует к Candidate, не подменяет владение Hub | | |
| 4 | Стадии Ready for HR / Hired (или согласованные коды) | | |
| 5 | HR: Employee + HR Case | | |
| 6 | Документы не копируются при handoff | | |
| 7 | HR доступ через links + при необходимости HR review context | | |
| 8 | Смена ответственности через явный handoff event | | |

### 6.2 Governance-ревью (8 вопросов)

После или параллельно функциональному прогону — по чеклисту [operational-event-boundaries.md — чеклист ревью](../architecture/operational-event-boundaries.md#review-checklist): владелец lifecycle, command, source of truth, event, consumer, чужой домен, hidden orchestration, копии документов.

| # | Вопрос | OK / Issue | Заметка |
|---|--------|------------|---------|
| 1 | Кто владелец lifecycle? | | |
| 2 | Кто инициировал command? | | |
| 3 | Кто изменил source of truth? | | |
| 4 | Кто выпустил event? | | |
| 5 | Кто consumer? | | |
| 6 | Прямая запись в чужой домен? | | |
| 7 | Hidden orchestration (UI / Telegram / automation)? | | |
| 8 | Копирование документов вместо links? | | |

### 6.3 Журнал прогона (фиксация)

Заполняется после прохождения §6.1–6.2 (можно одной строкой на релиз стенда).

**Operational mindset:** цель прогона — не «доказать, что всё идеально», а получить **данные**. **Fail / Issue — это тоже данные:** раннее обнаружение нарушений канона, классификация (код / UI / Telegram / automation / спека), **минимальный** corrective fix без ломки invariants. «Хороший результат» на этом этапе — violations видны, понятны и устраняются дисциплинированно; execution покажет, где boundaries уже чистые, а где governance расходится с поведением системы.

| Дата (UTC) | Окружение (URL / ветка / compose) | Исполнитель | §6.1 все Pass? | §6.2 все OK? | DOD §1 целиком | Ссылка (тикет / заметки) |
|------------|-----------------------------------|-------------|----------------|--------------|----------------|---------------------------|
| *пример: YYYY-MM-DD* | | | да / нет | да / нет | да / нет | |
| 2026-05-06 | HostFlowDev — deployed backend + frontend | — | да | да | да | Operational verification: workforce docs + hr-bundle/context 200; `GET /api/v1/db/documents/{id}/file` 200; hr-review + checks 200; no `GET …/candidates/…/documents/…/file` → 401 after fix. |
| 2026-05-07 | HostFlowDev — deployed backend + frontend | — | да | да | да | **Прогон 2 — idempotency:** повторный ready_for_hr / handoff того же кандидата; один `WorkforceEmployee`; case контролируемо; документы без копий; HR reviews без неконтролируемого размножения; UI без дублей; return flow проверен. См. блок «Прогон 2» в §6.3. |
| *архив: contradiction* | HostFlowDev | — | — | — | — | Recruitment write после workforce — см. блок «Operational contradiction» ниже; исправлено в коде + регрессионные тесты. |
| 2026-05-08 | HostFlowDev — deployed backend + frontend | — | да | да | да | Recruitment write lock — см. отдельную строку ниже + блок «Прогон 3». |
| 2026-05-06 | repo — static code audit (no new stand session) | — | — | — | — | **Hub vs legacy inventory:** SPA recruitment — `docsApi` (Hub), не `/api/v1/candidates/.../documents`; HR employee documents — workforce list + `downloadDocumentFile` (Hub); legacy candidate routes и `CandDoc.file_url` → `/candidates/.../file` остаются на backend/public intake; contradiction относительно HR file access не найдена. Детали: [`current-separation-status-recruitment-hr-doc-hub.md`](current-separation-status-recruitment-hr-doc-hub.md) § «Document Hub vs legacy — инвентаризация по коду». |
| 2026-05-08 | repo — code | — | — | — | — | **Workforce documents response:** `GET /workforce/employees/{id}/documents` больше не отдаёт recruitment candidate `/file` URLs (`cand_doc_for_workforce_hr_response`); HR SPA убран `downloadUrl` из `listWorkforceEmployeeDocuments`; регрессионные тесты. См. [`current-separation-status-recruitment-hr-doc-hub.md`](current-separation-status-recruitment-hr-doc-hub.md). |

**Отдельная строка журнала (recruitment write lock — stand verification):**

| Result | Evidence | Violation |
|--------|----------|-----------|
| PASS | Recruitment write lock after WorkforceEmployee materialization works; return flow releases lock; admin override remains explicit; bulk paths checked. | resolved |

**Итог цикла (domain separation):** ownership Recruitment по operational dossier **заканчивается** в момент HR materialization (`WorkforceEmployee`) — не «логически» и не по договорённости, а **enforced**: ACL / `can_agency_user_edit_candidate`, lifecycle (в т.ч. return/reject снимают lock), явный admin override, закрыты bulk-пути. Инвариант подтверждён **execution** на стенде; contradiction остаётся в журнале как historical evidence.

Колонки **Pass?** / **OK?** допускают **нет** при подробных заметках: фиксируйте *что* и *где* нарушено и ссылку на тикет/PR с фиксом.

При **да** по DOD §1 — можно обновить §3 GAP и объявить фазу 1 закрытой по продуктовому критерию; AS-IS таблицу (§2) при необходимости синхронизировать в том же PR.

**Прогон стенда (operational verification) — закрыт:**

| Поле | Содержание |
|------|------------|
| **Result** | PASS |
| **Environment** | HostFlowDev / deployed backend + frontend |
| **Flow** | Candidate created → documents added → candidate transferred to HR/workforce → employee opened → HR documents visible → document file opened via Document Hub → HR review submitted. |
| **Evidence** | Все релевантные запросы — 200: `GET /api/v1/workforce/employees/{id}/documents`, hr-bundle, hr-operational-context, `GET /api/v1/db/documents/{document_id}/file`, `POST …/hr-review`, document checks после review. В хвосте логов нет старого `GET …/candidates/{id}/documents/{id}/file` → 401. |
| **Violation (этот прогон)** | Нет. |
| **Regression note** | Workforce `GET …/documents` санитизирован (без candidate `/file` в JSON); HR UI — только Hub по `document.id`. Не регрессировать к подстановке recruitment URL в этот ответ. |

**Прогон 2 — idempotency / repeated handoff (operational verification) — закрыт:**

| Поле | Содержание |
|------|------------|
| **Result** | PASS |
| **Environment** | HostFlowDev / deployed backend + frontend |
| **Scope** | Второй полноценный operational PASS после прогона 1: initial handoff → HR materialization → document reuse → HR review → **return flow** → **повторный handoff** того же кандидата → **duplicate protection / idempotency**. |
| **Подтверждает** | Handoff contract держится; ownership boundaries сохранены; materialization `WorkforceEmployee` идемпотентна; Document Hub не плодит копии файлов; повторный flow не ломает состояние; HR reviews не размножаются неконтролируемо; UI без дублей; HR case — одно или контролируемое поведение. |
| **Violation (этот прогон)** | Нет. |
| **Дальше** | Не расширять scope без **новой** operational contradiction (новый факт со стенда, регрессия или спорный PR/flow). |

**Operational contradiction: recruitment write после workforce (закрыт в коде):**

| Поле | Содержание |
|------|------------|
| **Result (на стенде до фикса)** | FAIL / contradiction found |
| **Issue** | После успешного handoff в HR рекрутинг всё ещё мог редактировать данные кандидата (PATCH). |
| **Classification** | Access / ownership violation after handoff |
| **Invariant** | Handoff transfers **edit responsibility**. Source сохраняет просмотр и историю, но **теряет write** на переданное operational dossier, кроме явных команд (return / reopen / admin override / correction flow). |
| **Expected** | Candidate dossier **readonly** для recruitment после internal HR materialization (`WorkforceEmployee`), пока нет return и т.п. |
| **Minimal fix** | Блокировать PATCH/update пути при наличии workforce-строки для `candidate_id`; bulk stage/manager — та же проверка; GET без изменений; admin — override; после `return_to_recruitment` — снова write для рекрутёра. |

**Доменный принцип (после фикса):** передача **operational edit responsibility** к HR фиксируется **фактом materialization** — наличие `WorkforceEmployee` по `candidate_id`, а не только транспортным артефактом `CandidateHandoff`. Return/reject internal HR **снимают** lock (в т.ч. удаление workforce-строки при return/reject), иначе возможен **irreversible ownership capture**.

**Чеклист стенда после деплоя (recruitment write lock):**

1. Recruiter `PATCH` → **403** после HR materialization.  
2. HR по-прежнему успешно редактирует там, где политика/ACL разрешают.  
3. Admin override на candidate-owned полях — только с **`override_reason`**.  
4. Return flow: `WorkforceEmployee` исчезает там, где canonical return это подразумевает; recruiter `PATCH` снова разрешён (при смене PII при необходимости с `override_reason`).  
5. Bulk stage / bulk manager — та же семантика (**403** для рекрутёра на заблокированных кандидатах).  
6. UI: **`can_edit`: false** и явный readonly, а не «сохранилось с неочевидной ошибкой».

**Прогон 3 — recruitment write lock (operational verification) — закрыт:**

| Поле | Содержание |
|------|------------|
| **Result** | PASS |
| **Environment** | HostFlowDev / deployed backend + frontend |
| **Evidence** | Recruitment write lock after WorkforceEmployee materialization works; return flow releases lock; admin override remains explicit; bulk paths checked. |
| **Violation** | resolved |

**Историческая запись: violation и фикс (HR document file preview):**

| Поле | Содержание |
|------|------------|
| **Result (до фикса)** | FAIL / partial: открытие файла из HR → 401 без `Authorization` на candidate route. |
| **Issue** | HR document file preview изначально открывал candidate-owned file URL в новой вкладке без заголовка `Authorization` → `401 Missing Authorization header`. |
| **Classification** | UI file access bug / stale Recruitment coupling (не ошибка HR handoff / backend ownership). |
| **Invariant** | HR обращается к переиспользуемым документам через Document Hub или разрешённый document-link context, а не через навигацию на Recruitment candidate file route. |
| **Fix** | `HrEmployeeDocumentsSection` открывает файлы через Document Hub: `downloadDocumentFile(documentId)` — authenticated запрос через `docsApi`, blob preview в новой вкладке. |
| **Regression risk** | *Снято (2026-05-08):* workforce list больше не отдаёт recruitment `file_url`; клиенты открывают файл через Hub по `document.id`. |
| **Follow-up (не срочно)** | ~~Опционально: в ответе workforce documents возвращать Hub file URL или `null`~~ — сделано: `null` + вырезание legacy URL во вложенных полях; Hub URL в list не добавлялся намеренно (идентичность `document.id` достаточна). |

**Минимальный ретест (после деплоя фикса):**

1. Открыть Employee в HR → раздел документов.  
2. Нажать «открыть файл».  
3. В логах/Network: **нет** `GET /api/v1/candidates/{candidate_id}/documents/{document_id}/file` с `401`.  
4. Есть authenticated запрос к Document Hub на скачивание/файл (как у `docsApi`).  
5. Повторить для двух документов, уже прошедших hr-review.

### 6.4 Граница Fleet (не часть Recruitment → HR прогона)

**Fleet boundary check: PASS** (по статическому разбору кода и намерению продукта).

- Fleet **не** потребляет Recruitment candidate-логику и **не** зависит от HR operational context напрямую.  
- Fleet **не** обращается к document links / `CandDoc` / `document_entity_link` в роутинге `/api/v1/fleet/*`.  
- Связь с HR — только через **явный** опциональный FK `fleet_drivers.workforce_employee_id` → `workforce_employees` (bridge в UI), **без** скрытой оркестрации.  
- **Вывод:** модуль Fleet **не входит** в обязательный тестовый контур «Recruitment → Document Hub → HR» для текущей цели; тестировать Fleet отдельно, если меняется сам транспортный домен.

### 6.5 Idempotency / duplicate protection (handoff) — чеклист (выполнен)

Использовался для **прогона 2** в **§6.3** (таблица журнала + блок «Прогон 2»).

1. Повторно перевести кандидата в **ready_for_hr** / **ready_for_handoff** (и далее по сценарию стенда).  
2. Ровно **один** `WorkforceEmployee`.  
3. **Один** HR case **или** явно **контролируемое** поведение по case.  
4. Документы **не копируются** (reuse через Hub / links).  
5. HR reviews **не плодятся** неконтролируемо при повторе.  
6. **UI** не показывает дублей.

**Статус:** PASS зафиксирован в **§6.3** (2026-05-07). **Сводка по ветке:** Recruitment → Document Hub → HR — PASS; HR file access — исправлен, PASS после ретеста; Fleet boundary — PASS, вне обязательного прогона; idempotency / repeated handoff — PASS (прогон 2).

**Дальше:** только новая operational contradiction — без расширения scope «про запас».

### 6.6 Operational write paths — enforcement audit (follow-up PR scope)

Enforcement audit found grey write paths after HR materialization:

- Document Hub DB API mutations by `candidate_id`
- `candidate_tasks` mutations
- `candidate_permits` mutations

**Next PR scope:** add operational-write guard to these paths only.  
**Out of scope:** RODO, document merge, visas/employments, delete-request, handoff create.

Главная цель PR: не расширить архитектуру, а закрыть известные bypass paths вокруг candidate-owned operational mutations.

**Статус (код):** operational guard (`ensure_candidate_operational_write_allowed` после ACL) на DB Hub mutations по `candidate_id`, `candidate_tasks` и `candidate_permits`; регрессия — `test_operational_write_guards_db_hub_tasks_permits_after_workforce_materialization` в `test_single_tenant_recruitment_hr_handoff_flow.py`.

> **(Phase 2.1, 2026-05-09)** `candidate_tasks` HTTP-роуты удалены; `test_operational_write_guards_db_hub_tasks_permits_after_workforce_materialization` теперь покрывает тот же readonly-инвариант через `POST /api/v1/activities` (recruiter ⇒ 403 `candidate_readonly`, admin ⇒ write проходит). Document Hub DB API + `candidate_permits` ветви guard'а не тронуты.

### 6.7 Next validation contour — return-to-recruitment consistency

После усиления lock/enforcement следующий риск — не сам readonly lock, а корректное снятие ownership lock при возврате кандидата из HR в Recruitment.

Проверяем не новые endpoints «по списку», а консистентность состояния после return.

**Цель:**

- после HR materialization Recruitment readonly включается;
- после canonical return-to-recruitment readonly снимается;
- `permissions.can_edit` пересчитывается корректно;
- `operational_owner` возвращается в recruitment;
- UI снова показывает editable state;
- mutation routes снова доступны там, где это продуктово разрешено;
- HR/Workforce state не оставляет «вечный lock»;
- повторный handoff после return не создаёт дублей.

**Проверить минимум:**

1. Candidate → HR materialization.
2. Recruiter `PATCH` / notes / tasks / permits / document mutation → 403 `candidate_readonly`.
3. Return to recruitment.
4. `GET /candidates/{id}` возвращает `can_edit=true`, `operational_owner=recruitment`.
5. Recruiter снова может: `PATCH` candidate; `POST` note; `POST` task; `POST` permit; `POST` candidate document через DB Hub, если это разрешено текущей моделью.
6. UI карточки кандидата снимает readonly.
7. Повторная передача в HR создаёт не дубли, а корректный новый/восстановленный flow согласно текущему контракту.

**Out of scope:**

- новые handoff events;
- Fleet;
- Communications;
- RODO / merge / visas / employments;
- phase 2 Document Hub model.

**Expected evidence:**

- один стендовый PASS или FAIL;
- при FAIL — root cause + minimal fix + regression test;
- запись в **§6.3**.

---

## 7. Связанные файлы кода (ориентиры для реализации и тестов)

- [`current-separation-status-recruitment-hr-doc-hub.md`](current-separation-status-recruitment-hr-doc-hub.md) — **Current Separation Status**: домены, маршруты, контракты, legacy, следующий validation-контур (Document Hub legacy).  
- `backend/app/constants/stages.py` — коды стадий, pipeline completed.  
- `backend/app/services/workforce_employees.py` — `WORKFORCE_HANDOFF_STAGE_CODES`, `handoff_from_candidate`, `should_workforce_handoff_on_stage_change_resolved`.  
- `backend/app/api/v1/tenants/router.py` + `schemas.py` — флаги tenant link (`workforce_handoff_on_ready_for_handoff_stage`).  
- `backend/app/services/workforce_hr_operational_context.py` — `ensure_hr_operational_context`.  
- `backend/app/models/workforce_hr_case.py`, `backend/app/models/document_entity_link.py`.  
- `backend/app/api/v1/workforce/router.py` — `hr-operational-context`, `hr-review`, список документов сотрудника.  
- `backend/app/api/v1/candidates/service.py` — вызов handoff при смене стадии.  
- `backend/app/models/document.py`, `backend/app/services/document_dossier_access.py` — зоны досье и доступ HR.  
- `backend/app/services/handoff.py`, `backend/app/api/v1/handoffs.py` — agency/client handoff (не путать с single-tenant stage path).  
- `backend/app/api/v1/fleet/*` — домен Fleet отдельно от Recruitment→HR; связь с HR только опциональный FK `workforce_employee_id` (см. **§6.4**).  
- `hostflow-frontend/src/pages/hr/HrEmployeeDocumentsSection.tsx` — контекст + HR review в UI; открытие файла — `downloadDocumentFile` (Document Hub), не candidate `/file` URL.  
- `hostflow-frontend/src/api/documents/file.ts` — `downloadDocumentFile` (authenticated blob).  
- `docs/specs/architecture/ADR-002-modular-recruitment-hr-boundary.md`, `ADR-009-document-hub-platform-layer.md`.

---

## 8. AI Agent Notes

- **Governance loop — остановлен** до operational фактов. Следующий разговор **не** начинать с «ещё опишем…» или «добавим abstraction…» — только с **операционного артефакта**: FAIL, regression, side effect, bypass, hidden orchestration, inconsistent flow, спорный PR, или **clean validation** (заполненный §6.3 и т.п.). Это и есть переход **architecture-definition → architecture-verification**.  
- **Ветка governance/architecture завершена** до появления operational evidence. Единственный источник изменений канона и кода на этом этапе: **execution**, **validation**, **regressions**, **violations**, **реальные противоречия flow** — не теоретическое расширение.  
- Приоритет этапа: **operational validation** (§6, цикл выше), не новые governance-доки без повторяющихся противоречий со стенда.  
- Не расширять scope на фазы 3–5, пока **§1 DOD фазы 1** не выполнен.  
- Любая задача формулируется как: «закрывает пункт GAP P0.x / шаг A/B фазы 1» с ссылкой на этот файл.  
- Перед изменением стадий или путей handoff — сверяться с [**handoff-contract.md**](../architecture/handoff-contract.md).  
- Ревью PR и интеграций — [**чеклист в operational-event-boundaries**](../architecture/operational-event-boundaries.md#review-checklist).  
- Стенд фазы 1 — заполнять **§6** (функциональный + governance + журнал).  
- При изменении поведения handoff или документов — обновлять AS-IS таблицу (§2) в том же PR, если меняется фактическая модель.
