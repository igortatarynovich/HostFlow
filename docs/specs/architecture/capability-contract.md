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
| Forms Sprint 1 | **UNLOCKED** |
| Forms Builder | **LOCKED** |

Contract tests:

- E2E: `backend/tests/api/test_stage_3d_epic_p_contract.py`  
- Suites: attribution · lifecycle · KPI · Stage 3A–3C  
- Gates: `backend/tests/api/test_stage_3d_epic_p_gates.py`  
- Spec: [`../tasks/acquisition-epic-p-stage-3d.md`](../tasks/acquisition-epic-p-stage-3d.md)  
- Migrations: `202607180004_acq_3d` → `202607180005_acq_3d_o` → `202607180006_acq_3d_k`

### Forms Sprint 1 (UNLOCKED after Epic P)

```text
Passport → Manifest → Public Contract
  publish → endpoint → submission → result
→ Adapter → Contract Tests
```

Без собственного pipeline вне Endpoint spine. Adapter поверх Endpoint — не новая form engine.  
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
