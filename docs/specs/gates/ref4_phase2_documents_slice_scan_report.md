# REF-4 Phase 2 Documents Slice Scan Report

Status: `PASS_WITH_BASELINE_NOTE`  
Date: 2026-05-29  
Slice: `REF-4.P2.4` (`Documents`)

Related:
- `docs/specs/gates/ref4_phase2_documents_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Target Scan

Command:

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|from backend.app.reference|ReferenceServiceFacade|document_type_runtime_resolver|normalize_doc_type|document_categories|passport|visa|residence_permit|legal_status|citizenship|work_country|from backend.app.services.hr_|from backend.app.services.recruitment_|from backend.app.services.workforce_|raw config|dictionary|legacy" \
  backend/app/services/document*.py backend/app/services/hr_document*.py backend/app/modules/documents/*.py backend/app/api/v1/candidate_documents.py
```

## 2. Findings

`Must-fix / boundary gaps`:
1. `backend/app/services/documents.py`  
   blocker-1 fixed in this step: local/raw `doc_types.json` dictionary normalization replaced by canonical document-type contract (`list_canonical_document_type_codes_via_contract`).  
   blocker-2 fixed in this step: raw/string `citizenship` and `work_country` inputs are normalized via `ReferenceServiceFacade` (`normalize_citizenship_alpha2`, `normalize_country_alpha2`).  
   blocker-3 closed as `MODULE_OWNED_POLICY_ISOLATED`: hardcoded applicability logic moved from `documents.py` to module-owned policy (`backend/app/services/document_applicability_policy.py`) with canonical normalized inputs preserved.

`Allowed baseline hits`:
1. legacy markers/comments (`legacy_*`) in modules/documents and storage are baseline compatibility artifacts;
2. `normalize_doc_type` usage in document catalog/crud/router is expected canonical normalization path and not a blocker by itself.
3. known cross-domain coupling markers in documents API/module layer are tracked as baseline notes for subsequent slice-level cleanup and are out of this blocker diff scope.

## 3. Facade Adoption Gaps

1. documents applicability behavior is now isolated as module-owned policy and consumes canonical inputs;
2. some module endpoints still couple to non-documents domains directly (recruitment/handoff guard coupling baseline note);
3. duplicate normalization surfaces exist across documents services/modules with mixed legacy assumptions (baseline note).

## 4. Target Test Pack

Command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_document_*.py \
  backend/tests/services/test_hr_review_document_resolution.py
```

Result:
1. `47 passed`
2. `1 failed`

Failed baseline test:
1. `backend/tests/services/test_hr_review_document_resolution.py::test_legal_stay_maps_passport_doc_type`

Baseline note:
1. failure is known from prior slices and unchanged in this documents scan step.

## 5. Blocker-1 Remediation Evidence

Scope:
1. replace local/raw document-type dictionary path only;
2. no document workflow logic changes;
3. no expiry/owner-summary logic changes.

Diff evidence:
1. `backend/app/services/documents.py` removed local `load_config("doc_types.json")` + `by_code` dictionary path;
2. `backend/app/services/documents.py` now consumes canonical contract set via `list_canonical_document_type_codes_via_contract`;
3. `backend/app/services/document_hub_delivery_contract.py` provides canonical document type code set for boundary-safe consumption.

Targeted scan evidence:
1. no `load_config("doc_types.json")` path remains in `backend/app/services/documents.py`;
2. canonical contract call present and used for `ensure_doc` gating.

## 6. Blocker-2 Remediation Evidence

Scope:
1. replace raw `citizenship`/`work_country` string assumptions only;
2. keep applicability decisions inside Documents module;
3. no document workflow/required-doc behavior changes.

Diff evidence:
1. `backend/app/services/documents.py` now normalizes citizenship via `ReferenceServiceFacade.normalize_citizenship_alpha2(...)`;
2. `backend/app/services/documents.py` now normalizes work country via `ReferenceServiceFacade.normalize_country_alpha2(...)`;
3. `backend/app/services/reference_service_facade.py` exposes normalization helpers as reference boundary contract.

Targeted scan evidence:
1. no direct `.upper()`-based raw normalization path remains for `citizenship` and `work_country` in `auto_apply_rules`;
2. module logic still performs applicability decisions locally (expected for this blocker scope).

## 7. Blocker-3 Remediation Evidence

Scope:
1. isolate hardcoded applicability logic as module-owned policy;
2. keep applicability behavior in Documents module;
3. no system/reference migration of module business rules.

Diff evidence:
1. added `backend/app/services/document_applicability_policy.py` with module-owned policy contract;
2. `backend/app/services/documents.py` now calls policy using canonical normalized inputs;
3. behavior remains unchanged (`work_permit_type`, `visa_required`, `driver attestation` outputs preserved).

Targeted test evidence:
1. `backend/tests/services/test_document_applicability_policy.py` verifies legacy behavior parity;
2. policy source guard verifies no `backend.app.reference` or `ReferenceServiceFacade` import inside module-owned policy file.

## 8. Gate Decision

Decision: `PASS_WITH_BASELINE_NOTE`

Reason:
1. blocker-1 (`local/raw doc_types`) is remediated;
2. blocker-2 (`raw citizenship/work_country assumptions`) is remediated;
3. blocker-3 (`hardcoded applicability logic`) is closed as `MODULE_OWNED_POLICY_ISOLATED` with behavior preserved in module layer;
4. targeted tests are stable with pre-existing baseline failure only.

## 9. Invariant Enforcement Note

1. confirmed invariant for this slice: system/reference remains contract-only;
2. module-owned business rules stay in module layer;
3. promotion of module rules into system/reference is forbidden unless reused by at least two independent modules or required as a cross-module contract.
