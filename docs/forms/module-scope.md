# Модуль Forms: Core Platform Module

Норматив: **[`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md)**.  
Intake spine / Endpoint: **[`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)**.  
**Capability Boundary / passport:** [`platform-capability-catalog.md`](../specs/architecture/platform-capability-catalog.md#forms).

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

## Platform epic (после Epic P DoD)

**Forms Sprint 1–4 — ✅ COMPLETE** · **Forms Sprint 5 — IN PROGRESS** ([`../specs/tasks/forms-sprint-5.md`](../specs/tasks/forms-sprint-5.md)):

Normalized answers (`forms.normalized_answers.v1`) → Shared Intake; Builder **LOCKED**.

Compose Acquisition (не копировать): Endpoint binding · Universal Routing · Result attribution · Outcome · KPI.

Gate evidence: Epic P [`../specs/tasks/acquisition-epic-p-stage-3d.md`](../specs/tasks/acquisition-epic-p-stage-3d.md) · Forms E2E `backend/tests/forms_platform/test_forms_sprint1_contract.py`.

## История

- 2026-05: платформенная capability.  
- 2026-07-18: Core Platform Module + Endpoint spine.  
- 2026-07-18: Forms Sprint 1 gated on Epic P; Capability Contract sequence.  
- 2026-07-18: Epic P COMPLETE — Sprint 1 **UNLOCKED**; Builder **LOCKED**.  
- 2026-07-18: Sprint 1 infra started — Public Contract + Adapter + contract tests.  
- 2026-07-18: Sprint 1 **COMPLETE** (PR #36); Sprint 2 runtime hardening opened.
