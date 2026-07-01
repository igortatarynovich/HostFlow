# REF-4 Phase 2 HR Slice Gate

Status: execution-gate (PASS_WITH_BASELINE_NOTE)  
Date: 2026-05-28  
Slice: `HR` (`REF-4.P2.1`)

Related:
- `docs/specs/gates/ref4_phase2_start_gate.md`
- `docs/specs/gates/ref4_phase2_module_rollout_plan.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Scope

Allowed:
1. migrate HR reference reads to `ReferenceServiceFacade` contracts;
2. remove/replace direct reference access paths in HR runtime;
3. keep behavior stable (no workflow feature expansion).

Blocked:
1. HR workflow redesign;
2. policy decision rewrite;
3. UI changes;
4. consumer rollout outside HR slice.

## 2. Required Target Scan

Command:

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend.app.constants|from backend.app.reference|raw config|document_reference_sync" \
  backend/app/services/hr_*.py backend/app/services/workforce_hr_*.py
```

Expected:
1. identify direct-access candidates for HR slice remediation;
2. classify each hit as `must-fix`, `temporary`, or `allowed`.

## 3. Required Target Tests

Command baseline:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_hr_*.py
```

Expectation:
1. no guard regression;
2. no contract regression;
3. HR targeted tests remain green after each remediation diff.

## 4. PASS Criteria

1. HR slice reference reads routed through facade contracts only;
2. no new direct-access regressions in guard scan;
3. exceptions registry updated for any temporary deviations;
4. targeted tests and scans green.

## 5. STOP Criteria

1. new direct import/reference bypass appears in HR scope;
2. rollout diff introduces workflow behavior changes;
3. unresolved `CRITICAL` violation remains in HR slice;
4. temporary exception added without owner + milestone.

## 6. Current Execution State

1. target scan: completed (no reference-layer direct-access blockers detected);
2. targeted test pack: `69 passed`, `1 failed`;
3. failing test classified as pre-existing HR baseline (out of current boundary-remediation scope);
4. gate state: `PASS_WITH_BASELINE_NOTE`.
