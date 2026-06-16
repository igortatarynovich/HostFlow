# Integrations Module Test Boundary

Status: baseline-established  
Date: 2026-05-29

## Mandatory Boundary Test Types

1. import-boundary scans for integration entrypoints;
2. canonicalization compatibility tests (inbound country/citizenship normalization);
3. delivery-contract compatibility checks (`document_hub_delivery_contract`);
4. regression tests ensuring boundary diffs do not change intake/lead/telegram behavior unexpectedly.

## Focused Boundary Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/modules/test_meta_form_field_mapping.py
```

## Optional Extended Integrations Pack

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/api/test_public_intake.py \
  backend/tests/api/admin/test_meta_leads.py
```

## PASS Criteria

1. no direct module-internal cross-domain imports in integrations entrypoints;
2. external payloads are canonicalized before runtime handoff;
3. contract-based document access remains enforced;
4. targeted tests/scans are green or baseline-note stable.

## STOP Criteria

1. direct module import bypass reappears in integrations paths;
2. raw/local reference normalization bypass appears in ingress paths;
3. boundary regressions appear without gate/exception decision.
