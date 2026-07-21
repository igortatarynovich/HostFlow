# REF-3.1 exception: document_type_version_assignment_resolver.py

**Status:** temporary allowlist (integration base)  
**Date:** 2026-07-21  
**Owner:** Platform / Document Hub (ADR-018 PR 2B-4)  
**Removal milestone:** REF-3.4 facade rollout — version assignment via `reference_service_facade.py`

## Violation

| Field | Value |
|-------|-------|
| Rule | `DIRECT_REFERENCE_MODEL_IMPORT` |
| Path | `backend/app/services/document_type_version_assignment_resolver.py` |
| Snippet | `from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion` |

## Why intentional

Deterministic **document type version assignment** for ADR-018 migration (PR 2B-4). It evaluates `RefDocumentType` / `RefDocumentTypeVersion` schemas and validity windows against Document facts.

Direct ref-model import is **pre-existing integration-base debt**, unmasked when earlier CI gates (SPA path literals) started passing. Same pattern as other infrastructure-adjacent resolvers on the allowlist.

## Why allowlist (not baseline extension)

- File is a **platform migration resolver**, not a new module consumer cutover.
- Facade extraction needs typed version-assignment reads on `ReferenceServiceFacade` — tracked under REF-3.4, not this CI-unblock slice.
- Allowlist entry is **temporary**; remove when facade exposes version assignment.

## Remediation

| Item | Detail |
|------|--------|
| Owner | Platform / Document reference facade team |
| Exit | Resolver reads types/versions via facade; direct `ref_document_type` import removed |
| Verification | `python3 scripts/architecture/check_reference_facade_boundary.py` passes without this allowlist entry |

## Related

- [`ref3_1_transfer_policy_resolver_exception.md`](ref3_1_transfer_policy_resolver_exception.md)
- Allowlist: `scripts/architecture/reference_facade_allowlist.txt`
