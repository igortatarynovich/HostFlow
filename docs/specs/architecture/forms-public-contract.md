# Forms Public Contract v1 — Sprint 1 + Sprint 2 hardening

**Status:** canonical · **ACTIVE**  
**Capability id:** `forms`  
**Contract id:** `forms.public_contract.v1`  
**Adapter id:** `forms.endpoint_adapter_v1`  
**Passport:** [`platform-capability-catalog.md`](platform-capability-catalog.md#forms)  
**Tasks:** [`forms-sprint-1.md`](../tasks/forms-sprint-1.md) … [`forms-sprint-6.md`](../tasks/forms-sprint-6.md) ✅ · Product Layer [`forms-product-layer-epic.md`](../tasks/forms-product-layer-epic.md)  
**Normative:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md)

---

## Identity

Forms владеет **HostFlow Form surface** (immutable publish + consent pin + submission entry).  
Универсальный Endpoint / Submission routing envelope / Result attribution / Outcome / KPI — **не** Forms SoT.

Storage bridge: `TenantLeadForm` current pointer (`published_snapshot_v1`) + append-only ledger `form_publication_versions` (Sprint 3).

---

## Public operations

| Op | Stability | Description |
|----|-----------|-------------|
| `resolve` | **Stable** | Idempotent read of publication view (`form_id` or `public_slug`) |
| `publish` | **Stable** | **Mutation:** append ledger row + bump pointer `published_version` + freeze current snapshot + pin consent; optional `idempotency_key` |
| `validate_submission` / `normalize_answers` | **Stable** | Validate + canonicalize → `forms.normalized_answers.v1` (raw/normalized + intake_handoff) |
| `list_versions` / `get_version` | **Stable** | Audit/read historical ledger rows (immutable) |
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
| `forms_publication_version_not_found` | 404 | Unknown ledger version |
| `forms_publication_version_pinned` | 409 | Delete/mutate version with submission pins or current pointer |
| `forms_submission_validation_failed` | 422 | Field schema validation failed (unknown/required/type) |
| `forms_unknown_field` | 422 | Field not in frozen schema |
| `forms_required_field_missing` | 422 | Required field empty |
| `forms_field_type_invalid` | 422 | Value failed type check |

### Inputs / outputs (summary)

**`resolve`** — In: `tenant_id` + `form_id` XOR `public_slug`; optional `require_active`. Out: publication DTO including `published_version`, `lifecycle_status`, `consent_pin`, `has_immutable_snapshot`.

**`publish` (`commit_publish`)** — In: `tenant_id`, `form_id`, optional consent versions, optional `field_schema` / `fields` / `presentation_runtime`. Out: publication DTO at new version with frozen `field_schema` when provided. Does **not** edit prior snapshot in place.

**`validate_submission`** — In: frozen schema + payload. Out: `forms.normalized_answers.v1` with `raw_values`, `normalized_values`, `errors[{field_id,code,message_key,message}]`, `published_version`, `form_id`, `intake_handoff` for Shared Intake. Pre-schema snapshots skip unknown rejection.

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
2. Published snapshot is **immutable** per version. `published_snapshot_v1` is the **current pointer** only; history is `form_publication_versions` (append-only). New publish → new ledger row + new pointer version. Frozen `field_schema` (Sprint 4) is part of that immutable snapshot.  
3. Submission must match pinned `published_version` (+ consent pin when required) and may register a ledger **submission pin** (blocks delete). When `forms.field_schema.v1` is present, validate against **that version's** schema only.  
4. First entry uses Universal Routing once; continuation inherits attribution (ADR-024).  
5. Forms **never** owns Campaign / Flight / Outcome / KPI tables.  
6. Consumers call **Adapter** ops only.  
7. Product Layer Builder remains **LOCKED** until Field Catalog (P1); when unlocked, Builder still **must not invent field types**.

---

## Field Catalog SoT (Product Layer rule)

**Normative** ([`forms-product-layer-epic.md`](../tasks/forms-product-layer-epic.md) · P1 [`forms-product-p1-field-catalog.md`](../tasks/forms-product-p1-field-catalog.md)):

- **Field Catalog** is a **component registry** (SoT): type identity, properties, config schema, validation, normalization, **storage contract**, Builder palette, Public Form render.
- Each component has stable `component_id` + `component_version` (stronger than a bare type string).
- **P1.1 Registry** (`forms.field_catalog.registry.v1`): platform-wide register/get/find/resolve_compatible; semver major/minor/patch; no major auto-jump ([`forms-product-p1-1-registry.md`](../tasks/forms-product-p1-1-registry.md)).
- **Builder** is a Catalog **client** (not owner): composition only; same components may serve forms, entity cards, CRM, mobile.
- P1 lands as **P1.1 Registry → P1.2 Descriptors → P1.3 Standard library → P1.4 Extension API**.
- Published `forms.field_schema.v1` fields must resolve to Catalog components (enforced when Catalog ships).
- Gaps discovered during Builder work → surgical platform extension; **no** rewrite of Sprint 1–6 contour.

---

## Forbidden consumer paths

- Importing `TenantLeadForm` internals instead of Adapter  
- Editing a published snapshot in place  
- Creating Forms-local routing / attribution / Outcome / KPI engines  
- Calling Builder APIs that invent field types outside Field Catalog  
- Bypassing Acquisition for campaign↔result links when Acquisition context applies  
- Duplicating Shared Intake
- Rewriting Sprint 1–6 storage/validation contracts as a parallel stack

---

## Adapter binding

| Op | Implementation |
|----|----------------|
| resolve / publish / activate / deactivate / endpoint / submission / result | `backend/app/forms_platform/adapter.py` |
| Publication view | `publication_bridge.py` |
| Errors | `forms_platform/errors.py` |
| Snapshot columns | migration `202607180007_forms_s2` (current pointer) |
| Version ledger | migration `202607180008_forms_s3` · `publication_versions.py` |
| Field schema / validation | `schema.py` · `validation.py` (`forms.field_schema.v1`) |
| Normalized answers | `answers.py` (`forms.normalized_answers.v1`) → Shared Intake handoff |
| Submission envelope | `submission_envelope.py` · migration `202607180009_forms_s6` |
| Field Catalog registry (P1.1) | `field_catalog/` · `forms.field_catalog.registry.v1` |
| Compose Acquisition | binding · routing · attribution (unchanged ownership) |

HTTP read surface: `GET /api/v1/platform/forms/publications/resolve`, `GET /api/v1/platform/forms/handlers`.

---

## Contract tests

- Sprint 1: `test_forms_sprint1_contract.py` · `test_forms_sprint1_gates.py`  
- Sprint 2: `test_forms_sprint2_contract.py` · `test_forms_sprint2_gates.py`  
- Sprint 3: `test_forms_sprint3_contract.py` · `test_forms_sprint3_gates.py`  
- Sprint 4: `test_forms_sprint4_contract.py` · `test_forms_sprint4_gates.py`  
- Sprint 5: `test_forms_sprint5_contract.py` · `test_forms_sprint5_gates.py`  
- Sprint 6: `test_forms_sprint6_contract.py` · `test_forms_sprint6_gates.py`  
- P1.1: `test_forms_p1_1_registry_contract.py` · `test_forms_p1_1_registry_gates.py`  
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
- 2026-07-18: Sprint 2 COMPLETE (PR #37).  
- 2026-07-18: Sprint 3 — append-only `form_publication_versions` ledger; `published_snapshot_v1` clarified as current pointer.  
- 2026-07-18: Sprint 3 COMPLETE (PR #38).  
- 2026-07-18: Sprint 4 — `forms.field_schema.v1` frozen in snapshot; `validate_submission` runtime (no Builder).  
- 2026-07-18: Sprint 4 COMPLETE (PR #39).  
- 2026-07-18: Sprint 5 — `forms.normalized_answers.v1` (raw/normalized + Shared Intake handoff).  
- 2026-07-18: Sprint 5 COMPLETE (PR #40).  
- 2026-07-18: Sprint 6 — append-only `form_submission_envelopes` persistence.  
- 2026-07-18: Sprint 6 COMPLETE (PR #41) — Submission Envelope Contract ACTIVE; Builder LOCKED.  
- 2026-07-18: Product Layer epic — Field Catalog SoT; Builder must not invent types.  
- 2026-07-18: Product Layer ACTIVE (`29f4057f`); P1 = component registry (id/version/config/validation/normalization/storage/renderers).  
- 2026-07-18: P1.1–P1.4 plan; Builder = thin Field Catalog client (not owner).  
- 2026-07-18: P1.1 Registry implementation — `forms.field_catalog.registry.v1`.
