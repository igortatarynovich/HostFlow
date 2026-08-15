# Capability Contract (L1 delivery artifact)

**Status:** canonical (Phase 1 operating practice)  
**Layer:** L1 — applies L0 templates; **does not** amend L0 constitution  
**Owner:** Architecture canon owner  
**References:** [`L0-platform-architecture.md`](L0-platform-architecture.md) · [`platform-capability-catalog.md`](platform-capability-catalog.md) · [`capability-settings-manifest.md`](capability-settings-manifest.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md) · [`architecture-guide.md`](architecture-guide.md)

---

## Purpose

Между **Passport** и **Adapter** обязателен явный артефакт **Public Capability Contract**.

Свойство: **UI никогда не определяет архитектуру.** Сначала фиксируется внешний контракт, затем реализация, затем интерфейс.

L0 уже требует Passport + Exposes + Manifest schema. Capability Contract — **операционный** артефакт Phase 1: конкретный публичный surface (операции, события, инварианты, стабильность) до кода Adapter.

---

## Mandatory sequence (any new L1 capability)

```text
1. Passport          ← Catalog: Owns / Non-Goals / Forbidden / Exposes / deps
2. Manifest          ← Settings keys (flags, limits, defaults, permissions, adapter config)
3. Public Contract   ← THIS artifact (operations + events + invariants)
4. Adapter           ← P-01 boundary implementation
5. Contract Tests    ← enforce Public Contract
6. UI                ← only after 1–5
```

Запрещён порядок: UI → «подтянуть» контракт; Adapter без Contract; Manifest «потом когда понадобится».

Применяется ко всем последующим L1: **Forms**, Documents, Notifications, Activity, Search, AI, Automations, Integrations, …

---

## What a Capability Contract contains

Один документ (или секция Passport + linked file) на capability / major surface:

| Section | Content |
|---------|---------|
| **Identity** | Capability id, owner, related Passport anchor |
| **Public operations** | Named ops consumers may call (e.g. `publish`, `submit`, `attribute_result`) |
| **Inputs / outputs** | Typed DTOs or schema refs; no module internals |
| **Events emitted** | Event names + payload stability |
| **Invariants** | Must-hold rules (ownership, chain order, delete policy) |
| **Forbidden consumer paths** | What modules must not do |
| **Stability** | Stable / Experimental / Internal per op (ADR-030) |
| **Adapter binding** | Which Adapter id implements which ops |
| **Contract tests** | Path to test module that locks the chain |

**Не** путать с Settings Manifest (конфиг) и с Passport (ownership / scope). Contract = **поведение на границе**.

---

## Minimal example shapes

### Acquisition vertical (Epic P) — ✅ COMPLETE

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome → KPI
```

| Gate | Status |
|------|--------|
| Acquisition Stage 3D | ✅ COMPLETE |
| Forms Sprint 1 | ✅ **COMPLETE** (PR #36 · `37b652af`) |
| Forms Sprint 2 | ✅ **COMPLETE** (PR #37 · `ec5fcd86`) |
| Forms Sprint 3 | ✅ **COMPLETE** (PR #38 · `f5771df6`) |
| Forms Sprint 4 | ✅ **COMPLETE** (PR #39 · `779cffd3`) |
| Forms Sprint 5 | ✅ **COMPLETE** (PR #40 · `a6df02f0`) |
| Forms Sprint 6 | ✅ **COMPLETE** (PR #41 · `7e259f22`) |
| Forms Product Layer | P1 ✅ CLOSED · P2 MVP ✅ · C3–C6 ✅ / Foundation ✅ · P3 Publish UI / P4 / P5 **LOCKED** |
| Entity Workspace Phase D | D1 ✅ · D2 ✅ ([brief](../tasks/entity-workspace-d2-composition-contract.md) · [#254](https://github.com/igortatarynovich/HostFlow/pull/254)); D3 [brief](../tasks/entity-workspace-d3-consumer-cutover.md) (feat locked); slot catalog; no Passport |
| Forms Platform C1 | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| Forms Platform C2 | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| Forms Platform C3 | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244); draft save ≠ publish |
| Forms Platform C4 | ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246); Runtime Model; not P3 / P4 / C5 |
| Forms Platform C5 | ✅ ([brief](../tasks/forms-platform-c5-form-execution.md)) |
| Forms Platform C6 | ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249)/[#250](https://github.com/igortatarynovich/HostFlow/pull/250); Foundation close |

Contract tests:

- E2E: `backend/tests/api/test_stage_3d_epic_p_contract.py`  
- Suites: attribution · lifecycle · KPI · Stage 3A–3C  
- Gates: `backend/tests/api/test_stage_3d_epic_p_gates.py`  
- Spec: [`../tasks/acquisition-epic-p-stage-3d.md`](../tasks/acquisition-epic-p-stage-3d.md)  
- Migrations: `202607180004_acq_3d` → `202607180005_acq_3d_o` → `202607180006_acq_3d_k`

### Forms Sprint 1–6 ✅ (backend platform contour)

```text
Passport → Manifest → Public Contract
  resolve · publish → endpoint → validate/normalize → envelope → result
→ Adapter → Contract Tests
```

| Artifact | Path |
|----------|------|
| Sprint 1–6 tasks | [`../tasks/forms-sprint-1.md`](../tasks/forms-sprint-1.md) … [`forms-sprint-6.md`](../tasks/forms-sprint-6.md) ✅ |
| Public Contract | [`forms-public-contract.md`](forms-public-contract.md) |
| Adapter | `backend/app/forms_platform/adapter.py` (`forms.endpoint_adapter_v1`) |
| Manifest keys | [`capability-settings-manifest.md`](capability-settings-manifest.md#forms) · `forms_platform/manifest.py` |
| Migrations | `202607180007_forms_s2` … `202607180009_forms_s6` |
| Contract tests | `test_forms_sprint1_*.py` … `test_forms_sprint6_*.py` · `test_forms_c1_contract_seal.py` |

Без собственного pipeline вне Endpoint spine. Adapter поверх Endpoint / C4 publication bridge — не новая form engine.  
**Не** Builder / drag-and-drop / schema editor / marketplace / новый routing / Forms Outcome-KPI.

---

## Review gate

Перед merge Adapter / API для новой capability:

- [ ] Passport заполнен (не outline-only для целевой capability)  
- [ ] Manifest keys зафиксированы (хотя бы draft values)  
- [ ] Public Contract документ существует и ссылается из Catalog / module-scope  
- [ ] Adapter реализует только ops из Contract  
- [ ] Contract tests зелёные  
- [ ] Нет UI-only surface без Contract  

См. также [`architecture-review-checklist.md`](architecture-review-checklist.md).

---

## Non-goals

- Не замена L0 Passport / Exposes  
- Не OpenAPI dump всего backend  
- Не UI wireframes  
- Не изменение L0 freeze (это L1 practice поверх конституции)

---

## History

- 2026-07-18: Introduced as Phase 1 mandatory artifact between Passport and Adapter.  
- 2026-07-18: Epic P COMPLETE; Forms Sprint 1 unlocked; Builder locked.  
- 2026-07-18: Forms Sprint 1 infra — Public Contract + Adapter + contract tests linked.
