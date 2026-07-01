# REF-3.4 Facade Rollout Closure Report — 2026-05-28

Status: PASS  
Purpose: close REF-3 rollout before opening REF-4.

## 1) Consumers Cutover to Facade (completed)

1. `backend/app/services/handoff_snapshot.py`
- expected documents read-path -> `ReferenceServiceFacade.get_applicable_documents(...)`

2. `backend/app/services/workforce_eligibility_resolver.py`
- applicability + runtime document metadata -> facade methods

3. `backend/app/services/hr_documents_queue.py`
- applicability + runtime document metadata -> facade methods

4. `backend/app/services/hr_verification_plan.py`
- applicability read-path -> facade

5. `backend/app/services/workforce_operational_profile.py`
- expected documents path -> facade applicability response

## 2) Remaining Allowlist (temporary compatibility)

Source: `scripts/architecture/reference_facade_allowlist.txt`

Remaining temporary compatibility paths:
1. `backend/app/services/hr_expected_documents_resolver.py`
2. `backend/app/services/hr_review_document_resolution.py`
3. `backend/app/services/status_transitions.py`
4. `backend/app/services/handoff_snapshot.py`
5. `backend/app/api/v1/candidates/service.py`

## 3) Allowed Direct-Access Exceptions (current)

Baseline keys (`scripts/architecture/reference_facade_boundary_baseline.txt`):
1. `DIRECT_APPLICABILITY_RESOLVER|backend/app/api/v1/candidates/service.py`
2. `DIRECT_APPLICABILITY_RESOLVER|backend/app/services/hr_expected_documents_resolver.py`
3. `DIRECT_REFERENCE_MODEL_IMPORT|backend/app/services/hr_expected_documents_resolver.py`
4. `DIRECT_TYPE_RUNTIME_RESOLVER|backend/app/services/handoff_snapshot.py`
5. `DIRECT_TYPE_RUNTIME_RESOLVER|backend/app/services/hr_review_document_resolution.py`
6. `DIRECT_TYPE_RUNTIME_RESOLVER|backend/app/services/status_transitions.py`

## 4) Updated Baseline/Allowlist (direct-access reduced)

Removed from temporary compatibility and baseline after cutovers:
1. `backend/app/services/hr_documents_queue.py`
2. `backend/app/services/hr_verification_plan.py`
3. `backend/app/services/workforce_eligibility_resolver.py`

## 5) Violations That Block REF-4

REF-4 must be STOP if any appears:
1. any new direct resolver usage outside allowlist;
2. any new direct `Ref*` model read in module consumer paths outside allowlist;
3. any new module-local `doc_type`-driven applicability/metadata decisions;
4. any compatibility path added without owner + milestone.

## 6) Enforcement State

1. Guard scan active: `scripts/architecture/check_reference_facade_boundary.py`
2. CI enforcement active: `.github/workflows/backend-ci.yml` (`REF-3.1 facade boundary guard scan` step)
3. Violation marker active on failure:
- `docs/specs/gates/ref3_1_arch_violation_marker.md`
4. Latest guard report: `docs/specs/gates/ref3_1_guard_scan_latest.md`

Current result: guard-scan PASS (no new violations vs baseline).

## 7) REF-4 Entry Decision

Decision: `ALLOW REF-4 START` with constraints.

Constraints:
1. keep facade as mandatory boundary;
2. no runtime expansion;
3. no new consumers outside facade;
4. compatibility set may only shrink, never expand without new gate record.
