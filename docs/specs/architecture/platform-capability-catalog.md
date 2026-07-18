# Platform Capability Catalog

**Status:** canonical (practical SoT for P-02…P-05)  
**Rules:** [`ADR-025`](ADR-025-standard-adapter-boundary.md) (P-01) · [`ADR-026`](ADR-026-capability-ownership.md) (P-02) · [`ADR-027`](ADR-027-capability-composition.md) (P-03) · [`ADR-028`](ADR-028-configuration-ownership.md) (P-04) · [`ADR-029`](ADR-029-settings-contract.md) (P-05)  
**Settings Manifest schema:** [`capability-settings-manifest.md`](capability-settings-manifest.md)  
**Index / product keys:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
**PR gate:** [`architecture-review-checklist.md`](architecture-review-checklist.md)  
**Guide:** [`architecture-guide.md`](architecture-guide.md)

---

## Purpose

Справочник **возможностей платформы**, не список экранов CRM. Настройки — **не** техническая свалка: пользователь настраивает **capability**, не «систему».

| Правило | Вопрос | Каталог / Manifest |
|---------|--------|---------------------|
| **P-01** | Как вызывать поведение? | **Exposes** |
| **P-02** | Кто владеет функциональностью? | Owner + **Owns** |
| **P-03** | Как строить новое? | **Consumes** |
| **P-04** | Кто владеет конфигурацией? | **Configures** (pointer) |
| **P-05** | Как конфигурация публикуется? | **Settings Manifest** / Contract |

Проектирование:

> **Какой capability это принадлежит — и это Owns, Configures, Exposes или Consumes?**

Admin IA:

> **Какое конфигурационное пространство capability открыть?** (не «General → SMTP»)

---

## Four boundaries + two documents

| Граница | Смысл | Пример |
|---------|--------|--------|
| **Owns** | Функциональный SoT | Documents: Registry, Metadata, Versions, Storage, Verification |
| **Configures** | *Какие классы* настроек принадлежат capability (**P-04**) — детали в Manifest | Notifications: Email/SMS/Push/Retry/Quiet Hours |
| **Exposes** | Adapters / contracts (**P-01**) | Document Adapter, Verification Adapter |
| **Consumes** | Чужие capabilities (**P-03**) | Recruitment → Forms, Documents, Notifications, AI, Search |

| Документ | Тип | Содержание |
|----------|-----|------------|
| **Capability Passport** | Архитектурный | Purpose · Owns · Exposes · Consumes · Events · Forbidden · Data Ownership · Configures *(указатель)* |
| **Settings Manifest** | Эксплуатационный (**P-05**) | General · Integrations · Defaults · Policies · Feature Flags · License Gates · Validation Rules |

Knobs **не** перечисляются полностью в Passport — только в [`capability-settings-manifest.md`](capability-settings-manifest.md) / будущих JSON Manifests.

SMTP в Recruitment → нет в Manifest Notifications write path → нарушение **P-04/P-05**.

---

## Capability kinds

| Kind | Роль | Правило |
|------|------|---------|
| **Infrastructure** | Сквозная «труба» | Business **только Consumes**; свой Manifest только для своей трубы |
| **Platform** | Переиспользуемые capability | Один owner; Business композирует |
| **Business** | Домен ADR-004 (+ Sales) | Manifest **только** domain settings; **не** SMTP/OCR/LLM/Meta App |

| Kind | Capabilities |
|------|----------------|
| **Infrastructure** | Endpoint, Submission, Notifications, Activity, Search |
| **Platform** | Forms, Documents, Automations, AI, Integrations / Marketplace, Acquisition / Campaigns, Process Engine |
| **Business** | Recruitment, Sales, HR, Fleet, Services / Orders, Finance |

---

## Capability Passport (template)

Архитектурный документ. Неполный passport — блокер review.

| # | Раздел | Содержание |
|---|--------|------------|
| 1 | **Purpose** | Зачем существует |
| 2 | **Owns** | Функциональный SoT |
| 3 | **Configures** | Классы настроек + ссылка на Settings Manifest (**P-04/P-05**) |
| 4 | **Exposes** | Adapters / public contracts |
| 5 | **Consumes** | Чужие capabilities |
| 6 | **Events** | Publishes / Consumes |
| 7 | **Forbidden** | Запреты (в т.ч. чужой Manifest) |
| 8 | **Data Ownership** | SoT entities |

**Settings Manifest** (отдельно): см. [`capability-settings-manifest.md`](capability-settings-manifest.md).

Уровни Tenant → Company → Module — [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) (**хранение**); семантика и UI — owner Manifest.

---

## Index

| Capability | Kind | Owner | Passport |
|------------|------|-------|----------|
| Endpoint | Infrastructure | Intake / Acquisition boundary | [§](#endpoint) |
| Submission | Infrastructure | Shared Intake | [§](#submission) |
| Notifications | Infrastructure | Activity & Notification Operating Layer | [§](#notifications) |
| Activity | Infrastructure | Activity & Notification Operating Layer | [§](#activity) |
| Search | Infrastructure | Global Search | [§](#search) |
| Forms | Platform | Forms | [§](#forms) |
| Documents | Platform | Document Hub | [§](#documents) |
| Automations | Platform | Automations | [§](#automations) |
| AI | Platform | AI capability | [§](#ai) |
| Integrations / Marketplace | Platform | Integrations | [§](#integrations--marketplace) |
| Acquisition / Campaigns | Platform | Acquisition | [§](#acquisition--campaigns) |
| Process Engine | Platform | Process Engine | [§](#process-engine) |
| Recruitment | Business | Recruitment | [§](#recruitment) |
| Sales | Business | Sales | [§](#sales) |
| HR | Business | HR | [§](#hr) |
| Fleet | Business | Fleet | [§](#fleet) |
| Services / Orders | Business | Services | [§](#services--orders) |
| Finance | Business | Finance | [§](#finance) |

**Forms vs Submission:** Forms Owns form surface + consent pin; universal Submission / routing envelope — Shared Intake.  
**Notifications vs Activity:** одна Operating Layer ([`ADR-012`](ADR-012-activity-notification-operating-layer.md)); два паспорта; не два ADR-004 модуля.

---

## Infrastructure capabilities

### Endpoint

**Normative:** [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)

**Purpose.** Каноническая точка входа данных (Meta, HostFlow Form, API, Webhook, WhatsApp, Mobile, …).

| | |
|--|--|
| **Owns** | Endpoint type registry; endpoint identity / binding metadata (не Form Builder) |
| **Configures** | Endpoint type enablement; ingest auth / rate limits (platform) |
| **Exposes** | Endpoint Adapter family |
| **Consumes** | Submission; Forms (когда type = HostFlow Form); Acquisition (campaign context) |
| **Events** | Publishes: `endpoint.submission_accepted`. Consumes: form publish / integration webhooks |
| **Forbidden** | Form Builder / Consent SoT; Result domain entities; второй intake pipeline |
| **Data Ownership** | Endpoint definitions / bindings (ADR-024) |

---

### Submission

**Normative:** ADR-021 / ADR-022 / [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)

**Purpose.** Универсальная intake-запись и routing envelope до Decision / Business Entity.

| | |
|--|--|
| **Owns** | Universal Submission object; routing stamp / unresolved codes; append-before-decision; routing-once semantics |
| **Configures** | Routing policy knobs (Intake/Acquisition — не Recruitment) |
| **Exposes** | Submission / Intake contracts; universal routing resolve |
| **Consumes** | Endpoint; Acquisition; Decision Layer (после routed) |
| **Events** | Publishes: `submission.appended` / `routed` / `unresolved` |
| **Forbidden** | Form Builder; auto-create Application/Inquiry без Decision; Campaign creative SoT |
| **Data Ownership** | Submission / intake append log + routing metadata |

---

### Notifications

**Normative:** [`ADR-012`](ADR-012-activity-notification-operating-layer.md)

**Purpose.** Доставка уведомлений — единый delivery SoT.

| | |
|--|--|
| **Owns** | Channels; Delivery; Queue; Retry engine; Preference model; notification template runtime |
| **Configures** | Email, SMS, WhatsApp, Push, working hours, Retry Policy → Manifest [Notifications](capability-settings-manifest.md#notifications) |
| **Exposes** | Notification Adapter |
| **Consumes** | Integrations (provider connectors); Activity (compose внутри layer) |
| **Events** | Publishes: `notification.queued` / `delivered` / `failed` |
| **Forbidden** | Recruitment/Sales pipeline SoT; Document registry; Form Builder; SMTP config в бизнес-модулях |
| **Data Ownership** | Notification; DeliveryAttempt; NotificationTemplate; ChannelConfig; Preference |

---

### Activity

**Normative:** ADR-012 · [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md)

**Purpose.** Задачи, напоминания, scheduler/calendar surfaces — не отдельный ADR-004 модуль.

| | |
|--|--|
| **Owns** | Activity / Task model; Reminders; Scheduler surfaces; Calendar views; operational timeline contracts |
| **Configures** | Default reminder offsets; calendar / working-hours defaults (где owned by layer) |
| **Exposes** | Activity contracts (create / assign / complete / schedule) |
| **Consumes** | Notifications; Search (optional) |
| **Events** | Publishes: `activity.created` / `completed` / `reminder_due` |
| **Forbidden** | Отдельный «модуль todo» как ADR-004; Hiring/Sales stage SoT; второй notification stack |
| **Data Ownership** | Activity; Reminder |

---

### Search

**Purpose.** Глобальный поиск / индекс — единый query SoT.

| | |
|--|--|
| **Owns** | Search index & query; indexing contracts |
| **Configures** | Index backends; ranking defaults |
| **Exposes** | Search Adapter |
| **Consumes** | Module Public Contracts (projectable fields) |
| **Events** | Consumes domain create/update/delete; publishes reindex signals |
| **Forbidden** | Модульный полнотекст как замена Search SoT |
| **Data Ownership** | Search index documents (derived); query API SoT |

---

## Platform capabilities

### Forms

**Normative:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`../../forms/module-scope.md`](../../forms/module-scope.md)

**Purpose.** Платформенный input layer: единственный SoT HostFlow Form.

| | |
|--|--|
| **Owns** | Form Builder; Templates; Versioning; Form Submission **surface**; Consent + version pin; Public/Internal Forms; Form Logic; Themes; CAPTCHA surface; multi-language copy; Endpoint Publishing **для HostFlow Form** |
| **Configures** | Branding, default language, CAPTCHA, consent policy, public URLs, themes → Manifest [`capability-settings-manifest.md`](capability-settings-manifest.md#forms) |
| **Exposes** | Form Adapter; Endpoint Adapter (HostFlow Form specialization); Consent pin contract |
| **Consumes** | Endpoint / Submission (routing after surface); Documents (file fields); Notifications; Automations (opt.); Field Registry |
| **Events** | Publishes: `form.published`, `form.version_created`, `form.submission_received`, consent accepted |
| **Forbidden** | Candidate / Client / Campaign SoT; Notification delivery / SMTP; Document registry SoT; AI SoT; universal Campaign routing SoT |
| **Data Ownership** | Form; FormVersion; FormTemplate; FormTheme; FormLogic; ConsentDefinition + pin; form-surface payload |

---

### Documents

**Normative:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md)

**Purpose.** Document Hub: документ как платформенный объект со links.

| | |
|--|--|
| **Owns** | Registry; Metadata; Versions; Storage; Verification / Review; Preview; Digital Signature; OCR capability; Links; Required Document Sets |
| **Configures** | OCR, file storage, retention, auto-deletion, e-sign → Manifest [Documents](capability-settings-manifest.md#documents) |
| **Exposes** | Document Adapter; Verification Adapter; document set resolution |
| **Consumes** | Notifications (reminders); Automations (opt.); AI (opt. assist); Integrations (providers) |
| **Events** | Publishes: `document.created` / `linked` / `verified` / `expired` |
| **Forbidden** | Employee / Candidate / Vehicle / Invoice **domain** SoT; module-local file table как SoT; SMTP для бизнес-статусов |
| **Data Ownership** | Document; DocumentVersion; DocumentType; DocumentTemplate; DocumentLink; DocumentRequirement; DocumentReview |

---

### Automations

**Normative:** [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md)

**Purpose.** Правила, триггеры, сценарии — единый automation control plane.

| | |
|--|--|
| **Owns** | Automation definitions; triggers; actions catalog; run history; entitlement control plane |
| **Configures** | Entitlements Basic/Advanced; rate limits / safety rails |
| **Exposes** | Automation Adapter |
| **Consumes** | Notifications; Activity; Documents; AI; module Exposes (action targets) |
| **Events** | Publishes: `automation.triggered` / `completed` / `failed` |
| **Forbidden** | Скрытый второй automation engine в каждом бизнес-модуле; provider SDK из rule body в обход adapters |
| **Data Ownership** | AutomationRule; AutomationRun |

---

### AI

**Purpose.** Единая AI capability через AI Adapter.

| | |
|--|--|
| **Owns** | AI Adapter / model routing; prompt/policy governance; usage metering hooks |
| **Configures** | Provider, model, limits, Prompt Library, usage policies → Manifest [AI](capability-settings-manifest.md#ai) |
| **Exposes** | AI Adapter |
| **Consumes** | Integrations (model providers) |
| **Events** | Publishes: `ai.invocation_*` (audit) |
| **Forbidden** | Прямой LLM SDK / API-key SoT в Business capabilities |
| **Data Ownership** | AI invocation audit / policy config |

---

### Integrations / Marketplace

**Normative:** [`ADR-006`](ADR-006-marketplace-and-integration-platform.md)

**Purpose.** Connectors, apps, installation lifecycle, marketplace metadata.

| | |
|--|--|
| **Owns** | Integration registry; installation; connector credential patterns; marketplace catalog metadata |
| **Configures** | Meta App / provider app bindings; installed scopes; connector enablement |
| **Exposes** | Integration Adapters (per provider family) |
| **Consumes** | Module Exposes as install targets |
| **Events** | Publishes: `integration.installed` / `revoked` |
| **Forbidden** | Дублирующие SDK-вызовы из Business в обход Integration Adapter |
| **Data Ownership** | IntegrationInstallation; connector config |

---

### Acquisition / Campaigns

**Normative:** [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md)

**Purpose.** Demand / growth: Campaign, Flight, attribution, routing context — не Result SoT.

| | |
|--|--|
| **Owns** | Campaign / CampaignRun / Flight; source / placement bindings; `route_intent` / eligibility; attribution for new Lead |
| **Configures** | Campaign defaults / windows; source registry defaults |
| **Exposes** | Campaign / Flight / routing APIs; binding APIs (uses-not-owns Form associations) |
| **Consumes** | Endpoint; Submission; Forms (compose); Notifications (opt.) |
| **Events** | Campaign/Flight lifecycle; consumes submission routing outcomes |
| **Forbidden** | Application / Candidate / Inquiry SoT; Form Builder / Consent; Document Hub; SMTP |
| **Data Ownership** | Campaign; Flight; association tables; attribution on intake path |

---

### Process Engine

**Normative:** [`../platform/process-engine.md`](../platform/process-engine.md)

**Purpose.** Stages, profiles, pipelines, transition/handoff rules, runtime evaluator.

| | |
|--|--|
| **Owns** | Process definitions / profiles; transition rules / evaluator; handoff rule engine (engine-owned) |
| **Configures** | Process profile defaults (engine-level) |
| **Exposes** | Process contracts |
| **Consumes** | Module domain objects as subjects |
| **Events** | Transition evaluated / applied |
| **Forbidden** | Параллельные несовместимые engines без контракта |
| **Data Ownership** | Process/pipeline definition artifacts (модуль выбирает, **какой** profile applies — см. Recruitment Owns pipeline **application**) |

---

## Business capabilities

**Общее Forbidden для Business:** Forms / Documents / Notifications / AI / Search / Automations / Endpoint stacks; infrastructure **Configures** (SMTP, OCR Engine, LLM Provider, Meta App, …).

### Recruitment

**Normative:** [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`ADR-008`](ADR-008-job-publishing-and-distribution.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`../../recruitment/module-scope.md`](../../recruitment/module-scope.md)

**Purpose.** Подбор: Vacancy → publish → Application/Candidate → evaluation → hiring handoff.

| | |
|--|--|
| **Owns** | Vacancy; Job Post / Job Publishing surface; Candidate; Application; Evaluation; Hiring Pipeline; Interview; Offer; handoff intents to HR/Fleet |
| **Configures** | Pipeline / stage definitions; hiring gates; interview defaults; job publishing **defaults** (каналы — через Integrations) |
| **Exposes** | Recruitment domain APIs; handoff contracts |
| **Consumes** | Forms; Documents; Notifications; Activity; AI; Search; Automations; Endpoint; Submission; Acquisition; Process Engine |
| **Events** | Application/Candidate/Vacancy lifecycle; handoff requested; consumes `submission.routed` |
| **Forbidden** | Forms/Documents/Notifications/AI/Search/Automations/Endpoint SoT; Campaign SoT; SMTP/OCR/LLM/Meta App config; Sales Inquiry / Employee / Invoice SoT |
| **Data Ownership** | Vacancy; JobPost; Candidate; Application; Interview; Offer; recruitment pipeline state |

---

### Sales

**Normative:** [`ADR-023`](ADR-023-recruitment-sales-module-separation.md)

**Purpose.** Commercial surface: inquiry → qualification → client account.

| | |
|--|--|
| **Owns** | Sales Inquiry; ClientAccount (sales scope); sales pipeline / qualification |
| **Configures** | Sales pipeline / qualification defaults |
| **Exposes** | Sales / inquiry APIs |
| **Consumes** | Forms; Endpoint; Submission; Acquisition; Documents; Notifications; Activity; Automations; AI; Search |
| **Events** | Inquiry lifecycle; consumes routed submissions with sales intent |
| **Forbidden** | Recruitment Candidate/Vacancy SoT; infrastructure/platform Configures; Invoice SoT |
| **Data Ownership** | Inquiry; ClientAccount (sales); sales pipeline state |

---

### HR

**Normative:** [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) · [`../../hr/module-scope.md`](../../hr/module-scope.md)

**Purpose.** Employee lifecycle — автономен без Recruitment.

| | |
|--|--|
| **Owns** | Employee profile; HR cases; employment lifecycle; HR contracts / ZUS / permits (HR domain); payroll **data** (HR scope) |
| **Configures** | HR process / case defaults |
| **Exposes** | HR / workforce APIs; handoff accept |
| **Consumes** | Documents; Notifications; Activity; Forms; Automations; AI; Search |
| **Events** | Employee lifecycle; consumes Recruitment handoff |
| **Forbidden** | Candidate pipeline SoT; Document storage / OCR Engine SoT; SMTP; Fleet assignment SoT |
| **Data Ownership** | Employee; HR Case; employment records |

---

### Fleet

**Normative:** [`../../fleet/module-scope.md`](../../fleet/module-scope.md)

**Purpose.** Vehicles, assignments, handover, inspections — не воронка найма.

| | |
|--|--|
| **Owns** | Vehicle; Fleet Assignment / handover; inspections / damage / readiness / return |
| **Configures** | Fleet operational defaults |
| **Exposes** | Fleet APIs |
| **Consumes** | Documents; Notifications; Activity; Automations; Search |
| **Events** | Assignment / vehicle lifecycle |
| **Forbidden** | Hiring pipeline; Forms/Documents/Notifications SoT; infrastructure Configures |
| **Data Ownership** | Vehicle; Assignment; inspection records |

---

### Services / Orders

**Normative:** [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)

**Purpose.** Каталог услуг и заказы; эмит Billing Events (не invoices).

| | |
|--|--|
| **Owns** | Service catalog; Service Order / statuses; Billing Event **emission** |
| **Configures** | Catalog / order defaults |
| **Exposes** | Services / orders APIs; Billing Event producer contract |
| **Consumes** | Documents; Notifications; Activity; Forms; Finance (consumer of events) |
| **Events** | Publishes Billing Events |
| **Forbidden** | Invoice SoT; infrastructure/platform stacks |
| **Data Ownership** | Service; ServiceOrder; BillingEvent (producer side) |

---

### Finance

**Normative:** [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`../../finance/module-scope.md`](../../finance/module-scope.md)

**Purpose.** Invoices, payments, tax — из Billing Events.

| | |
|--|--|
| **Owns** | Invoice; Payment; tax / billing rules; billing profile (finance-owned) |
| **Configures** | Tax / numbering; payment provider bindings (**finance-owned semantics**; connectors via Integrations) |
| **Exposes** | Finance / invoice APIs; Billing Event consumer |
| **Consumes** | Documents; Notifications; Activity; Search; Integrations |
| **Events** | Invoice/Payment lifecycle; consumes Billing Events |
| **Forbidden** | Invoice create из Recruitment/HR напрямую; Forms/Documents/Notifications stacks; SMTP SoT |
| **Data Ownership** | Invoice; Payment; finance rules |

---

## How to use (design & review)

1. Найти capability → открыть **Passport**.  
2. Новое поведение → **Owns**? → extend owner / compose.  
3. Новый knob → **P-04** owner + запись в **Settings Manifest** (**P-05**) — не в чужой Passport list.  
4. Admin UI → capability space из Manifest; не техническая свалка.  
5. Межмодульный вызов → **Exposes**. Business → только **Consumes** Infrastructure/Platform.  
6. Нет Index entry → ADR + kind + Passport + Manifest **до** кода.

---

## History

- **2026-07-18** — каталог + Capability Boundary.  
- **2026-07-18** — v2: Owns / Configures / Exposes / Consumes; kinds; **P-04**.  
- **2026-07-18** — v3: Passport vs **Settings Manifest**; **P-05** Settings Contract; capability-scoped admin IA.
