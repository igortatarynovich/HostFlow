# HostFlow Constitution — платформенная конституция

**Status:** canonical (L0 — принципы, стабильные годами). **Заморожена.** Новое правило — только если **без него невозможно** принять архитектурное решение (не «можно лучше»).  
**Audience:** product, architecture, engineering.  
**Применение:** фильтр при решениях; продуктовый приоритет — [`m1-money-path.md`](../journeys/m1-money-path.md).  
**Не заменяет:** детальные ADR, domain maps, workflow specs — задаёт **порядок мышления** для любого решения.

---

## Первый принцип

> **HostFlow моделирует реальную операционную деятельность организации, а не структуру экранов, подразделений или баз данных. Все архитектурные решения должны отражать бизнес-процесс прежде, чем способ его отображения в интерфейсе.**

> **Архитектура моделирует реальную операционную деятельность бизнеса. Интерфейс — лишь одна из возможных проекций этой модели.**

**Главный архитектурный вопрос** для любого решения:

> Мы сейчас моделируем **реальную работу бизнеса** или просто **придумываем удобный экран**?

Если новая функция **требует нарушения** этого принципа — проблема почти всегда в **проектировании функции**, а не в конституции.

**Критерий для всех ADR:** сначала доказать, **какую часть реального бизнес-процесса** отражает изменение; только потом обсуждать модели, API и интерфейс.

Это объясняет отказ от Setup Hub как центра продукта, уход от меню-реестров, появление Workspaces, приоритет Search над Vacancy, Domain как мост и UI как последний слой.

---

## North star

> **HostFlow моделирует бизнес через сущности предметной области и их жизненные циклы. У каждой Business Entity — неизменная Identity, канонический State, явные Transitions, first-class History и бизнес-время. Один Owner Domain публикует Domain Contract. Workspaces — Commands и Views без собственного state. UI — проекция на языке пользователя, не источник архитектуры. Новые возможности расширяют модель, не дублируют её.**

---

## Два измерения (не одна лестница)

```
  МОДЕЛЬ БИЗНЕСА                    РАБОТА ПОЛЬЗОВАТЕЛЯ
  ─────────────────                  ─────────────────────

  Business Entity                          │
       ↓                                   │
  Identity (immutable)                     │
  State + Time + History                   │
  Life Cycle (explicit transitions)        │
       ↓                                   │
  Owner Domain + Contract ═════════════════╪══► Workspaces
       │                                   │    (Commands + Views)
       │                                   │         ↓
       │                                   │   Permissions
       │                                   │         ↓
       └──► Canonical State               └──►      UI
            + History                         (Human Language)
```

### Измерение 1 — модель бизнеса

| Уровень | Вопрос | Пример |
|---------|--------|--------|
| **Business Entity** | Что существует в предметной области? | Candidate, Search, Client, Vehicle |
| **Life Cycle** | Как **эта** сущность меняет состояние? | Search: draft → ready → active → paused → closed |
| **Owner Domain** | Кто **единственный владелец** изменений entity? | Candidate → Recruitment; Employee → HR |

**Life Cycle принадлежит Entity**, не Domain. Domain **реализует** переходы, но не «придумывает» цикл.

**Entity существует независимо** (см. Entity Independence). **Owner Domain** — единственный, кто **мутирует** каноническое состояние entity. Другие домены: **read**, **use**, **subscribe to events** — не **own**.

### Измерение 2 — организация работы пользователя

| Уровень | Вопрос |
|---------|--------|
| **Workspace** | Где человек **делает работу** с сущностями домена? |
| **Permissions** | Что видно и разрешено? |
| **UI** | Как отображается? |

---

## Три класса сущностей

| Класс | Примеры |
|-------|---------|
| **Business Entity** | Candidate, Search, Client, Vehicle, Employee |
| **Support Entity** | Notification, Audit Log, Integration, Template |
| **Infrastructure** | OAuth Token, Webhook, Queue, Cache |

Полный архитектурный тест — для **Business Entity**. Support/Infrastructure — capability layer, без нового Domain Workspace.

---

## Ownership (один Owner Domain на entity)

| Business Entity | Owner Domain |
|-----------------|--------------|
| Candidate | Recruitment |
| Search | Recruitment |
| Application (отклик) | Recruitment |
| Interview | Recruitment |
| Employee | HR |
| Client | Sales |
| Vehicle | Fleet |
| Driver Assignment | Fleet |

**Правила:**

1. У каждой **Business Entity** — **ровно один** Owner Domain.  
2. Только Owner Domain **изменяет** каноническое состояние entity.  
3. Другие домены **читают**, **используют**, **подписываются на события** — не владеют.  
4. Handoff между доменами — **явный контракт** (событие + snapshot), не двойная запись.

*Пример нарушения:* Recruitment и HR одновременно меняют «статус» Candidate без единого owner — запрещено.

*Переход Candidate → Employee:* смена owner через handoff; Employee с owned HR, Candidate остаётся историей в Recruitment (read-only после handoff — по контракту домена).

---

## Domain Contract (что домен гарантирует)

Ownership отвечает: **кто владеет**. Domain Contract отвечает: **что домен обязан гарантировать** другим доменам и потребителям API.

| Owner Domain | Гарантии (примеры) |
|--------------|-------------------|
| **Recruitment** | Candidate всегда валиден; canonical state и history доступны по контракту; handoff в HR — атомарный snapshot |
| **HR** | Employee соответствует требованиям трудоустройства; изменения employment state — только через допустимые transitions |
| **Fleet** | Vehicle и Driver Assignment отражают актуальное операционное состояние |
| **Sales** | Client — единый контракт для CRM, billing, recruitment (read/use) |

**Правила:**

1. Каждый Domain **публикует стабильный контракт** (события, read API, snapshots для handoff).  
2. Другие домены **не зависят от внутренней реализации** owner — только от контракта.  
3. Breaking change контракта — **версионирование** или явная миграция, не «тихий» refactor.

Ownership + Contract = другие домены знают, **кому доверять** и **чего ожидать**, не заглядывая в таблицы Recruitment.

---

## Canonical State (одно каноническое состояние)

Для каждой **Business Entity** существует:

- **один** канонический статус (life cycle state);  
- **один** жизненный цикл;  
- **одна** история изменений состояния (audit trail).

**Запрещено:**

- Recruitment считает кандидата Approved, HR — Pending, Dashboard — Active одновременно как «истину».  
- Параллельные «статусы» в разных модулях без mapping к canonical state.

Все workspaces, отчёты и домены **читают одно** canonical state из Owner Domain. Производные представления («требует внимания», «горит») — **views**, не вторые источники истины.

---

## Identity, State и Time

Три части модели каждой Business Entity — не смешивать.

### Identity vs State

| | Identity | State |
|---|----------|-------|
| **Что** | Кто/что это в системе | Где entity сейчас в процессе |
| **Пример (Candidate)** | `candidate_id`, дата создания, источник | `current_stage`, `status`, `assigned_recruiter` |
| **Изменения** | **Неизменна** после создания сущности | Меняется постоянно |

**Правило:** **Identity неизменна после создания сущности. Life Cycle изменяет только State.**

Запрещено «переписывать» identity ради UI или миграции (новый id вместо handoff, слияние без audit).

### Time

Время — **часть бизнес-модели**, не техническое поле `updated_at`.

| Entity | Бизнес-время (примеры) |
|--------|------------------------|
| **Search** | `created_at`, `ready_at`, `activated_at`, `paused_at`, `closed_at` |
| **Employee** | `hired_at`, `terminated_at` |
| **Candidate** | `applied_at`, stage timestamps в history |

Timestamp перехода = факт процесса; нужен для SLA, аналитики и «сколько в стадии». Не выводить только из audit log, если бизнес оперирует этим временем явно.

---

## History is First-Class

Canonical state отвечает: **где сейчас**. History отвечает: **как сюда пришли**.

Важно не только «Candidate сейчас Interview», но и цепочка:

```
Applied → Phone Screen → Interview → Offer → Rejected
```

**Правила:**

1. История переходов state — **часть модели**, наравне с текущим состоянием (не побочный debug-log).  
2. History **append-only** относительно прошлых state; исправления — через явные compensating events, не silent overwrite.  
3. Views, аналитика и handoff **могут опираться на history**, не только на current snapshot.

---

## Explicit Transitions

Если у entity есть Life Cycle — **любое** изменение state идёт через **допустимый переход**, не произвольная запись поля.

**Search:**

```
Draft → Ready → Active → Paused → Closed
```

**Запрещено:** `Draft → Closed`, если бизнес этого не допускает.

**Правила:**

1. Переходы **именованы** и **документированы** (не магические enum updates).  
2. Domain API **не экспонирует** «set status = X» без проверки transition graph.  
3. Side effects (уведомления, handoff) **привязаны к transition**, не к UI action.

---

## Entity Independence (тест сущности)

**Business Entity должна иметь смысл сама по себе.**

Если удалить UI, Workspace и конкретный Domain API — она **остаётся** валидной частью бизнеса.

| | Проходит тест? |
|---|----------------|
| Candidate | да |
| Search | да |
| Notification | нет → Support Entity |

---

## Workspace: принципы

### 1. Принадлежит Domain, не Entity

Recruitment Workspace — да. Candidate Workspace — нет.

### 2. «Что делать сейчас», не «какие таблицы существуют»

См. **Navigation follows Work** ниже.

### 3. Commands и Views

Workspace состоит из двух типов элементов:

| Тип | Меняет состояние? | Примеры |
|-----|-------------------|---------|
| **Command** | да | Создать поиск; позвонить кандидату; назначить интервью |
| **View** | нет — помогает решить | Активные подборы; сегодняшние интервью; требуют внимания |

CRM деградируют в таблицы, когда **Views** маскируются под навигацию, а **Commands** размазаны по Settings. Workspace **явно** разделяет действие и обзор.

### 4. Workspace никогда не хранит состояние

Workspace — **не источник данных**. Всегда строится из **Domain API** и canonical state.

Recruitment Workspace можно **полностью переписать** — данные не теряются. Нет «wizard progress», «UI flags», «setup completed» как источника истины.

### 5. Navigation follows Work

Навигация — **по работе**, не по entity:

| Запрещено (entity-nav) | Правильно (work-nav) |
|------------------------|----------------------|
| Candidates | Подборы |
| Searches | Сегодня |
| Interviews | Требуют внимания |
| Documents | Календарь |
| Leads | Коммуникации |

Кандидаты, документы, интервью открываются **внутри** процесса работы (command или drill-down из view), не как обязательные пункты верхнего меню.

---

## Human Language First

Внутренние имена доменной модели **не обязаны** совпадать с языком пользователя.

| В системе (модель / API) | В UI (язык пользователя) |
|--------------------------|--------------------------|
| Candidate | Кандидат |
| Search | Подбор |
| Entity Profile | *(контекстно, часто скрыто)* |
| Intake | Источник заявок |

**Правило:** пользовательский язык определяется **предметной областью пользователя**, а не внутренними именами доменной модели.

Защита от «протекания» Entity Profile, Intake, Lead, Vacancy, G6 в продуктовый UX. Переименование в UI **не требует** переименования entity; переименование entity **требует** ADR и проверки контрактов.

---

## Evolution Principle (расширять, не дублировать)

HostFlow живёт годами. Новые возможности **расширяют** существующую модель, а не создают параллельную.

**Перед новой сущностью / workspace / domain — три вопроса:**

1. Можно ли использовать **существующую Business Entity**?  
2. Можно ли использовать **существующий Life Cycle** (новый transition, не новая entity)?  
3. Можно ли использовать **существующий Workspace** (новый Command или View)?

**Только если трижды «нет»** — создаём новое. Иначе — evolution через контракт, transition, command/view.

*Пример:* «Talent Pool» как отдельная entity — только если Search + Candidate lifecycle не покрывают процесс; иначе — атрибут Search или View.

---

## Правило зависимостей

| Слой | Не знает о |
|------|------------|
| **Business Entity** | Workspace, UI |
| **Life Cycle** | UI, Workspace |
| **Domain (owner)** | React-страницах, UI-типах |
| **Workspace** | ORM, таблицах; **не хранит** business state |
| **UI** | бизнес-правилах |

**Domain** — единственный мост: UI → Workspace → **Domain API** → Entity / Canonical State.

---

## Скорость роста слоёв

| Слой | Рост |
|------|------|
| Business Entities | постоянно |
| Owner Domains | редко |
| Workspaces | очень медленно |

---

## Архитектурный тест (порядок обязателен)

0. **Какой реальный бизнес-процесс?** (первый принцип + критерий ADR)  
0b. **Evolution:** можно ли расширить entity / cycle / workspace?

**Бизнес-модель:**

1. Новая Business Entity? (иначе Support / Infrastructure)  
2. **Identity** vs **State** — что immutable, что в cycle?  
3. Life Cycle + **explicit transitions**?  
4. **Owner Domain** + **Domain Contract**?  
5. **Canonical state** + **history first-class**?  
6. **Business time** — какие timestamps часть процесса?

**Работа и UI:**

7. Новый Domain Workspace? *(редко)*  
8. Command или View?  
9. Permissions?  
10. **Human language** в UI vs имена модели?  
11. Navigation follows work?

### Примеры

**Search:** Entity → cycle → Owner Recruitment → canonical state в Recruitment → Workspace Recruitment → Command «создать поиск» + View «активные подборы».

**Notification:** Support Entity → Platform capability → не owner business entity.

---

## Launchpad

> **Какую работу вы хотите выполнить сегодня?**

Подбор персонала · Оформление · Транспорт · Клиенты · Аналитика

---

## Recruitment Workspace (ориентир)

**Views:** активные подборы · требуют внимания · сегодня · новые отклики  
**Commands:** создать поиск · позвонить · назначить интервью  
**Start:** Search → ссылка / QR / Meta → первый отклик — без gates на экране.

---

## Терминология: Domain Workspace vs Record Workspace

| Термин | Смысл | Пример |
|--------|-------|--------|
| **Domain Workspace** | Среда домена | Recruitment Workspace |
| **Record Workspace** | Карточка одной записи ([ADR-017](../architecture/ADR-017-workspace-layer.md)) | Candidate card |

---

## Связь с текущей реализацией

| Конституция | Сегодня | Направление |
|-------------|---------|-------------|
| Search + Owner Recruitment | Vacancy | фасад / эволюция |
| Canonical state | разрозненные flags, gates, UI | Owner Domain SSOT |
| Commands + Views | nav = таблицы | work-nav |
| Workspace без state | setup wizard progress | domain-only state |
| Ownership + Domain Contract | HR + Recruitment оба трогают candidate | handoff + published contract |
| Identity / State / Time | смешаны id, flags, gates | разделить; business timestamps |
| History + Transitions | частичный audit | first-class history graph |
| Human Language | Vacancy, Lead, Entity Profile в UI | Search, Кандидат, Подбор |
| Evolution | Vacancy + Search + Request параллельно | Search extends Vacancy |

Legacy activation lock: только `recruitment_activation_lock`.

---

## Litmus tests

| Вопрос | Когда |
|--------|-------|
| **Какой бизнес-процесс — не экран?** | ADR, любая фича |
| **Расширяем модель или дублируем?** | новая capability |
| Start или Optimize/Scale? | scope фичи |
| Identity отделена от State? | модель entity |
| Transition допустим? | любая смена status |
| History сохранится? | мутации, миграции |
| Кто Owner и что в Domain Contract? | API между доменами |
| Один canonical state? | статусы, dashboards |
| Command или View? | элемент workspace |
| Human language в UI? | copy, nav, onboarding |
| Navigation follows work? | menu / launchpad |

---

## Связанные документы

- [`architecture-decision-framework.md`](architecture-decision-framework.md) — L1: ADR, Domain Contract, Entity Spec, Layers of Change  
- [`templates/ADR-template.md`](templates/ADR-template.md)  
- [`templates/domain-contract-template.md`](templates/domain-contract-template.md)  
- [`templates/entity-specification-template.md`](templates/entity-specification-template.md)  
- [`platform-architecture-principles.md`](../architecture/platform-architecture-principles.md)  
- [`hostflow-core-domain-map-v1.md`](../architecture/hostflow-core-domain-map-v1.md)  
- [`hostflow-interaction-architecture.md`](../architecture/hostflow-interaction-architecture.md)  
- [`handoff-contract.md`](../architecture/handoff-contract.md)  
- [`ADR-017`](../architecture/ADR-017-workspace-layer.md)  
- [`people-lifecycle-workflow.md`](../workflows/people-lifecycle-workflow.md)  
- [`m1-product-contracts.md`](../journeys/m1-product-contracts.md)  

**При конфликте** по порядку решений: **первый принцип → evolution (расширить?) → entity → identity/state/time → cycle & transitions → history → owner domain & contract → canonical state → workspace → permissions → human language → UI**.
