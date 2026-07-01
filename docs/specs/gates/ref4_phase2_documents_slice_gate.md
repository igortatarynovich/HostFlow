# REF-4 Phase 2 Documents Slice Gate

Status: execution-gate (`PASS_WITH_BASELINE_NOTE`)  
Date: 2026-05-29  
Slice: `Documents` (`REF-4.P2.4`)

Related:
- `docs/specs/gates/ref4_phase2_module_rollout_plan.md`
- `docs/specs/gates/ref4_phase2_workforce_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Scope

Allowed:
1. reference adoption through facade/delivery contracts only;
2. boundary cleanup for direct-access patterns in documents slice;
3. normalization path alignment to canonical contracts.

Blocked:
1. document workflow behavior rewrite;
2. HR/Recruitment/Workforce logic changes;
3. UI/admin changes;
4. cross-slice rollout beyond documents scope.

## 2. Required Target Scan

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|from backend.app.reference|ReferenceServiceFacade|document_type_runtime_resolver|normalize_doc_type|document_categories|passport|visa|residence_permit|legal_status|citizenship|work_country|from backend.app.services.hr_|from backend.app.services.recruitment_|from backend.app.services.workforce_|raw config|dictionary|legacy" \
  backend/app/services/document*.py backend/app/services/hr_document*.py backend/app/modules/documents/*.py backend/app/api/v1/candidate_documents.py
```

## 3. Required Target Tests

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_document_*.py \
  backend/tests/services/test_hr_review_document_resolution.py
```

## 4. PASS Criteria

1. no direct reference-layer bypass in documents slice;
2. no cross-domain shortcut imports violating boundaries;
3. canonical normalization path is contract-based;
4. targeted scan clean for blocker patterns or explicitly baseline-noted;
5. targeted tests are green or baseline-note stable.
6. module-owned applicability behavior is isolated from `system/reference` promotion unless cross-module contract criteria are met.

## 5. STOP Criteria

1. unresolved direct-access blocker remains;
2. remediation diff alters workflow/runtime behavior;
3. temporary exception has no owner + milestone;
4. targeted tests regress due to remediation.

## 6. Architecture Invariant

1. `System layer` stores shared language and contracts only (`canonical codes`, `field keys`, shared schemas, facade contracts);
2. `Module layer` stores module business behavior (`workflow`, `decisions`, `checklists`, `statuses`, `approvals`, `scoring`);
3. no module-owned business rule may be promoted to `system/reference` unless:
   a) it is reused by at least two independent modules; or
   b) it is required as an explicit cross-module delivery contract.

## 7. Current Execution State

1. target scan: completed;
2. blocker-1 (`local/raw doc type dictionary path`) remediated via canonical delivery contract in `backend/app/services/documents.py`;
3. blocker-2 (`raw citizenship/work_country assumptions`) remediated via `ReferenceServiceFacade` normalization contract in `backend/app/services/documents.py`;
4. blocker-3 (`hardcoded applicability logic`) closed as `MODULE_OWNED_POLICY_ISOLATED` in `backend/app/services/document_applicability_policy.py`;
5. targeted tests: `47 passed`, `1 failed` (known baseline note);
6. gate state: `PASS_WITH_BASELINE_NOTE`.
