# REF-4 Phase 2 Integrations Slice Gate

Status: execution-gate (`PASS_WITH_BASELINE_NOTE`)  
Date: 2026-05-29  
Slice: `Integrations` (`REF-4.P2.5`)

Related:
- `docs/specs/gates/ref4_phase2_module_rollout_plan.md`
- `docs/specs/gates/ref4_phase2_documents_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Scope

Allowed:
1. reference adoption through facade/delivery contracts only;
2. canonical normalization/mapping for external intake payloads (Meta/forms/webhooks);
3. boundary cleanup for direct-access paths in integration entrypoints.

Blocked:
1. recruitment/hr/workforce workflow behavior changes;
2. document decision/eligibility behavior rewrites;
3. UI/admin changes;
4. cross-slice rollout beyond integrations scope.

## 2. Required Target Scan

```bash
cd /opt/HostFlow && rg -n \
  "normalize|mapping|meta|webhook|intake|country|citizenship|document_type|ReferenceServiceFacade|from backend.app.modules|from backend.app.services\\.(hr_|recruitment_|workforce_)|dictionary|legacy|load_config\\(" \
  backend/app/api/public/intake.py \
  backend/app/api/v1/communications/_helpers/telegram_intake/*.py \
  backend/app/modules/leads/*.py \
  backend/app/modules/leads/service/*.py \
  backend/app/services/*intake*.py \
  backend/app/services/*lead*.py
```

## 3. Required Target Tests

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/modules/test_meta_form_field_mapping.py \
  backend/tests/api/test_public_intake.py \
  backend/tests/api/admin/test_meta_leads.py
```

## 4. PASS Criteria

1. external payloads are normalized/mapped into canonical reference language before runtime module handoff;
2. no direct reference-layer bypass in integrations paths;
3. no direct cross-module internal access without approved delivery/facade contract;
4. local mapping helpers are either module-owned and scoped or moved behind canonical contracts;
5. targeted scan is clean for blocker patterns or baseline-noted with owner/milestone;
6. targeted tests are green or baseline-note stable.

## 5. STOP Criteria

1. unresolved direct-access blocker remains in integrations entrypoints;
2. payload normalization still relies on raw/local reference dictionaries without canonical boundary;
3. remediation diff changes runtime module behavior instead of boundary adoption;
4. temporary exception has no owner + milestone;
5. targeted tests regress due to remediation diff.

## 6. Current Execution State

1. target scan: completed;
2. blocker-1 (`direct imports backend.app.modules.documents.*`) remediated via `document_hub_delivery_contract`;
3. blocker-2 (`raw citizenship/country handling`) remediated via integration-level inbound normalizer backed by `ReferenceServiceFacade`;
4. blocker-3 (`duplicate normalization surfaces`) remediated via unified integration inbound normalizer adoption in leads ingest paths;
5. focused targeted rerun: `20 passed`;
6. gate state: `PASS_WITH_BASELINE_NOTE` (full integrations target pack follow-up remains baseline note).
