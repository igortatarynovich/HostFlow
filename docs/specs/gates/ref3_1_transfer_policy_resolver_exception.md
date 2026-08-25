# REF-3.1 exception: transfer_policy_resolver.py

**Status:** temporary allowlist (integration base)  
**Date:** 2026-07-13  
**Owner:** Platform architecture / Recruitment handoff  
**Removal milestone:** REF-3.4 facade rollout closure (see `ref3_4_facade_rollout_closure_report_2026-05-28.md`)

## Violation

| Field | Value |
|-------|-------|
| Rule | `DIRECT_REFERENCE_MODEL_IMPORT` |
| Path | `backend/app/services/transfer_policy_resolver.py` |
| Snippet | `from backend.app.models.ref_document_type import RefPack, TenantDocumentPackEnablement` |

## Why intentional

`TransferPolicyResolver` is a **tactical runtime aggregator** for Recruitment handoff readiness. It evaluates document pack enablement (`RefPack`, `TenantDocumentPackEnablement`) alongside recruitment package blocks, pipeline overrides, and recruiter confirmations.

Direct ref-model import is **pre-existing integration-base debt**, not introduced by Stage 1A. Equivalent pattern already tracked in baseline for `hr_expected_documents_resolver.py`.

## Why allowlist (not baseline extension)

- File is **infrastructure-adjacent runtime evaluator**, not a new consumer cutover.
- Facade extraction requires `ReferenceServiceFacade` pack-enablement read API — tracked under REF-3.4 rollout, not Stage 1A.
- Allowlist entry is **temporary**; must be removed when facade exposes pack resolution.

## Remediation owner & exit criteria

| Item | Detail |
|------|--------|
| Owner | Platform / Document reference facade team |
| Exit | `TransferPolicyResolver` reads packs via `reference_service_facade.py`; direct `ref_document_type` import removed |
| Verification | `python3 scripts/architecture/check_reference_facade_boundary.py` passes without allowlist entry |

## Related

- [`ref3_1_enforcement_baseline_2026-05-27.md`](ref3_1_enforcement_baseline_2026-05-27.md)
- [`transfer-policy.md`](../workflows/transfer-policy.md) — resolver role
- Allowlist entry: `scripts/architecture/reference_facade_allowlist.txt`
