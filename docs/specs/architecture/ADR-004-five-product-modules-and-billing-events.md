# ADR-004: Five independent product modules & Billing Events

## Status

Accepted (architecture). **Имплементация поэтапная.** Текущий код частично смешивает Recruitment с услугами/счетами — это **технический долг**; новая разработка и рефакторинг должны следовать этому ADR.

## Context

HostFlow продаёт возможности как **независимые продукты** (отдельно, addons, bundle). При этом **Recruitment не является «главным» модулем**: услуги, заказы и финансы не должны жить «внутри» рекрутинга как вторичные функции.

Границы **Tenant / Company / Module / User assignment** — см. [`ADR-003-tenant-company-module-data-boundaries.md`](ADR-003-tenant-company-module-data-boundaries.md). Здесь фиксируется **каталог из пяти модулей** и **единое правило выставления счетов**. Сводная карта **Core / Platform** **vs** пять бизнес-модулей — [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0 и **[`platform-architecture-principles.md`](platform-architecture-principles.md)**.

## Decision: five product modules

Канонические ключи модулей (для `enabled_modules`, лицензий, UI):  
`recruitment` | `hr` | `fleet` | `services` | `finance`

В текущей имплементации tenant-snapshot поле **`recruitment`** выводится как **AND(`candidates`, `leads`, `vacancies`)** (legacy triad); переключатель `recruitment` в API синхронизирует triad. Дальнейшая декомпозиция triad — по мере выноса UI целиком под продукт Recruitment.

| # | Модуль | Назначение (что входит) | Не входит (anti-scope) |
|---|--------|-------------------------|-------------------------|
| **1** | **Recruitment** | Лиды, кандидаты, **вакансии (внутренний спрос)** и **публикация** (job posts, каналы, отклики через Forms — [`ADR-008`](ADR-008-job-publishing-and-distribution.md)), клиенты рекрутинга, процесс подбора, handoff кандидатов | Выставление счетов, каталог/исполнение услуг как бизнес-заказов, employee profile / HR lifecycle, fleet operations |
| **2** | **HR / Kadry** | Employee profile, HR cases, договоры, ZUS, разрешения, документы сотрудника, жизненный цикл сотрудника | Воронка кандидата как основной объект; fleet как операционный контур |
| **3** | **Fleet Management** | ТС, водители/назначения, handover, документы ТС, повреждения, осмотры, готовность к рейсу | «Pipeline» в смысле CRM-воронки; модуль работает через **assignments** и операционные статусы |
| **4** | **Services / Orders** | Каталог услуг, заказы, привязка к клиенту (company/party), выполнение, статусы, **Billing Event** как выход | Прямое создание **invoice**; полный финансовый контур |
| **5** | **Finance / Billing** | Billing events (агрегация), invoices, payments, корректировки / credit notes, НДС/налоговые данные, правила биллинга, статусы оплаты | Операционное выполнение услуги или найма; управление ТС |

### Независимость и автономия

- **Fleet** может работать при выключенных Recruitment и HR (ручной ввод, import/API, ссылки опциональны).
- **HR** может работать без Recruitment (employee из import/API/ручного создания).
- **Services** и **Finance** не обязаны требовать Recruitment.
- Модули интегрируются через **ссылки, события, handoffs**, а не через обязательный монолитный UI или единый pipeline.

### Платформенный слой ввода: Forms (не шестой модуль каталога)

**Forms / Public Forms** — отдельная **platform capability** (шаблоны, публичные ссылки, submissions, файлы, согласия, маппинг, автоматизации). Это **input layer** для Recruitment, HR, Fleet, Services и Finance; **не** расширяет таблицу «пять продуктовых модулей» выше. Продуктовое разделение **Basic** (baseline) vs **Advanced** (addon) — см. [`ADR-007`](ADR-007-forms-platform-capability.md), детальный охват — [`../../forms/module-scope.md`](../../forms/module-scope.md).

### Recruitment и остальные модули

Recruitment **может** инициировать **Billing Event** (например, успешное закрытие этапа, разовый fee по политике tenant) — как **основание** для последующего счёта, но **не** создаёт invoice и не ведёт финансовый учёт.

## Decision: Billing Events (обязательное правило)

**Модули не создают invoices напрямую.**  
Они создают **Billing Event** (или эквивалент в доменной модели): нормализованное событие с суммой/валютой/налоговой базой, ссылкой на источник (entity type + id), `owner_company_id`, модулем-источником.

**Finance / Billing** — единственный модуль, который **создаёт и версионирует invoices** (и связанные платежи/корректировки) **на основании** Billing Events (агрегация, правила, расписания).

Источники Billing Events (не исчерпывающе):

- Recruitment  
- Services / Orders  
- Fleet (например, поездки, штрафы, аренда — по продуктовой политике)  
- **Опционально** HR (например, разовые услуги кадрового аутсорса — только если продукт это вводит)

## Decision: данные и `owner_company_id`

Все перечисленные сущности несут **`owner_company_id`** (или конвергентное поле после унификации — см. ADR-003):

- leads, candidates, vacancies, clients (в контексте модуля)  
- employees (workforce)  
- vehicles, assignments, fleet-артефакты  
- services, service orders  
- **billing_events**, **invoices**, payments  

`tenant_id` остаётся для RLS и биллинга workspace, но **не** заменяет операционный scope по company.

## Company `enabled_modules`

Для каждой **Company** задаётся подмножество модулей, разрешённых на **Tenant**. Пример:

- Company A: `recruitment` only  
- Company B: `hr` + `fleet`  
- Company C: `fleet` only  

См. правила совместимости в ADR-003.

## Company type

Только presets (onboarding, suggested modules, default dashboards). **Не** определяет ownership и не подменяет `enabled_modules`.

## Consequences

1. Планируется **расширение tenant `settings.modules`** (или лицензий) ключами `recruitment`, `services`, `finance` наряду с существующими `candidates`/`leads`/… — потребуется **маппинг** старых флагов на новые продуктовые модули (миграция настроек).
2. UI и маршруты «Услуги / Заказы / Счета» должны в перспективе жить под **своими** product boundaries и проверками модуля, а не только под Recruitment.
3. Ввод **таблицы/шины Billing Event** и запрет прямых `invoice` из Recruitment/Services/Fleet — отдельная серия задач (схема БД + сервисный слой).
4. Документы модулей (`docs/hr/…`, `docs/fleet/…`) и будущий `docs/recruitment/`, `docs/services/`, `docs/finance/` должны ссылаться на этот ADR.

## References

- [`ADR-005-three-level-settings-hierarchy.md`](ADR-005-three-level-settings-hierarchy.md) — tenant / company / module settings; **Tenant = что куплено**, **Company = кто работает**, **Module Settings = как работает модуль у company**.  
- [`ADR-006-marketplace-and-integration-platform.md`](ADR-006-marketplace-and-integration-platform.md) — **пять модулей** как *paid business modules* внутри слоёв платформы; интеграции и Marketplace — отдельно от ADR-004.  
- [`ADR-007-forms-platform-capability.md`](ADR-007-forms-platform-capability.md) — **Forms** как платформенный ввод данных; не шестой ключ `enabled_modules` ADR-004.  
- [`ADR-008-job-publishing-and-distribution.md`](ADR-008-job-publishing-and-distribution.md) — **Job Publishing** как capability **внутри** Recruitment (Vacancy / Job Post / Channel + Forms).  
- [`ADR-009-document-hub-platform-layer.md`](ADR-009-document-hub-platform-layer.md) — **Document Hub**: общий registry документов для модулей; файлы не «принадлежат» только Recruitment или только HR.  
- [`ADR-003-tenant-company-module-data-boundaries.md`](ADR-003-tenant-company-module-data-boundaries.md)  
- [`ADR-002-modular-recruitment-hr-boundary.md`](ADR-002-modular-recruitment-hr-boundary.md)  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — ключи тенанта, карта API, scope-файлы.  
- `docs/specs/architecture/rbac_matrix.md`
