# Каталог продуктовых модулей и карта маршрутов (HostFlow)

**Канон домена и границ (v1):** **[`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md)** — владение, скоупы, cross-company, взаимодействие модулей.

**Обзор архитектуры платформы** (multi-company SaaS, Tenant vs Company, модули vs shared layer, RBAC, cross-company) — **[`platform-architecture-principles.md`](platform-architecture-principles.md)**.  
**Platform Rules P-01…P-05 · L0 FROZEN** — [`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md); P-ADRs [`ADR-025`](ADR-025-standard-adapter-boundary.md)…[`ADR-029`](ADR-029-settings-contract.md); **Catalog** — [`platform-capability-catalog.md`](platform-capability-catalog.md); **Settings Manifest** — [`capability-settings-manifest.md`](capability-settings-manifest.md); **Capability Contract** — [`capability-contract.md`](capability-contract.md); **обязательный** checklist — [`architecture-review-checklist.md`](architecture-review-checklist.md); guide — [`architecture-guide.md`](architecture-guide.md); **compliance outbound** — [`ADR-031`](ADR-031-compliance-outbound-requires-opaque-result.md) (**Accepted**); **Sales Order → Order Line → Vacancy → Billable** — [`ADR-032`](ADR-032-client-order-vacancy-flight-chain.md) (**Accepted**); **Lead lifecycle email company policy** — [`ADR-033`](ADR-033-lead-lifecycle-email-company-policy.md) (**Accepted**); **Four trust roles RBAC** — [`ADR-036`](ADR-036-four-trust-roles-rbac.md) (**Accepted**).

Документ — **нормативная карта** для разработки: какие ключи модулей существуют, как они связаны с API и настройками тенанта/компании, и что уже имплементировано vs запланировано. Детали биллинга и владения данными — [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md), [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md). **Иерархия настроек** (Tenant → Company → Module Settings per company) — [`ADR-005`](ADR-005-three-level-settings-hierarchy.md). **Интеграции, витрина Marketplace и слои платформы** (core integrations vs модули vs apps) — [`ADR-006`](ADR-006-marketplace-and-integration-platform.md). **Публичные формы как платформенный input layer** — [`ADR-007`](ADR-007-forms-platform-capability.md), scope — [`../../forms/module-scope.md`](../../forms/module-scope.md). **Acquisition / Campaigns and Intake Routing** — [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md), [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md). **Публикация вакансий (Vacancy / Job Post / каналы)** внутри Recruitment — [`ADR-008`](ADR-008-job-publishing-and-distribution.md). **Document Hub** — общий слой документов для всех модулей — [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md). **Единые списки сущностей в SPA** (таблицы, фильтры, колонки, rail/modal) — [`ADR-010`](ADR-010-unified-resource-list-shell.md). **Полный стандарт UI приложения** (кнопки, сетка, шрифты, формы, даты, языки, настройки) — [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md). **Activity & Notification Operating Layer** — единая capability для задач/напоминаний/уведомлений/планировщика/календаря — [`ADR-012`](ADR-012-activity-notification-operating-layer.md), canon — [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md). Граница Recruitment ↔ HR — [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md). **Разделение Recruitment ↔ Sales (продуктовая поверхность)** и **Deployment / URL Boundaries** (поддомены модулей) — [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) §3.7.

---

## 0. Карта платформы: Core / Platform vs Business modules

Сводная модель продукта (для позиционирования и границ ответственности). Полная формулировка принципов — **[`platform-architecture-principles.md`](platform-architecture-principles.md)**. **Кодовые флаги**, legacy triad и матрица ролей — в §1–2; детали Forms / Marketplace / Job Publishing / Document Hub — в ADR-006–009.

### Core / Platform (shared capabilities)

Возможности **workspace**, от которых зависят бизнес-модули; **не** пять ключей ADR-004. Tenant — граница подписки и биллинга; **операционные данные принадлежат Company** (`owner_company_id`, см. ADR-003 и platform principles).

| Область | Назначение |
|---------|------------|
| **Companies** | Операционная / data boundary: `Company`, `enabled_modules`, ACL, party (ADR-003) |
| **Users / Roles / Permissions** | Trust roles (**ADR-036**: `superadmin` / `administrator` / `employee` / `viewer`), permissions, presets, org, scope, `access_context` (`tenant`\|`portal`); матрица — [`rbac_matrix.md`](rbac_matrix.md) |
| **Settings** | Три уровня: Tenant → Company → Company Module Settings ([`ADR-005`](ADR-005-three-level-settings-hierarchy.md)) |
| **Forms** | **Input layer** ([`ADR-007`](ADR-007-forms-platform-capability.md), [`../../forms/module-scope.md`](../../forms/module-scope.md)) |
| **Acquisition / Campaigns** | Demand flow + intake routing ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md), [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md)); **не** Marketing-продукт |
| **Document Hub** | Единый registry документов ([`ADR-009`](ADR-009-document-hub-platform-layer.md), [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md)) |
| **Process Engine** | Единый движок процессов: stages, profiles, pipelines, transition/handoff rules, runtime evaluator ([`process-engine.md`](../platform/process-engine.md)) |
| **Integrations / Marketplace** | Core integrations + apps ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md)); module installation audit/canon: [`module-registry-marketplace-installation.md`](../platform/module-registry-marketplace-installation.md) |
| **Automations** | Правила, триггеры, сценарии между сущностями |
| **Activity & Notification Operating Layer** | Единый слой задач, напоминаний, уведомлений, планировщика и календарных представлений; **не** разные модули, см. [`ADR-012`](ADR-012-activity-notification-operating-layer.md) и canon [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md) |
| **Trust & Reputation Layer** | Проверенная операционная история и сигналы доверия (политика продукта); см. [`platform-architecture-principles.md`](platform-architecture-principles.md) §6.1 |
| **Resource List Shell** | Единая оболочка списков в SPA (таблица, фильтры, колонки, сортировка); [`ADR-010`](ADR-010-unified-resource-list-shell.md) |
| **UI Platform Standard** | Токены, a11y, даты, i18n ([`ADR-011`](ADR-011-hostflow-ui-platform-standard.md)); **composition** — React kit public API ([`ADR-043`](ADR-043-ui-component-composition-canon.md) · [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md)); **analytics** — [`ADR-046`](ADR-046-analytics-visualization-canon.md) · [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md) (grammar + presentation/sharing); реализация CSS — `components.css` |

*Дополнительно на уровне tenant: subscription, billing, security, audit — см. [`platform-architecture-principles.md`](platform-architecture-principles.md) §2.*

### 0.1 Platform Capability Catalog (owners index)

**Полный SoT границ (Owns / Configures / Exposes / Consumes / Forbidden / passport):**  
→ [`platform-capability-catalog.md`](platform-capability-catalog.md)

Ниже — **краткий индекс владельцев** (**P-02**). Потребление — через канонические адаптеры (**P-01**). Новое — композиция (**P-03**). Конфигурация — **P-04** / **Configures**. Споры о границах — только по полному каталогу.

| Capability | Owner (SoT) | Normative ADR / docs | Typical consumers | Canonical contract family |
|------------|-------------|----------------------|-------------------|---------------------------|
| **Endpoint** | Intake / Acquisition boundary | [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) | Acquisition, Forms (HostFlow Form is-a), API, Mobile, Meta, … | Endpoint Adapter |
| **Submission** (universal intake record) | Shared Intake | ADR-021 / ADR-022 / ADR-024 | Recruitment, Sales, HR, Services, … | Submission / Intake contracts |
| **Forms** (builder, version, consent, form surface) | Forms | [`ADR-007`](ADR-007-forms-platform-capability.md), [`../../forms/module-scope.md`](../../forms/module-scope.md) | All modules | Endpoint Adapter (HostFlow Form) + Forms public APIs |
| **Acquisition / Campaigns** | Acquisition | [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md), [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md) | Growth / demand; not Result SoT | Campaign / Flight / routing APIs |
| **Documents** | Document Hub | [`ADR-009`](ADR-009-document-hub-platform-layer.md) | Recruitment, HR, Fleet, Finance, … | Document Adapter |
| **Notifications** | Activity & Notification Operating Layer | [`ADR-012`](ADR-012-activity-notification-operating-layer.md) | All modules | Notification Adapter |
| **Activity** | Activity & Notification Operating Layer | ADR-012 | All modules | Activity contracts |
| **Automations** | Automations | [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) | All modules | Automation Adapter |
| **AI** | AI platform capability | ADR-025 (AI Adapter); future AI ADR | All modules | AI Adapter |
| **Search** | Global Search | Search services / future Search ADR | All modules | Search Adapter |
| **Integrations / Marketplace** | Integrations | [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) | All modules | Integration Adapters |
| **Process Engine** | Process Engine | [`process-engine.md`](../platform/process-engine.md) | Business modules | Process contracts |
| **Field Registry / Entity Profile** | Platform Reference | platform specs | Forms, Intake, modules | Reference / profile contracts |
| **Object Kind Catalog (meta)** | Platform architecture | [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) | Documents, Requirements, Automations, Forms (index) | Meta-index — **not** a data SoT |
| **Platform Standardization Model** | Platform architecture | [`ADR-038`](ADR-038-platform-standardization-model.md) · [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) | All modules / capabilities | Area map + Platform-first — **not** a data SoT |
| **State / Lifecycle Inventory** | Platform architecture | [`ADR-039`](ADR-039-state-lifecycle-inventory.md) · [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md) | Object Kind slice consumers | Dimension inventory — **not** shared status enum |
| **Naming & Identifiers** | Platform architecture | [`ADR-040`](ADR-040-naming-identifiers.md) · [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md) | Registries / bridges / modules | Naming rules + conflict inventory — **not** DocumentType seed alignment |
| **Data Types** | Platform Reference (target) | [`ADR-041`](ADR-041-data-types.md) · [`../platform/data-types.md`](../platform/data-types.md) | Field Registry, Forms, UI binders | Semantic types — Field **uses** DataType; runtime adoption deferred |
| **Relationships** | Platform architecture | [`ADR-042`](ADR-042-relationships.md) · [`../platform/relationships.md`](../platform/relationships.md) | Document Hub, handoff, Activity, Comms | RelationshipKind contract — confirmed slice only; **not** full CRM graph |
| **UI Component Canon** | Frontend platform | [`ADR-043`](ADR-043-ui-component-composition-canon.md) · [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md) | SPA product modules | React kit composition — **not** a restyle |
| **List Workspace Canon** | Frontend platform | [`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md) · [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md) | All operational entity lists | `collection_orchestration` / `ListWorkspace`; modules pass definition + data; DataTable is a representation |
| **Analytics, Visualization & Reporting Canon** | Frontend platform | [`ADR-046`](ADR-046-analytics-visualization-canon.md) · [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md) | Efficiency dashboards / Overview | Meaning→family + story composition + Analytics View; Recruitment = reference; other dashboards migrate-on-touch |
| **Actions** | Platform Automations (target) | [`ADR-047`](ADR-047-actions.md) · [`../platform/actions.md`](../platform/actions.md) | Document Hub, PE, Activity, Notifications | Action contract — confirmed slice; **not** 3A-3 runtime registry |
| **Platform Extraction** | Frontend platform + architecture | [`platform-extraction-phase.md`](platform-extraction-phase.md) · [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) | All product modules | Core Platform Kit before Phase B — **not** a fifteenth vocabulary area |
| **Resource List Shell / UI Standard** | Frontend platform | ADR-010 / ADR-011 / ADR-043 / ADR-044 | SPA | List zones + ListWorkspace product API |

**Уточнение Submission vs Forms:** Forms владеет **form surface + consent version pin** для HostFlow Form. Универсальный **Submission** как intake object и routing envelope — Shared Intake (ADR-024 spine). Не два Form Builder; не два Document Hub.

**Business modules** (Recruitment, Sales/Services, HR, Fleet, Finance) владеют **только** своими domain entities и **композируют** platform capabilities — границы в [`platform-capability-catalog.md`](platform-capability-catalog.md).

### Business modules (пять продуктов ADR-004)

Лицензируемые контуры; ключи `recruitment` \| `hr` \| `fleet` \| `services` \| `finance`.

| # | Модуль | Состав (логический; не исчерпывает все сущности) |
|---|--------|--------------------------------------------------|
| **1** | **Recruitment** | **Applications**, **Candidates**, **Vacancies**, **job posts**, **job publishing**, подбор, handoff; pipeline только по Application/Candidate ([`ADR-008`](ADR-008-job-publishing-and-distribution.md), [`ADR-023`](ADR-023-recruitment-sales-module-separation.md)); **не** Sales Inquiry / ClientAccount / employees lifecycle / fleet / services / invoices |
| **2** | **HR / Kadry** | Employee profile, HR cases, lifecycle, contracts, ZUS, work permits, employee docs, payroll data, onboarding/termination; **автономен** без Recruitment |
| **3** | **Fleet Management** | **Не воронка** — модуль **назначений и операций**: ТС, водители, assignments, handover, документы ТС, damage, inspections, readiness, return; автономен без Recruitment/HR |
| **4** | **Services / Orders** | Каталог, заказы, статусы, **Billing Events** — не invoices ([`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)); **не** отдельный deploy-host — UI entry через Sales commercial surface ([`ADR-023`](ADR-023-recruitment-sales-module-separation.md) §3.7) |
| **5** | **Finance / Billing** | **Invoices** из **Billing Events**; платежи, НДС, правила; модули **не** создают invoice напрямую |

### Deployment hosts (пять бизнес-модулей + shell) — ADR-023 §3.7

Канон URL (production): `hostflow.cc` (shell) + `recruitment` \| `hr` \| `sales` \| `fleet` \| `finance` `.hostflow.cc`.  
**Sales** — deployable commercial host; ADR-004 key `services` остаётся лицензией capability, не шестым поддоменом.

**Правило:** Leads / Candidates / Vacancies / Job Publishing — **не** выносятся в отдельные «модули ADR-004»; они входят в **Recruitment** как подсистемы. Столбцы Core / Platform (**Settings**, **Forms**, **Acquisition / Campaigns**, **Document Hub**, **Integrations**, **Automations**, **Activity & Notification Operating Layer**, **Trust & Reputation**, **Resource List Shell**, **UI Platform Standard**, **Users**, **Companies**) **не** являются шестым+ ключом `enabled_modules` ADR-004 — это **shared capabilities**; лицензирование features (Basic/Advanced) — отдельно ([`platform-architecture-principles.md`](platform-architecture-principles.md)).

**Правило для Activity & Notification:** «Notifications» и «Activity / Tasks» — **не два отдельных модуля**, а **одна capability** (`ADR-012`). Никаких «модулей уведомлений», «модулей задач», «модулей планировщика» или «модулей todo» в каталоге HostFlow быть не должно. Реализация — `Activity` + `Notification` (две таблицы), всё остальное — представления.

---

## 1. Два слоя: продукт vs подмодули UI

| Слой | Назначение | Где живёт |
|------|------------|-----------|
| **Пять продуктовых модулей (ADR-004)** | Лицензирование, продуктовые границы, company scope | Ключи: `recruitment`, `hr`, `fleet`, `services`, `finance`; внутри **recruitment** — capability **Job Publishing** ([`ADR-008`](ADR-008-job-publishing-and-distribution.md)), не отдельный модуль ADR-004 |
| **Forms / Public Forms (ADR-007)** | Платформенный **input layer**: шаблоны, публичные ссылки, submissions, маппинг в сущности модулей | **Не** шестой ключ ADR-004; Basic = core capability, Advanced = addon; см. [`../../forms/module-scope.md`](../../forms/module-scope.md) |
| **Acquisition / Campaigns (ADR-024)** | Кампании, источники, атрибуция, `route_intent` → module object | **Не** Marketing-продукт; shell UI; см. [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md); матрица входов [`intake-canonical-input-matrix.md`](intake-canonical-input-matrix.md) |
| **Document Hub (ADR-009)** | Платформенный **document layer**: типы, шаблоны, наборы требований, links, multi-module review | **Не** ключ ADR-004; Basic / Advanced document management; см. [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md) |
| **Legacy / гранулярные флаги тенанта** | Матрица ролей, постепенный перенос UI | `candidates`, `leads`, `vacancies`, `documents`, `companies`, `client_portal`, плюс те же пять где применимо |

**Правило чтения `recruitment`:** в снимке настроек (`get_module_settings_snapshot`) значение **`recruitment` всегда выводится** как  
`candidates ∧ leads ∧ vacancies`. При PATCH платформы/тенанта переключение `recruitment` синхронизирует triad (см. `backend/app/api/v1/tenants/service.py`). Матрица ролей может показывать строку `recruitment` отдельно — эффективное «вкл/выкл продукта» для данных контура подбора = triad.

---

## 2. Канонические ключи (`tenant.settings.modules` / матрица)

Полный набор ключей в `_MODULE_DEFAULTS` (источник правды в коде):

| Ключ | Продуктовый модуль / роль | Примечание |
|------|---------------------------|------------|
| `candidates` | Recruitment (часть triad) | |
| `leads` | Recruitment (часть triad) | |
| `vacancies` | Recruitment (часть triad) | |
| `companies` | Recruitment / общий справочник | Клиентские компании в CRM |
| `documents` | Recruitment (документы кандидата) | Не путать с HR-документами сотрудника |
| `services` | Services / Orders (ADR-004) | Услуги, заказы; **отдельного HTTP module-gate по `services` пока нет** |
| `client_portal` | Канал доставки | Не отдельный продуктовый модуль ADR-004 |
| `hr` | HR / Kadry | HTTP gate: `auth/hr_workforce_access.py` → `/api/v1/workforce/*` |
| `fleet` | Fleet | HTTP gate: `auth/fleet_access.py` → `/api/v1/fleet/*` |
| `recruitment` | Recruitment (продукт) | Derived в snapshot; хранится синхронно при записи |
| `finance` | Finance / Billing | Флаги UI/матрицы; **отдельного HTTP gate «только finance» пока нет**; счета — см. `/api/v1/invoices` |

`Company.enabled_modules` (JSON, nullable): пересечение с эффективными модулями тенанта — `services/company_module_access.py`. **HTTP-проверки по company для модулей** (ADR-003 P1b): **частично** — Recruitment: **candidate** (POST, GET by id, PATCH с переназначением company/vacancy), **список** (`GET /candidates`, `count`, `fetch_*`, insights) через SQL-предикат `recruitment_candidate_list_sql_clause`, **no-next-action**, **bulk-stage** / **bulk-manager**, **delete**; **vacancy** (GET by id, POST create, PATCH, DELETE, attach candidate). Далее — фильтр `GET /vacancies` по company, **leads**, остальные модули.

### 2.1 Иерархия настроек (канон)

Каноническая модель — **три уровня**, см. [`ADR-005`](ADR-005-three-level-settings-hierarchy.md):

1. **Tenant Settings** — подписка, глобальные модули, биллинг, пользователи workspace, security, audit, брендинг workspace, locale, **только default presets** (не операционные процессы company).  
2. **Company Settings** — тип company, юрданные, пользователи/роли company, `enabled_modules`, ответственные, часы работы, оргструктура, брендинг company, visibility.  
3. **Company Module Settings** — пайплайны, шаблоны, правила конкретного модуля **внутри company**; рекомендуемая таблица `company_module_settings` (`tenant_id`, `company_id`, `module_key`, `settings_json`, `is_enabled`, `configured_at`).

**Текущий код** частично кладёт всё в `tenant.settings`; новые фичи — с company scope и ADR-005.

**Architecture gate (P0, блокирует модульную независимость):** [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) — company-scoped funnels, module ownership, Recruitment resolver, strangler для legacy `system_stage`. **Target canon:** [`ADR-035`](ADR-035-module-object-pipeline-settings.md) (Module → Objects → Pipelines → Settings; system transitions). **HR manifest / employee pipeline / typed module-settings UI — только после закрытия P0 gate.**

---

## 3. Карта: продукт → основные API-префиксы

Неполный перечень ориентиров; новые эндпоинты модуля добавлять в эту таблицу в том же PR.

| Продукт | Ключ(и) | Префиксы `/api/v1/...` | Tenant gate (код) |
|---------|---------|-------------------------|-------------------|
| **Recruitment** | triad + `recruitment` | **facade** `recruitment/applications`; `candidates`, `vacancies`, `documents`, `funnels`, `handoffs`, `stages`, `recruiters`, `next-actions`, …; `leads` = transport/admin only ([`ADR-023`](ADR-023-recruitment-sales-module-separation.md)) | Нет единого deps; видимость через матрицу модулей / роли |
| **Sales** (commercial) | commercial surface; not Finance owner | **product** `sales/inquiries`, `sales/clients` (legacy `client-accounts` compat); later opportunities | [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) Stage 2A; Invoice/Payment → Finance |
| **HR** | `hr` | `workforce`, `admin/...` (оргструктура) | `hr_workforce_access` на `workforce` |
| **Fleet** | `fleet` | `fleet` | `fleet_access` |
| **Services** | `services` | **product** `services/catalog`, `services/orders` (+ legacy `/services`, `/service-orders`); **owns** Service Order lifecycle | Нет выделенного gate (Stage 2B) |
| **Finance** | `finance` | **product** `finance/invoices`, `finance/payments` (+ legacy `/invoices`); **owns** Invoice/Payment model | Нет выделенного gate (Stage 2B); Cash Loop gated — ADR-023 §3.6 |
| **HR** | `hr` | **product** `hr/employees` (+ legacy `workforce/*`); inbox under `/hr/*` | `hr_workforce_access` на workforce; Stage 2B expands gates |

Порталы: `client`, `candidate`, публичные intake — RBAC: portal guest = `viewer` + `access_context=portal` ([`ADR-036`](ADR-036-four-trust-roles-rbac.md), [`rbac_matrix.md`](rbac_matrix.md)); candidate/magic-link — вне CRM trust roles.

---

## 4. SPA и пути

Канонические пути приложения: **`shared/crm_app_paths.json`** → `scripts/codegen/generate_crm_app_paths.py` → `hostflow-frontend/src/app/crmAppPaths.generated.ts`, `backend/app/constants/spa_paths.py`. При добавлении раздела продукта обновлять JSON и прогонять codegen.

---

## 5. Охват по модулям (документы scope)

| Модуль | Документ scope |
|--------|----------------|
| Recruitment | [`docs/recruitment/module-scope.md`](../../recruitment/module-scope.md) |
| Sales (Product B surface) | [`ADR-020`](ADR-020-sales-to-engagement-commercial-model.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) — umbrella над Inquiry + Services + Finance cash path (separate `docs/sales/module-scope.md` not yet present) |
| HR | [`docs/hr/module-scope.md`](../../hr/module-scope.md) |
| Fleet | [`docs/fleet/module-scope.md`](../../fleet/module-scope.md) |
| Services / Orders | [`docs/services/module-scope.md`](../../services/module-scope.md) |
| Finance / Billing | [`docs/finance/module-scope.md`](../../finance/module-scope.md) |
| Forms / Public Forms (платформа) | [`docs/forms/module-scope.md`](../../forms/module-scope.md) |
| Acquisition / Campaigns (платформа) | [`docs/acquisition/module-scope.md`](../../acquisition/module-scope.md) |
| Document Hub (платформа) | [`docs/document-hub/module-scope.md`](../../document-hub/module-scope.md) |

---

## 6. Чек-лист готовности к следующей волне имплементации

Использовать как **ворота** перед серией PR (company-gates, Billing Events, роли).

- [x] Зафиксированы ADR-002, ADR-003, ADR-004 и настоящий каталог.
- [x] **[`platform-architecture-principles.md`](platform-architecture-principles.md)** — modular multi-company SaaS, shared platform capabilities (вкл. Settings, Automations, Notifications, Activity), формула Tenant/Company/Module/User scope.
- [x] **ADR-007** — Forms / Public Forms как платформенный input layer (не шестой продуктовый модуль ADR-004); см. §8 и [`../../forms/module-scope.md`](../../forms/module-scope.md).
- [x] **ADR-024** — Acquisition / Campaigns and Intake Routing (не Marketing-продукт); [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md); Stage 3 после cutover.
- [x] **ADR-008** — Job Publishing / Distribution внутри Recruitment (Vacancy ≠ Job Post ≠ Channel; форма отклика через Forms); см. §9 и [`../../recruitment/module-scope.md`](../../recruitment/module-scope.md).
- [x] **ADR-009** — Document Hub как shared platform layer (Document / Link / Requirement / Review; без копирования между модулями); см. §10 и [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md).
- [x] Tenant defaults и snapshot `recruitment`/triad в коде.
- [x] Колонка `companies.enabled_modules` + `company_module_access` (без обязательного HTTP enforcement).
- [x] Таблица + API **`company_module_settings`**: `GET/PATCH /api/v1/companies/{company_id}/module-settings/{module_key}` (канонические ключи `recruitment` \| `hr` \| `fleet` \| `services` \| `finance`); список `GET .../module-settings`.
- [x] Типизированные схемы **`HrModuleSettingsV1`**, **`RecruitmentModuleSettingsV1`**, **`FleetModuleSettingsV1`**, **`ServicesModuleSettingsV1`**, **`FinanceModuleSettingsV1`** (`backend/app/schemas/company_module_settings_json.py`): валидация на PATCH, нормализация на GET для всех пяти ключей.
- [x] Минимальный UI на карточке компании (вкладки модулей, JSON, `is_enabled`); полноценные формы по полям — в бэклоге.
- [ ] **[`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md)** — Recruitment: `funnels.company_id` + `module_key`, resolver, runtime wiring (`/meta/stages`, candidate/lead, analytics, funnels UI); gate before HR pipeline.
- [ ] Единый способ **active company** в запросе (header / session) согласован с фронтом.
- [ ] Зависимости FastAPI: `company_allows_module(..., "fleet"|"hr"|…)` на соответствующих роутерах.
- [ ] API админки: PATCH company с `enabled_modules` + валидация ключей.
- [ ] Таблица/сервис **Billing Event** + запрет прямого invoice из операционных модулей (кроме явных legacy путей под миграцию).
- [ ] Назначения ролей `(user, company, module, role)` — дизайн миграции от текущей модели.

Когда пункты выше согласованы с продуктом — можно считать **спецификацию закрытой для старта P2/P3** в терминах ADR-003.

---

## 7. План: Marketplace & Integration Platform ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md))

Эволюция **Integration Hub** → **HostFlow Marketplace**; разделение **Platform features**, **Business modules** (ADR-004), **Core integrations (free)** и **Marketplace apps**. Чек-лист имплементации (не блокирует текущую разработку модулей):

- [x] Канонические **`offer_key`** и категории витрины — [`../marketplace-catalog-keys.md`](../marketplace-catalog-keys.md) + `backend/app/constants/marketplace_offer_catalog.py` (единый каталог UI/API без отдельной таблицы `marketplace_offers` — в бэклоге).
- [x] MVP **tenant**: таблица `tenant_integration_installations` (`offer_key`, `offer_kind`, `status`, `settings_json`) — см. [`marketplace-integrations-data-model.md`](marketplace-integrations-data-model.md).
- [x] MVP **company**: таблица `company_integration_enablements` (`is_enabled`, `usage_json`) + существующие `enabled_modules` + `company_module_settings` (ADR-005).
- [ ] UI витрины: не смешивать **базовые comms** с платными модулями без явной маркировки; продуктовое правило — **не монетизировать агрессивно** WhatsApp/Telegram/Gmail/Google-интеграции (см. ADR-006).
- [ ] Биллинг / entitlements для **marketplace apps** (free / paid / third-party) — дизайн отдельно от core integrations.
- [ ] Позиционирование платформы в коммуникациях: **Modular Workforce Operations Platform with Marketplace Ecosystem** (см. ADR-006).

---

## 8. План: Forms / Public Forms ([`ADR-007`](ADR-007-forms-platform-capability.md))

Отдельный контур форм, используемый всеми бизнес-модулями; эволюция от **`tenant_lead_forms`** / **`/public/intake`** к универсальной модели.

- [ ] Целевая схема: **FormTemplate** → **Publication** (public link) → **Submission** + вложения + consent; версии шаблонов.  
- [ ] Режимы **standalone** и **linked** (привязка к сущности / процессу / модулю).  
- [ ] **Handlers** создания/обновления: Lead, Candidate, Employee, Client/party, Service Order, сущности Fleet (damage, inspection, …), Document, billing profile — по конфигурации формы.  
- [ ] **Basic** (бесплатно / baseline): форма, ссылка, submission, файлы.  
- [ ] **Advanced** (платно / addon): условные поля, маппинг, автоматизации, e-sign/consent tracking, бренд, мультиязычность, expiry, порталы.  
- [ ] Entitlements / биллинг Advanced отдельно от пяти модулей ADR-004 (флаг вида `forms_advanced` или эквивалент — по продукту).  
- [ ] Документация потребителей: [`../../forms/module-scope.md`](../../forms/module-scope.md) + ссылки из scope HR/Fleet/Services/Finance.

---

## 9. План: Job Publishing / Distribution ([`ADR-008`](ADR-008-job-publishing-and-distribution.md))

Слой **внутри Recruitment**: внутренняя **Vacancy** ≠ публичный **Job Post** ≠ **Publishing Channel**; отклик через **Forms** → Lead/Candidate.

- [x] Зафиксированы сущности, flow и зависимость от Recruitment + Forms (документ ADR-008 + recruitment scope).  
- [ ] Модель данных: `job_posts`, привязки к `vacancies`, каналы, статусы публикации, ссылка на form template / publication id.  
- [ ] Мультипосты на vacancy (языки, порталы, кампании); атрибуция source/channel/campaign на lead/candidate.  
- [ ] Basic vs **advanced** addon (политика SKU); коннекторы порталов через Marketplace ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md)).  
- [ ] Закрытие публикации без смешения со статусом vacancy; метрики **channel → candidate**.  
- [ ] Блокировка UI/API при `recruitment` выключен.

---

## 10. План: Document Hub ([`ADR-009`](ADR-009-document-hub-platform-layer.md))

Единый слой документов для всех модулей; **не** ключ ADR-004.

- [x] Зафиксированы сущности, правило **no copy** (только links + permissions), Requirement/Review для мульти-модульной проверки, Basic/Advanced (документ + scope).  
- [ ] Схема БД / миграции: `document_links`, `document_requirements`, `document_reviews`, document sets (эволюция от текущих `Document*` таблиц).  
- [ ] API: запрос required set по модулю/процессу; создание документа из Forms upload → Hub.  
- [ ] UI: экран Document Hub + встраивание в карточки Candidate / Employee / Vehicle / Order / Client / HR Case / Assignment.  
- [ ] Handoff документов клиенту: явные политики доступа и срока.  
- [ ] Entitlements: Advanced document management как addon.

---

## История

- 2026-08-21: **ListWorkspace orchestration** — kit-layer id `collection_orchestration`; Vacancies proof (`useListWorkspace` + definition; DataTable is a representation).
- 2026-08-13: **Platform Extraction** — Vocabulary Canon (ADR-037…047) closed; Core Platform Kit is the active slice before Phase B ([`platform-extraction-phase.md`](platform-extraction-phase.md)).
- 2026-08-13: **ADR-044** (Accepted) — List Workspace & Data Presentation (`ListWorkspace` + one `DataTable`); L2 [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md); runtime extract epic P1–P2.
- 2026-08-13: **ADR-046** (Accepted) — Analytics, Visualization & Reporting Canon (four layers; Analytics View; Recruitment efficiency reference); L2 [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md).
- 2026-08-13: **ADR-043** (Accepted) — UI Component & Composition Canon (React kit public API; CSS implementation); L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md); epic [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md).
- 2026-08-13: **ADR-047** (Accepted) — Actions (Action ≠ Permission ≠ Capability; confirmed Documents/Activity/PE slice); L2 [`../platform/actions.md`](../platform/actions.md); 3A-3 runtime deferred.
- 2026-08-13: **ADR-042** (Accepted) — Relationships (RelationshipKind contract + confirmed slice; opaque result ≠ domain entity); L2 [`../platform/relationships.md`](../platform/relationships.md); CRM graph deferred.
- 2026-08-13: **ADR-041** (Accepted) — Data Types (Field ≠ DataType; v1 semantic set + fragment map); L2 [`../platform/data-types.md`](../platform/data-types.md); runtime adoption deferred.
- 2026-08-13: **ADR-040** (Accepted) — Naming & Identifiers (kinds / namespaces / alias policy); L2 [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md); DocumentType runtime alignment deferred.
- 2026-08-13: **ADR-039** (Accepted) — State / Lifecycle Inventory for Object Kind slice (`ObjectKind → Object → dimension → owners`); L2 [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md); shared status enum deferred.
- 2026-08-13: **ADR-038** (Accepted) — Platform Standardization Model (5 groups · 14 areas · Platform-first / Reuse-first; Enforcement as mechanism); L2 [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md).
- 2026-08-13: **ADR-037** (Accepted) — Platform Object Kind Catalog meta-canon (`ObjectKind` / `RuleKind` / `LibraryKind`); L2 index [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md); Documents / Requirements / Automation / Templates slice.
- 2026-08-07: **ADR-036** (Accepted) — four trust roles invariant; ceilings; presets ≠ roles; `access_context` tenant\|portal; inventory gate [`rbac-role-usage-inventory.md`](rbac-role-usage-inventory.md); [`ADR-036-four-trust-roles-rbac.md`](ADR-036-four-trust-roles-rbac.md).
- 2026-08-07: **ADR-035** (Accepted, frozen) — Module → Objects → Pipelines → Settings; operational stages vs platform system transitions; four-object rule; [`ADR-035-module-object-pipeline-settings.md`](ADR-035-module-object-pipeline-settings.md).
- 2026-07-30: **ADR-034** (Accepted) — three canonical public funnels (Growth / Auth / Candidate); Success Path via guided readiness UI [`self-service-success-path.md`](../journeys/self-service-success-path.md); no parallel product landings.
- 2026-07-29: **ADR-033** (Accepted) — Company-owned lead lifecycle email policy + sparse Vacancy override; Control Center under Communications; [`lead-lifecycle-email-policy.md`](../workflows/lead-lifecycle-email-policy.md).
- 2026-07-31: **ADR-033 errata** — SoT = OwnCompany (firm); client company + vacancy = optional override; resolver slice A.
- 2026-07-28: **ADR-032** (Accepted) — Sales Service Order → Order Line → Vacancy → Billable Item; tables `sales_*`; Flight executor only.
- 2026-07-26: **ADR-031** (Proposed) — compliance/ops outbound requires opaque module result; task [`compliance-outbound-pipeline-early-result.md`](../tasks/compliance-outbound-pipeline-early-result.md).
- 2026-05: первичная фиксация каталога ключей, карты API и ссылок на scope-документы пяти продуктов.
- 2026-05: зафиксирован **пул настроек по модулям** (`settings.hr`, …); приоритет волны — HR **без** отдельных воронок вне CRM на этом шаге.
- 2026-05: выравнивание с **ADR-005** — целевое хранение модульных настроек на уровне **company** (`company_module_settings`), tenant — только крышка и presets.
- 2026-05: добавлен **ADR-006** (Marketplace / Integration Platform) и §7 плана в этом каталоге.
- 2026-05: MVP таблицы `tenant_integration_installations` / `company_integration_enablements`, спека [`marketplace-catalog-keys.md`](../marketplace-catalog-keys.md).
- 2026-05: **ADR-007** (Forms как platform capability), §8 плана, [`../../forms/module-scope.md`](../../forms/module-scope.md).
- 2026-07: **ADR-024** (Acquisition / Campaigns), [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md); Stage 3 после production cutover.
- 2026-07-18: **Epic P / Stage 3D** active; [`capability-contract.md`](capability-contract.md); Forms Sprint 1 gated on 3D DoD.
- 2026-05: **ADR-008** (Job Publishing внутри Recruitment), §9 плана.
- 2026-05: **§0** — карта Core / Platform vs Business modules (Companies, Users/Roles, Forms, Document Hub, Integrations; пять продуктов с подсистемами Recruitment).
- 2026-05: [`platform-architecture-principles.md`](platform-architecture-principles.md) — консолидация modular multi-company SaaS; §0 расширен (Settings, Automations, Notifications, Activity/Tasks, уточнение модулей).
- 2026-05: **ADR-009** (Document Hub), §10 плана, [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md).
- 2026-05: **ADR-012** (Activity & Notification Operating Layer) — две строки §0 «Notifications» + «Activity / Tasks» сведены в одну capability; canon [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md).
- 2026-07-18: **§0.1 Platform Capability Catalog** + P-01/P-02/P-03 (ADR-025…027); Endpoint/Forms/Submission ownership clarified.
