# Forms Public Contract v1 — Sprint 1

**Status:** canonical (Forms Sprint 1)  
**Capability id:** `forms`  
**Contract id:** `forms.public_contract.v1`  
**Adapter id:** `forms.endpoint_adapter_v1`  
**Passport:** [`platform-capability-catalog.md`](platform-capability-catalog.md#forms)  
**Task:** [`../tasks/forms-sprint-1.md`](../tasks/forms-sprint-1.md)  
**Normative:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md)

---

## Identity

Forms владеет **HostFlow Form surface** (publish + consent pin intent + submission entry).  
Универсальный Endpoint / Submission routing envelope / Result attribution / Outcome / KPI — **не** Forms SoT.

Storage bridge (Sprint 1): `TenantLeadForm` via C4 publication bridge until FormTemplate migration.

---

## Public operations

| Op | Stability | Description |
|----|-----------|-------------|
| `publish` | **Stable** | Resolve publication view for a HostFlow Form (`form_id` or `public_slug`) |
| `endpoint` | **Stable** | Map publication → Endpoint identity (`endpoint_type=hostflow_public_form`) |
| `submission` | **Stable** | Expose submission entry (public intake path + handler metadata); payload accepted by Shared Intake |
| `result` | **Stable** | Handoff only: Result SoT is destination/Decision; Forms returns compose pointers to Acquisition attribution — **does not** create Result/Outcome/KPI |

### Inputs / outputs (summary)

**`publish`**

- In: `tenant_id`, `form_id` XOR `public_slug`  
- Out: publication DTO (`contract_version`, `publication_id`, `public_slug`, `is_active`, `mode`, `submission_handler`, `public_intake_path`, …)

**`endpoint`**

- In: publication DTO (or same resolve keys)  
- Out: `{ endpoint_type, form_id, publication_id, public_slug, intake_source_profile_id?, public_intake_path }`

**`submission`**

- In: publication / endpoint identity  
- Out: `{ public_intake_path, submission_handler, storage_backend, forms_role=submission_surface }`  
- Write path: existing `/api/v1/public/intake` + `intake_platform.submission_store` — **not** a second Forms submit engine

**`result`**

- In: attributed Result context after Decision (compose)  
- Out: handoff `{ result_owner, forms_role, acquisition_ops[], forbidden[] }`  
- Attribution: `acquisition.result_attribution.record_result_attribution_from_routing`  
- **Forbidden:** Forms creating Outcome / KPI / campaign routing decisions

---

## Events (Sprint 1 stability)

| Event | Stability | Notes |
|-------|-----------|-------|
| `form.submission_received` | Experimental | Emitted by intake path today; formal event bus wiring may follow |
| `form.published` | Experimental | Bridge treats active `TenantLeadForm` as published; formal version publish later |

Sprint 1 **does not** require a new event bus.

---

## Invariants

1. HostFlow Public Form **is-a** Endpoint; Campaign binds Endpoint, not Form internals.  
2. Submission anchors published surface identity (`publication_id` / form id); later edits do not rewrite past submission anchors (version pin intent — full FormVersion later).  
3. First entry uses Universal Routing once; continuation inherits attribution (ADR-024).  
4. Forms **never** owns Campaign / Flight / Outcome / KPI tables.  
5. Consumers call **Adapter** ops only — no second Forms stack in Recruitment/Sales.  
6. Builder / schema editor / marketplace remain **out of contract**.

---

## Forbidden consumer paths

- Importing `TenantLeadForm` internals instead of Adapter `publish`/`endpoint`  
- Creating Forms-local routing / attribution / Outcome / KPI engines  
- Calling Builder APIs as Sprint 1 “done”  
- Bypassing Acquisition for campaign↔result links when Acquisition context applies

---

## Adapter binding

| Op | Implementation |
|----|----------------|
| All Sprint 1 ops | `backend/app/forms_platform/adapter.py` (`forms.endpoint_adapter_v1`) |
| Publication resolve | wraps `publication_bridge.resolve_forms_platform_publication` |
| Handler registry | `forms_platform.handlers` |
| Compose Acquisition | `acquisition.binding_service` · `submission_routing` · `result_attribution` |

HTTP read surface (unchanged C4): `GET /api/v1/platform/forms/publications/resolve`, `GET /api/v1/platform/forms/handlers`.

---

## Contract tests

- E2E: `backend/tests/forms_platform/test_forms_sprint1_contract.py`  
- Gates: `backend/tests/forms_platform/test_forms_sprint1_gates.py`  
- Regression: `backend/tests/forms_platform/test_forms_platform_c4.py`

---

## Compose Acquisition (not copy)

```text
Forms.publish → Forms.endpoint
       ↓
Acquisition.bind Form as Endpoint specialization (Stage 3B)
       ↓
Forms.submission (intake surface) → Universal Routing (3C)
       ↓
Decision → Result → Acquisition.attribution / Outcome / KPI (3D)
```

Forms Sprint 1 stops at **Adapter + contract proof** of this compose path. Outcome/KPI remain Acquisition-owned.

---

## History

- 2026-07-18: Introduced as Forms Sprint 1 Public Contract after Epic P DoD.
