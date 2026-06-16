# Recruitment Module Test Boundary

Status: baseline-established  
Date: 2026-05-29

## Mandatory Boundary Tests

1. import-boundary checks for recruitment entrypoints;
2. delivery-contract compatibility checks (documents + workforce eligibility contracts);
3. recruitment regression checks ensuring boundary diffs do not alter workflow behavior;
4. guard scans for direct module-internal bypass patterns.

## Focused Boundary Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_recruitment_*.py
```

## Optional Cross-Slice Contract Check

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/modules/test_meta_form_field_mapping.py
```

## PASS Criteria

1. no direct cross-module recruitment access to documents/workforce internals;
2. recruitment uses approved delivery contracts for cross-domain data;
3. targeted scans show no new boundary violations;
4. failures, if any, are baseline-noted and unchanged by boundary diff.

## STOP Criteria

1. direct `modules.documents.*` or direct `workforce_eligibility_resolver` dependency reappears in recruitment consumer paths;
2. contract bypass introduced without registry update;
3. boundary test regressions without baseline decision.
