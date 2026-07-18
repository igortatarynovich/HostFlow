# ADR-007: Forms — Core Platform Module (input & consent layer)

## Status

**Accepted (product & architecture direction).**  
**2026-07-18:** Forms зафиксирован как **Core Platform Module** (рядом с Documents, Activity, Notifications, Automations, Search) — не часть Recruitment/Acquisition и **не** шестой лицензируемый продукт ADR-004. Basic Forms доступен всем тенантам; Advanced — addon/bundle (ADR-006).

**Связанное главное решение платформы:** абстракция **Endpoint** и spine  
`Endpoint → Submission → Routing → Decision → Business Entity` — в [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md). Forms — SoT **сбора данных**, когда Endpoint типа HostFlow Public Form; Acquisition не зависит от Forms internals.

**Платформенный принцип:** [`ADR-025`](ADR-025-standard-adapter-boundary.md) **P-01** + [`ADR-026`](ADR-026-capability-ownership.md) **P-02** + [`ADR-027`](ADR-027-capability-composition.md) **P-03** — потребители Forms работают только через **Endpoint Adapter** у владельца; вторая реализация Forms запрещена; Recruitment/Sales/… **композируют** Forms, не копируют.

**Submission:** Forms владеет form surface + consent version pin. Универсальный Submission object / routing envelope — Shared Intake ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)); catalog — [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1.

Имплементация **поэтапная**. Текущий код (`tenant_lead_forms`, `/public/intake`, квоты) — исторический bridge.

## Context

Формы не должны восприниматься как «анкета кандидата» или подсистема Acquisition. Recruitment, Sales, HR, Fleet, Finance, Services **потребляют** Forms. Параллельные form-стеки в модулях **запрещены**.

Связанные: [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md), [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md), [`../../forms/module-scope.md`](../../forms/module-scope.md).

## Decision: Forms = Core Platform Module

**Forms** — единственный SoT для:

- Form Builder / Form Templates  
- Versioning / Publishing  
- Public и Internal Form Endpoints (поверхность HostFlow Form)  
- Submission Engine (для HostFlow Form)  
- Consent Management (GDPR / RODO / Terms / Privacy) + **version pinning**  
- Multi-language / Form Logic / Form Themes  
- CAPTCHA, webhooks, post-submit automation events  

Forms:

- доступен всем тенантам (Basic / core);
- **не** лицензируется как отдельный продукт ADR-004;
- **не** принадлежит Recruitment или Acquisition.

**Endpoint** ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)) — более широкая абстракция входа. HostFlow Public Form **is-a** Endpoint. Meta Lead Form, API, Webhook и т.д. — тоже Endpoint, но **не** объекты Forms SoT.

```text
Endpoint → Submission          ← универсально (ADR-024)
Forms ──owns──► HostFlow Form surface + consent + form submissions
Campaign ──uses──► Endpoint    ← не Form
```

### Юридический инвариант

Submission ссылается на **конкретную опубликованную версию** формы. Позднейшая v4 **не** меняет якорь уже принятого Submission.

### First entry vs continuation

| Режим | Поведение |
|-------|-----------|
| **First entry** | Новый Submission → Universal Routing → новый Lead (+ Campaign context) → Decision Layer |
| **Continuation** | Новый Submission на **существующий** Lead; routing/attribution **наследуются**; Campaign не пересчитывается |

### Handlers (потребители)

Lead, Candidate, Employee, Client, Service Order, Fleet records, Document, Billing profile — через handlers модулей-владельцев.

### Basic vs Advanced

| Tier | Содержание | Монетизация |
|------|------------|-------------|
| **Basic** | Форма, публичная ссылка, submissions, файлы | **Core platform** |
| **Advanced** | Conditional logic, deep mapping, e-sign/consent tracking, branding, multi-language, portals | **Paid addon** / bundle |

## Связь с ADR-024

- Канон intake: `Endpoint → Submission → Routing → Decision → Business Entity`.  
- Stage 3B V1 Form/Intake associations = transitional Endpoint specializations.
- Stage 3C: любой Endpoint → тот же Universal Routing.
- **Gate:** Epic P / Stage 3D **COMPLETE** ([`../tasks/acquisition-epic-p-stage-3d.md`](../tasks/acquisition-epic-p-stage-3d.md)).  
- **Forms Sprint 1–6:** ✅ **COMPLETE** — L0 backend platform contour ([`../tasks/forms-sprint-6.md`](../tasks/forms-sprint-6.md)).  
- **Forms Product Layer:** **OPEN** ([`../tasks/forms-product-layer-epic.md`](../tasks/forms-product-layer-epic.md)) — P1 Field Catalog next.  
- **Architectural rule:** **Field Catalog is SoT** for field types / params / validation / normalization / Builder + Public render. **Builder must not invent field types** — only compose Catalog blocks.  
- **Forms Builder:** **LOCKED** until Product Layer P1 DoD.  
- Forms compose Acquisition Endpoint/Submission/Result — не копируют Outcome/KPI.

## Platform epic (roadmap)

**Done (Sprint 1–6):** Endpoint Engine (HostFlow Form publish); Version ledger; Schema/validation/normalization; Immutable submission envelope; Shared Intake handoff; Audit.

**Open — Product Layer:** Field Catalog → Builder → Publish UI → Themes → Analytics ([`../tasks/forms-product-layer-epic.md`](../tasks/forms-product-layer-epic.md)).

Also roadmap: Consent Management depth; Conditional Logic; Multi-language; Automations / Documents / Universal Entity integration.

## Consequences

1. Главное изменение платформы — **Endpoint**, не «перенос Form Builder». Подчиняется **P-01…P-03**.  
2. Forms = единственный SoT формы и form-submission surface / consent.  
3. Campaign / Acquisition потребляют Endpoint → Submission через Adapter.  
4. RODO/Terms/Privacy не живут в Recruitment settings.  
5. Новый публичный сбор данных — только через Forms (HostFlow Form) или другой Endpoint type + handler (композиция, не дубликат).

## References

[`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) · [`ADR-008`](ADR-008-job-publishing-and-distribution.md) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`../../forms/module-scope.md`](../../forms/module-scope.md)

## История

- 2026-05: Forms как платформенная capability.  
- 2026-07-02: C4 bridge MVP.  
- 2026-07-18: Core Platform Module; Endpoint spine (ADR-024); Forms SoT + consent version pinning; Platform Forms epic; link **P-01** ([`ADR-025`](ADR-025-standard-adapter-boundary.md)).  
- 2026-07-18: Forms Sprint 1 gated on Epic P / 3D DoD; sequence Passport → Manifest → Public Contract → Adapter → Tests (not Builder first).  
- 2026-07-18: Epic P COMPLETE — Forms Sprint 1 **UNLOCKED**; Builder **LOCKED**.  
- 2026-07-18: Sprint 1 infra — Public Contract v1 + Adapter + contract tests (no Builder).  
- 2026-07-18: Sprint 1 COMPLETE (PR #36); Sprint 2 — immutable snapshot + activate/deactivate + version pin.  
- 2026-07-18: Sprint 1–6 COMPLETE; Product Layer epic OPEN; Field Catalog SoT / Builder-no-invent-types rule.
