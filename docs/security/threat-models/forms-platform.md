# Threat Model — Forms Platform (C2 Contract Identity)

## Assets

- Frozen `FormPublicationVersion` ledger rows (`form_publication_versions`): `field_schema` + Contract Identity  
- Mutable Form definition / draft (`TenantLeadForm` bridge — not a publication)  
- Authenticated resolve DTO (`GET /api/v1/platform/forms/publications/resolve`)  
- Submission pin to a publication version (`FormSubmission` / envelope)  
- Contract Identity tuple: `contract_id`, `manifest_version`, `public_contract_version`, `object_kind`, `schema_hash`, `adapter_version`

Public anonymous intake tokens remain in [`public-links.md`](./public-links.md). This model covers the **platform capability** surface after C2: identity on a frozen publication version, not Builder UX.

## Trust boundaries

- Authenticated tenant operator → platform Forms APIs (JWT + `X-Tenant-Id` + RLS via `get_db_with_tenant`)  
- Adapter (`forms.endpoint_adapter_v1`) is the only consumer contract; modules must not read ledger internals  
- Draft / FormDefinition is **not** a publication and must not be treated as one  
- `lifecycle_status` is Publication State (mutable); it is **not** Contract Identity  
- Public intake path is a separate trust boundary (anonymous); resolve HTTP here is authenticated

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

## Митигации

- HTTP resolve goes through Adapter `resolve_publication` (not bridge-only). Frozen versions return ledger identity; drafts stay identity-less.  
- Identity is computed at freeze (RFC 8785 JCS + SHA-256 of `field_schema`) and re-checked on resolve / submit. Mismatch → `forms_schema_hash_mismatch`.  
- `replace_publication_snapshot` is forbidden after freeze; schema change = new ledger row.  
- Submit requires a ledger version + complete identity; archived refuses new submissions.  
- Backfill reconstructs identity **provably** from frozen schema + sealed C1 lineage, or fail-close (`forms_contract_identity_unreconstructable`). No unknown/legacy-accepted.  
- Compatibility is a Forms-owned closed tuple set (`forms_platform/compatibility.py`); undeclared mixes fail.  
- Tenant: `_ensure_tenant` + `get_db_with_tenant`; publication lookup is tenant-scoped.  
- Named CI: Manifest / Public Contract / Adapter / Contract Identity gates. Full-repo pytest red does not waive them.

## Тесты

- `backend/tests/forms_platform/test_forms_c2_manifest_gate.py`  
- `backend/tests/forms_platform/test_forms_c2_public_contract_gate.py`  
- `backend/tests/forms_platform/test_forms_c2_adapter_gate.py`  
- `backend/tests/forms_platform/test_forms_c2_identity_gate.py`  
- `backend/tests/forms_platform/test_forms_platform_c4.py` (HTTP resolve: identity on frozen version; draft `contract_identity is None`; unknown `version` → 404)

## Связанные спеки

- [`docs/specs/tasks/forms-platform-c2-runtime-contract.md`](../../specs/tasks/forms-platform-c2-runtime-contract.md)  
- [`docs/specs/architecture/forms-public-contract.md`](../../specs/architecture/forms-public-contract.md)  
- [`docs/specs/architecture/ADR-007-forms-platform-capability.md`](../../specs/architecture/ADR-007-forms-platform-capability.md)  
- [`docs/security/threat-models/public-links.md`](./public-links.md)
