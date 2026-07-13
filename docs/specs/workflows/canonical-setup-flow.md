# Canonical Setup Flow

**Status:** canonical (L2) — **операционная модель подготовки системы к первому рабочему результату**.  
**Hierarchy:** L2 workflow canon.  
**Owner:** Product + Platform UX + Architecture.

**Родительский принцип:** [`hostflow-operational-model.md`](../architecture/hostflow-operational-model.md) — единый способ работы; setup **не** исключение из traceability и gates.

**Flow 1 audit (режим 1):** [`operational-model-adoption-register.md`](../architecture/operational-model-adoption-register.md) §4.6.

**Delivery KPI (M1 implementation):** [`first-successful-customer-journey.md`](../journeys/first-successful-customer-journey.md) — DoD, product contracts, backlog, browser E2E, human gate.

**Назначение:** зафиксировать **один законченный операционный процесс** от «новый клиент HostFlow» до состояния **«готов принимать людей»**. Без UI, wizard, макетов. Экраны — следствие этого документа, не наоборот.

**Не покрывает:** поведение после первого контакта (Lead → Candidate → …) — [`people-lifecycle-workflow.md`](people-lifecycle-workflow.md). Пользовательская терминология и полная ось «до сотрудника» — [`consumer-setup-flow-people-to-employee.md`](consumer-setup-flow-people-to-employee.md) (UI-язык, autopilot, Employment Lifecycle).

**Первопричина Flow 1 (уточнённая):** в продукте отсутствовала **единая операционная модель подготовки системы к первому рабочему результату**. Narrative, Wizard, Health Check и «Источники» — **следствия** этой модели, не сами по себе.

### Ключевой принцип HostFlow (setup)

> **HostFlow не ведёт пользователя по заранее написанному сценарию.** HostFlow показывает **текущее состояние системы** и **одно следующее действие**, необходимое для достижения готовности.

Wizard, Health Check, Sources — **не требования**. Единственное требование: система должна перейти в состояние **READY**. UI — способы привести пользователя в это состояние; их можно заменить (например, Wizard → «Setup Status») **без изменения** этого документа.

---

## 1. Какую цель хочет достичь пользователь?

Одна формулировка intent (эталон Flow 1 audit):

> **«Я подключил HostFlow и хочу, чтобы система была готова принимать людей из моих каналов — без сюрпризов при первом контакте.»**

| `business_type` | «Люди» в первом результате | Первый рабочий результат *после* ready |
|-----------------|----------------------------|----------------------------------------|
| **agency** | Входящие контакты → лиды/кандидаты для клиентов | Lead ingest с известным маршрутом |
| **employer** | Кандидаты на свои вакансии | Lead ingest с известным маршрутом |
| **services** | Входящие запросы (лиды клиентов) | Lead ingest с известным маршрутом |

**Не цель setup:** нанять первого человека, закрыть требования, передать в HR, увидеть demo pipeline, «пройти wizard», создать reminder.

**Граница процесса:** setup **заканчивается до** первого реального inbound signal. Первый Lead — **проверка** ready state, не его определение.

---

## 2. Какие минимально необходимые шаги существуют?

Setup — **линейный операционный процесс** с обязательными gates. Пропуск шага без явного «не применимо для business_type» = процесс **не завершён**.

```text
S0  Workspace exists          (tenant + operator account)
S1  Operating context         (company + business_type)
S2  Hiring context            (client если agency · vacancy)
S3  Process context           (funnel + requirement profile)
S4  Intake route              (source → полный маршрут + «запомнить»)
S5  Readiness verified        (все gates → READY)
```

| Шаг | Обязателен | Пропуск |
|-----|------------|---------|
| **S0** | Всегда | — |
| **S1** | Всегда | — |
| **S2 client** | `agency` | `employer`, `services`* |
| **S2 vacancy** | `agency`, `employer` | `services`* |
| **S3 funnel** | Recruitment hiring (`agency`, `employer`) | `services` — свой pipeline preset |
| **S3 requirement profile** | Recruitment hiring | По профилю вакансии / entity profile code |
| **S4 intake route** | Всегда (мин. один source или явная manual policy) | — |
| **S5 readiness** | Всегда | — |

\* `services`: hiring context = client **или** явная политика «лиды без клиента»; см. §3.

**Инварианты (из Operational Model + consumer-setup §0):**

1. **Один маршрут на источник** — настраивается один раз; повторный inbound с тем же ключом **не** спрашивает маршрут снова.
2. **Маршрут живёт в Intake Routing** — не в Meta-only таблице, не только внутри вакансии, не только в form builder.
3. **RODO / consent** — не шаг setup-мастера; gate на этапе работы с контактом ([`consumer-setup-flow`](consumer-setup-flow-people-to-employee.md) §5).
4. **Setup не создаёт Candidate** — только контекст для Lead ingest.

**Запрещено в каноническом процессе (симптомы Flow 1 audit):**

- Завершение setup без прохождения S5.
- «Finish anyway» без failed gates.
- Скрытые критерии активации (`first_lead_created`, `next_action_created`) как **определение** ready.
- Demo seed как имитация ready state.
- Три параллельных onboarding UI без единого S0–S5.

---

## 3. Какие объекты создаются на каждом шаге?

| Шаг | Оператор видит (UI-язык) | Платформенные объекты (минимум) | Owner |
|-----|--------------------------|----------------------------------|-------|
| **S0** | Регистрация / покупка | `Tenant`, `User`, membership | Platform |
| **S1** | Компания, тип бизнеса | `OwnCompany` / operating `Company`, `business_type` | Tenant admin |
| **S2a** | Клиент (agency) | `Company` (role=client) | Recruitment |
| **S2b** | Вакансия | `Vacancy` → `owner_company_id`, client link | Recruitment |
| **S3a** | Воронка / этапы отбора | Module-owned `Funnel` + stages | Recruitment |
| **S3b** | Требования к кандидату | `Entity Profile` binding (`entity_profile_code`) | Platform + Recruitment |
| **S4a** | Источник (Meta, форма, …) | Provider connection + `IntakeSourceProfile` | Platform Intake |
| **S4b** | Маршрут источника | `IntakeSourceBinding`: source → vacancy, funnel, profile, assignee | Intake Routing |
| **S5** | Проверка готовности | **Readiness snapshot** (computed, не ручной флаг) | Platform aggregation |

**Маршрут (S4b) — одна строка, пять колонок** ([`consumer-setup-flow`](consumer-setup-flow-people-to-employee.md) §3C):

```text
Источник → Вакансия → Воронка → Требования к кандидату → Ответственный
```

Платформа: `external_key` / binding → `vacancy_id`, funnel ref, `entity_profile_code`, `default_assignee_id`.

**Manual intake policy** (если нет внешнего канала на старте): явная запись «оператор создаёт Lead вручную» + S2–S3 выполнены; S4a = `provider=manual`, binding optional до первого external source.

---

## 4. Какие проверки должны пройти?

Каждый шаг имеет **gate**. Gate **блокирует** переход к S5, пока не PASS. Проверки **вычисляются** из данных (Operational Model §4 rule 4), не из «галочки в wizard».

### Gate table

| Gate ID | Проверка | PASS когда |
|---------|----------|------------|
| **G0** | Workspace | Tenant active; ≥1 admin user |
| **G1** | Operating context | Operating company exists; valid `business_type` |
| **G2** | Client (agency) | ≥1 client `Company` **или** явный waiver «работаю только с одним implicit client» (employer path) |
| **G3** | Vacancy | ≥1 active `Vacancy` в scope operating company |
| **G4** | Funnel | Vacancy (или tenant default) привязана к funnel с ≥1 stage |
| **G5** | Requirement profile | Vacancy/recruitment context имеет resolved `entity_profile_code` с активным ruleset |
| **G6** | Source connected | ≥1 intake source **active** (credentials / published form / webhook endpoint) **или** manual policy declared |
| **G7** | Route complete | Для каждого active source: binding заполнен (vacancy + funnel + profile + assignee) **или** autopilot rule exists для `external_key` |
| **G8** | No dual routing | Нет conflicting route для того же source key (Meta `meta_ads_map` **и** IntakeSourceBinding — один winner; см. strangler) |

### Readiness aggregation (S5)

**Readiness snapshot** = AND всех применимых G* для `business_type`.

| Gate | agency | employer | services |
|------|--------|----------|----------|
| G0–G1 | ✓ | ✓ | ✓ |
| G2 | ✓ | — | optional |
| G3 | ✓ | ✓ | — |
| G4–G5 | ✓ | ✓ | own preset |
| G6–G7 | ✓ | ✓ | ✓ |
| G8 | ✓ | ✓ | ✓ |

**Blocker → next action** (Operational Model §4 rule 3): каждый failed gate возвращает **одно** следующее действие с ссылкой на место исправления (не абстрактное «донастройте систему»).

**Health Check (UI):** **проекция** gate table §4 — не отдельная бизнес-логика. Экран показывает G0–G8; не дублирует wizard progress.

---

## 5. Что означает состояние «Готов принимать людей»?

### READY — вычисляемое состояние, не событие

**READY** определяется **не** событием и **не** UI-флагом:

| Неправильно (событие / артефакт) | Правильно (состояние) |
|----------------------------------|------------------------|
| Wizard completed | `readiness_snapshot` по G0–G8 = PASS |
| First Lead received | То же — lead **после** ready |
| OAuth connected | G6 + G7 PASS в snapshot |
| Demo seed loaded | Никогда не READY |

**Re-evaluation:** snapshot **пересчитывается** при изменении данных. Если пользователь удалил funnel, отвязал source или деактивировал vacancy — READY **автоматически** становится NOT READY. Это ожидаемое поведение; не «сломали wizard progress».

Контекст setup: **`recruitment.setup.intake`** (см. §9 — platform pattern). Scope: tenant + active operating company + `business_type`.

### Определение (единственное)

> **READY** = readiness snapshot (§4) **PASS** для tenant + active operating company.

**Формулировка для пользователя:**

> «Система готова принимать людей» — когда любой inbound signal из настроенного источника **автоматически** попадёт в известный hiring context (vacancy, funnel, requirements, assignee) **без** повторной настройки маршрута.

### Явно НЕ является READY

| Состояние | Почему не READY |
|-----------|-----------------|
| Wizard `finished` | UI progress ≠ gates |
| Demo seed active | Фиктивные данные ≠ intake route |
| `first_lead_created` | Первый результат **после** ready; может случиться до READY только при manual bypass (bug) |
| `next_action_created` (reminder) | Операционное действие, не setup gate |
| Meta OAuth connected без G7 | Source без complete route |
| Vacancy создана без G5 | Нет requirement profile |

### После READY

| Событие | Ожидание |
|---------|----------|
| Первый inbound Lead | Создаётся с route applied; disposition ≠ `needs_routing` для known `external_key` |
| Первый unknown source | **Один** interrupt: «новый источник → укажите маршрут → запомнить» (consumer-setup §3E) |
| Переход к Flow 2 audit | Допустим **только** после повторного Flow 1 audit в режиме 1 с READY достигнутым в продукте |

---

## 6. Следствия для продуктовых поверхностей (не дизайн)

Этот раздел фиксирует **что должно существовать**, не **как выглядит**. Детали UI — отдельные спеки после принятия §1–§5.

| Следствие | Роль |
|-----------|------|
| **Canonical Setup Flow (этот документ)** | Единственный операционный процесс S0–S5 |
| **Readiness / Health Check** | Проекция §4 gates |
| **Sources (Источники)** | Primary surface для S4; не Meta admin |
| **Onboarding / Wizard** | **Guided traversal** S0–S5, не параллельный процесс |
| **Activation backend** | Должен совпадать с READY snapshot, не с legacy counters |
| **Getting Started checklist** | Deprecated as separate process → merge into gate projection |

**REPLACE surfaces** (см. Adoption Register §2): onboarding activation path, Health Check (missing), intake routing UX — **приводятся** к S0–S5, не переписываются «ради красоты».

---

## 8. Идемпотентный setup (resume, не restart)

Setup **идемпотентен**: прогресс не привязан к прохождению wizard, а к **фактическому состоянию gates**.

Если пользователь дошёл до S3, закрыл ноутбук и вернулся через неделю, система **обязана** ответить (Operational Model §3.1, §4 rule 3):

| Вопрос | Источник ответа |
|--------|-----------------|
| Что уже выполнено? | Gates G* со статусом PASS |
| Что осталось? | Gates G* со статусом FAIL + applicable S* |
| Что сейчас мешает? | **Blockers** — текущие failed gates |
| Что делать дальше? | **Одно** next action — первый failed gate по приоритету S0→S5 |

**Запрещено:**

- «Начать мастер заново» при частично выполненном setup.
- Сброс progress при повторном входе.
- Несколько next actions без приоритета.

**Разрешено:** guided UI (wizard, checklist, Setup Status) — **только** как навигация к месту исправления **первого** failed gate. Wizard step index **не** source of truth; gates — source of truth.

---

## 9. READY как платформенная capability (ориентир)

**Не реализовывать сейчас** — зафиксировать направление архитектуры.

Паттерн **Setup Readiness** — общая platform capability (как Document Hub, Requirement Engine):

| Контекст | Scope key (пример) | READY означает |
|----------|-------------------|----------------|
| **Recruitment setup** (этот документ) | `recruitment.setup.intake` | Можем принимать людей через intake |
| **HR setup** *(future)* | `hr.setup.employment` | Можем оформлять сотрудников |
| **Fleet setup** *(future)* | `fleet.setup.assignments` | Можем назначать ТС / водителей |
| **Finance setup** *(future)* | `finance.setup.billing` | Можем выставлять счета |

**Контракт (platform):**

- Модуль **объявляет** gate set + `ReadinessContribution` для своего setup scope.
- Platform **агрегирует** snapshot, blockers, **одно** next action.
- UI **проецирует** snapshot — не владеет логикой READY.

Recruitment setup (G0–G8) — **первый** instance этого паттерна. Workspace Readiness ([`ADR-017`](../architecture/ADR-017-workspace-layer.md)) — sibling pattern для **рабочей записи** после setup; не путать scope.

---

## 10. Traceability

| Вопрос | Ответ |
|--------|--------|
| Почему setup линейный? | Operational Model §3 — один операционный процесс; setup = pre-workspace для intake |
| Почему маршрут в Routing? | [`intake-routing-foundation.md`](../modules/intake-routing-foundation.md), consumer-setup §4 |
| Почему не wizard finished? | §5 — READY = gates, Forbidden F6 |
| Почему Flow 2 blocked? | Adoption Register §4.6 — audit contamination |
| Почему resume, не wizard? | §8 — idempotent setup |
| Почему READY не event? | §5 — computed snapshot |
| Platform READY дальше? | §9 — module gate sets |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | §8 idempotent setup; §5 computed READY + re-evaluation; §9 platform READY ориентир; core principle |
| 2026-07-03 | Initial: Mode 2 Flow 1 — S0–S5, gates G0–G8, READY definition; no UI |
