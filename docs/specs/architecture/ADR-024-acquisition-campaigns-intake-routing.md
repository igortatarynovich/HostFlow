# ADR-024: Acquisition / Campaigns and Universal Intake Routing

## Status

**Accepted (product & architecture direction).** Кодовый этап: **Stage 3 — Universal Acquisition and Intake Routing**.

**Stage 3A — DONE** (2026-07-18): Campaign foundation API + registries + integrity tests.  
**Stage 3B — DONE** (2026-07-18): Form + Intake Source binding to CampaignRun.  
**Stage 3C — DONE** (2026-07-18): Universal submission routing. Next: **3D** outcome attribution and basic analytics.

## Canonical statement

> **Campaigns** — системная capability HostFlow для создания, публикации, маршрутизации и анализа кампаний привлечения. Кампания может продвигать **любой зарегистрированный** объект бизнес-модуля, но созданные обращения и конечные бизнес-результаты принадлежат **модулю назначения**.

> **Acquisition creates demand flow; destination modules own resulting business objects.**

**Базовый архитектурный скелет HostFlow (intake spine):**

```text
Endpoint → Submission → Routing → Decision → Business Entity
```

| Слой | Ответственность |
|------|-----------------|
| **Endpoint** | Принимает обращение (любой внешний/внутренний вход) |
| **Forms** | Собирает данные и согласия, когда вход — HostFlow Form ([`ADR-007`](ADR-007-forms-platform-capability.md)) |
| **Acquisition** | Происхождение, Attribution, Routing Context, Intent / Source |
| **Decision Layer** | Бизнес-решение по Submission / Lead |
| **Business Modules** | Работают с готовыми сущностями (Application, Inquiry, …) |

Главное архитектурное изменение Stage 3 / платформы intake — **не** «вынести Form Builder», а ввести универсальную абстракцию **Endpoint**. Все новые каналы подключаются как Endpoint types; Campaign и Universal Routing не меняются.

Ключевое архитектурное разделение HostFlow:

> **Привлечение спроса** (Campaigns / Acquisition) **отделено от исполнения** бизнес-процессов (Recruitment, Sales, Fleet, HR, Finance).

> Кампания **никогда** напрямую не владеет кандидатом, обращением или клиентом. Она создаёт атрибутированный intake, который маршрутизируется в модуль-владелец.

> Campaigns — универсальный механизм продвижения. Target, модуль и result задаются **registry**; lifecycle рекламы, **Endpoint**, атрибуции и аналитики — **одинаковый**.

Позиционирование продукта:

> HostFlow — не «просто CRM или ATS», а **система управления ростом компании**: Growth → Intake → Operations → Intelligence → (снова) Growth.

Стратегическая ценность:

> Большинство ATS заканчиваются на «получили отклик»; большинство CRM — на «получили лид». HostFlow держит **сквозную цепочку** от запуска кампании до найма или сделки и отвечает не только «сколько лидов», а **«какая кампания достигла бизнес-цели (Outcome) / принесла прибыль / закрыла вакансии»**.

## Context

Привлечение трафика исторически завязано на Recruitment. После ADR-023 Sales (и позже HR/Fleet) нуждаются в тех же классах каналов без второго Meta/forms стека. Отдельный продукт **Marketing** отклонён (не шестой ключ ADR-004, не `marketing.*` host).

Связанные: [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-007`](ADR-007-forms-platform-capability.md), [`ADR-008`](ADR-008-job-publishing-and-distribution.md), [`ADR-013`](ADR-013-public-intake-strategy.md), [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md), [`ADR-023`](ADR-023-recruitment-sales-module-separation.md), [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md).

## Decision

### 0. Четыре уровня платформы роста

HostFlow складывается в замкнутый цикл управления ростом:

```text
Growth → Intake → Operations → Intelligence ↺ Growth
```

| Уровень | Вопрос | Состав (ориентир) | Задача |
|---------|--------|-------------------|--------|
| **1. Growth** | Откуда приходит спрос? | Campaigns, Audiences, Channels, Assets, **Endpoints**, Attribution, Analytics | Привести нужных людей |
| **2. Intake** | Что после заявки? | Sources, Submissions, Routing, Inbox, Deduplication, Screening | Правильно распределить обращения |
| **3. Operations** | Что делает бизнес? | Recruitment, HR, Sales, Fleet, Finance | Создать ценность для клиента |
| **4. Intelligence** | Что система узнала? | Аудитории/формы/каналы/менеджеры/вакансии/ROI; рекомендации | Улучшать следующие кампании и решения |

**Intelligence** — не конечный «отчётный экран», а слой принятия решений, который **питает следующий Growth** (какая аудитория лучше, какая форма конвертит, какой канал дешевле, какой ROI, какие вакансии сложнее).

ADR-024 нормирует прежде всего **Growth** (+ стык с Intake routing и attribution из Operations). Inbox / Dedup / Screening — контракты Intake; пять модулей — Operations (ADR-004 / ADR-023); полный Intelligence suite — эволюция после Stage 3, но **Outcome** и feedback-loop уже в каноне Campaigns.

### 1. Campaign = долгосрочный маркетинговый проект (не «Meta Campaign», не «один запуск»)

**Campaign** — это **долгоживущая инициатива привлечения**, а не обёртка над одной рекламной кампанией провайдера и не синоним одного сезонного запуска.

Одна Campaign может одновременно включать несколько каналов:

Meta Ads · Google Ads · LinkedIn · TikTok · Email · WhatsApp · referrals · ярмарка вакансий · офлайн-событие · QR на ТС · лендинг · …

И — что критично — **несколько волн запуска** (Flight / CampaignRun) без размножения «проектов» и без потери общей истории.

```text
Campaign                         ← долгоживущая инициатива («Recruit Drivers Germany»)
├── Goal Type + Primary KPI      ← зачем + чем измеряем успех
├── Targets                      ← что продвигаем (стабильны между волнами)
├── Flights / CampaignRuns       ← конкретные запуски (сентябрь / октябрь / …)
│     ├── dates, budget
│     ├── Channels + Assets
│     ├── Audiences (wave-scoped)
│     ├── Endpoints (links)
│     └── Results (wave facts)
├── Attribution / Analytics      ← roll-up по Flight → Campaign
├── Timeline                     ← общая история инициативы
└── Outcomes                     ← progress к цели (кванты)
```

Выше по слою (после V1): **CampaignTemplate** → instantiate → Campaign.

**Неверно:** `Campaign = Meta Campaign`.  
**Неверно:** `Campaign = один запуск / одна волна`.  
**Верно:** `Campaign → Flight(s) → Channels → Assets → Forms → Results → Outcomes`, где Meta — **один** из Channels внутри Flight (с optional external campaign id для sync).

Это и есть **Campaign Manager** HostFlow — не «маркетинговый список источников» и не серия одноразовых «кампаний» на каждый месяц.

#### 1.1 Flight / CampaignRun — конкретный запуск внутри Campaign

Маркетинг почти никогда не работает по схеме «один запуск = одна кампания». Обычно есть долгоживущая инициатива и множество волн.

| | Campaign | Flight (CampaignRun) |
|--|----------|----------------------|
| Смысл | Долгосрочный проект / инициатива | Конкретный запуск / волна |
| Пример Recruitment | «Набор водителей в Германию» | Flight #1 сентябрь; #2 октябрь; #3 декабрь |
| Пример Sales | «Продвижение услуги Recruitment» | Flight #1 Польша; #2 Германия; #3 Румыния |
| Хранит | Goal, Targets, общая история, Outcomes | даты, бюджет волны, объявления, аудитории волны, channel bindings, Results волны |

**Имена в каноне:** продуктово — **Flight**; в данных/API — сущность **`CampaignRun`** (синоним). Не вводить третий термин.

Без Flight Campaign быстро превращается в одноразовую сущность: либо плодят новые Campaign на каждую волну (теряется история), либо переиспользуют одну (смешиваются бюджеты/даты/креативы разных запусков).

**Атрибуция:** Result атрибутируется к **Flight**, с обязательным roll-up на родительский **Campaign**. Сравнение волн = сравнение Flight внутри одной Campaign.

#### 1.2 V1: Flight зарезервирован, но не раздут

В Stage 3 / V1 **не** строить полноценный multi-flight UX (A/B волны, сезонный конструктор, сравнение волн).

Но модель **обязана** предусмотреть Flight с первого дня:

- при создании Campaign всегда создаётся **ровно один** `CampaignRun` (или явный `current_flight_id`);  
- Channels / spend / Form links / Results в V1 крепятся к этому единственному Flight (или через него);  
- UI может почти не показывать слово «Flight», пока волна одна.

Так позже добавляются повторные запуски, A/B, сезоны, разные бюджеты/аудитории **без миграции всей модели**.

#### 1.3 CampaignTemplate — готовый playbook (следующий уровень после foundation)

**CampaignTemplate** — не Campaign и не Flight. Это **переиспользуемый сценарий запуска**: продаваемая / шаримая экспертиза агентства или готовый playbook тенанта.

Пример агентства: найдена идеальная воронка «Recruit CE Drivers». Новый клиент → выбрать Template → HostFlow материализует структуру:

- Campaign (+ Goal Type / Primary KPI defaults);  
- стандартные Flights (или один starter Flight);  
- Audience definitions / bindings;  
- Form (+ Questions) links;  
- Screening defaults (где применимо);  
- Assets placeholders / packs;  
- Outcome / KPI scaffolding;  
- Automation rule stubs (ADR-019);  
- отчётные пресеты.

Примеры шаблонов: `Recruit CE Poland` · `Physiotherapist Germany` · `Lead Generation for Transport Companies`.

```text
Template → Campaign → Flight → Results → Outcomes
```

Для клиента (не только агентства): «Создать кампанию» → выбрать шаблон → за минуты получить готовую структуру вместо пустого конструктора.

**Владение:** Shared Acquisition (template catalog + instantiate). Form/Audience/Automation **SoT** остаются у своих capability — Template хранит **ссылки / рецепт**, не exclusive copies как единственный владелец.

**Stage 3 / V1:** Template **в каноне**, но **не** в scope 3A–3E. 3A по-прежнему реализует только Campaign + Goal (+ Type/KPI) + Target + reserved Flight. Instantiate-from-template — отдельный срез после вертикали V1 (ориентир: после multi-Flight / catalog UX, или параллельно V2).

**Не делать в 3A:** catalog UI, marketplace templates, deep clone всех связанных объектов.

### 2. Capability на Shared Platform

Живёт на shell (`hostflow.cc`) рядом с Inbox, **Forms**, Automations, Integrations, Settings.

Пользователь в проекте кампании: выбирает **Goal Type + Primary KPI**; модуль и targets; каналы (на уровне Flight); аудитории; объявления/креативы; **привязывает** формы; задаёт result/`route_intent`; ведёт бюджет волны и сквозную аналитику. (Позже: старт из **CampaignTemplate**.)

### 3. Ownership

| Объект | Владелец |
|--------|----------|
| CampaignTemplate (playbook / recipe; instantiate → Campaign) | Shared Acquisition (после V1 foundation) |
| Campaign, CampaignGoal (type + primary KPI), CampaignTarget, CampaignRun (Flight), Channel binding, Ad / Creative (Asset), Audience (definition), Budget, Attribution, Campaign Timeline | Shared Acquisition |
| Provider account / OAuth / webhook credentials | Shared Integrations (+ Acquisition UX) |
| **Form** (template, versions, public link, consents) | **Shared Forms** ([`ADR-007`](ADR-007-forms-platform-capability.md)) — **Core Platform Module** |
| **Endpoint** (Meta Lead Form, HostFlow Public Form, API, Webhook, WhatsApp, Telegram, QR, Mobile App, …) | Shared Intake association on Flight; HostFlow Form SoT remains Forms |
| CampaignRun ↔ Endpoint (usage) | Acquisition (association only) |
| CampaignRun ↔ `TenantLeadForm` (`acq_campaign_run_forms`) | **V1 transitional** Endpoint type = HostFlow Public Form (Stage 3B); migrate to generic Endpoint |
| CampaignRun ↔ IntakeSourceProfile | V1 Endpoint / channel specialization (e.g. Meta) |
| Submission, Routing Rule / `route_intent` | Shared Intake |
| Vacancy / Подбор / Application / Candidate | **Recruitment** |
| Inquiry / Client / Service Order (SoT) | **Sales** (+ Services for order) |
| Future Fleet / HR inquiry objects | **Fleet** / **HR** |

### 4. Endpoint Model (главная платформенная абстракция)

**Главное решение:** любой внешний или внутренний вход в HostFlow — это **Endpoint**. Все Endpoint сходятся в одну модель:

```text
Endpoint → Submission
```

Примеры Endpoint (registry; без fork Campaign):

- Meta Lead Form  
- HostFlow Public Form ([`ADR-007`](ADR-007-forms-platform-capability.md))  
- API  
- Webhook  
- WhatsApp / Telegram  
- QR Code / Mobile App  
- …

**Campaign больше не работает с Form напрямую.** Целевая модель:

```text
Campaign → Endpoint → Submission
```

(часто через Flight: `Campaign → Flight → Endpoint → Submission`)

Campaign отвечает **только** за:

- Attribution  
- Routing Context  
- Intent (`route_intent` / Target)  
- Source / происхождение спроса  

Campaign **ничего не знает** о внутреннем устройстве Forms (builder, versions, consents, themes). Forms — SoT формы и (для HostFlow Form) Submission capture; Acquisition потребляет уже готовый Submission через Endpoint.

```text
Campaign ──uses──► Endpoint
HostFlow Public Form ──is-a──► Endpoint
Forms SoT ──owns──► template / version / publish / consent / form submission surface
```

**Stage 3B V1:** `acq_campaign_run_forms` + `acq_campaign_run_intake_sources` — переходные специализации Endpoint. Целевая модель — единый **CampaignRun ↔ Endpoint**. До миграции Form∪Profile matrix в 3C — корректная V1 реализация двух endpoint-типов. HostFlow Public Form = один `endpoint_type`.

### 4b. Routing once per Lead

Routing выполняется **только один раз** — при создании нового Lead (first entry).

| Submission | Поведение |
|------------|-----------|
| First entry (новый Lead) | Endpoint → optional Flight → `route_intent` → Decision Layer; stamp routing/attribution context |
| Continuation (существующий Lead) | **Наследует** Routing Context Lead; **не** определяет Campaign повторно; **не** меняет Attribution; используется только для продолжения процесса |

Forms (или другой Endpoint) может создавать новые Submissions в обоих случаях; Acquisition Universal Routing — только first entry ([`ADR-007`](ADR-007-forms-platform-capability.md)).

### 5. Audience — первоклассный объект HostFlow

Аудитория **не** живёт только внутри Meta.

Пример: «Водители CE · PL/UA · опыт > 1 года · до 55 лет» — определение в HostFlow, переиспользуемое в Meta, Google, Email, SMS, Push, LinkedIn, …

```text
Campaign → Audience(s) → Flight → Channels
```

а не «аудитория = настройка одного канала». Audience definition живёт на platform; привязка к волне — на Flight (переиспользование одной Audience в нескольких Flight / Campaign).

| Объект | Смысл |
|--------|--------|
| **Audience** | Каноническое определение сегмента (критерии, гео, язык, exclusions) |
| **Audience ↔ Channel mapping** | Как сегмент материализуется у провайдера (lookalike, custom list, filters) |

V1 может хранить Audience как HostFlow definition + manual/provider sync; V2+ — push/sync в ad platforms.

### 6. Универсальная связь Target (без typed FK) + Goal ≠ route_intent

```text
Campaign → Goal(s)
Campaign → CampaignTarget(s) → Flight → Endpoint → Submission → Route Intent → Result Object
```

**Запрещено** на `Campaign`: `vacancy_id`, `service_id`, `client_id`, `order_id`.

На **`CampaignTarget`:** `target_type`, `target_id`, `target_module`, `route_intent` (+ role: primary target vs context).

#### Target ≠ Context ≠ Result

| Роль | Смысл | Пример |
|------|--------|--------|
| **Target** | Что продвигаем | Услуга; вакансия C+E |
| **Context** | Для кого / в рамках чего | Client X; Подбор для клиента Y |
| **Result** | Что создаётся | Inquiry; Application |

#### Goal ≠ route_intent ≠ Outcome

Три разных вопроса — три разных поля модели:

| Понятие | Вопрос | Примеры |
|---------|--------|---------|
| **Goal Type** | **Класс** бизнес-цели кампании | Hiring; Lead Generation; Sales; Awareness; … |
| **Primary KPI** | **Главный критерий успеха** внутри типа | Hires; Cost per Hire; Qualified Leads; CPL; Revenue; CAC; Applications; ROI; Reach; … |
| **`route_intent`** | **Что создать** во Intake после submission | Application; Inquiry; … |
| **Outcome** | **Измеримый progress** (квант цели) | Нанять 20 водителей; 30 B2B-лидов; revenue ≥ X |

**Goal не является плоским enum** вроде Hire / Sales / Brand. Через год типов станет мало и смешаются «зачем» и «чем измеряем».

Вместо этого на Campaign (или `CampaignGoal`):

```text
goal_type:     Hiring | Lead_Generation | Sales | Awareness | …   (registry)
primary_kpi:   Hires | Cost_per_Hire | Qualified_Leads | Revenue | … (registry)
```

Так две кампании с `goal_type = Hiring` могут оптимизироваться по-разному: одна по **Cost per Hire**, другая по **количеству Hires**.

`route_intent` отвечает на операционный вопрос Intake.  
**Goal Type + Primary KPI** отвечают на стратегический вопрос Growth.  
**Outcome** quantifies progress; Results feed attribution.

Registry для Goal Type и Primary KPI расширяется без fork Campaign service (как Promotion Target registry). Recommended defaults: Goal Type → suggested Primary KPI list (не жёсткая 1:1).

### 7. Promotion Target registry

Новый продвигаемый объект = registry entry (`target_type`, owning module, intents, preview, access, outcome metrics) — **без** переписки Campaigns. Примеры: услуга, вакансия, подбор, заказ, автомобиль, событие, партнёрская программа, …

### 8. Подбор ≠ Кампания; flows

| | Подбор | Campaign |
|--|--------|----------|
| Owner | Recruitment | Acquisition |
| Смысл | Потребность найти людей | Проект привлечения (каналы, аудитории, assets, forms, KPI) |

Из Подбора: **Запустить кампанию** →  
`Submission → Application → Candidate`

Sales: target = услуга →  
`Submission → Inquiry → Client / Order` (ownership модулей).

Job Publishing (ADR-008): Vacancy/Job Post — Recruitment; multi-channel placement/attribution — Acquisition.

### 9. Сквозная аналитика: Goal Type + Primary KPI → Results → Outcomes

**Goal Type** — класс / зачем. **Primary KPI** — главный критерий успеха. См. §6.

**Result** — факт, который произошёл (событие / объект):

- создан Inquiry / Application / Candidate;  
- нанят водитель;  
- подписан договор;  
- создан Client Account.

**Outcome** — измеримая бизнес-цель / progress **в рамках Goal Type** (часто в единицах Primary KPI):

- нанять 20 водителей;  
- получить 30 B2B-лидов;  
- продать 15 автомобилей;  
- увеличить базу на 500 контактов.

```text
Campaign (Goal Type + Primary KPI) → Flight → Results → Outcomes
```

Аналитика отвечает на вопросы:

| Вопрос | Слой |
|--------|------|
| Зачем кампания / чем измеряем успех? | Goal Type + Primary KPI |
| Что произошло? | Results (+ channel/form metrics; по Flight и roll-up) |
| Достигла ли цель? | Outcomes (progress / attainment) |

Сравнение кампаний — по Goal Type / Primary KPI / Outcomes. Сравнение волн — между Flight одной Campaign.

| Уровень метрик | Примеры |
|----------------|---------|
| Реклама / канал | расходы, показы, охват, CPM |
| Трафик | клики, CTR, CPC |
| Анкета | открытия, start, submit, conversion |
| Обращения | созданные, дубликаты, валидные |
| Квалификация | подходящие / нет, связались |
| Results (Operations) | кандидаты, hire; клиенты, заказы |
| Outcomes | % цели, gap to goal, time-to-outcome |
| Экономика | CPL, цена найма, CAC, выручка, ROI |

Results поставляют owning modules (атрибуция к Flight → Campaign); Outcomes объявляются на Campaign в рамках Goal Type / Primary KPI и считаются по attributed Results. Intelligence агрегирует и замыкает цикл на Growth / следующий Flight / Template.

### 10. Campaign Timeline

Кампания — **управляемый проект с историей**, не только набор настроек. Единая шкала:

- создание кампании;  
- подключение канала (Meta/…);  
- смена креатива / формы / бюджета / аудитории;  
- первые submissions / leads;  
- первый Candidate / Inquiry;  
- первый hire / первая сделка.

События Timeline — append-only audit/projection; бизнес-объекты по-прежнему deep-link через Stage 6C.

### 11. Automation Campaigns

Правила платформенных Automations (ADR-019) могут управлять Campaigns, например:

- вакансия / подбор открыт > 14 дней → увеличить бюджет, включить Google, сменить регион, уведомить менеджера;  
- стоимость найма / CPL > порог → задача маркетологу;  
- нет валидных заявок N дней → pause channel / escalate.

Acquisition **не** дублирует automation engine: триггеры/actions регистрируются как automation capability над Campaign objects.

### 12. UI: пять экранов (+ Timeline; Results не конечная точка)

1. **Обзор** — проекты, статусы, расходы, progress к Outcomes; (позже) список Flight.  
2. **Конструктор** — **Goal Type + Primary KPI**, targets/context, Flight dates/budget, channels, audiences, route_intent, **Outcome** quanta; (позже) «создать из Template».  
3. **Assets / Объявления** — тексты, креативы, placements, variants (привязка к Flight).  
4. **Forms** — выбор/линк переиспользуемых форм (Forms SoT).  
5. **Performance** — channel stats, воронка, **Results**, **Outcomes** (goal attainment), экономика + **Timeline**; сравнение Flight когда волн > 1.

Экран «Результаты» **не** является конечной точкой модели: без Outcomes нельзя ответить «достигли ли цели». В UI можно объединять Results+Outcomes во вкладке Performance, но в данных и каноне это **разные** понятия.

Модульные хосты — контекст своего target.

### 13. Итоговая модель (глоссарий)

```text
Campaign Manager (growth engine)
├── CampaignTemplate          ← playbook / экспертиза (после V1 foundation)
└── Campaign
    ├── Goal Type + Primary KPI
    ├── Targets
    ├── Flights / CampaignRuns
    │     ├── Channels
    │     ├── Audiences (bindings)
    │     ├── Assets
    │     ├── Endpoints (links)
    │     └── Budget (wave)
    ├── Attribution
    ├── Analytics
    ├── Timeline
    ├── Results
    └── Outcomes
```

Слойность:

```text
Template → Campaign → Flight → Results → Outcomes
```

| Понятие | Смысл |
|---------|--------|
| **CampaignTemplate** | Готовый **сценарий / playbook** запуска; instantiate → Campaign (+ defaults). Не Campaign и не Flight |
| **Campaign** | Долгоживущая **инициатива** привлечения (не Meta-обёртка, не одна волна) |
| **Goal Type** | Класс бизнес-цели (Hiring, Lead Generation, Sales, Awareness, …) — registry |
| **Primary KPI** | Главный критерий успеха внутри типа (Hires, Cost per Hire, Revenue, CPL, …) — registry |
| **Flight / CampaignRun** | Конкретный **запуск / волна**; V1 = ровно один |
| **Channel** | Где привлекаем (Meta, Google, Email, offline, QR, …) внутри Flight |
| **Audience** | Кого привлекаем (HostFlow definition → channel mappings) |
| **Form** | Как собираем данные (Forms SoT; Campaign/Flight **uses**) |
| **Target** | Что продвигаем (`CampaignTarget` + registry) |
| **`route_intent`** | Что создать во Intake после submission |
| **Result** | **Что произошло** — факт/объект; атрибуция к Flight |
| **Outcome** | **Насколько достигнута цель** — измеримый progress в рамках Goal Type / Primary KPI |
| **Timeline** | История изменений и milestone-событий инициативы (across Flights) |
| **Automation** | Реакция через platform Automations (ADR-019) — **не** отдельный campaign engine |

```text
Campaign (Goal Type + Primary KPI) → Flight → Results → Outcomes
```

Это уже не «подсистема рекламы», а **универсальный движок роста** — одинаково для Recruitment, Sales и будущих модулей HostFlow.

**Ключевая граница:**

> Acquisition / Growth управляет созданием спроса и входящего потока.  
> Business modules (Operations) управляют обработкой и Result-объектами.  
> Intelligence оценивает Outcomes (Goal Type / Primary KPI) и улучшает следующий Growth / Flight / Template.

Защита от ошибок: Campaign ≠ Meta; Campaign ≠ волна; Template ≠ Campaign; Forms не exclusive child; Automations не дублируются; Goal ≠ плоский enum; Goal ≠ `route_intent`.

### 14. Delivery: Stage 3 slices (после production cutover)

Полный Campaign Manager **не** реализуется одним релизом. Порядок:

| Slice | Name | Доказывает / отдаёт |
|-------|------|---------------------|
| **3A** ✅ | Campaign foundation (Goal + Target + reserved Flight) | **DONE.** Campaign-as-initiative; **Goal Type + Primary KPI**; `CampaignTarget` via registry; **CampaignRun** (V1 = ровно один / `current_flight`); company + module gate; `target_module` canonical; route_intent validation. **Не** Template catalog |
| **3B** ✅ | Endpoint binding (V1: Form + Intake Source) | **DONE.** V1: `CampaignRun ↔ TenantLeadForm` + `↔ IntakeSourceProfile` as transitional Endpoint specializations; uses-not-owns. **Canon:** CampaignRun ↔ Endpoint (HostFlow Public Form = one type) — [`ADR-007`](ADR-007-forms-platform-capability.md) |
| **3C** ✅ | Universal submission routing | **DONE.** Submission from any Endpoint → Form∪Profile Flight resolve → `route_intent` → Application \| Inquiry; unresolved → disposition-only queue. **Routing once per new Lead** |
| **3D** | Outcome attribution and basic analytics | Result → Flight → Campaign; **Outcome** progress (в единицах Primary KPI); базовые расходы + lead metrics |
| **3E** | Timeline and automation events | Timeline событий; emit events для Automations (полные Automation Campaigns — позже) |

#### Stage 3A Definition of Done — met

- `POST /api/v1/platform/campaigns` создаёт долгоживущую инициативу (`acq_campaigns`) и **автоматически** один reserved Flight (`acq_campaign_runs`, `code=flight_1`, `current_flight_id`) в одной транзакции.
- **CampaignGoal** (V1): `goal_type` + `primary_kpi` на Campaign (ADR допускает inline или отдельную сущность); API отдаёт и поля, и вложенный `goal`.
- Goal Type + Primary KPI валидируются как связанная пара из SSOT `shared/campaign_registries.json`.
- `CampaignTarget` — универсальный (type/id/module/route_intent); target проверяется через registry; `target_module` всегда канонический (клиентский override отклоняется).
- Конкретный `target_id` проверяется на **существование и доступность** в company/tenant scope (cross-company → 404).
- `route_intent` разрешён только для выбранного target type.
- Ownership: `own_company_id` + tenant; destination module gated (`enforce_module_gate`); Campaign **не** владеет Recruitment/Sales объектами (нет FK на Candidate/Application/Inquiry/Client).
- API: `/api/v1/platform/campaigns`, `…/registries`, `…/{id}/targets`; cookie и Bearer auth дают одинаковый create-path.
- Tests: `backend/tests/api/test_stage_3a_campaign_foundation.py` (registry + spoof module + bad KPI/route + cross-company + disabled module + flight invariant + no domain ownership + cookie/Bearer).

**Вне 3A (как и было):** CampaignTemplate UI; Audience; Assets; Budget; Analytics; multi-Flight UX; Forms.

#### Stage 3B Definition of Done — met

- Flight links existing `TenantLeadForm` via `acq_campaign_run_forms` (association only; Forms SoT unchanged).
- Flight links existing `IntakeSourceProfile` via `acq_campaign_run_intake_sources` (provider-neutral; Meta = existing profile `provider=meta`).
- Association stores **only** FKs + `role` + `is_active` — **no** `provider` / `external_ref` snapshots; API JOINs profile + live `IntakeSourceBinding`.
- DB: at most one **active primary** Form and one **active primary** Intake Source per Flight (partial unique indexes).
- Same Form reusable across Campaigns; detach removes association, not Form/Profile; second active primary → 422; deactivate primary → allow reassign.
- Company scope: Intake Source `own_company_id` must match Campaign; Form same tenant + active.
- API: `…/campaigns/{id}/forms`, `…/intake-sources` (+ PATCH link flags; explicit `…/flights/{flight_id}/…`); nested on `CampaignOut.flights[]`.
- No Application/Inquiry creation; no attribution metrics.
- Tests: `backend/tests/api/test_stage_3b_form_intake_binding.py`; migrations `202607180002_acq_3b` + `202607180003_acq_3b_fix` (snapshot drop + primary indexes; revision ids ≤32 chars).

#### Stage 3C Definition of Done — met

- **Submission before Decision Layer:** public policy submit resolves target Lead → universal routing → stamp `acquisition_routing_v1` → `append_submission` → Decision Layer **only if** `status=routed`. Unresolved never calls domain create.
- **Two-layer composition:** `IntakeRouter` unchanged (Binding → Profile). `resolve_universal_submission_routing` runs after it (Meta via `intake_route`; public via `intake_submit_service`).
- **Form ∪ Profile Flight matrix:** eligible Form-only / Profile-only / same Flight → campaign routing; Form≠Profile → `form_profile_flight_conflict`; >1 eligible in either set → `multiple_active_flights`; ∅∅ → profile default. (V1 dual Endpoint types; later unified Endpoint association.)
- **Routing once:** first-entry Lead only; continuation Submissions inherit Lead routing context (canon; enforce in follow-up if any path re-routes).
- **Routing-eligible (single predicate):** association `is_active` + Campaign `status=active` + Flight `status=active` + optional `starts_at`/`ends_at` window. Ineligible links excluded from sets (not conflicts).
- **Closed unresolved reasons:** `no_intake_context`, `multiple_active_flights`, `form_profile_flight_conflict`, `campaign_not_routable`, `flight_not_routable`, `missing_primary_target`, `multiple_primary_targets`, `unknown_route_intent`, `unsupported_route_intent` (free-text only in `warnings`).
- **Unresolved Queue = disposition-only:** stamp + Lead `needs_routing` / Decision Layer `review_queue`; no new queue table/UI in 3C.
- Acquisition still does not own Candidate / Application / Inquiry (no FK).
- Tests: `backend/tests/api/test_stage_3c_universal_submission_routing.py`.

#### Минимальный вертикальный срез V1 (3A→3D, базовый Timeline в 3E)

Должен доказать **всю** цепочку:

```text
Campaign + Goal Type + Primary KPI → Target → Flight(1) → Endpoint → Submission
  → Route Intent → Recruitment Application | Sales Inquiry
  → Result attribution (Flight → Campaign) → Outcome progress
```

**В минимальный V1 входит:** Campaign; **Goal Type + Primary KPI**; Targets; **один CampaignRun**; **Endpoints** (V1: Form + Intake Source specializations); Submission; routing в Recruitment **и** Sales; базовые spend/lead metrics; Result → Flight → Campaign; хотя бы одно **Outcome** + progress; Timeline событий.

**Места в модели уже закреплены, но идут после вертикали V1:** **CampaignTemplate** (instantiate playbook); multi-Flight UX / сравнение волн; Audience; Assets; полноценный Budget; расширенная Intelligence; create/manage ads in-provider (V2); Automation Campaigns / AI (V3).

#### Product phases (поверх slices)

| Phase | Scope |
|-------|--------|
| **V1** | Сквозной срез 3A–3E (минимальный) — один Flight; Goal Type + Primary KPI + Outcome; **без** Template catalog |
| **V2** | Multi-Flight; **CampaignTemplate** catalog + instantiate; create/manage provider ads; Audience sync; richer analytics / wave compare |
| **V3** | Automation Campaigns; optimization; recommendations; AI assets/forms; template marketplace / agency packs |

V1 **не** заменяет Meta Ads Manager.

**Не делать:** Marketing product module; `Campaign = Meta Campaign`; `Campaign = одна волна` без Flight в модели; Template в scope 3A; Form exclusive child; Audience only-in-Meta; typed FK на Campaign; Goal как плоский enum Hire/Sales/Brand; Goal = только `route_intent`; SoT Candidate/Inquiry/Client из Campaign service; пытаться сдать весь Campaign Manager / multi-Flight / Template в одном Stage 3.

## Consequences

1. **Intake spine** HostFlow: `Endpoint → Submission → Routing → Decision → Business Entity` — базовый скелет для всех каналов и модулей.  
2. **Endpoint** — главная платформенная абстракция входа; новый канал = новый `endpoint_type` в registry, не fork Campaign/Routing.  
3. **Forms** = Core Platform Module ([`ADR-007`](ADR-007-forms-platform-capability.md)): SoT формы + согласий; не часть Acquisition.  
4. Campaign отвечает за Attribution / Routing Context / Intent / Source — **не** за Form Builder.  
5. HostFlow позиционируется как **система управления ростом**: Growth → Intake → Operations → Intelligence ↺ Growth.  
6. Привлечение спроса и исполнение процессов — разные слои.  
7. **Goal Type ≠ Primary KPI ≠ route_intent ≠ Outcome**.  
8. **Campaign ≠ Flight**; **Template ≠ Campaign**.  
9. **Result ≠ Outcome**; атрибуция Result → Flight → Campaign.  
10. **Routing once per Lead**; continuation Submissions наследуют context, не меняют Attribution.  
11. Stage 3A–3C DONE в V1; 3B Form/Intake links = transitional Endpoint specializations; **Platform Forms epic** после Acquisition V1.  
12. Deep links: Campaign / Audience / Form на shell; Application/Inquiry — module hosts (6C).

## References

- [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md)  
- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) · [`ADR-007`](ADR-007-forms-platform-capability.md) · [`ADR-008`](ADR-008-job-publishing-and-distribution.md) · [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)

## История

- 2026-07-17: Acquisition as platform capability; Target/Context/Result; V1–V3.  
- 2026-07-17: Campaign = project; Form uses-not-owns; Audience first-class; Timeline; Automation Campaigns.  
- 2026-07-17: Glossary + Stage **3A–3E** slices; minimal V1 vertical chain; deferred Audience/Assets/Budget.  
- 2026-07-17: Four levels Growth→Intake→Operations→Intelligence; **Result ≠ Outcome**; `Campaign → Results → Outcomes`.  
- 2026-07-17: **Flight / CampaignRun** (V1 = один) + **CampaignGoal** ≠ `route_intent`; 3A foundation = Campaign + Goal + Target + reserved Run.  
- 2026-07-17: **CampaignTemplate** (canon, post-V1); Goal → **Goal Type + Primary KPI** (не плоский enum).  
- 2026-07-18: **Stage 3A DONE** — foundation API, registries, auto Flight, gates, integrity tests.  
- 2026-07-18: **Stage 3B DONE** — Flight↔Form / Flight↔IntakeSource associations; Meta via existing profile bind.  
- 2026-07-18: 3B fix — drop `provider`/`external_ref` snapshots; partial unique indexes for one active primary per Flight.  
- 2026-07-18: **Stage 3C DONE** — UniversalSubmissionRouter; Form∪Profile matrix; Submission-before-DL; disposition-only unresolved.  
- 2026-07-18: **Architecture lock** — Forms = Core Platform Module ([`ADR-007`](ADR-007-forms-platform-capability.md)); **Endpoint** as primary intake abstraction; Campaign → Endpoint → Submission; routing once per Lead; intake spine `Endpoint → Submission → Routing → Decision → Business Entity`.
