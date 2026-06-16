# Workforce Module Test Boundary

Status: baseline-established  
Date: 2026-05-29

## Mandatory Boundary Test Types

1. import-boundary tests for workforce consumer paths;
2. contract compatibility tests for:
   - `workforce_eligibility_delivery_contract`
   - `document_hub_delivery_contract`
   - `ReferenceServiceFacade` interactions;
3. workforce regression tests ensuring boundary changes do not alter operational behavior unexpectedly;
4. guard scans for direct cross-module bypass patterns.

## Focused Boundary Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_workforce_*.py \
  backend/tests/services/test_hr_*.py
```

## PASS Criteria

1. no direct `modules.documents.*` imports in workforce consumer boundaries;
2. no direct `workforce_eligibility_resolver` dependency in workforce consumer boundaries;
3. cross-domain reads occur through approved delivery/facade contracts only;
4. targeted tests/scans are green or baseline-note stable.

## STOP Criteria

1. direct cross-module bypass reappears in workforce consumers;
2. boundary diff mixes in workflow redesign outside scope;
3. regressions occur without baseline/exception decision.
