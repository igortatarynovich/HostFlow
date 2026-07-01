# REF-4 Phase 2 Recruitment Slice Gate

Status: execution-gate (PASS_WITH_BASELINE_NOTE)  
Date: 2026-05-28  
Slice: `Recruitment` (`REF-4.P2.2`)

Related:
- `docs/specs/gates/ref4_phase2_module_rollout_plan.md`
- `docs/specs/gates/ref4_phase2_hr_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Scope

Allowed:
1. migrate recruitment reference reads to facade contracts;
2. remove recruitment direct-access paths to reference internals;
3. preserve recruitment workflow behavior.

Blocked:
1. recruitment workflow redesign;
2. UI behavior changes;
3. cross-module rollout beyond recruitment scope.

## 2. Required Target Scan

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend.app.constants|from backend.app.reference|raw config|document_reference_sync" \
  backend/app/services/recruitment_*.py backend/app/api/v1/candidates/*.py backend/app/services/lead_*.py
```

## 3. Required Target Tests

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_recruitment_*.py
```

## 4. PASS Criteria

1. recruitment reference access is facade-only;
2. no new direct-access regressions in recruitment slice;
3. registry updated for temporary deviations;
4. targeted tests/scan are green or have explicit baseline note.

## 5. STOP Criteria

1. direct reference/config bypass appears in recruitment scope;
2. workflow behavior changes are bundled with boundary remediation;
3. temporary exception added without owner + milestone.

## 6. Current Execution State

1. target scan: completed;
2. blocker-1 (`candidates/router.py` direct `modules.documents` import): remediated via delivery-contract adapter;
3. blocker-2 (`candidates/service.py` direct workforce eligibility dependency): remediated via `workforce_eligibility_delivery_contract`;
4. targeted tests: `52 passed`, `4 failed` (baseline unchanged);
5. gate state: `PASS_WITH_BASELINE_NOTE`.
