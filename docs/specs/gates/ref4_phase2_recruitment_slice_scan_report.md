# REF-4 Phase 2 Recruitment Slice Scan Report

Status: `PASS_WITH_BASELINE_NOTE`  
Date: 2026-05-28  
Slice: `REF-4.P2.2` (`Recruitment`)

Related:
- `docs/specs/gates/ref4_phase2_recruitment_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Target Scan

Command:

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend.app.constants|from backend.app.reference|raw config|document_reference_sync|eligibility|permit|passport|visa|residence_permit|normalize|normalization|hr_|ReferenceServiceFacade|reference_service_facade" \
  backend/app/services/recruitment_*.py backend/app/api/v1/candidates/*.py backend/app/services/lead_*.py
```

## 2. Direct-Access Findings

`Must-fix` findings (current):
1. none

`Closed in blocker-1 diff`:
1. `backend/app/api/v1/candidates/router.py:140`  
   previous direct `modules.documents` import removed; replaced with delivery-contract adapter usage (`document_hub_delivery_contract`).

`Needs review (not auto-blocker by itself)`:
1. `backend/app/api/v1/candidates/service.py:75`  
   `document_applicability_resolver` direct dependency; evaluate if this remains an allowed platform contract or should be facade-routed in P2 recruitment.
2. multiple lead-normalization helpers (`lead_rodo*`, `lead_communications*`, `normalize_*`) found in lead services; no direct evidence they bypass Phase 1 reference layer in this scan.

## 3. Allowed Baseline Hits

1. `backend/app/api/v1/candidates/helpers.py` constants imports (`catalogs`, `stages`) treated as current baseline utility usage, not direct Phase 1 reference-layer bypass in this slice scan.
2. recruitment lifecycle normalization helpers (`recruitment_application_lifecycle`) treated as domain behavior baseline.

## 4. Facade Adoption Gaps

1. Recruitment candidate router currently uses direct `modules.documents` import (cross-domain).
2. Recruitment candidate service has direct eligibility resolver dependency instead of explicit facade-level delivery contract handoff for this slice.

## 5. Target Test Pack

Command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_recruitment_*.py
```

Result:
1. `52 passed`
2. `4 failed`

Failed tests:
1. `test_assign_recruiter_unassigned_when_pool_lacks_company_scope`
2. `test_assign_recruiter_unassigned_when_outside_working_hours`
3. `test_assign_recruiter_unassigned_when_canonical_paused`
4. `test_candidate_create_unassigned_audit_payload`

Note:
1. failures unchanged after blocker-1 diff and treated as existing recruitment baseline in this slice step (no behavioral change introduced by direct-import removal).
2. failures unchanged after blocker-2 diff and treated as existing recruitment baseline (outside boundary-remediation scope).

`Closed in blocker-2 diff`:
1. `backend/app/api/v1/candidates/service.py` direct dependency on `workforce_eligibility_resolver` removed from consumer usage path;
2. service now uses `workforce_eligibility_delivery_contract` contract call.

## 6. Gate Decision

Decision: `PASS_WITH_BASELINE_NOTE`

Reason:
1. recruitment cross-domain direct-access blockers in this slice are remediated;
2. targeted test pack keeps the same `4 failed` baseline unrelated to this boundary-remediation diff-set.

Next required action:
1. keep baseline note for auto-assign failures in Phase 2 tracking;
2. continue sequence to `Workforce` slice gate.
