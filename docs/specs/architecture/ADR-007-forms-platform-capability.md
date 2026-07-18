# ADR-007: Forms — Core Platform Module (input & consent layer)

## Status

**Accepted (product & architecture direction).**  
**2026-07-18:** Forms зафиксирован как **Core Platform Module** (на уровне Documents, Activity, Notifications, Automations, Search) — не часть Recruitment/Acquisition и **не** шестой лицензируемый продукт ADR-004. Basic Forms доступен всем тенантам; Advanced — addon/bundle (ADR-006).

Имплементация **поэтапная**. Текущий код (`tenant_lead_forms`, `/public/intake`, квоты) — исторический bridge; целевая модель ниже обязательна для новой разработки.

## Context

Формы не должны восприниматься как «анкета кандидата» или как подсистема Acquisition. **Анкета кандидата** — один use case. Recruitment, Sales, HR, Fleet, Finance, Services **потребляют** Forms; никто не создаёт собственный параллельный form-стек.

Связанные: [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md), [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) (Campaign → **Endpoint**; HostFlow Public Form = один тип Endpoint), [`../../forms/module-scope.md`](../../forms/module-scope.md).

## Decision: Forms = Core Platform Module

**Forms** — базовый платформенный модуль HostFlow. Он:

- доступен всем тенантам (Basic / core);
- **не** лицензируется как отдельный продукт ADR-004;
- **не** принадлежит Recruitment или Acquisition;
- полностью владеет **жизненным циклом формы** и **юридической поверхностью** согласий.

Acquisition **не знает** внутренностей Forms. Campaign получает **Submission** через **Endpoint** ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)); HostFlow Public Form — один из типов Endpoint.

### Ответственность Forms (SoT)

| Область | Владеет Forms |
|---------|----------------|
| Form Builder / templates | да |
| Версии + история изменений | да |
| Публикация / Internal Forms | да |
| Public Endpoints (slug, publish) | да |
| Submission engine | да |
| Согласия, GDPR / RODO, Privacy Policy, Terms | да (версия формы = юридический якорь) |
| Многоязычность, оформление / themes | да |
| CAPTCHA, webhooks | да |
| Автоматизации **после отправки формы** (emit events) | да (исполнение — Automations) |
| File upload → Document Hub | да (файл SoT — ADR-009) |

**Юридический инвариант:** Submission ссылается на **конкретную опубликованную версию** формы (например v3). Позднейшая публикация v4 **не** меняет якорь уже принятого Submission — доказуемость согласий.

### Режимы использования HostFlow Form

| Режим | Поведение |
|-------|-----------|
| **First entry** (`/apply/…`, `/company/jobs/…`, …) | Form создаёт **новый** Submission → Universal Submission Routing → Lead (+ Campaign context) → Decision Layer |
| **Process continuation** (менеджер: «заполните расширенную анкету») | Form создаёт **новую** Submission на **существующий** Lead. **Routing не повторяется.** Campaign / attribution context **наследуется** от Lead |

См. ADR-024: **routing выполняется один раз** при создании Lead.

### Состав (целевая функциональность)

Form templates; versions; publish; public/internal endpoints; submissions; file uploads; consent capture; field mapping → Field Registry / Entity Profile (форма **не** создаёт семантику поля); automation triggers; CAPTCHA; webhooks; multi-language; themes.

### Целевые handlers (потребители)

Lead, Candidate, Employee, Client, Service Order, Fleet records, Document, Billing profile — через handlers модулей-владельцев, не через Forms SoT domain objects.

### Basic vs Advanced

| Tier | Содержание | Монетизация |
|------|------------|-------------|
| **Basic** | Создать форму, публичная ссылка, submissions, файлы | **Core platform** (все тенанты) |
| **Advanced** | Conditional logic, deep entity mapping, e-sign/consent tracking, branding, multi-language, portal links, rich automations | **Paid addon** / bundle модулей |

## Связь с ADR-004 / ADR-024

- Каталог пяти продуктовых модулей **не** расширяется ключом `forms`.  
- Acquisition Stage 3B V1 хранит `CampaignRun ↔ TenantLeadForm` как **переходную** специализацию Endpoint типа HostFlow Public Form; канон — **CampaignRun ↔ Endpoint** (ADR-024).  
- Universal Submission Routing одинаков для Meta, Public Form, API, Webhook и др.

## Platform epic (roadmap после текущего Acquisition V1)

Отдельный эпик **Platform — Forms** (не блокирует 3D/3E):

- Visual Form Builder  
- Public Endpoint Engine  
- Versioning + Submission Engine  
- Consent Management (GDPR/RODO/Terms/Privacy) с version pinning  
- Conditional Logic; File Upload; Multi-language; Themes  
- Endpoint Publishing; Submission API  
- Интеграция с Automations, Documents, Universal Entity Workspace  

## Consequences

1. Новые публичные сценарии сбора данных — только через **Forms** + handler модуля, без fork intake.  
2. `TenantLeadForm` / public intake → миграция к FormTemplate / FormPublish / Submission (отдельные задачи).  
3. RODO/Terms/Privacy **не** живут как настройки Recruitment.  
4. Campaign / Acquisition **не** зависят от Forms internals — только от Endpoint → Submission.  
5. Безопасность публичных ссылок, rate limit, антиспам, PII — общие политики платформы.

## References

- [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) · [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) · [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) · [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) · [`ADR-008`](ADR-008-job-publishing-and-distribution.md) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) · [`../../forms/module-scope.md`](../../forms/module-scope.md)

## История

- 2026-05: Forms как платформенная capability; Basic/Advanced; handlers; ADR-008/009.  
- 2026-07-02: C4 bridge MVP — `TenantLeadForm` via `forms_platform/`.  
- 2026-07-18: **Core Platform Module** lock-in; Forms owns full form + consent lifecycle; Campaign → Endpoint (не Form); first-entry vs continuation; Platform Forms epic.
