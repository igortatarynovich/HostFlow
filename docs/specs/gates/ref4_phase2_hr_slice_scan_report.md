# REF-4 Phase 2 HR Slice Scan Report

Status: `PASS_WITH_BASELINE_NOTE`  
Date: 2026-05-28  
Slice: `REF-4.P2.1` (`HR`)

Related:
- `docs/specs/gates/ref4_phase2_hr_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Scan Scope

Files:
1. `backend/app/services/hr_*.py`
2. `backend/app/services/workforce_hr_*.py`

Patterns:
1. `reference_foundation`
2. `operational_risk_reference`
3. `workforce_operational_taxonomy`
4. `from backend.app.constants`
5. `from backend.app.reference`
6. `raw config`
7. `document_reference_sync`

## 2. Scan Command

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend.app.constants|from backend.app.reference|raw config|document_reference_sync" \
  backend/app/services/hr_*.py backend/app/services/workforce_hr_*.py
```

## 3. Findings

Raw hits:
1. `backend/app/services/hr_operational_risk.py:16` → `from backend.app.constants.hr_task_types import HR_TASK_TYPES`
2. `backend/app/services/hr_dashboard.py:11` → `from backend.app.constants.hr_task_types import HR_TASK_TYPES`

Classification:
1. `must-fix before slice PASS`: none
2. `temporary allowed`: none
3. `allowed platform access`: `hr_task_types` constants import (not reference-layer/config/policy bypass)

## 4. Target Tests

Command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_hr_*.py
```

Result:
1. `69 passed`
2. `1 failed`

Failed test:
1. `backend/tests/services/test_hr_review_document_resolution.py::test_legal_stay_maps_passport_doc_type`
2. Assertion mismatch: expected `passport` in `DOC_KEY_CANDIDATE_TYPES["Legal stay"]`.

## 5. Gate Decision

Current decision: `PASS_WITH_BASELINE_NOTE`

Baseline note:
1. failing test `backend/tests/services/test_hr_review_document_resolution.py::test_legal_stay_maps_passport_doc_type` is pre-existing branch baseline;
2. provenance indicates pre-existing HR review/document mapping behavior (historical commit lineage), not introduced by current HR slice gate activities;
3. no direct-access boundary violation detected in HR slice scope.

Residual risk:
1. HR test baseline remains with `1 failed` in targeted pack and should be addressed in dedicated HR behavior stream, separate from Phase 2 boundary rollout.
