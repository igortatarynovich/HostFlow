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

**Forms Sprint 1–6 — ✅ COMPLETE** (backend platform contour · PR #41 · `7e259f22`).

Submission Envelope / Immutable Storage / Idempotent Processing / Audit API — **ACTIVE**.

**Next:** [Forms Platform C6 — Optimization](../specs/tasks/forms-platform-c6-optimization.md) ← **COMPLETE** ([#249](https://github.com/igortatarynovich/HostFlow/pull/249)/[#250](https://github.com/igortatarynovich/HostFlow/pull/250)). Forms **Foundation ✅**. Product Track → [host runtime-equivalence](../specs/tasks/workspace-capability-host-runtime-equivalence.md) (WCP G1–G5 PASS_WITH_CONSTRAINTS; program not COMPLETE). P3 Publish UI / P4 Themes / P5 Analytics remain **LOCKED**. Forms is a **platform capability** (peer of EntityWorkspace / ListWorkspace / Analytics Kit / RBAC / Automations) — not a product module.

**Rule:** P1 Foundation **CLOSED**; Catalog v1 **FROZEN**. **Builder MVP COMPLETE** (P2.1–P2.5). C3 ✅ = editor of FormDefinition (draft save ≠ publish). C4 ✅ = **Runtime Model** from frozen publication (not an Engine). C5 ✅ = Execution against Runtime Model. C6 ✅ = Foundation Optimization (production serve→execute). P3 Publish UI / P4 Themes / P5 Analytics **LOCKED**.  
**Matrix:** [`Intake Canonical Input Matrix`](../specs/architecture/intake-canonical-input-matrix.md) **ACCEPTED / FROZEN** · epic [`COMPLETE`](../specs/tasks/intake-canonical-input-matrix.md).  
**Runtime:** [`Intake Runtime Split V1`](../specs/tasks/intake-runtime-split-v1.md) (**ACTIVE** · R1+R2 ✅ · R3) — Flights / Intake Routing runtime **UNLOCKED**.  
**Communications:** [`Intake Domain Separation & Communication Context V1`](../specs/tasks/intake-domain-separation-communication-context-v1.md) (**READY**) · Stage 1 audit [`ACTIVE`](../specs/architecture/intake-communication-context-audit-v1.md).  
**Forms P3–P5** remain **LOCKED**.

Compose Acquisition (не копировать): Endpoint binding · Universal Routing · Result attribution · Outcome · KPI.

Gate evidence: Epic P [`../specs/tasks/acquisition-epic-p-stage-3d.md`](../specs/tasks/acquisition-epic-p-stage-3d.md) · Forms E2E `backend/tests/forms_platform/test_forms_sprint1_contract.py`.

## История

- 2026-05: платформенная capability.  
- 2026-07-18: Core Platform Module + Endpoint spine.  
- 2026-07-18: Forms Sprint 1 gated on Epic P; Capability Contract sequence.  
- 2026-07-18: Epic P COMPLETE — Sprint 1 **UNLOCKED**; Builder **LOCKED**.  
- 2026-07-18: Sprint 1 infra started — Public Contract + Adapter + contract tests.  
- 2026-07-18: Sprint 1 **COMPLETE** (PR #36); Sprint 2 runtime hardening opened.  
- 2026-07-18: Sprint 6 **COMPLETE**; Product Layer epic opened (Field Catalog first).  
- 2026-07-19: P2.1 Read Model COMPLETE; P2.2 Composition READY.  
- 2026-07-19: P2.2 Composition COMPLETE; P2.3 Commands READY.  
- 2026-07-19: P2.3 Commands COMPLETE; P2.4 Persistence READY.  
- 2026-07-19: P2.4 Persistence COMPLETE; P2.5 UI READY.  
- 2026-07-19: P2.5 Builder UI COMPLETE — MVP closed; next Flights / Intake Routing.  
- 2026-08-20: Product Track → [Entity Platform Completion](../specs/tasks/workspace-capability-platform-completion.md) (feat locked). D1–D9 brief-complete / goal-incomplete.  
- 2026-08-14: C6 ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249)/[#250](https://github.com/igortatarynovich/HostFlow/pull/250); Forms Foundation ✅; Product Track → [Entity Workspace D1](../specs/tasks/entity-workspace-d1-contract-seal.md).
- 2026-08-14: C4 ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246); C5 ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247)/[#248](https://github.com/igortatarynovich/HostFlow/pull/248); Product Track → [C6 Optimization](../specs/tasks/forms-platform-c6-optimization.md) (brief; feat locked).
- 2026-08-14: C4 brief [#245](https://github.com/igortatarynovich/HostFlow/pull/245); feat = Runtime Model.
- 2026-08-14: C3 ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244); Product Track → [C4 Form Runtime](../specs/tasks/forms-platform-c4-form-runtime.md) (brief; feat locked).
- 2026-08-14: C1+C2 merged; Product Track → [C3 Builder Runtime](../specs/tasks/forms-platform-c3-builder-runtime.md).  
- 2026-08-13: Product Track → [Forms Platform C1](../specs/tasks/forms-platform-c1-contract-seal.md); P3–P5 remain LOCKED.  
- 2026-08-13: Next after C1 = [C2 Runtime Contract](../specs/tasks/forms-platform-c2-runtime-contract.md); Builder locked until C2 feat.  
- 2026-07-19: Intake Canonical Input Matrix epic ACTIVE; matrix READY (docs-only gate).  
- 2026-07-19: Matrix ACCEPTED / FROZEN; Runtime Split V1 READY; Flights / Intake Routing runtime UNLOCKED.  
- 2026-07-19: Runtime Split R1+R2 merged; R3 handlers + Communication Context epic / Stage 1 audit opened.
