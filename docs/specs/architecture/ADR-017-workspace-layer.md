# ADR-017: Workspace Layer — стандарт работы с одной записью

**Родительский принцип:** [`hostflow-operational-model.md`](hostflow-operational-model.md) — единая операционная модель HostFlow.  
**Этот ADR** — технический стандарт **композиции рабочей сущности** (sections, readiness, next action). Не «большой контейнер Workspace».

## Status

**Accepted** (architecture). Имплементация **эволюционная**: существующие экраны модулей постепенно приводятся к **единому продуктовому паттерну**; технические контракты (registry, readiness, section providers) — **средство**, не цель.

## Goal

> **Реализовать операционную модель §2 [`hostflow-operational-model.md`](hostflow-operational-model.md) на экране одной записи** — через declarations и platform aggregation, без дублирования domain logic.

Модули автономны. **Паттерн работы** общий: информация → требования → состояние → действия. Рекрутер и HR **не делят экран** — они делят **модель**.

## Context

HostFlow продаёт **независимые продуктовые модули** без прямых зависимостей между ними ([`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)). Модули интегрируются через **ссылки, события, handoffs, platform capabilities** — не через общий монолитный UI.

**Роли и модули разделены по продукту:**

| Роль | Типичный модуль | Не открывает |
|------|-----------------|--------------|
| Рекрутер | Recruitment | HR dossier как primary path |
| HR | HR | Recruitment checklist как primary path |
| Диспетчер | Fleet | Recruitment / HR |
| Бухгалтер | Finance | Operational recruitment |

Задача Workspace Layer — **не** склеить модули в один экран для одного человека. Задача — **одинаковые принципы работы** в каждом модуле, чтобы система ощущалась как одна, а не как набор несвязанных продуктов.

Жизненный цикл человека ([`people-lifecycle-workflow.md`](../workflows/people-lifecycle-workflow.md)) описывает **передачу данных и контекста между этапами** (handoff, те же документы). Это **platform continuity**, не требование, чтобы один оператор «не замечал смену модуля».

Общая модель взаимодействия (List → Workspace → Capabilities → Domain) — [`hostflow-interaction-architecture.md`](hostflow-interaction-architecture.md).

**Связанные ADR (не заменяют этот):**

| ADR | Слой |
|-----|------|
| [`ADR-010`](ADR-010-unified-resource-list-shell.md) | **Списки** — как пользователь находит сущность |
| [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) | **Визуальные токены** — как выглядит интерфейс |
| **ADR-017 (этот)** | **Workspace** — как пользователь работает с записью |

## Decision

### 0. Продуктовое правило (главное)

> **Любая рабочая сущность в HostFlow использует единый паттерн взаимодействия.** Независимо от модуля пользователь работает по одной модели: **информация → требования → состояние → действия.**

Примеры — **один паттерн**, не один экран:

| Модуль | Запись | Информация | Требования | Состояние | Действия |
|--------|--------|------------|------------|-----------|----------|
| Recruitment | Кандидат | профиль, вакансия | checklist | blockers, readiness | next action, handoff |
| HR | Сотрудник | dossier | verification items | blockers, employment state | next action, confirm |
| Fleet | Водитель / ТС | карточка | compliance items | blockers | next action, assign |
| Finance | Счёт / депозит | реквизиты | billing rules | blockers | next action, invoice |

Layout может отличаться. **Семантика зон** — одинаковая. Пользователь не переучивается при смене модуля.

**Workspace** в этом ADR — имя **паттерна и платформенной capability**, которая его реализует. Не React-компонент «Shell» и не синоним Candidate Card.

### 1. Архитектурные принципы (реализация паттерна)

> **Модули владеют данными и бизнес-логикой. Workspace владеет композицией UX паттерна.**

> **Workspace не создаёт бизнес-правил. Он только отображает capabilities модулей в едином паттерне.**

> **Workspace Layer — не новая оболочка приложения.** Эволюция существующих экранов модулей к декларативной композиции (registry, status rail, section providers).

Урок Step 5: не строить второй контейнер поверх уже работающего экрана — **привести экран к паттерну**.

| Слой | Отвечает за | Запрещено |
|------|-------------|-----------|
| **Module** | Сущности, правила, API, gates, events, **решение** о next action | Знать layout другого модуля; зависеть от Workspace |
| **Workspace capability** | Композиция navigation, work area, status rail; **приоритизация** отображения | Создавать бизнес-правила; хранить доменные данные; **вычислять** next action |
| **Platform capabilities** | Readiness aggregation contract, Document Hub, Activity, … | Владеть продуктовым сценарием целиком |

### 2. Workspace — capability, не framework

**Workspace — платформенная capability** (как Resource List Shell), **не** обязательный framework, через который модули обязаны работать.

| Правильно | Неправильно |
|-----------|-------------|
| Модуль **предоставляет capabilities** (sections, readiness, actions) | Модуль **обязан** рендериться только через Workspace |
| Workspace **решает, как показать** зарегистрированные capabilities | Workspace **владеет** бизнес-flow модуля |
| Зависимость **односторонняя:** Module → (declares to) Workspace | Workspace → Module internal services |

```text
Module capabilities (declaration)
         │
         ▼  односторонняя зависимость
Workspace capability (composition)
         │
         ▼
   Desktop / Mobile / Tablet / Compact / Embedded
   (разные presenters — без изменения модулей)
```

Модуль **может** иметь собственные standalone-экраны (admin, batch, API-only) — Workspace не блокирует это. Но **primary operator path** для работы с записью/человеком идёт через Workspace.

**Запрещено:** импорт Workspace Layer внутрь module domain/services. Модуль публикует **контракт** (declaration registry), Workspace его **потребляет**.

### 3. Workspace context — не тип сущности

Workspace оперирует **контекстом работы** (`WorkspaceContext`), а не жёсткой привязкой к типу сущности.

**Краткосрочные названия в UI** («Входящий контакт», «Кандидат») — продуктовые ярлыки. **Архитектурный ключ** — context:

| Context key | Смысл | Типичный anchor (модуль) |
|-------------|-------|--------------------------|
| `intake` | Intake / triage / решение | Recruitment (`Lead`) |
| `recruitment` | Сбор требований, документы, handoff | Recruitment (`Candidate`) |
| `hr` | Верификация, оформление, employment | HR (`WorkforceEmployee`) |
| `hr_active` | Операционное сопровождение сотрудника | HR (+ Fleet) |
| `fleet` | Назначения, ТС, водительские операции | Fleet |
| `finance` | Billing, invoices *(когда применимо)* | Finance |
| `services` | Заказы, исполнение | Services |

**Будущие контексты** (не привязывать ADR к «человеку» только):

| Context key | Пример anchor |
|-------------|---------------|
| `company` | CRM Company / client |
| `vehicle` | Fleet vehicle |
| `vacancy` | Vacancy demand |
| `client` | Client relationship workspace |

**Правило:** один anchor-объект (например `candidate_id`) может сменить context (`recruitment` → `hr`) без смены shell. Context выбирается по: жизненному этапу, роли, `enabled_modules`, связанным сущностям, product routing.

**Запрещено в архитектуре:** `LeadWorkspace`, `CandidateWorkspace` как **типы классов**, жёстко сопоставленные 1:1 с entity. Допустимо в UI copy и маршрутах как **alias** context key.

### 4. Композиционная модель паттерна (техническая реализация)

Паттерн §0 реализуется **логическими зонами** на экране записи. Отдельный route или «Shell» **не обязателен** — существующая карточка модуля может их уже содержать:

```text
┌─────────────────┬──────────────────────────┬─────────────────────┐
│  Navigation     │  Work area               │  Status             │
│  (sections)     │  информация / требования │  blockers           │
│                 │  (active section)        │  readiness          │
│                 │                          │  next action        │
└─────────────────┴──────────────────────────┴─────────────────────┘
```

| Зона | Владелец композиции | Источник содержимого |
|------|---------------------|----------------------|
| **Navigation** | Workspace composition layer | Section declarations (§5) — tabs, sidebar, или секции внутри карточки |
| **Work area** | Workspace mounts slot | Module capability renderer **или** generic renderer по declaration |
| **Workspace Status** | Workspace aggregates | Platform Readiness + module contributions (§6–7) — **один rail на экран** |

Шапка (header, identity, stage chain) остаётся частью **того же экрана** — [`people-lifecycle-workflow.md`](../workflows/people-lifecycle-workflow.md) §5.1.

**Step 5 lesson:** отдельная страница `/requirements` с вторым status rail — антипаттерн. Правильный путь — встроить section body **в существующую карточку**, не оборачивать карточку в новый «Workspace Shell».

### 5. Section declaration — не UI-экран

Модуль **не говорит:** «Вот мой экран.»  
Модуль **говорит:** «Я предоставляю такой раздел.»

**SectionDeclaration** (концептуальный контракт):

```typescript
interface SectionDeclaration {
  section_id: string              // stable: 'requirements', 'employment', …
  module_key: ModuleKey
  label_key: string                 // i18n
  icon?: string
  order: number                     // priority in navigation
  capability_key: string            // which module capability powers this section
  contexts: WorkspaceContextKey[]   // when visible
  permissions: string[]             // RBAC atoms
  readiness_contribution?: boolean  // participates in status rail
  actions?: ActionDeclaration[]     // quick actions exposed in section / rail
}

interface ActionDeclaration {
  action_id: string
  label_key: string
  permission: string
  // execution: module API endpoint or registered handler — not workspace business logic
}
```

Workspace на runtime:

1. Собирает **union** declarations от **всех зарегистрированных** module capabilities.
2. Фильтрует по context, role, `enabled_modules`.
3. Сортирует navigation по `order`.
4. Монтирует work area через **capability renderer registry** (модуль регистрирует renderer для `capability_key` — это единственная UI-точка модуля, и она **не знает** общий layout).

**Постепенное подключение модулей (§8):** новый модуль = новые declarations в registry. Существующий код Recruitment/HR **не меняется**.

### 6. Workspace Status — platform Readiness capability

**Readiness** — **платформенная capability**, не частный виджет Recruitment.

Каждый модуль может публиковать **ReadinessContribution**:

```typescript
interface ReadinessContribution {
  module_key: ModuleKey
  context: WorkspaceContextKey
  priority: number
  summary: string                   // i18n key or resolved label
  status: 'ready' | 'blocked' | 'warning' | 'not_applicable'
  blockers?: ReadinessBlock[]       // module-owned semantics
  next_action?: NextActionDeclaration | null
}

interface NextActionDeclaration {
  action_id: string
  module_key: ModuleKey             // who owns the decision
  label_key: string
  permission: string
  priority: number                  // for aggregation only
  // handler via module — workspace does NOT implement business effect
}
```

**Примеры вопросов по модулям:**

| Модуль | Readiness question |
|--------|-------------------|
| Recruitment | Документы и требования закрыты? |
| HR | Контракт подписан? Данные подтверждены? |
| Fleet | Водитель назначен на ТС? |
| Finance | Депозит оплачен? |
| Services | Заказ готов к исполнению? |

**Workspace Status rail** (справа) — **не** «Recruitment Readiness», а **агрегат** contributions:

- список blockers (все модули);
- общий progress indicator (если применимо);
- **одно** отображаемое next action — см. §7.

### 7. Next Action — модуль решает, Workspace показывает

| | Module | Workspace |
|---|--------|-----------|
| **Решение** «что делать дальше» | ✅ | ❌ |
| **Приоритет** внутри модуля | ✅ | ❌ |
| **Выбор** наиболее приоритетного среди contributions | ❌ | ✅ (display policy only) |
| **Выполнение** действия | ✅ (API / handler) | ❌ (dispatch only) |

Примеры:

- Recruitment: `next_action = { label: "Загрузить паспорт", … }`
- HR: `next_action = { label: "Подтвердить разрешение на работу", … }`

Workspace **только отображает** winning `NextActionDeclaration` по **display policy** (фиксированные правила композиции, не доменные правила). Смена display policy — изменение Workspace capability, **не** модулей.

### 8. Постепенное подключение модулей

Registry pattern:

```text
T0: context=recruitment, modules=[recruitment, document_hub]
    → sections: requirements, documents, …

T+1: fleet module enabled
    → registry += fleet SectionDeclarations
    → navigation gains: driver_card, vehicles, …
    → status rail gains Fleet ReadinessContribution
    → zero changes to recruitment declarations
```

**Инвариант:** отключённый модуль **не регистрирует** declarations → разделы исчезают из navigation без `#ifdef` в Workspace.

### 9. Continuity данных vs единый паттерн UX

Два разных требования — **не смешивать**:

| Требование | Для кого | Смысл |
|------------|----------|-------|
| **Platform continuity** | Система / handoff / audit | Документы, активности, audit trail передаются между этапами (`Lead` → `Candidate` → `WorkforceEmployee`). См. [`people-lifecycle-workflow.md`](../workflows/people-lifecycle-workflow.md) §0.1 |
| **Единый продуктовый паттерн** | Каждый оператор в **своём** модуле | Одинаковая модель: информация → требования → состояние → действия. Рекрутер **не** обязан «не замечать» HR-модуль — он его не открывает |

Handoff между модулями — **событие платформы**. UX каждого модуля остаётся **своим primary path**, но **на одном языке**.

### 10. Карточка и Workspace — не противоположности

| Устаревшая формулировка | Актуальная (post Step 5) |
|-------------------------|---------------------------|
| «Заменить карточки на Shell» | **Эволюционировать** карточку в декларативную композицию |
| Candidate Card = tech debt | Candidate Card = **уже workspace**; проблема — разрозненные блоки, дубли, исторические артефакты |
| Новый контейнер поверх UI | **Workspace Refactoring** — registry + единый status rail + section providers **внутри** экрана |
| Entity-typed workspace classes | `WorkspaceContextKey` + declarations |
| Модуль рисует всю страницу ad hoc | Модуль публикует **declarations** + **capability renderers** |

Пользователь **не должен** увидеть «новый Workspace». Ожидание: *«Карточка стала намного удобнее»*.

**Resource List** (ADR-010) — поиск и выбор записи. **Workspace** (ADR-017) — работа с выбранной записью (часто уже реализованная карточка, приведённая к контрактам).

### 11. Границы (сводка)

| Workspace capability | Modules |
|----------------------|---------|
| Композиция navigation из declarations | Публикуют SectionDeclaration |
| Агрегация Workspace Status | Публикуют ReadinessContribution + NextActionDeclaration |
| Display policy для приоритета next action | Владеют семантикой действий |
| Presenters (desktop/mobile/…) | Не знают о presenters |
| RBAC filter на видимость | Enforce в API |
| **Не** создаёт бизнес-правил | Requirement Engine, HR gates, Fleet rules, … |
| **Не** вычисляет domain readiness | Отдают contribution payload |

## Consequences

### Positive

- Модули **автономны**; продуктовый язык — **единый**.
- Разные роли видят **свои** модули без принудительной склейки UI.
- Fleet / Finance подключаются **декларативно** с тем же паттерном.
- Бизнес-логика **не мигрирует** в UI-слой (принцип §1).

### Negative / cost

- Registry declarations + capability renderers (frontend platform).
- Platform **Readiness aggregation** contract — новая shared capability.
- Миграция legacy cards — поэтапная.
- Display policy для next action — нужен явный owner (Platform UX).

### Implementation order

См. [`workspace-layer-contracts-p0.md`](../platform/workspace-layer-contracts-p0.md) §4 — **обязательный порядок:**

1. Platform types (`shared/workspace/workspace_layer_contracts.ts`).
2. Section registry.
3. Workspace status aggregation.
4. `recruitment.requirements` SectionDeclaration.
5. Requirements capability renderer *(integration spike on legacy route — proves contracts, not final UX)*.
6. **Workspace Refactoring (Candidate)** *(не новый Shell — рефакторинг существующей карточки)*.

**Step 5 lessons (2026-07-03):**

1. Отдельная страница section + второй status rail — антипаттерн.
2. Candidate Card уже содержит header, timeline, status, documents — **не выбрасывать**, а **композировать**.
3. Step 6 — **не** «построить Shell и перенести карточку внутрь», а **убрать мусор, один rail, section providers, retire `/requirements`**.

## Alternatives considered

| Альтернатива | Почему отклонена |
|--------------|------------------|
| Workspace as mandatory framework | Обратная зависимость; ломает mobile/embedded variants |
| **New Workspace Shell wrapper** (card inside card at higher level) | Дублирует контейнер; пользователь уже в карточке — Step 5 показал тот же UX-риск |
| Replace Candidate Card with greenfield screen | Ломает привычный UX; карточка уже содержит нужные зоны |
| Entity-typed workspaces | Дробление при Company/Vehicle/Vacancy contexts |
| Section provider returns React component only | Модуль знает layout; слабая composability |
| Workspace computes next action | Утечка бизнес-логики в UI |
| Readiness only in Recruitment | Не масштабируется на HR/Fleet/Finance |

## Cross-references

| Документ | Роль |
|----------|------|
| [`hostflow-operational-model.md`](hostflow-operational-model.md) | **Operational Model** — единый способ работы пользователя |
| [`people-lifecycle-workflow.md`](../workflows/people-lifecycle-workflow.md) | Поведение по этапам |
| [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) | Workspace + Readiness в Core/Platform |
| [`ADR-010`](ADR-010-unified-resource-list-shell.md) | List layer |
| [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) | Visual layer |
| [`workspace-layer-contracts-p0.md`](../platform/workspace-layer-contracts-p0.md) | P0 types + implementation order (steps 1–6) |

## AI Agent Notes

- **Сначала** [`hostflow-operational-model.md`](hostflow-operational-model.md); **потом** registry / renderers / refactoring.
- Модуль **не импортирует** Workspace — только **регистрирует** declarations.
- `NextAction` payload от модуля; Workspace **display only**.
- Не проектировать «единый экран для всех ролей» — проектировать **одинаковую семантику зон**.
- Context key, не entity type, в архитектурных именах.

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-07-03 | Goal reframed: unified product pattern across modules, not unified screen; roles stay in their modules |
| 2026-07-03 | Step 5: evolution not replacement; Step 6 = Workspace Refactoring (Candidate), not new Shell |
| 2026-07-03 | Initial Accepted |
| 2026-07-03 | Clarifications: capability not framework; context not entity; declaration not UI; platform Readiness; next action ownership; gradual module attach; second principle |
