# Threat Model — Forms Platform (C2 identity + C3 Builder + C4 Runtime + C5 Execution)

## Assets

- Frozen `FormPublicationVersion` ledger rows (`form_publication_versions`): `field_schema` + Contract Identity  
- **Runtime Model** (`forms.runtime.model.v1`) — read-only projection of a frozen publication  
- Mutable `FormDefinition` / Draft (`form_builder_drafts` + `TenantLeadForm` pointer — not a publication)  
- Authenticated Builder HTTP (`/api/v1/platform/forms/builder/...` draft GET/PUT/archive)  
- Authenticated resolve DTO (`GET /api/v1/platform/forms/publications/resolve`)  
- **Form Execution** (`forms_platform/execution/`) — validate / pin / persist against Runtime Model only  
- Submission pin to a publication version (`FormSubmission` / envelope)  
- Contract Identity tuple: `contract_id`, `manifest_version`, `public_contract_version`, `object_kind`, `schema_hash`, `adapter_version`

Public anonymous intake tokens remain in [`public-links.md`](./public-links.md). This model covers the **platform capability** surface: identity on a frozen publication version (C2), FormDefinition ↔ Draft only in Builder (C3), Form Runtime serving **Runtime Model** only (C4), and Form Execution binding submit to that model (C5). Not Builder canvas UX, not Publish UI, not Themes / Analytics.

## Trust boundaries

- Authenticated tenant operator → platform Forms APIs (JWT + `X-Tenant-Id` + RLS via `get_db_with_tenant`)  
- Adapter (`forms.endpoint_adapter_v1`) is the only consumer contract for publish / resolve / submission; modules must not read ledger internals  
- Builder (`forms_platform/builder/` and Builder HTTP) mutates **only** `FormDefinition` ↔ Draft  
- Runtime (`forms_platform/runtime/`) is **read-only**: Adapter resolve DTO in → Runtime Model out. It does not look up publications.  
- Execution (`forms_platform/execution/`) consumes **Runtime Model only** → Validation → Submission pin → Shared Intake envelope persist. It does not import Builder or Adapter publish.  
- Builder ↛ Runtime ↛ Builder; Builder ↛ Execution; Runtime ↛ Execution imports (Runtime does not know submit)  
- Draft / FormDefinition is **not** a publication and must not be treated as one  
- `lifecycle_status` is Publication State (mutable); it is **not** Contract Identity  
- Public intake path is a separate trust boundary (anonymous); resolve HTTP here is authenticated  
- C5 does **not** add a second Forms submit HTTP — write path remains `/api/v1/public/intake`

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| FP-1 | Cross-tenant publication leak | Resolve by `form_id` / `public_slug` / `version` without tenant bind |
| FP-2 | Forged Contract Identity | Client-supplied identity on resolve/submit without ledger check |
| FP-3 | Frozen schema rewrite | PATCH of `field_schema` / `schema_hash` / identity on an existing ledger row |
| FP-4 | Draft as publication | Serving a live Builder draft as a frozen version (missing identity, mutable schema) |
| FP-5 | Submission against the wrong version | Pin omitted, archived version accepted, or validation against live draft schema |
| FP-6 | Version pin IDOR | `version=` of another form / tenant accepted as “the” publication |
| FP-7 | Integrity wash on backfill | `unknown` / `legacy but accepted` identity for old snapshots |
| FP-8 | Extra-contract answers | Adapter accepts keys absent from that version’s frozen schema |
| FP-9 | Undeclared compatibility mix | Manifest vN + Public Contract vM + Adapter vK with no closed-set row |
| FP-10 | Confusion with public intake | Treating authenticated resolve identity as a public-link token / vice versa |
| FP-11 | Editor fused to runtime | Builder save calls Adapter `publish` / `commit_publish` / `resolve_publication` |
| FP-12 | Identity leak onto Draft | Draft payload or Builder session writes `contract_identity` / `schema_hash` |
| FP-13 | Unknown Catalog accepted | Builder persists a component id/version not in frozen Catalog v1 |
| FP-14 | Runtime fused to Builder | Runtime imports `forms_platform.builder` / reads Draft / FormDefinition |
| FP-15 | Second resolve engine | Runtime looks up publications (Adapter / ledger / Manifest) instead of consuming resolve DTO |
| FP-16 | Runtime mutation | `serve` publishes, saves drafts, re-mints identity, or accepts submission |
| FP-17 | Builder fused to Runtime Model | Builder imports `forms_platform.runtime` / `RuntimeModel` |
| FP-18 | Execution fused to Builder / draft | Execution validates against Draft / FormDefinition / ledger row without Runtime Model |
| FP-19 | Second Forms submit engine | New public Forms submit HTTP beside Shared Intake |
| FP-20 | Identity re-mint on execute | `freeze_contract_identity` during Execution |

## Митигации

- HTTP resolve goes through Adapter `resolve_publication` (not bridge-only). Frozen versions return ledger identity; drafts stay identity-less.  
- Identity is computed at freeze (RFC 8785 JCS + SHA-256 of `field_schema`) and re-checked on resolve / submit. Mismatch → `forms_schema_hash_mismatch`.  
- `replace_publication_snapshot` is forbidden after freeze; schema change = new ledger row.  
- Submit requires a Runtime Model + complete identity; archived / inactive refuses new submissions.  
- Backfill reconstructs identity **provably** from frozen schema + sealed C1 lineage, or fail-close (`forms_contract_identity_unreconstructable`). No unknown/legacy-accepted.  
- Compatibility is a Forms-owned closed tuple set (`forms_platform/compatibility.py`); undeclared mixes fail.  
- Tenant: `_ensure_tenant` + `get_db_with_tenant`; publication and draft lookup are tenant-scoped.  
- Builder package does not import Adapter / publication ledger / Contract Identity / **Runtime** / **Execution**. HTTP draft save goes through `save_session_async` (Draft only). Dirty and Saved remain mutable.  
- Runtime package does not import Builder / Adapter / ledger / Manifest / submission / Execution. `serve(publication)` is read-only; missing identity or authoring payload → fail-closed (`forms_contract_identity_incomplete` / `forms_runtime_not_publication`).  
- Execution package does not import Builder / Adapter publish / Manifest. Validate + persist require `RuntimeModel`; `freeze_contract_identity` forbidden on execute; public path stays `/api/v1/public/intake`.  
- Unknown Catalog component fails closed (`validation_error`); no draft row is written.  
- Named CI: Manifest / Public Contract / Adapter / Contract Identity / **C3 Builder Runtime** / **C4 Form Runtime** / **C5 Form Execution** gates. Full-repo pytest red does not waive them.

## Тесты

- `backend/tests/forms_platform/test_forms_c2_manifest_gate.py`  
- `backend/tests/forms_platform/test_forms_c2_public_contract_gate.py`  
- `backend/tests/forms_platform/test_forms_c2_adapter_gate.py`  
- `backend/tests/forms_platform/test_forms_c2_identity_gate.py`  
- `backend/tests/forms_platform/test_forms_c3_builder_runtime_gate.py`  
- `backend/tests/forms_platform/test_forms_c4_form_runtime_gate.py`  
- `backend/tests/forms_platform/test_forms_c5_form_execution_gate.py`  
- `backend/tests/forms_platform/test_forms_platform_c4.py` (HTTP resolve: identity on frozen version; draft `contract_identity is None`; unknown `version` → 404) — historical Sprint HTTP; **not** the C4 Form Runtime Gate

## Связанные спеки

- [`docs/specs/tasks/forms-platform-c2-runtime-contract.md`](../../specs/tasks/forms-platform-c2-runtime-contract.md)  
- [`docs/specs/tasks/forms-platform-c3-builder-runtime.md`](../../specs/tasks/forms-platform-c3-builder-runtime.md)  
- [`docs/specs/tasks/forms-platform-c4-form-runtime.md`](../../specs/tasks/forms-platform-c4-form-runtime.md)  
- [`docs/specs/tasks/forms-platform-c5-form-execution.md`](../../specs/tasks/forms-platform-c5-form-execution.md)  
- [`docs/specs/architecture/forms-public-contract.md`](../../specs/architecture/forms-public-contract.md)  
- [`docs/specs/architecture/ADR-007-forms-platform-capability.md`](../../specs/architecture/ADR-007-forms-platform-capability.md)  
- [`docs/security/threat-models/public-links.md`](./public-links.md)
