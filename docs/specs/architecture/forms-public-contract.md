# Forms Public Contract v1 — Sprint 1 + Sprint 2 hardening

**Status:** canonical · **ACTIVE**  
**Capability id:** `forms`  
**Contract id:** `forms.public_contract.v1`  
**Adapter id:** `forms.endpoint_adapter_v1`  
**Passport:** [`platform-capability-catalog.md`](platform-capability-catalog.md#forms)  
**Tasks:** [`forms-sprint-1.md`](../tasks/forms-sprint-1.md) ✅ · [`forms-sprint-2.md`](../tasks/forms-sprint-2.md)  
**Normative:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md)

---

## Identity

Forms владеет **HostFlow Form surface** (immutable publish + consent pin + submission entry).  
Универсальный Endpoint / Submission routing envelope / Result attribution / Outcome / KPI — **не** Forms SoT.

Storage bridge: `TenantLeadForm` + `published_snapshot_v1` via C4 publication bridge until FormTemplate migration.

---

## Public operations

| Op | Stability | Description |
|----|-----------|-------------|
| `resolve` | **Stable** | Idempotent read of publication view (`form_id` or `public_slug`) |
| `publish` | **Stable** | **Mutation:** bump `published_version`, freeze `published_snapshot_v1`, pin consent versions, optionally activate |
| `activate` / `deactivate` | **Stable** | Endpoint activation without rewriting published snapshot |
| `endpoint` | **Stable** | Map **active** publication → Endpoint identity (`hostflow_public_form`) |
| `submission` | **Stable** | Submission entry for Shared Intake; requires active endpoint + version pin metadata |
| `result` | **Stable** | Handoff only — compose Acquisition; no Forms Result/Outcome/KPI |

### Error semantics (stable codes)

| Code | HTTP | When |
|------|------|------|
| `forms_publication_not_found` | 404 | Unknown form / wrong tenant |
| `forms_endpoint_inactive` | 409 | `require_active` or endpoint/submission on inactive |
| `forms_publication_archived` | 409 | Archived lifecycle |
| `forms_stale_published_version` | 409 | Client version ≠ pinned `published_version` |
| `forms_publication_key_required` | 422 | Missing `form_id` / `public_slug` |
| `forms_builder_locked` | 403 | Builder surface attempted |

### Inputs / outputs (summary)

**`resolve`** — In: `tenant_id` + `form_id` XOR `public_slug`; optional `require_active`. Out: publication DTO including `published_version`, `lifecycle_status`, `consent_pin`, `has_immutable_snapshot`.

**`publish` (`commit_publish`)** — In: `tenant_id`, `form_id`, optional consent versions. Out: publication DTO at new version. Does **not** edit prior snapshot in place.

**`endpoint` / `submission`** — Reject inactive. Submission gate: `assert_submission_version_compatible`.

**`result`** — Handoff `{ result_owner, acquisition_compose[], forbidden[] }`.

Write path for payloads: `/api/v1/public/intake` + `intake_platform.submission_store` — **not** a second Forms submit engine.

---

## Events

| Event | Stability | Notes |
|-------|-----------|-------|
| `form.published` | Experimental | Emitted conceptually on `commit_publish` (bus wiring later) |
| `form.submission_received` | Experimental | Intake path |

---

## Invariants

1. HostFlow Public Form **is-a** Endpoint; Campaign binds Endpoint, not Form internals.  
2. Published snapshot is **immutable**; new publish → new `published_version`. Live title edits do not rewrite frozen snapshot.  
3. Submission must match pinned `published_version` (+ consent pin when required).  
4. First entry uses Universal Routing once; continuation inherits attribution (ADR-024).  
5. Forms **never** owns Campaign / Flight / Outcome / KPI tables.  
6. Consumers call **Adapter** ops only.  
7. Builder / schema editor / marketplace remain **out of contract**.

---

## Forbidden consumer paths

- Importing `TenantLeadForm` internals instead of Adapter  
- Editing a published snapshot in place  
- Creating Forms-local routing / attribution / Outcome / KPI engines  
- Calling Builder APIs  
- Bypassing Acquisition for campaign↔result links when Acquisition context applies  
- Duplicating Shared Intake

---

## Adapter binding

| Op | Implementation |
|----|----------------|
| resolve / publish / activate / deactivate / endpoint / submission / result | `backend/app/forms_platform/adapter.py` |
| Publication view | `publication_bridge.py` |
| Errors | `forms_platform/errors.py` |
| Snapshot columns | migration `202607180007_forms_s2` |
| Compose Acquisition | binding · routing · attribution (unchanged ownership) |

HTTP read surface: `GET /api/v1/platform/forms/publications/resolve`, `GET /api/v1/platform/forms/handlers`.

---

## Contract tests

- Sprint 1: `test_forms_sprint1_contract.py` · `test_forms_sprint1_gates.py`  
- Sprint 2: `test_forms_sprint2_contract.py` · `test_forms_sprint2_gates.py`  
- C4: `test_forms_platform_c4.py`

---

## Compose Acquisition (not copy)

```text
Forms.publish (immutable) → Forms.endpoint (active)
       ↓
Acquisition.bind Form as Endpoint specialization (Stage 3B)
       ↓
Forms.submission (version-pinned) → Universal Routing (3C)
       ↓
Decision → Result → Acquisition.attribution / Outcome / KPI (3D)
```

---

## History

- 2026-07-18: Sprint 1 Public Contract after Epic P DoD.  
- 2026-07-18: Sprint 1 COMPLETE (PR #36).  
- 2026-07-18: Sprint 2 — resolve/publish split, snapshot, activate/deactivate, error codes, version pin.
