# Operational Model Adoption Register

**Status:** canonical (L2 architecture — evolution map).  
**Owner:** Product + Platform UX + Architecture.  
**Parent canon:** [`hostflow-operational-model.md`](hostflow-operational-model.md) — L1 конституция продукта.  
**UI platform:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md) — HostFlow Platform Canon.  
**Product surface:** [`ui-constitution-v1.md`](ui-constitution-v1.md) — objects, ownership, Lead ban.  
**Build strategy:** [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md) — Phase 1: DataTable Engine.  
**Setup canon (Mode 2 Flow 1):** [`canonical-setup-flow.md`](../workflows/canonical-setup-flow.md).

**Назначение:** не список нарушений и не compliance audit. **Журнал приближения продукта к Operational Model** — что уже соответствует, что в переходе, что должно исчезнуть.

Operational Model отвечает на «можно ли?». Этот register — на «где мы сейчас и куда?». **Инструмент принятия решений** — не чек-лист симптомов: после аудита потока — **1–2 root-cause решения**, не десять задач на каждое замечание.

---

## 1. Как читать register

### 1.1 Статусы (по измерению)

Каждая **surface** (экран, route, API surface, паттерн) оценивается **по измерениям**, не одним общим вердиктом.

| Status | Смысл |
|--------|--------|
| **PASS** | Соответствует Operational Model (+ Platform Standards). Можно развивать в рамках модели. |
| **DEBT** | Работает, но противоречит модели. **Новые features запрещены**; bugfix и critical ops — да. Привести при первом крупном касании. |
| **REPLACE** | Противоречие настолько существенно, что **новое развитие запрещено** до миграции на canonical replacement. |

Одна surface может быть **PASS** по Domain и **REPLACE** по UX — это нормально и ожидаемо (пример: `/requirements` spike).

### 1.2 Измерения (dimensions)

| Dimension | Вопрос |
|-----------|--------|
| **Domain** | Бизнес-логика, ownership, gates, data continuity — соответствуют §3–§6 и module canon? |
| **Platform** | Контракты, API, capabilities (Hub, Requirement Engine, handoff) — правильный platform path? |
| **UX** | Операционная модель §3.1–3.2, ADR-010/011/017 — зоны, rail, navigation, без дублей? |
| **Architecture** | Traceability §0.2, Forbidden F1–F7, dependency direction — без архитектурного дрейфа? |

### 1.3 Reason (почему не PASS)

Фиксируется при первой классификации; не пересматривать без смены статуса.

| Reason code | Когда использовать |
|-------------|-------------------|
| **Legacy UI** | Экран/компонент до ADR-017 и §3.2 zones |
| **Pre-Operational Model** | Решение до freeze конституции; поведение «исторически сложилось» |
| **Spike** | Намеренный proof-of-contract; product path определён отдельно |
| **Temporary compatibility** | Dual-stack, strangler, backward-compat path с известным sunset |
| **External dependency** | Блокер вне HostFlow (интеграция, migration window) |
| **Waiting for Platform Step** | Ждёт platform layer (registry, aggregation, Step N в ADR-017) |
| **Waiting for Module Refactor** | Platform готов; module card/workspace refactor не завершён |

Допускается несколько reason через `;`.

### 1.4 Legacy freeze (правило миграции)

> **Legacy допускается существовать, но не допускается развиваться.**

| Разрешено на DEBT/REPLACE surface | Запрещено |
|-----------------------------------|-----------|
| Bugfix, security, critical production | Новые features, новые секции, новый UX |
| Минимальные правки для совместимости | «Временно» без ticket (Forbidden F7) |
| Миграция на **Canonical Replacement** при refactor trigger | Big Bang без trigger |

---

## 1.5 HostFlow Platform Canon Program (active)

**Nearest goal:** Phase 1 DoD + Interaction Rules enforcement → Phase 2 Entity Workspace.

| Layer | Focus | Status |
|-------|-------|--------|
| Foundation | tokens, grid, type | ADR-011 |
| **Interaction Rules** | click, keyboard, selection, navigation, editing | **CANON DEFINED** — enforce in code |
| **Primitives** | DataTable + Selection + Detail Rail | **ACTIVE (Phase 1)** |
| Compositions | Entity Header, Context Rail, … | Phase 2 |
| Workspaces | Collection · Entity · Application · Process | Entity next |

**Supreme rule:** any UI change → canon first, then platform, then modules.

Canon: [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md), [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md).

---

## 1.6 UI Primitives Program (legacy section title)

Same as §1.5 — retained for changelog continuity.

---

## 2. Adoption register

**Legend:** `D` = Domain · `P` = Platform · `U` = UX · `A` = Architecture

| Surface | D | P | U | A | Reason | Canonical Replacement | Owner | Refactor Trigger | Backlog / link | Notes |
|---------|---|---|---|---|--------|----------------------|-------|------------------|----------------|-------|
| **Candidate Card** (`/app/candidates/:id`) | PASS | DEBT | DEBT | DEBT | Legacy UI; Waiting for Platform Step | Same route — declarative §3.2: SectionRegistry + **single** Status Rail + capability renderers in work area ([ADR-017](ADR-017-workspace-layer.md) Step 6) | Recruitment FE + Platform UX | Step 6 kickoff; any epic touching card layout/status | [`workspace-layer-contracts-p0.md`](../platform/workspace-layer-contracts-p0.md) §4 Step 6; [`a3-requirements-workspace-backlog.md`](../tasks/a3-requirements-workspace-backlog.md) §2.1 | Header/timeline/stage — keep. Retire triple parallel checklists in rail. |
| **`/requirements` route** | PASS | PASS | REPLACE | PASS | Spike; Pre-Operational Model product path | Candidate Card → Requirements **section** (`?section=requirements` or tab); retire route ([`workspace-layer-contracts-p0.md`](../platform/workspace-layer-contracts-p0.md) Step 6c) | Platform + Recruitment FE | Step 6b–6c | ADR-017 Step 5 lesson; operational model §0.3 | Spike **PASS** for contracts. Product evolution on route = **REPLACE**. Bugfix only until retire. |
| **Requirement Runtime — engine** | PASS | PASS | — | PASS | — | — (canonical) | Platform + Recruitment | — | [`requirement-rules-engine-p0.md`](../platform/requirement-rules-engine-p0.md), evidence model | Rules Engine, blockers, transfer-readiness API — source of truth. |
| **Requirement Runtime — presentation** | PASS | DEBT | DEBT | DEBT | Legacy UI; Waiting for Platform Step | `RecruitmentRequirementsCapabilityRenderer` **inside** card work area; remove `RECRUITMENT_DOSSIER_BLOCKS` as primary | Recruitment FE | Step 6b; A3-FE consolidation | [`a3-requirements-workspace-backlog.md`](../tasks/a3-requirements-workspace-backlog.md) §1–2 | Three parallel UI surfaces today; FE catalog duplicates API (F5). |
| **Employee Card (HR Dossier)** | PASS | PASS | DEBT | DEBT | Legacy UI; Waiting for Module Refactor | Same route — `context=hr` workspace: sections + Status Rail + next action ([ADR-017](ADR-017-workspace-layer.md)) | HR module FE + Platform UX | First HR card epic post Candidate Step 6 template | [`implementation-roadmap-single-tenant-hr-handoff.md`](../workflows/implementation-roadmap-single-tenant-hr-handoff.md) | Backend/Hub/handoff enrichment PASS on stand. UI not yet §3.2 declarative. |
| **Lead Intake** (Lead detail) | DEBT | PASS | DEBT | DEBT | Pre-Operational Model; Legacy UI | **Intake Decision Workspace** — `context=intake`; convert/reject only; no mini-Candidate ([`lead-intake-resolution-and-activity-continuity.md`](../workflows/lead-intake-resolution-and-activity-continuity.md)) | Recruitment FE + Product | Intake Resolution slices 4–6 stable; any Lead detail redesign | [`recruitment-operational-goals-and-order.md`](../workflows/recruitment-operational-goals-and-order.md) §3 | Forbidden: dossier, driver checklist, handoff fields on Lead. |
| **Document Hub — data & API** | PASS | PASS | — | PASS | — | — (canonical for new doc flows) | Document Hub / Platform | — | ADR-009; stand verification in implementation roadmap | Recruitment SPA → Hub; HR file via Hub — verified. |
| **Document Hub — UI embedding** | PASS | DEBT | DEBT | PASS | Waiting for Module Refactor | Hub-native sections in Candidate / Employee / Vehicle cards; optional standalone Hub screen ([`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §10) | Document Hub + module FE | Card refactor per module; Document Hub UI epic | [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md) | Full Hub screen not complete; embedding incomplete. |
| **Legacy candidate file routes** (`/candidates/.../file`) | DEBT | REPLACE | — | DEBT | Temporary compatibility; Pre-Operational Model | Document Hub file API only | Platform + Recruitment | Last consumer migrated to Hub download path | Implementation roadmap § Hub vs legacy inventory | Backend/public intake only; freeze — do not extend. |
| **Form Builder (P10A)** | PASS | PASS | DEBT | PASS | Temporary compatibility (dual-stack) | Lead-first public intake forms; presentation-only role locked ([`recruitment-operational-goals-and-order.md`](../workflows/recruitment-operational-goals-and-order.md) §5) | Forms + Recruitment | Legacy candidate reuse path retired | ADR-007; a3 backlog intake notes | Business requiredness **never** in Form Builder — Requirement Engine only. |
| **Pipelines — module-owned** | PASS | PASS | — | PASS | — | — (target for new stages) | Recruitment / HR module owners | — | [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) | HR `employee_pipeline` post-handoff — Done. |
| **`system_stage` (global legacy)** | DEBT | DEBT | DEBT | DEBT | Temporary compatibility; Pre-Operational Model | Module-owned pipeline manifest per company | Platform + modules | Module-owned pipelines P0 gate closed | module-catalog § Architecture gate | Strangler — no new semantics on global stage. |
| **Transfer / Handoff — platform contract** | PASS | PASS | — | PASS | — | — (canonical) | Platform + HR + Recruitment | — | Gates 409, fulfillments, idempotency, write lock — stand PASS | 
| **Transfer / Handoff — UX gates** | PASS | PASS | DEBT | PASS | Waiting for Module Refactor | Unified Status Rail blockers from `transfer-readiness`; no separate handoff-only UX | Recruitment FE | Step 6a single rail; handoff modal reads same aggregation | [`recruitment-operational-goals-and-order.md`](../workflows/recruitment-operational-goals-and-order.md) §6 | Risk: handoff before perfect closure — strengthen UI blockers, not new flow. |
| **`CandidateProfile` JSON config** | DEBT | REPLACE | — | DEBT | Pre-Operational Model | Entity Profile + Requirement Rules sources | Recruitment + Platform | Entity Profile mapped for active recruitment profiles | consumer-setup-flow; config_deprecation | UI label: «Требования к кандидату», not legacy config name. |
| **`RECRUITMENT_DOSSIER_BLOCKS` (FE catalog)** | DEBT | REPLACE | DEBT | DEBT | Legacy UI; Pre-Operational Model | `requirements/workspace` / checklist API as single UI source | Recruitment FE | A3-FE4; Step 6b | a3 backlog §2.3 | Duplicates requirements API (Forbidden F5). |
| **Onboarding activation path** (Wizard + Getting Started + Company ready) | DEBT | **REPLACE** | REPLACE | DEBT | Pre-Operational Model; Legacy UI; **PI-1 violation** (v4) | Guided traversal **S0–S5** per [`canonical-setup-flow.md`](../workflows/canonical-setup-flow.md); **PI-1 enforce-at-publish** per [`platform-backlog.md`](../platform/platform-backlog.md) | Product + Platform UX | Slice **Enforce Next Action Reachability** → re-audit v4 | [`platform-backlog.md`](../platform/platform-backlog.md) | Setup Status PASS; platform published unreachable next action (no pre-publish reachability check) |
| **Health Check screen** | — | REPLACE | REPLACE | PASS | Waiting for Module Refactor | **Projection of gates G0–G8** (canonical-setup-flow §4) | Product | After S0–S5 canon accepted | canonical-setup-flow §4–5 | Not implemented in SPA |
| **Intake routing UX (Meta / forms)** | PASS | DEBT | REPLACE | DEBT | Temporary compatibility; Pre-Operational Model | **S4 Sources** surface: full route row per canonical-setup-flow §3 | Platform + Recruitment | Flow 1 implementation | canonical-setup-flow §3–4; consumer-setup §4 | Meta admin + dual stack |

---

## 3. Mixed-status examples (official pattern)

### `/requirements` route

| Dimension | Status | Why |
|-----------|--------|-----|
| Domain | PASS | Requirements closure logic correct |
| Platform | PASS | SectionDeclaration, ReadinessContribution, aggregation proved |
| UX | REPLACE | Second status rail; «open workspace» from inside workspace (F2/F3) |
| Architecture | PASS | Spike followed ADR-017 order; lesson captured |

**Decision:** keep route for bugfix/spike reference only; **product evolution forbidden** until Step 6c retire.

### Requirement Runtime

| Dimension | Status | Why |
|-----------|--------|-----|
| Domain | PASS | Engine + gates + evidence |
| Platform | PASS | APIs consumed by adapters |
| UX | DEBT | Three parallel checklist UIs |
| Architecture | DEBT | FE catalog parallel to API |

---

## 4. Flow audit protocol (active phase)

**Фаза:** прогон существующих пользовательских потоков через Operational Model. **Не** писать новые ADR/стандарты до завершения первого прохода.

**Смена процесса разработки:**

```text
Было:   идея → спецификация → реализация → тест
Стало:  поток → расхождения с Operational Model → первопричина →
        архитектурное решение → реализация → повторный прогон потока
```

Пользовательский поток — **источник архитектурных решений**, не только сценарий тестирования.

### 4.1 Два режима (жёсткое разделение)

Во время аудита **запрещено проектировать решение**. Большинство архитектурных ревью ломается именно здесь: обсуждение первой кнопки вместо оценки всего пути.

#### Режим 1 — Диагностика

| Разрешено | Запрещено |
|-----------|-----------|
| Пройти путь пользователя целиком | Рисовать новый экран |
| Ответить на три вопроса (§4.4) | Обсуждать UI / layout |
| Зафиксировать расхождения | Писать API / контракты |
| Определить первопричину | Придумывать рефакторинг |

**Результат диагностики:** одна запись в Adoption Register (формат §4.5) + обновление §2 surfaces. Ничего больше.

#### Режим 2 — Проектирование

**Только после** завершения диагностики потока.

- Берётся **одна** первопричина из записи.
- Проектируется **одно** изменение с максимальным устранением расхождений.
- Traceability: решение выводится из Operational Model (+ ADR при необходимости).
- После реализации — **повторный прогон того же потока** (диагностика снова, режим 1).

Режимы **не смешиваются** в одной сессии и не смешиваются в одном PR.

### 4.2 Одна итерация = один полный поток

| Правило | Смысл |
|---------|--------|
| Пройти **весь** поток | Onboarding от начала до «готов принять первый лид» — без остановок |
| **Ничего не исправлять** во время прохода | Десять «хочется исправить» — только в observations, не в обсуждении |
| **Только фиксировать** | Gaps, surfaces, intent mismatch |
| **Одно root-cause решение** — после завершения потока | Не на первой найденной проблеме |

Если аудит остановился на первой проблеме — итерация **не засчитывается**. Начать поток заново или явно зафиксировать «аудит прерван».

### 4.3 Порядок (зависимость слоёв)

Каждый следующий поток опирается на предыдущий. Ошибка в раннем слое обесценивает рефакторинг поздних.

| # | Поток | Scope (кратко) | Статус аудита |
|---|-------|----------------|---------------|
| 1 | **Onboarding & setup** | Покупка → tenant/company → routing → готовность принять первый лид | ✅ audit complete · **FAIL** Slice B v4 · open: Enforce Next Action Reachability |
| 2 | **Lead** | Получение → routing → decision → convert | pending |
| 3 | **Candidate** | Карточка → документы → requirements → readiness | pending |
| 4 | **Handoff** | Gates → fulfillments → materialization | pending |
| 5 | **HR** | Employee card → verification → employment | pending |
| 6 | **Fleet / прочие модули** | По мере активации | pending |

Справочно для потока 1: [`consumer-setup-flow-people-to-employee.md`](../workflows/consumer-setup-flow-people-to-employee.md).

### 4.4 Три вопроса (только режим 1 — диагностика)

На каждый поток — **только** диагностика. Решения и backlog — **после** фиксации gap.

1. **Что пользователь хочет сделать?** (intent одной фразой)
2. **Что система заставляет его сделать?** (шаги, экраны, дубли)
3. **Совпадают ли эти две вещи?**

Если нет — gap найден. **Не искать решение сразу.**

Пример:

| Intent | Система заставляет | Gap |
|--------|-------------------|-----|
| «Принять кандидата» | 3 вкладки, 2 списка, отдельный экран, confirm в другом месте | UX drift от §3.2 |

Затем — классификация surfaces в §2 (D/P/U/A + Reason). Рефакторинг — отдельный шаг.

### 4.5 Одно root-cause решение на поток (переход в режим 2)

После аудита — **максимум 1–2 решения**, которые устраняют **максимум** отклонений.

| Плохой исход | Хороший исход |
|--------------|---------------|
| 18 замечаний → 18 задач | 18 замечаний → **1 решение:** «объединить три источника статуса в один Status Rail» → половина симптомов исчезает |

**Формат записи после аудита потока:**

```text
Flow: <name>
Intent gap: <1–2 предложения>
Observations: <N> (для истории, не backlog)
Decision (1–2):
  1. <минимальное изменение → canonical replacement>
Surfaces updated in §2: <список>
Refactor trigger: <когда>
```

Пример (Candidate, ожидаемый):

```text
Decision: Single Status Rail via platform aggregation (Step 6a).
         Retire /requirements as product surface (Step 6c).
```

### 4.6 Flow audit records

#### Flow 1 — Onboarding & setup (2026-07-03)

**Эталон intent (шаг 1):** «Купил HostFlow и хочу начать получать кандидатов.»  
**Критерий конца потока:** система **готова принять первый лид** (канон: [`consumer-setup-flow`](../workflows/consumer-setup-flow-people-to-employee.md) §6 Health Check — все ✅).

**Проход (шаг 2) — agency, Meta как типичный канал:**

| # | Шаг | Intent пользователя | Система требует | Совпадает? |
|---|-----|-------------------|-----------------|------------|
| 1 | Signup | Зарегистрироваться и начать | Workspace name, email, password, два consent | ✅ |
| 2 | Company create | Создать компанию, выбрать тип бизнеса | Name, type, industry, team size, hours preset | ⚠️ Избыточно для «получать кандидатов», но не блокирует |
| 3 | Post-company «ready» | Понять, что дальше | Magic animation + **demo pipeline stats** + CTA wizard **или** dashboard | ❌ Показывает фиктивный pipeline до реальной настройки |
| 4 | Wizard step 1 (type) | — | Confirm workspace already ready | ⚠️ Redundant после company page |
| 5 | Wizard step 2 (channel) | Подключить источник лидов | Выбрать канал → **открыть другую страницу** (Meta / forms / webhook) в новой вкладке; можно **Skip** | ❌ Не завершает подключение; routing не настраивается |
| 6 | Wizard step 3–4 (client, vacancy) | Настроить, куда попадут люди | Client + vacancy forms; оба **Skip** | ❌ Без vacancy routing для Meta не замкнут |
| 7 | Meta integration (если Meta) | Настроить маршрут формы | Settings → Integrations → Meta: OAuth, field mapping, **intake route** (`putMetaFormRoute`) — отдельно от «Источники»; параллельно `meta_ads_map` | ❌ Два routing surface; не vacancy→funnel→requirements→assignee |
| 8 | Funnel + requirements | Настроить этапы и требования | **Не в onboarding path**; funnel — Settings → Funnels (Getting Started checklist); entity profile — «Entity Profile» в form admin | ❌ Ключевые шаги канона §3B вне потока |
| 9 | Wizard step 5 / finish | Увидеть, что система готова | Ждать реальный lead **или** seed demo **или** «Finish setup anyway» | ❌ «Готовность» = wizard finished, не intake readiness |
| 10 | Activation gate (backend) | — | Agency: `first_lead_created` **и** `next_action_created` (reminder) | ❌ Скрытый критерий; не совпадает с intent пользователя |
| 11 | Health Check | Одним экраном проверить готовность | **Экрана нет** в SPA | ❌ Канон §6 не реализован |

**Observations:** 11 шагов; **7 явных gap**; **2 partial**.

**Intent gap (сводка):** пользователь хочет один понятный путь «настроил → готов принимать людей»; система разводит setup по **трём onboarding UI**, **Integrations/Meta admin**, **Lead Forms**, без единого **readiness end state** и без **Sources-centric routing** из consumer-setup-flow.

**Root-cause decision (1) — режим 1:**

> В продукте **отсутствовала единая операционная модель подготовки системы к первому рабочему результату**. Пользователь нигде не проходит один законченный операционный процесс. Narrative, Wizard, Health Check, «Источники» — следствия; не первопричина.

**Mode 2 decision (1) — канонический процесс:**

> Принят **[`canonical-setup-flow.md`](../workflows/canonical-setup-flow.md)** — S0–S5, gates G0–G8, определение **READY**. UI (onboarding, Sources, Health Check) — guided traversal и проекция gates; **не** отдельные процессы.

**Surfaces updated in §2:** Onboarding activation path, Health Check screen, Intake routing UX (Meta/forms).

**Refactor trigger:** реализация S0–S5 + readiness snapshot → **повторный Flow 1 audit (режим 1)** → только после PASS READY переход к Flow 2.

**Operational Model refs:** §3.1, §4 rules 3–4, §0.2, Forbidden F6–F7.

---

#### Flow 1 Re-Audit v4 — Slice B (2026-07-03) — **EXPERIMENT COMPLETE**

**Протокол (frozen):** единица наблюдения = **Next Action** (не gate). Скрытые шаги: **Type 1** (следующий экран показывает что делать) / **Type 2** (пользователь должен догадаться). После каждого action — **Confidence:** «Я уверен, что знаю, что делать дальше?» Да/Нет.

**Slice B success criteria (все 5 — иначе FAIL):**

1. Next action корректен.
2. Gate меняет состояние после действия.
3. Нет скрытых обязательных шагов Type 2 вне next actions.
4. READY достигается автоматически после последнего blocker gate.
5. После каждого next action Confidence = **Да** (операционная модель понятна без внешних знаний).

**Acceptance для повторного v4 (после platform slice):** платформенный контракт PI-1 — для **любого** Next Action:

```text
1. опубликован
2. достижим
3. выполняется
4. изменяет состояние
5. публикует следующий Next Action
```

Не «G4 работает» — тот же протокол v4, без ослаблений.

**Primary tenant:** fresh — `sliceb1783086549@work-host.com` (workspace «Slice B Audit Fresh»).  
**Control tenant:** legacy — `biuro@work-host.com` (314 companies, «Host Flow»).  
**Объект:** https://hostflow.cc · код не менялся во время аудита.

**Intent (эталон):** «Подключил HostFlow — хочу довести setup до READY, следуя только тому, что система называет следующим действием.»

**Вердикт Slice B: FAIL** — цепочка обрывается на action №3; READY не достигнут (6/9 gates).

##### Таблица next actions (fresh tenant)

| № | Next Action | Ожидание | Факт | Gate Δ | Скрытый шаг | Confidence |
|---|-------------|----------|------|--------|-------------|------------|
| 0 | *(pre-chain)* Continue setup после «Система готова» | Hub setup status | Demo-stats + лишний клик; не в цепочке next actions | — | **Type 2** | Нет |
| 1 | Добавьте клиента | Создать клиента, понять что дальше | → clients; модал создания (**Type 1**); после save — карточка клиента, **нет return к hub** | 4/9→5/9 G2 | Type 1 + **Type 2** return | Нет |
| 2 | Создайте активную вакансию | Создать вакансию | → `/vacancies/new`; title + client → save OK; остаётся на форме | 5/9→6/9 G3 | Type 1 form; **Type 2** return | Нет |
| 3 | Привяжите вакансию к воронке | Открыть экран привязки | Link → `/app/settings/funnels`; **redirect на getting-started** (activation lock Slice A). Карточка вакансии — поля воронки нет. `/app/work` заблокирован | **нет** G4 FAIL | **Type 2** dead end | Нет |

Actions G5–G8 **не прогонялись** — next action недостижим.

##### Control (сравнение при том же snapshot 6/9)

| | Fresh | Control |
|---|-------|---------|
| Клик «Привяжите вакансию к воронке» | redirect → hub | открывается `/app/settings/funnels` |
| Страница воронок | недоступна | Internal Server Error; пустой список |

Одинаковый readiness snapshot — **разное** поведение next action между tenants (secondary observation; primary FAIL не снимает).

##### Установленный root cause (режим 1 — впервые с доказательством)

> **Платформа не проверяет достижимость Next Action перед публикацией.**

Следствие (наблюдаемое): Next Action **опубликован**, но **недостижим** — система говорит «сделайте X», затем в том же состоянии делает X невыполнимым (пример v4: `handler_ref` = `/app/settings/funnels` + activation lock). Это не маршрутизация как первичная причина и не wording — **нарушение Operational Model**.

Сегодня проявление — G4 / funnels. Завтра — HR, Fleet, любой surface с тем же контрактом публикации.

**Platform invariant (первый experiment-born):** **PI-1 Enforce Next Action Reachability** — [`platform-backlog.md`](../platform/platform-backlog.md). Новые PI — только после воспроизводимого эксперимента (platform-backlog §0).

##### Mode 2 decision (1) — не «G4 fix», не allowlist-first

> Открыть platform slice **[Enforce Next Action Reachability](../platform/platform-backlog.md)** — **контракт:** недостижимый Next Action не публикуется; reachability evaluation перед snapshot/rail/hub. **Механизм** (allowlist, bypass, alternative handler) — шаг 2, не название slice. После merge — **повтор v4** (протокол frozen).

**Surfaces updated in §2:** Onboarding activation path (Platform → REPLACE по PI-1).

**Refactor trigger:** close Enforce Next Action Reachability → re-audit v4 fresh tenant → PASS PI-1 acceptance (5-step cycle) → Flow 2 audit.

**Slices закрыты в этой итерации:** FE-1 (projection), Slice A (entry collapse). **Slice B experiment:** complete FAIL. **Не открывать:** Slice G4 Fix; allowlist/guard как первая задача без publish-time contract.

---

## 5. Обновление register

| Событие | Действие |
|---------|----------|
| Новая surface или крупный refactor | Добавить/обновить строку **до merge**; PR ссылается на surface + статусы |
| DEBT → PASS | Changelog + закрыть backlog link |
| REPLACE → retired | Пометить surface **Retired** с датой; оставить строку для истории |
| Спор «можно ли feature?» | Сначала Operational Model §0.3; затем статус surface здесь |
| Gap не покрыт §3–Forbidden | **Не** расширять register правилами — эскалация в Operational Model §11 |

**PR template:** строка про Adoption Register — **не обязательна**, пока команда несколько недель не использует register на практике. Иначе — формальное заполнение без пользы. После стабилизации практики — вынести в `.github/pull_request_template.md`.

---

## 6. Связь с другими документами

| Документ | Роль |
|----------|------|
| [`hostflow-operational-model.md`](hostflow-operational-model.md) | Конституция — что разрешено |
| **This register** | Карта эволюции — где мы и куда |
| [`hostflow-interaction-architecture.md`](hostflow-interaction-architecture.md) | Platform standards overview |
| [`ADR-017-workspace-layer.md`](ADR-017-workspace-layer.md) | Workspace migration strategy |
| [`workspace-layer-contracts-p0.md`](../platform/workspace-layer-contracts-p0.md) | P0 implementation order (Steps 1–6) |
| [`recruitment-operational-goals-and-order.md`](../workflows/recruitment-operational-goals-and-order.md) | Recruitment stage order |
| [`platform-backlog.md`](../platform/platform-backlog.md) | Platform invariants (PI-1+) and open platform slices |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | PI-1 enforce-at-publish; slice Enforce Next Action Reachability; platform-backlog §0 experiment-first rule |
| 2026-07-03 | Flow 1 Re-Audit v4 (Slice B) complete — FAIL; root cause: no pre-publish reachability check |
| 2026-07-09 | UI Primitives Program §1.5 — UDT phase 1; supersedes workspace-first program |
| 2026-07-09 | Canonical Workspaces Program §1.5 (superseded) |
| 2026-07-03 | [`platform-backlog.md`](../platform/platform-backlog.md) — PI-1 (first experiment-born invariant) |
| 2026-07-03 | Mode 2 Flow 1: canonical-setup-flow.md (S0–S5, G0–G8, READY) |
| 2026-07-03 | Flow 1 audit complete (§4.6); §2 surfaces updated |
| 2026-07-03 | §4.1–4.2: Diagnosis vs Design modes; one iteration = one full flow; process shift |
| 2026-07-03 | §4 Flow audit protocol: layer order, 3-question rule, 1–2 root-cause decisions; PR template deferred |
| 2026-07-03 | Initial register: dimensional PASS/DEBT/REPLACE, Reason taxonomy, Canonical Replacement, legacy freeze |
