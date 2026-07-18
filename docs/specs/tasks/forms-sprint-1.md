# Forms Sprint 1 — Infrastructure (Capability Contract closure)

**Status:** READY FOR REVIEW (infra PR)  
**Canon:** [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md) · [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Module scope:** [`../../forms/module-scope.md`](../../forms/module-scope.md)  
**Prerequisite:** Epic P / Acquisition Stage 3D **COMPLETE** ([`acquisition-epic-p-stage-3d.md`](acquisition-epic-p-stage-3d.md) · merge `df099d35`)  
**Gate:** Forms Sprint 1 infra → **Builder remains LOCKED**

---

## Why now

Acquisition vertical is closed. Forms may proceed **only** as infrastructure:

```text
Passport → Manifest → Public Contract → Endpoint → Submission → Result → Adapter
```

UI / Builder **не** открываются этим спринтом.

---

## Goal

Зафиксировать публичную Forms-границу HostFlow Form поверх существующего Endpoint spine и C4 publication bridge — без FormTemplate migration, без Builder, без собственного routing/Outcome/KPI.

---

## Public chain (единственная)

```text
publish → endpoint → submission → result
```

| Op | Meaning |
|----|---------|
| **publish** | Resolve HostFlow Form publication (ADR-007 view; bridge = `TenantLeadForm`) |
| **endpoint** | HostFlow Public Form **is-a** Endpoint specialization |
| **submission** | Form submission surface → Shared Intake / public intake path |
| **result** | Result создаётся Decision / destination module; Forms **не** SoT Result. Attribution / Outcome / KPI — **Acquisition contracts** |

---

## Scope

### In

1. **Passport** — Catalog `#forms` полный для Sprint 1 surface + links  
2. **Manifest** — конкретные keys (flags, limits, defaults, permissions, adapter config)  
3. **Public Contract** — [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
4. **Adapter** — `backend/app/forms_platform/adapter.py` (P-01 facade over publication bridge)  
5. **Contract tests** — `test_forms_sprint1_contract.py` (+ gates)

### Out (LOCKED / forbidden)

- Visual Form Builder; drag-and-drop; arbitrary schema editor  
- Presentation designer; branching UI; themes marketplace  
- Form marketplace  
- New routing engine  
- Forms-owned Outcome / KPI / attribution engines  
- FormTemplate schema migration (unless a real schema blocker appears — none for Sprint 1)  
- KPI dashboard / UI surfaces

Forms **compose** Acquisition Endpoint / Submission / Result attribution — **не копируют**.

---

## DoD

- [x] Passport + Manifest + Public Contract linked from Catalog / module-scope / ADR-007  
- [x] Adapter exposes `publish` / `endpoint` / `submission` / `result` handoff  
- [x] Contract test: publish → endpoint → submission → result (compose Acquisition)  
- [x] No Forms Outcome/KPI tables or services  
- [x] No Builder unlock language in canon  
- [x] C4 bridge regression retained  
- [x] No new Alembic head / no new migration without schema cause  
- [x] No new SPA `/app` literals on Forms Sprint 1 surface  

---

## Deliverables

| Artifact | Path |
|----------|------|
| Task (this) | `docs/specs/tasks/forms-sprint-1.md` |
| Public Contract | `docs/specs/architecture/forms-public-contract.md` |
| Adapter | `backend/app/forms_platform/adapter.py` |
| Manifest keys (docs) | `capability-settings-manifest.md` `#forms` |
| Manifest keys (code) | `backend/app/forms_platform/manifest.py` |
| Contract test | `backend/tests/forms_platform/test_forms_sprint1_contract.py` |
| Gates | `backend/tests/forms_platform/test_forms_sprint1_gates.py` |

---

## History

- 2026-07-18: Sprint opened after Epic P merge `df099d35` (#34).
