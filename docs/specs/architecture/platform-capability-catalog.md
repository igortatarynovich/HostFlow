# Platform Capability Catalog

**Status:** canonical · **L0 FROZEN** — [`L0-platform-architecture.md`](L0-platform-architecture.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md) · [`architecture-invariants.md`](architecture-invariants.md)  
**Rules:** P-01…P-05 ([`ADR-025`](ADR-025-standard-adapter-boundary.md)…[`ADR-029`](ADR-029-settings-contract.md))  
**Settings Manifest:** [`capability-settings-manifest.md`](capability-settings-manifest.md)  
**Index:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1  
**Checklist:** [`architecture-review-checklist.md`](architecture-review-checklist.md)  
**Guide:** [`architecture-guide.md`](architecture-guide.md)

> Изменение **шаблона** Passport / kinds / границ = изменение L0 → только Architecture RFC.  
> Добавление/уточнение строк Index и заполнение Passport по шаблону = **применение** L0 (L1), не переоткрытие конституции.

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
| **Exposes** | Adapters / contracts (**P-01**) с уровнем **Stable \| Experimental \| Internal** |
| **Consumes** | Чужие capabilities (**P-03**) | Recruitment → Forms, Documents, Notifications, AI, Search |

| Документ | Тип | Содержание |
|----------|-----|------------|
| **Capability Passport** | Архитектурный | Purpose · Owns · Non-Goals · Exposes(+stability) · Consumes · Events · Forbidden · Data Ownership · Configures · deps · license · lifecycle |
| **Settings Manifest** | Эксплуатационный (**P-05**) | General · Integrations · Defaults · Policies · Feature Flags · License Gates · Validation Rules |
| **Architecture Invariants** | Аксиомы L0 | [`architecture-invariants.md`](architecture-invariants.md) |

**Forbidden vs Non-Goals:** Forbidden = нельзя реализовать внутри; Non-Goals = не миссия capability (анти-расползание scope).

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
| 3 | **Non-Goals** | Что **не** является задачей capability (scope) |
| 4 | **Configures** | Классы настроек → Settings Manifest (**P-04/P-05**) |
| 5 | **Exposes** | Adapters + **Stable \| Experimental \| Internal** |
| 6 | **Consumes** | Чужие capabilities (runtime use) |
| 7 | **Requires / Optional / Forbidden deps** | Граф зависимостей (**ADR-030**) |
| 8 | **License class** | Always Available \| Platform \| Licensed \| Enterprise Only |
| 9 | **Lifecycle defaults** | Bootstrap intent |
| 10 | **Events** | Publishes / Consumes |
| 11 | **Forbidden** | Что нельзя реализовывать / конфигурировать внутри |
| 12 | **Data Ownership** | SoT entities |

**Settings Manifest** (отдельно): [`capability-settings-manifest.md`](capability-settings-manifest.md).

Уровни Tenant → Company → Module — [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) (**хранение**); семантика и UI — owner Manifest.

---

## Index

| Capability | Kind | License | Requires (hard) | Passport |
|------------|------|---------|-----------------|----------|
| Endpoint | Infrastructure | Always Available | — | [§](#endpoint) |
| Submission | Infrastructure | Always Available | Endpoint | [§](#submission) |
| Notifications | Infrastructure | Platform | — | [§](#notifications) |
| Activity | Infrastructure | Platform | — | [§](#activity) |
| Search | Infrastructure | Platform | — | [§](#search) |
| Forms | Platform | Platform | Endpoint, Submission | [§](#forms) |
| Documents | Platform | Platform | — | [§](#documents) |
| Automations | Platform | Licensed | Notifications | [§](#automations) |
| AI | Platform | Licensed | — | [§](#ai) |
| Integrations / Marketplace | Platform | Platform | — | [§](#integrations--marketplace) |
| Acquisition / Campaigns | Platform | Platform | Endpoint, Submission | [§](#acquisition--campaigns) |
| Process Engine | Platform | Platform | — | [§](#process-engine) |
| Recruitment | Business | Licensed | Forms, Documents, Notifications | [§](#recruitment) |
| Sales | Business | Licensed | Forms, Documents, Notifications | [§](#sales) |
| HR | Business | Licensed | Documents, Notifications | [§](#hr) |
| Fleet | Business | Licensed | Documents, Notifications | [§](#fleet) |
| Services / Orders | Business | Licensed | Documents, Notifications | [§](#services--orders) |
| Finance | Business | Licensed | — | [§](#finance) |

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
| **Exposes** | Endpoint Adapter family (**Stable**) |
| **Non-Goals** | Business decisions; Form Builder; domain CRM; Result entity creation |
| **Consumes** | Submission; Forms (когда type = HostFlow Form); Acquisition (campaign context) |
| **Requires** | — |
| **Optional** | Forms, Acquisition |
| **License class** | Always Available |
| **Lifecycle defaults** | Install+Enable+Configure on tenant create |
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
| **Exposes** | Submission / Intake contracts (**Stable**); universal routing resolve (**Stable**) |
| **Non-Goals** | Form Builder; Campaign creative; Decision / domain entity creation |
| **Consumes** | Endpoint; Acquisition; Decision Layer (после routed) |
| **Requires** | Endpoint |
| **Optional** | Acquisition |
| **License class** | Always Available |
| **Lifecycle defaults** | Install+Enable+Configure on tenant create |
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
| **Exposes** | Notification Adapter (**Stable**) |
| **Non-Goals** | Domain pipelines; Document registry; Form Builder; Activity task SoT (compose Activity) |
| **Consumes** | Integrations (provider connectors); Activity (compose внутри layer) |
| **Requires** | — |
| **Optional** | Integrations, Activity |
| **License class** | Platform |
| **Lifecycle defaults** | Install+Enable+Configure (SMTP/channel defaults) on tenant create |
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
| **Exposes** | Activity contracts (**Stable**) |
| **Non-Goals** | Hiring/Sales CRM; Notification delivery SoT; ADR-004 product module |
| **Consumes** | Notifications; Search (optional) |
| **Requires** | — |
| **Optional** | Notifications, Search |
| **License class** | Platform |
| **Lifecycle defaults** | Install+Enable+Configure with Notifications |
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
| **Exposes** | Search Adapter (**Stable**) |
| **Non-Goals** | Domain SoT; primary write path for business entities |
| **Consumes** | Module Public Contracts (projectable fields) |
| **Requires** | — |
| **Optional** | — |
| **License class** | Platform |
| **Lifecycle defaults** | Install+Enable on tenant create |
| **Events** | Consumes domain create/update/delete; publishes reindex signals |
| **Forbidden** | Модульный полнотекст как замена Search SoT |
| **Data Ownership** | Search index documents (derived); query API SoT |

---

## Platform capabilities

### Forms

**Normative:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`../../forms/module-scope.md`](../../forms/module-scope.md)  
**Public Contract:** [`forms-public-contract.md`](forms-public-contract.md) (`forms.public_contract.v1`)  
**Object Kind index:** [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) (LibraryKind `FormComponent` / PresentationRule — meta-index)  
**Task:** [`../tasks/forms-sprint-1.md`](../tasks/forms-sprint-1.md)  
**Sprint 1–6:** ✅ COMPLETE (backend contour) · **Product Layer:** ACTIVE ([`../tasks/forms-product-layer-epic.md`](../tasks/forms-product-layer-epic.md) · `29f4057f`) · **P1:** component registry ([`../tasks/forms-product-p1-field-catalog.md`](../tasks/forms-product-p1-field-catalog.md)) · **Builder:** **LOCKED** until P1 · **Rule:** Builder must not invent field types · **Forms Outcome/KPI:** forbidden (compose Acquisition)

**Purpose.** Платформенный input layer: единственный SoT HostFlow Form.

| | |
|--|--|
| **Owns** | Form Submission **surface**; Consent + version pin **intent**; Public Form Endpoint publishing **для HostFlow Form**; publication bridge (`TenantLeadForm` until FormTemplate); handler registry metadata |
| **Configures** | Default language, public URL base, consent defaults, limits, adapter ids, builder flag → Manifest [`capability-settings-manifest.md`](capability-settings-manifest.md#forms) |
| **Exposes** | Form / HostFlow Form Endpoint Adapter **`forms.endpoint_adapter_v1` (Stable)** — ops `publish` · `endpoint` · `submission` · `result` handoff; Consent pin policy key (**Stable** intent); C4 HTTP resolve (**Stable**) |
| **Non-Goals** | BPM; Workflow engine; Candidate Evaluation; CRM; Notifications; Documents SoT; Campaign SoT; Outcome/KPI; Universal Routing engine; Visual Builder (Sprint 1) |
| **Consumes** | Endpoint / Submission (routing after surface); Acquisition binding + attribution contracts; Documents (file fields); Notifications; Automations (opt.); Field Registry |
| **Requires** | Endpoint, Submission |
| **Optional** | Documents, Notifications, Automations |
| **License class** | Platform (Basic); Licensed addons = Advanced Forms |
| **Lifecycle defaults** | Install+Enable+Configure (default Manifest) on tenant create |
| **Events** | Publishes: `form.published` (Experimental bridge), `form.submission_received` (Experimental); future: `form.version_created`, consent accepted |
| **Forbidden** | Candidate / Client / Campaign SoT; Notification delivery / SMTP; Document registry SoT; AI SoT; universal Campaign routing SoT; Forms-owned Outcome/KPI/attribution engines; Builder unlock without contract DoD |
| **Data Ownership** | Form surface / publication identity (bridge: `TenantLeadForm`); ConsentDefinition + pin (intent); form-surface payload. **Not yet:** FormTemplate / FormTheme / FormLogic SoT (post–Sprint 1) |
| **Contract tests** | `backend/tests/forms_platform/test_forms_sprint1_contract.py` · gates `test_forms_sprint1_gates.py` · C4 `test_forms_platform_c4.py` |

---

### Documents

**Normative:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md)  
**Object Kind index:** [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) (DocumentType / Document / packs / checklist templates — meta-index, not a second SoT)

**Purpose.** Document Hub: документ как платформенный объект со links.

| | |
|--|--|
| **Owns** | Registry; Metadata; Versions; Storage; Verification / Review; Preview; Digital Signature; OCR capability; Links; Required Document Sets |
| **Configures** | OCR, file storage, retention, auto-deletion, e-sign → Manifest [Documents](capability-settings-manifest.md#documents) |
| **Exposes** | Document Adapter (**Stable**); Verification Adapter (**Stable**); document set resolution (**Stable**); OCR internals (**Internal**) |
| **Non-Goals** | Employee/Candidate/Vehicle/Invoice domain; Recruitment pipeline; Notification delivery |
| **Consumes** | Notifications (reminders); Automations (opt.); AI (opt. assist); Integrations (providers) |
| **Requires** | — |
| **Optional** | Notifications, Automations, AI, Integrations |
| **License class** | Platform (Basic); Licensed = Advanced Document Hub |
| **Lifecycle defaults** | Install+Enable+Configure on tenant create |
| **Events** | Publishes: `document.created` / `linked` / `verified` / `expired` |
| **Forbidden** | Employee / Candidate / Vehicle / Invoice **domain** SoT; module-local file table как SoT; SMTP для бизнес-статусов |
| **Data Ownership** | Document; DocumentVersion; DocumentType; DocumentTemplate; DocumentLink; DocumentRequirement; DocumentReview |

---

### Automations

**Normative:** [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md)  
**Object Kind index:** [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) (AutomationReaction / Execution — meta-index; Reaction Orchestrator = `target`)

**Purpose.** Правила, триггеры, сценарии — единый automation control plane.

| | |
|--|--|
| **Owns** | Automation definitions; triggers; actions catalog; run history; entitlement control plane |
| **Configures** | Entitlements Basic/Advanced; rate limits / safety rails |
| **Exposes** | Automation Adapter (**Stable**) |
| **Non-Goals** | Domain SoT; Notification/Document stacks; embedded per-module engines |
| **Consumes** | Notifications; Activity; Documents; AI; module Exposes (action targets) |
| **Requires** | Notifications |
| **Optional** | Activity, Documents, AI |
| **License class** | Licensed |
| **Lifecycle defaults** | Install; Enable when entitled; else Disable |
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
| **Exposes** | AI Adapter (**Stable**); Prompt Library API (**Experimental**) |
| **Non-Goals** | Domain SoT; Forms/Documents ownership; direct Business LLM SDK surface |
| **Consumes** | Integrations (model providers) |
| **Requires** | — |
| **Optional** | Integrations |
| **License class** | Licensed (often Enterprise for advanced) |
| **Lifecycle defaults** | Install; **Disable** until entitled |
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
| **Exposes** | Integration Adapters per provider family (**Stable**); connector internals (**Internal**) |
| **Non-Goals** | Business domain logic; Form Builder; Notification content SoT |
| **Consumes** | Module Exposes as install targets |
| **Requires** | — |
| **Optional** | — |
| **License class** | Platform |
| **Lifecycle defaults** | Install+Enable on tenant create |
| **Events** | Publishes: `integration.installed` / `revoked` |
| **Forbidden** | Дублирующие SDK-вызовы из Business в обход Integration Adapter |
| **Data Ownership** | IntegrationInstallation; connector config |

---

### Acquisition / Campaigns

**Normative:** [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md)

**Purpose.** Demand / growth: Campaign, Flight, attribution, routing context — не Result SoT.

| | |
|--|--|
| **Owns** | Campaign / CampaignRun / Flight; source / placement bindings; `route_intent` / eligibility; attribution; Outcome progress; KPI read aggregates |
| **Configures** | Campaign defaults / windows; source registry defaults |
| **Exposes** | Campaign / Flight / routing APIs (**Stable**); binding APIs (**Stable**); Result attribution / Outcome / KPI read contracts (**Stable** after Epic P) |
| **Non-Goals** | Result SoT (Application/Inquiry); Form Builder; Marketing product ADR-004; Document Hub |
| **Consumes** | Endpoint; Submission; Forms (compose); Notifications (opt.) |
| **Requires** | Endpoint, Submission |
| **Optional** | Forms, Notifications |
| **License class** | Platform |
| **Lifecycle defaults** | Install+Enable when growth surface used; Configure defaults |
| **Events** | Campaign/Flight lifecycle; consumes submission routing outcomes |
| **Forbidden** | Application / Candidate / Inquiry SoT; Form Builder / Consent; Document Hub; SMTP |
| **Data Ownership** | Campaign; Flight; association tables; `acq_result_attributions`; `acq_outcomes`; spend/qualification sources |
| **Stage 3D / Epic P** | ✅ **COMPLETE** (2026-07-18) — E2E `test_stage_3d_epic_p_contract.py`; migrations `202607180004`…`006`; Forms Sprint 1 **UNLOCKED**; Builder **LOCKED** |

---

### Process Engine

**Normative:** [`../platform/process-engine.md`](../platform/process-engine.md)

**Purpose.** Stages, profiles, pipelines, transition/handoff rules, runtime evaluator.

| | |
|--|--|
| **Owns** | Process definitions / profiles; transition rules / evaluator; handoff rule engine (engine-owned) |
| **Configures** | Process profile defaults (engine-level) |
| **Exposes** | Process contracts (**Stable**) |
| **Non-Goals** | Domain entity SoT; Notification delivery; Form Builder |
| **Consumes** | Module domain objects as subjects |
| **Requires** | — |
| **Optional** | — |
| **License class** | Platform |
| **Lifecycle defaults** | Install+Enable with platform |
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
| **Exposes** | Recruitment domain APIs (**Stable**); handoff contracts (**Stable**) |
| **Non-Goals** | Forms/Documents/Notifications/AI platforms; Campaign SoT; Finance invoices; HR Employee SoT |
| **Consumes** | Forms; Documents; Notifications; Activity; AI; Search; Automations; Endpoint; Submission; Acquisition; Process Engine |
| **Requires** | Forms, Documents, Notifications |
| **Optional** | AI, Automations, Acquisition, Activity, Search, Process Engine |
| **Forbidden deps** | Не Requires Finance; invoices только через Billing Events contract |
| **License class** | Licensed |
| **Lifecycle defaults** | Install when sold; Enable per company modules; Configure pipeline defaults |
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
| **Exposes** | Sales / inquiry APIs (**Stable**) |
| **Non-Goals** | Recruitment Candidate/Vacancy; Platform Forms/Documents stacks; Invoice SoT |
| **Consumes** | Forms; Endpoint; Submission; Acquisition; Documents; Notifications; Activity; Automations; AI; Search |
| **Requires** | Forms, Documents, Notifications |
| **Optional** | AI, Automations, Acquisition, Activity, Search |
| **License class** | Licensed |
| **Lifecycle defaults** | Install when sold; Enable on sales host / entitlement |
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
| **Exposes** | HR / workforce APIs (**Stable**); handoff accept (**Stable**) |
| **Non-Goals** | Candidate pipeline; Document Hub storage; Fleet assignments; SMTP |
| **Consumes** | Documents; Notifications; Activity; Forms; Automations; AI; Search |
| **Requires** | Documents, Notifications |
| **Optional** | Forms, Activity, Automations, AI, Search |
| **License class** | Licensed |
| **Lifecycle defaults** | Install when sold; Enable per company |
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
| **Exposes** | Fleet APIs (**Stable**) |
| **Non-Goals** | Hiring pipeline; Forms platform; Notification delivery SoT |
| **Consumes** | Documents; Notifications; Activity; Automations; Search |
| **Requires** | Documents, Notifications |
| **Optional** | Activity, Automations, Search |
| **License class** | Licensed |
| **Lifecycle defaults** | Install when sold; Enable per company |
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
| **Exposes** | Services / orders APIs (**Stable**); Billing Event producer (**Stable**) |
| **Non-Goals** | Invoice SoT; Platform Forms/Documents stacks |
| **Consumes** | Documents; Notifications; Activity; Forms; Finance (consumer of events) |
| **Requires** | Documents, Notifications |
| **Optional** | Forms, Activity, Finance |
| **License class** | Licensed |
| **Lifecycle defaults** | Install with Services entitlement |
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
| **Exposes** | Finance / invoice APIs (**Stable**); Billing Event consumer (**Stable**) |
| **Non-Goals** | Recruitment/HR domain; Notification/Forms stacks; creating domain leads |
| **Consumes** | Documents; Notifications; Activity; Search; Integrations |
| **Requires** | — |
| **Optional** | Documents, Notifications, Activity, Search, Integrations |
| **License class** | Licensed |
| **Lifecycle defaults** | **Not Install** until Finance sold; then Enable+Configure tax/numbering |
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
7. Новый vocabulary / pattern / catalog element → [`ADR-038`](ADR-038-platform-standardization-model.md) Platform-first: проверить область в [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) до локального дубля.

---

## History

- **2026-08-13** — **ADR-044** List Workspace & Data Presentation; one `ListWorkspace` + `DataTable` (rule); runtime extract epic P1–P2.
- **2026-08-13** — **ADR-046** Analytics, Visualization & Reporting Canon; Recruitment efficiency reference (story + presentation mode); remaining dashboards migrate-on-touch.
- **2026-08-13** — **ADR-043** UI Component & Composition Canon; area `design_interaction` composition rule (React kit; runtime wrappers deferred).
- **2026-08-13** — **ADR-047** Actions; area `actions` → exists (confirmed slice; 3A-3 runtime deferred).
- **2026-08-13** — **ADR-042** Relationships; area `relationships` → exists (confirmed slice; CRM graph deferred).
- **2026-08-13** — **ADR-041** Data Types; area `data_types` → exists (Field/Forms runtime adoption deferred).
- **2026-08-13** — **ADR-040** Naming & Identifiers; area `naming_identifiers` → exists (DocumentType runtime alignment deferred).
- **2026-08-13** — **ADR-039** State / Lifecycle Inventory; area `states_transitions` → exists (shared enums deferred).
- **2026-08-13** — **ADR-038** Platform Standardization Model (14 areas + Platform-first); L2 [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md).
- **2026-08-13** — **ADR-037** Object Kind Catalog (meta-canon) linked from Documents / Automations / Forms; L2 [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md).
- **2026-07-18** — каталог + Capability Boundary.  
- **2026-07-18** — v2: Owns / Configures / Exposes / Consumes; kinds; **P-04**.  
- **2026-07-18** — v3: Passport vs **Settings Manifest**; **P-05** Settings Contract; capability-scoped admin IA.
- **2026-07-18** — v4: License / Requires / Optional / Lifecycle defaults; **L0 CLOSED** ([`ADR-030`](ADR-030-l0-platform-architecture-closure.md)).
- **2026-07-18** — v5 final: **Non-Goals** · Exposes stability · Invariants; L0 **FROZEN**.
