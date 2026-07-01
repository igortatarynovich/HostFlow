# Documents Module Test Boundary

Status: baseline-established  
Date: 2026-05-29

## Mandatory Boundary Test Types

1. import-boundary tests (no forbidden direct imports);
2. regression tests for documents behavior parity during boundary remediation;
3. facade/delivery compatibility tests;
4. guard scans for direct-access patterns.

## Core Test Pack (focused)

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_document_*.py \
  backend/tests/services/test_document_applicability_policy.py
```

## Integration-Facing Focused Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/modules/test_meta_form_field_mapping.py \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py
```

## PASS Criteria

1. no new direct cross-module import in documents consumer boundaries;
2. canonical reference/delivery contract path remains enforced;
3. module-owned applicability policy tests pass;
4. known baseline failures, if any, are explicitly documented in gate/report.

## STOP Criteria

1. new untracked direct-access pattern appears;
2. contract bypass introduced without exception registry update;
3. boundary test regressions without baseline decision.
