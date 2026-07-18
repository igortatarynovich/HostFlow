# Модуль Forms: Core Platform Module

Норматив: **[`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md)**.  
Intake spine / Endpoint: **[`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)**.

## Суть

```text
Endpoint → Submission → Routing → Decision → Business Entity
```

- **Endpoint** — главная абстракция входа (Meta, HostFlow Form, API, Webhook, …).  
- **Forms** — Core Platform Module: SoT **HostFlow Form** (builder, versions, publish, submission surface, consents).  
- HostFlow Public Form **is-a** Endpoint; Campaign использует Endpoint, не Form.  
- Forms **не** часть Recruitment/Acquisition; **не** продукт ADR-004 (Basic — всем тенантам).

## Responsibilities (SoT)

Form Builder; Templates; Versioning; Publishing; Public/Internal Form Endpoints; Submission Engine; Consent (GDPR/RODO/Terms/Privacy) + version pinning; Multi-language; Form Logic; Themes; CAPTCHA; webhooks; post-submit events.

## Routing

- First entry → Universal Routing (один раз на новый Lead).  
- Continuation → наследование Routing/Attribution context Lead.

## Platform epic (после Acquisition V1)

Form Builder; Endpoint Engine; Submission Engine; Versioning; Consent; Public Publishing; Internal Forms; Themes; Conditional Logic; File Upload; Multi-language; Automations / Documents / Entity Workspace.

## История

- 2026-05: платформенная capability.  
- 2026-07-18: Core Platform Module + Endpoint spine.
