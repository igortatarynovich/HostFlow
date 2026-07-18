# Модуль Forms: охват Core Platform Module

Нормативное решение — **[`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md)**.

## Суть

- **Forms** — **Core Platform Module** HostFlow (рядом с Documents, Activity, Notifications, Automations, Search).  
- **Не** часть Recruitment / Acquisition; **не** шестой лицензируемый продукт ADR-004. Basic — всем тенантам.  
- Полностью владеет жизненным циклом формы: Builder, templates, versions, publish, public/internal endpoints, Submission, consents (GDPR/RODO/Terms/Privacy), multi-language, themes, CAPTCHA, webhooks, post-submit automation events.  
- **Acquisition не знает Forms internals.** Campaign использует **Endpoint**; HostFlow Public Form — один тип Endpoint ([`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)).  
- Recruitment, Sales, HR, Fleet, Finance, Services — **потребители**; никто не строит свой form-стек.  
- Forms **не определяют смысл полей** — поверхность ввода над Entity Profile / Field Registry.

## First entry vs continuation

| Режим | Routing |
|-------|---------|
| First entry (новый Lead) | Submission → Universal Submission Routing → Lead / Campaign context |
| Continuation (существующий Lead) | Новая Submission **без** повторного routing; контекст Lead наследуется |

## Юридический якорь

Submission ссылается на **опубликованную версию** формы. Позднейшие версии не переписывают уже принятые согласия.

## Basic vs Advanced

| Tier | Содержание |
|------|------------|
| **Basic** | Форма, публичная ссылка, submissions, файлы — **core platform** |
| **Advanced** | Conditional logic, deep mapping, e-sign/consent tracking, branding, multi-language, portals — **addon / bundle** |

## Platform epic (после Acquisition V1)

Visual Form Builder; Public Endpoint Engine; Versioning; Submission Engine; Consent Management; Conditional Logic; File Upload; Multi-language; Themes; Endpoint Publishing; Submission API; Automations / Documents / Entity Workspace.

## Текущий код

`tenant_lead_forms`, `/public/intake`, `forms_platform/` bridge — исторический слой; миграция к FormTemplate / FormPublish / Submission — поэтапно (ADR-007).

## История

- 2026-05: Forms как платформенная capability.  
- 2026-07-18: Core Platform Module lock-in; Campaign → Endpoint; routing once; Platform Forms epic.
