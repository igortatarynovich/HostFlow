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

**Forms Sprint 1 — UNLOCKED** ([`capability-contract.md`](../specs/architecture/capability-contract.md)):

1. Passport (полный)  
2. Manifest keys (flags, limits, defaults, permissions, adapter config)  
3. Public Contract: `publish → endpoint → submission → result`  
4. Adapter поверх Endpoint  
5. Contract Tests  

**Forms Builder — LOCKED** until Sprint 1 contracts land.

Gate evidence: [`../specs/tasks/acquisition-epic-p-stage-3d.md`](../specs/tasks/acquisition-epic-p-stage-3d.md) · E2E `test_stage_3d_epic_p_contract.py`.

## История

- 2026-05: платформенная capability.  
- 2026-07-18: Core Platform Module + Endpoint spine.  
- 2026-07-18: Forms Sprint 1 gated on Epic P; Capability Contract sequence.  
- 2026-07-18: Epic P COMPLETE — Sprint 1 **UNLOCKED**; Builder **LOCKED**.
