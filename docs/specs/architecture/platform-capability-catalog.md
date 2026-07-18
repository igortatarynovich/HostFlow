# Platform Capability Catalog

**Status:** canonical (practical SoT for P-02 / P-03)  
**Rules:** [`ADR-025`](ADR-025-standard-adapter-boundary.md) (P-01) · [`ADR-026`](ADR-026-capability-ownership.md) (P-02) · [`ADR-027`](ADR-027-capability-composition.md) (P-03)  
**Index / product keys:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
**PR gate:** [`architecture-review-checklist.md`](architecture-review-checklist.md)  
**Guide:** [`architecture-guide.md`](architecture-guide.md)

---

## Purpose

Этот документ — **справочник возможностей платформы**, не список продуктовых модулей.

| ADR | Отвечают на | Этот каталог отвечает на |
|-----|-------------|--------------------------|
| P-01 | Как взаимодействовать? | Какие **Public Contracts** у capability |
| P-02 | Кто владелец? | **Что именно** принадлежит владельцу (**Capability Boundary**) |
| P-03 | Как строить новое? | Есть ли уже capability в каталоге — **композиция** vs новая запись |

Проектирование новой функции начинается не с вопроса «в какой модуль положить?», а с:

> **Какой существующей capability это принадлежит?**

- Ответ есть в каталоге → новая реализация **не** создаётся; используется owner через adapter.  
- Ответа нет → только тогда рассматривается **новая** capability (ADR + owner + passport **до** кода).

Краткий индекс владельцев без границ — [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1. **Нормативные границы Owned / Forbidden / Settings / Events — только здесь.**

---

## Capability Boundary

**Capability Boundary** — фиксированный состав того, что capability **владеет** и чего **не владеет**.

P-02 без границы остаётся декларацией («есть владелец»). С границей появляется операционный вопрос review:

1. Есть ли владелец?  
2. **Не пытается ли модуль забрать чужую ответственность?**

| Внутри границы (Owned) | Вне границы (Forbidden / Not owned) |
|------------------------|-------------------------------------|
| SoT сущности, настройки, логика, события capability | Domain objects и capabilities других владельцев |
| Единственное место реализации | Потребление только через Public Contracts |

Нарушение границы = блокер наравне с нарушением P-01 / P-02 / P-03.

---

## Passport template (Module / Capability Definition)

Каждая запись каталога заполняется **одинаковым паспортом**. Неполный паспорт для затронутой capability — блокер architectural review.

### 1. Purpose

Зачем существует capability / модуль (одно предложение + 1–3 bullets).

### 2. Owned Capabilities / Responsibilities

Что принадлежит **только** этому владельцу (Capability Boundary — «своё»).

### 3. Public Contracts

Какие Standard Adapters / API / contracts предоставляет наружу (P-01).

### 4. Required Capabilities

Какие чужие capabilities **композирует** (P-03); только через adapters.

### 5. Events

| Publishes | Consumes |
|-----------|----------|
| … | … |

### 6. Settings

Настройки, которые принадлежат **только** этому владельцу (Tenant / Company / Module Settings — уровни по [`ADR-005`](ADR-005-three-level-settings-hierarchy.md)).

### 7. Data Ownership (SoT entities)

Канонические сущности / таблицы / объекты, для которых этот owner — Single Source of Truth.

### 8. Forbidden

Что этому владельцу **запрещено** реализовывать или объявлять своим SoT.

---

## Index

| Capability / Module | Kind | Owner | Passport |
|---------------------|------|-------|----------|
| **Forms** | Platform | Forms | [§ Forms](#forms) |
| **Documents** | Platform | Document Hub | [§ Documents](#documents) |
| **Notifications** | Platform | Activity & Notification Operating Layer | [§ Notifications](#notifications) |
| **Activity** | Platform | Activity & Notification Operating Layer | [§ Activity](#activity) |
| **Endpoint** | Platform | Intake / Acquisition boundary | [§ Endpoint](#endpoint) |
| **Submission** | Platform | Shared Intake | [§ Submission](#submission) |
| **Acquisition / Campaigns** | Platform | Acquisition | [§ Acquisition](#acquisition--campaigns) |
| **Automations** | Platform | Automations | [§ Automations](#automations) |
| **AI** | Platform | AI capability | [§ AI](#ai) |
| **Search** | Platform | Global Search | [§ Search](#search) |
| **Integrations / Marketplace** | Platform | Integrations | [§ Integrations--marketplace](#integrations--marketplace) |
| **Process Engine** | Platform | Process Engine | [§ Process-Engine](#process-engine) |
| **Recruitment** | Business | Recruitment | [§ Recruitment](#recruitment) |
| **Sales** | Business | Sales | [§ Sales](#sales) |
| **HR** | Business | HR | [§ HR](#hr) |
| **Fleet** | Business | Fleet | [§ Fleet](#fleet) |
| **Services / Orders** | Business | Services | [§ Services--Orders](#services--orders) |
| **Finance** | Business | Finance | [§ Finance](#finance) |

**Forms vs Submission:** Forms владеет form surface + consent version pin. Универсальный Submission object / routing envelope — Shared Intake ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)). Не два Form Builder.

**Notifications vs Activity:** одна Operating Layer ([`ADR-012`](ADR-012-activity-notification-operating-layer.md)); два паспорта — одна зона delivery, другая — tasks/reminders/calendar; **не** два ADR-004 модуля.

---

## Platform capabilities

### Forms

**Normative:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`../../forms/module-scope.md`](../../forms/module-scope.md)

#### 1. Purpose

Платформенный **input layer**: единственный SoT HostFlow Form (builder → publish → form submission surface → consent).

#### 2. Owned

- Form Builder  
- Form Templates  
- Form Versioning  
- Form Submission surface (ответы формы; не путать с universal Submission / routing envelope)  
- Consent (GDPR / RODO / Terms / Privacy) + version pinning  
- Public Forms  
- Internal Forms  
- Endpoint Publishing **для HostFlow Form** (Form is-a Endpoint)  
- Form Logic (conditional / branching)  
- Form Themes  
- CAPTCHA / anti-abuse для form surface  
- Multi-language form copy  

#### 3. Public Contracts

- **Endpoint Adapter** (HostFlow Form specialization)  
- Forms public APIs (template, version, publish, render, submit-to-surface)  
- Consent version pin contract  

#### 4. Required Capabilities

- Endpoint / Shared Intake (universal routing after form surface)  
- Documents (file fields → Document Hub links, не локальный file SoT)  
- Notifications (post-submit delivery — compose)  
- Automations (опционально)  
- Field Registry / Entity Profile (маппинг полей)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `form.published` / `form.version_created` | Consent policy updates (platform) |
| `form.submission_received` (surface) | Theme / branding defaults from tenant |
| Consent accepted (pinned version) | |

#### 6. Settings

- Branding / themes defaults  
- CAPTCHA providers & thresholds  
- Default language / locale fallback  
- Consent defaults (text sources, required flags)  
- Public form host / publish defaults  

#### 7. Data Ownership

Form definition, FormVersion, FormTemplate, FormTheme, FormLogic, ConsentDefinition + pin, form-surface submission payload tied to form version.

#### 8. Forbidden

- Candidate / Client / Campaign / Vacancy domain SoT  
- Notification delivery stack / SMTP  
- Document registry / file storage SoT  
- AI inference SoT  
- Universal Campaign routing / Attribution SoT (→ Acquisition)  
- Второй intake pipeline вне Endpoint model  

---

### Documents

**Normative:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md)

#### 1. Purpose

Единый **Document Hub**: документ как платформенный объект со links, не «файл в карточке модуля».

#### 2. Owned

- Document Registry  
- File Storage (canonical blob / object store access)  
- Versioning  
- Metadata / Document Types / Templates  
- OCR (platform capability)  
- Expiration / retention signals  
- Verification / Review (в модели Hub)  
- Preview  
- Digital Signature (platform)  
- Document Links & Required Document Sets  
- Access / audit (Advanced)  

#### 3. Public Contracts

- **Document Adapter** (create, link, require, review, download policy)  
- Document set resolution APIs  

#### 4. Required Capabilities

- Notifications (expiry / review reminders — compose)  
- Automations (optional)  
- AI (optional assist — через AI Adapter)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `document.created` / `linked` / `verified` / `expired` | Module requirement presets (keys only) |
| Review status changes | |

#### 6. Settings

- Storage backends / quotas (platform)  
- Default retention / expiry policies  
- OCR / e-sign provider bindings (через Integrations, config у Hub)  
- Sensitivity / visibility defaults  

#### 7. Data Ownership

Document, DocumentVersion, DocumentType, DocumentTemplate, DocumentLink, DocumentRequirement, DocumentReview, binary object keys.

#### 8. Forbidden

- Employee / Candidate / Vehicle / Invoice **domain** SoT  
- Module-local «вторая» file table как SoT  
- Recruitment/HR pipeline status как часть Document  
- Прямой SMTP/SMS из Hub для бизнес-статусов (→ Notifications)  

---

### Notifications

**Normative:** [`ADR-012`](ADR-012-activity-notification-operating-layer.md) · [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md)

#### 1. Purpose

Доставка уведомлений: каналы, очередь, шаблоны, retry, preferences — единый delivery SoT.

#### 2. Owned

- Channels (email, SMS, push, in-app, …)  
- Delivery  
- Templates (notification templates)  
- Queue  
- Retry / backoff  
- Preferences / quiet hours  
- Provider bindings (SMTP, SMS, push — config у этой capability)  

#### 3. Public Contracts

- **Notification Adapter** (`notify`, template resolve, preference-aware send)  

#### 4. Required Capabilities

- Integrations / Marketplace (provider connectors)  
- Activity (связь task/reminder ↔ notification — compose внутри layer)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `notification.queued` / `delivered` / `failed` | Domain events from modules (via adapter calls) |
| Preference updated | Provider webhook delivery receipts |

#### 6. Settings

- SMTP / email providers  
- SMS providers  
- Push providers  
- Default templates / locale  
- Tenant/company notification preferences defaults  

#### 7. Data Ownership

Notification, DeliveryAttempt, NotificationTemplate, ChannelConfig, Preference.

#### 8. Forbidden

- Recruitment status / Sales pipeline SoT  
- Document registry SoT  
- Form Builder  
- Прямой вызов SMTP/SMS SDK из Recruitment/Sales/HR/…  

---

### Activity

**Normative:** ADR-012 · [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md)

#### 1. Purpose

Операционный слой задач, напоминаний, планировщика и календарных представлений (не отдельный ADR-004 модуль).

#### 2. Owned

- Activity / Task model  
- Reminders  
- Scheduler surfaces  
- Calendar views (presentation of Activity)  
- Activity timeline contracts (operational)  

#### 3. Public Contracts

- Activity contracts (create/assign/complete/schedule)  

#### 4. Required Capabilities

- Notifications (delivery of reminders)  
- Search (optional index)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `activity.created` / `completed` / `reminder_due` | Module domain hooks via adapter |

#### 6. Settings

- Default reminder offsets  
- Calendar / working-hours defaults (where owned by layer)  

#### 7. Data Ownership

Activity, Reminder (канон ADR-012).

#### 8. Forbidden

- Отдельный «модуль todo / scheduler» как продукт ADR-004  
- Domain pipeline SoT (Hiring, Sales stages)  
- Второй notification stack  

---

### Endpoint

**Normative:** [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)

#### 1. Purpose

Каноническая **точка входа** данных: Meta, HostFlow Form, API, Webhook, WhatsApp, Mobile, …

#### 2. Owned

- Endpoint type registry  
- Endpoint identity / publish metadata (не Form Builder)  
- Binding к Campaign / Flight / Profile (где применимо)  

#### 3. Public Contracts

- **Endpoint Adapter** family  

#### 4. Required Capabilities

- Submission (universal record)  
- Forms (когда type = HostFlow Form)  
- Acquisition (campaign context)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `endpoint.submission_accepted` | Form publish / integration webhooks |

#### 6. Settings

- Endpoint type enablement  
- Ingest auth / rate limits (platform)  

#### 7. Data Ownership

Endpoint definitions / bindings (модель ADR-024); не FormVersion.

#### 8. Forbidden

- Form Builder / Consent SoT (→ Forms)  
- Result domain entities (Application, Inquiry, …)  
- Второй параллельный intake pipeline  

---

### Submission

**Normative:** ADR-021 / ADR-022 / [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)

#### 1. Purpose

Универсальная **intake-запись** и routing envelope до Decision / Business Entity.

#### 2. Owned

- Universal Submission object  
- Routing stamp / unresolved disposition codes  
- Append-before-decision invariants  
- Continuity / routing-once semantics (with Lead context)  

#### 3. Public Contracts

- Submission / Intake contracts  
- Universal routing resolve API  

#### 4. Required Capabilities

- Endpoint  
- Acquisition (Campaign / Flight eligibility)  
- Decision Layer (consumer after routed)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `submission.appended` / `routed` / `unresolved` | Endpoint accepts |

#### 6. Settings

- Routing policy knobs owned by Intake/Acquisition (not by Recruitment)  

#### 7. Data Ownership

Submission / intake append log + routing metadata (не Form definition).

#### 8. Forbidden

- Form Builder  
- Auto-create Application/Inquiry without Decision path  
- Campaign creative / budget SoT  

---

### Acquisition / Campaigns

**Normative:** [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`../../acquisition/module-scope.md`](../../acquisition/module-scope.md)

#### 1. Purpose

Demand / growth flow: Campaign, Flight, attribution, intake routing context — **не** Result SoT.

#### 2. Owned

- Campaign / CampaignRun / Flight  
- Source / placement bindings (V1 Form/Intake transitional → Endpoint)  
- `route_intent` / eligibility  
- Attribution context for new Lead  

#### 3. Public Contracts

- Campaign / Flight / routing APIs  
- Binding APIs (uses-not-owns Form/Intake associations)  

#### 4. Required Capabilities

- Endpoint / Submission  
- Forms (compose, не own builder)  
- Notifications (optional)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Campaign/Flight lifecycle | Submission routing outcomes |

#### 6. Settings

- Campaign defaults / windows  
- Source registry defaults  

#### 7. Data Ownership

Campaign, Flight, association tables (FK + role), attribution fields на intake path.

#### 8. Forbidden

- Application / Candidate / Inquiry SoT  
- Form Builder / Consent SoT  
- Document Hub SoT  
- Marketing «продукт» как шестой ADR-004 ключ  

---

### Automations

**Normative:** [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md)

#### 1. Purpose

Правила, триггеры, сценарии между сущностями — единый automation control plane.

#### 2. Owned

- Automation definitions / triggers / actions catalog  
- Entitlement / execution control plane  
- Run history (automation runs)  

#### 3. Public Contracts

- **Automation Adapter**  

#### 4. Required Capabilities

- Notifications, Activity, Documents, AI, module Public Contracts (as action targets)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `automation.triggered` / `completed` / `failed` | Domain events via subscriptions |

#### 6. Settings

- Entitlements Basic/Advanced  
- Rate limits / safety rails  

#### 7. Data Ownership

AutomationRule, AutomationRun (канон ADR-019).

#### 8. Forbidden

- Встроенные «скрытые» automation engines внутри каждого бизнес-модуля как второй SoT  
- Прямой provider SDK из rule body (только через adapters)  

---

### AI

#### 1. Purpose

Единая платформенная AI capability (LLM / assist) через **AI Adapter**.

#### 2. Owned

- AI Adapter / model routing  
- Prompt/policy governance (platform)  
- Usage metering hooks (platform)  

#### 3. Public Contracts

- **AI Adapter**  

#### 4. Required Capabilities

- Integrations (model providers)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `ai.invocation_*` (audit) | Module assist requests |

#### 6. Settings

- Provider keys / model allowlists (platform)  
- Safety / retention policies  

#### 7. Data Ownership

AI invocation audit / policy config (не domain entities).

#### 8. Forbidden

- Прямой LLM SDK в Recruitment/Sales/HR/…  
- AI как владелец Candidate/Document SoT  

---

### Search

#### 1. Purpose

Глобальный поиск / индекс — единый query SoT.

#### 2. Owned

- Search index & query APIs  
- Indexing contracts for entities  

#### 3. Public Contracts

- **Search Adapter**  

#### 4. Required Capabilities

- Module Public Contracts (projectable fields)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Index lag / reindex signals | Domain create/update/delete |

#### 6. Settings

- Index backends / ranking defaults  

#### 7. Data Ownership

Search index documents (derived); query API SoT.

#### 8. Forbidden

- Модульный полнотекст как замена платформенного Search SoT  

---

### Integrations / Marketplace

**Normative:** [`ADR-006`](ADR-006-marketplace-and-integration-platform.md)

#### 1. Purpose

Core integrations, apps, connector lifecycle, marketplace installation.

#### 2. Owned

- Integration registry / installation  
- Connector credentials vault patterns  
- Marketplace catalog metadata  

#### 3. Public Contracts

- Integration Adapters (per provider family)  

#### 4. Required Capabilities

- Module Public Contracts as install targets  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| `integration.installed` / `revoked` | Provider OAuth callbacks |

#### 6. Settings

- Installed apps / scopes per tenant-company  

#### 7. Data Ownership

IntegrationInstallation, connector config (не business entity SoT).

#### 8. Forbidden

- Дублирующие SDK-вызовы из бизнес-модулей в обход Integration Adapter  

---

### Process Engine

**Normative:** [`../platform/process-engine.md`](../platform/process-engine.md)

#### 1. Purpose

Единый движок процессов: stages, profiles, pipelines, transition/handoff rules, runtime evaluator.

#### 2. Owned

- Process definitions / profiles  
- Transition rules / evaluator  
- Handoff rule engine (cross-module where owned by engine)  

#### 3. Public Contracts

- Process contracts  

#### 4. Required Capabilities

- Module domain objects as subjects (compose)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Transition evaluated / applied | Module stage change requests |

#### 6. Settings

- Process profile defaults  

#### 7. Data Ownership

Process/pipeline definition artifacts owned by engine (module owns **which** profile applies to its entities — см. Recruitment pipeline ownership).

#### 8. Forbidden

- Параллельные несовместимые process engines в каждом модуле без контракта  

---

## Business modules

### Recruitment

**Normative:** [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`ADR-008`](ADR-008-job-publishing-and-distribution.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`../../recruitment/module-scope.md`](../../recruitment/module-scope.md)

#### 1. Purpose

Подбор: потребность → публикация → отклик/кандидат → оценка → hiring handoff.

#### 2. Owned

- Vacancy  
- Job Post / Job Publishing (recruitment surface)  
- Candidate  
- Application (Отклик)  
- Candidate Evaluation  
- Hiring Pipeline (Application/Candidate)  
- Interview  
- Offer  
- Recruitment-specific handoff intents to HR/Fleet  

#### 3. Public Contracts

- Recruitment domain APIs (applications, candidates, vacancies, job posts)  
- Handoff contracts to HR/Fleet  

#### 4. Required Capabilities

- Forms, Endpoint, Submission, Acquisition (compose)  
- Documents  
- Notifications / Activity  
- Automations / AI / Search (compose)  
- Process Engine (pipeline profiles)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Application/Candidate/Vacancy lifecycle | `submission.routed` → Decision |
| Handoff requested | Document/Notification outcomes |

#### 6. Settings

- Pipeline / stage definitions (module-owned)  
- Hiring gates / interview defaults  
- Job publishing defaults (каналы — через Integrations)  
- **Не** SMTP, **не** Form consent defaults, **не** Document retention SoT  

#### 7. Data Ownership

Vacancy, JobPost, Candidate, Application, Interview, Offer, recruitment pipeline state.

#### 8. Forbidden

- Forms / Form Builder / Consent SoT  
- Documents / file SoT  
- Notifications delivery stack  
- AI / Search / Automations SoT  
- Campaign / Ad cabinet SoT  
- Sales Inquiry / ClientAccount / Employee / Invoice SoT  

---

### Sales

**Normative:** [`ADR-023`](ADR-023-recruitment-sales-module-separation.md)

#### 1. Purpose

Commercial surface: inquiry → qualification → client account / commercial pipeline (не Recruitment).

#### 2. Owned

- Sales Inquiry / commercial lead surface  
- ClientAccount (sales-owned where scoped)  
- Sales pipeline / qualification  

#### 3. Public Contracts

- Sales / inquiry APIs  

#### 4. Required Capabilities

- Forms, Endpoint, Submission, Acquisition  
- Documents, Notifications, Activity, Automations, AI, Search  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Inquiry lifecycle | Routed submissions with sales intent |

#### 6. Settings

- Sales pipeline / qualification defaults  
- **Не** platform Forms/Notifications/Documents settings SoT  

#### 7. Data Ownership

Inquiry / ClientAccount (sales scope) / sales pipeline state.

#### 8. Forbidden

- Recruitment Candidate/Vacancy SoT  
- Forms / Documents / Notifications / AI stacks  
- Invoice SoT (→ Finance)  

---

### HR

**Normative:** [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) · [`../../hr/module-scope.md`](../../hr/module-scope.md)

#### 1. Purpose

Employee lifecycle: profile, cases, contracts, compliance — автономен без Recruitment.

#### 2. Owned

- Employee profile / HR cases  
- Employment lifecycle (onboarding/termination)  
- HR contracts / ZUS / permits (HR domain)  
- Payroll **data** owned by HR where scoped  

#### 3. Public Contracts

- HR / workforce APIs  
- Handoff accept from Recruitment  

#### 4. Required Capabilities

- Documents, Notifications, Activity, Forms, Automations, AI, Search  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Employee lifecycle | Recruitment handoff |

#### 6. Settings

- HR process / case defaults  
- **Не** Document Hub storage SoT  

#### 7. Data Ownership

Employee, HR Case, employment records (HR scope).

#### 8. Forbidden

- Candidate pipeline SoT  
- Forms/Documents/Notifications stacks  
- Fleet assignment SoT  

---

### Fleet

**Normative:** [`../../fleet/module-scope.md`](../../fleet/module-scope.md)

#### 1. Purpose

Assignments & operations: vehicles, drivers-as-resources, handover, inspections — не воронка найма.

#### 2. Owned

- Vehicle  
- Fleet Assignment / handover  
- Inspections / damage / readiness / return  

#### 3. Public Contracts

- Fleet APIs  

#### 4. Required Capabilities

- Documents, Notifications, Activity, Automations, Search  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Assignment / vehicle lifecycle | HR/Recruitment readiness signals |

#### 6. Settings

- Fleet operational defaults  

#### 7. Data Ownership

Vehicle, Assignment, inspection records.

#### 8. Forbidden

- Hiring pipeline / Forms / Documents / Notifications SoT  

---

### Services / Orders

**Normative:** [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)

#### 1. Purpose

Каталог услуг и заказы; эмит **Billing Events** (не invoices).

#### 2. Owned

- Service catalog  
- Service Order / statuses  
- Billing Event emission (events, не Invoice)  

#### 3. Public Contracts

- Services / orders APIs  
- Billing Event producer contract  

#### 4. Required Capabilities

- Documents, Notifications, Activity, Forms, Finance (as consumer of events)  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Billing Events | Order lifecycle triggers |

#### 6. Settings

- Catalog / order defaults  

#### 7. Data Ownership

Service, ServiceOrder, BillingEvent (producer side).

#### 8. Forbidden

- Invoice SoT  
- Forms/Documents/Notifications stacks  

---

### Finance

**Normative:** [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`../../finance/module-scope.md`](../../finance/module-scope.md)

#### 1. Purpose

Invoices, payments, tax rules — из Billing Events; модули не создают invoice напрямую.

#### 2. Owned

- Invoice  
- Payment  
- Tax / billing rules  
- Billing profile (finance-owned)  

#### 3. Public Contracts

- Finance / invoice APIs  
- Billing Event consumer  

#### 4. Required Capabilities

- Documents, Notifications, Activity, Search  

#### 5. Events

| Publishes | Consumes |
|-----------|----------|
| Invoice/Payment lifecycle | Billing Events from Services/… |

#### 6. Settings

- Tax / numbering / payment provider bindings (finance-owned; providers via Integrations)  

#### 7. Data Ownership

Invoice, Payment, finance rules.

#### 8. Forbidden

- Creating Invoice from Recruitment/HR напрямую  
- Forms/Documents/Notifications stacks  

---

## How to extend the catalog

1. Найти capability по **границе ответственности**, не по UI-экрану.  
2. Если есть passport — **compose** (P-03); расширять Owned только у владельца.  
3. Если нет — ADR → Owner → полный passport (1–8) → строка Index → затем код.  
4. Споры Owned vs Forbidden — Architecture canon owner **до** merge.  
5. Тот же PR обновляет этот файл + §0.1 index + checklist при смене границы.

---

## History

- **2026-07-18** — введён как практический SoT для Capability Boundary + Module/Capability Passport; операционализирует P-02/P-03. Полные паспорта: Forms, Documents, Notifications, Activity, Endpoint, Submission, Acquisition, Automations, AI, Search, Integrations, Process Engine, Recruitment, Sales, HR, Fleet, Services, Finance.
