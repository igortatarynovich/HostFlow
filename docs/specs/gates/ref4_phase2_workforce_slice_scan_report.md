# REF-4 Phase 2 Workforce Slice Scan Report

Status: `PASS_WITH_BASELINE_NOTE`  
Date: 2026-05-28  
Slice: `REF-4.P2.3` (`Workforce`)

Related:
- `docs/specs/gates/ref4_phase2_workforce_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Target Scan

Command:

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend.app.reference|from backend.app.constants|from backend.app.modules.documents|documents_crud|raw config|status_map|legacy|dictionary|ReferenceServiceFacade|workforce_eligibility_resolver|workforce_eligibility_delivery_contract" \
  backend/app/services/workforce_*.py backend/app/services/hr_*.py backend/app/services/workforce_hr_*.py
```

## 2. Direct-Access Findings

`Must-fix` findings (current):
1. none

`Closed in blocker-1 diff`:
1. `backend/app/services/workforce_hr_operational_context.py` direct `documents_crud` import removed; switched to `document_hub_delivery_contract.list_candidate_documents_via_contract`.
2. `backend/app/services/workforce_hr_review.py` direct `documents_crud` usage removed; switched to `document_hub_delivery_contract.list_candidate_documents_via_contract`.

`Closed in blocker-2 diff`:
1. `backend/app/services/workforce_hr_review.py` switched from direct resolver call to `workforce_eligibility_delivery_contract`.
2. `backend/app/services/workforce_operational_profile.py` switched from direct resolver call to `workforce_eligibility_delivery_contract`.
3. `backend/app/services/workforce_action_policy.py` switched from direct resolver call to `workforce_eligibility_delivery_contract`.
4. targeted scan confirms no direct `workforce_eligibility_resolver` dependencies in Workforce consumer files (excluding resolver and contract implementation files).

`Allowed baseline hits`:
1. `hr_task_types` constants imports in HR services (`hr_operational_risk.py`, `hr_dashboard.py`) remain baseline utility usage.
2. `legacy_*` variable naming/comments in workforce HR review flow are baseline naming artifacts, not standalone boundary violations by themselves.

## 3. Facade/Contract Adoption Gaps

1. Workforce services still use direct document module CRUD in multiple paths.
2. Workforce services use resolver directly instead of `workforce_eligibility_delivery_contract` entrypoint.
3. Partial adoption state: resolver itself already uses `ReferenceServiceFacade`, but consumer boundary still bypasses delivery contract.

## 4. Target Test Pack

Command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_workforce_*.py \
  backend/tests/services/test_hr_*.py
```

Result:
1. `86 passed`
2. `1 failed`

Failed test:
1. `backend/tests/services/test_hr_review_document_resolution.py::test_legal_stay_maps_passport_doc_type`

Baseline note:
1. this failure is already known from previous slices and not introduced by workforce scan step.
2. failure remains unchanged after blocker-1 remediation.

## 5. Gate Decision

Decision: `STOP`

Reason:
1. workforce direct-access blockers for this slice are remediated;
2. targeted pack keeps known baseline failure only (`test_legal_stay_maps_passport_doc_type`), unchanged by remediation diffs.
