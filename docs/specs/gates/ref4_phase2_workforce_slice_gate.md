# REF-4 Phase 2 Workforce Slice Gate

Status: execution-gate (PASS_WITH_BASELINE_NOTE)  
Date: 2026-05-28  
Slice: `Workforce` (`REF-4.P2.3`)

Related:
- `docs/specs/gates/ref4_phase2_module_rollout_plan.md`
- `docs/specs/gates/ref4_phase2_recruitment_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Scope

Allowed:
1. reference adoption via facade/contracts only;
2. boundary cleanup for direct-access paths;
3. no behavior change in workforce runtime outcomes.

Blocked:
1. workforce workflow changes;
2. eligibility logic rewrite;
3. HR sync behavior changes;
4. UI/admin changes;
5. cross-slice rollout.

## 2. Required Target Scan

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend.app.reference|from backend.app.constants|from backend.app.modules.documents|documents_crud|raw config|status_map|legacy|dictionary|ReferenceServiceFacade|workforce_eligibility_resolver|workforce_eligibility_delivery_contract" \
  backend/app/services/workforce_*.py backend/app/services/hr_*.py backend/app/services/workforce_hr_*.py
```

## 3. Required Target Tests

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_workforce_*.py \
  backend/tests/services/test_hr_*.py
```

## 4. PASS Criteria

1. workforce references are consumed through approved facade/delivery contracts;
2. no direct import bypass for reference/document internals;
3. no cross-domain recruitment/HR shortcut imports added;
4. targeted scan clean for blocker-patterns or tracked via explicit baseline note;
5. targeted tests are green or baseline-note stable.

## 5. STOP Criteria

1. direct reference/documents bypass remains unresolved;
2. diff introduces eligibility/workflow behavior rewrite;
3. temporary exception has no owner/milestone;
4. targeted tests regress due to remediation diff.

## 6. Current Execution State

1. target scan: completed;
2. blocker-1 (`documents_crud` direct imports): remediated via `document_hub_delivery_contract`;
3. blocker-2 (`workforce_eligibility_resolver` direct dependencies): remediated via `workforce_eligibility_delivery_contract`;
4. targeted tests: `86 passed`, `1 failed` (known baseline note, unchanged);
5. gate state: `PASS_WITH_BASELINE_NOTE`.
