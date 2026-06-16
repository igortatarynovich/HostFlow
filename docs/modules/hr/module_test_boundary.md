# HR Module Test Boundary

Status: baseline-established  
Date: 2026-05-29

## Mandatory Boundary Test Types

1. import-boundary scans for HR services;
2. facade compatibility tests (`ReferenceServiceFacade`);
3. delivery contract compatibility tests (`document_hub_delivery_contract` / relevant workforce delivery contracts);
4. HR regression tests to ensure boundary diffs do not alter HR workflow behavior.

## Focused Boundary Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_hr_*.py
```

## Additional Cross-Boundary Sanity Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_workforce_*.py \
  backend/tests/services/test_reference_service_facade.py
```

## PASS Criteria

1. HR uses platform/document/workforce contracts without direct internal bypass;
2. no new direct cross-module imports appear in HR consumer paths;
3. boundary scans remain clean or explicitly baseline-noted;
4. test outcomes remain green or baseline-stable with explicit gate notes.

## STOP Criteria

1. HR introduces direct import bypass to recruitment/documents/workforce internals;
2. HR boundary diff rewrites workflow behavior outside approved scope;
3. boundary regressions appear without exception/gate decision.
