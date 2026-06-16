# REF-3.1 Enforcement Baseline — 2026-05-27

Status: approved governance baseline  
Applies to: all architecture-impacting backend changes in reference/applicability paths.

## 1. Baseline Intent

Freeze facade-boundary enforcement before next consumer cutover.

This baseline is binding for REF-3 track and must be applied in CI + architectural review.

## 2. Approved Allowlist

Source of truth:
- `scripts/architecture/reference_facade_allowlist.txt`

Approved allowlist groups:
1. Core infra (permanent):
- `backend/app/services/reference_service_facade.py`
- `backend/app/services/document_applicability_resolver.py`
- `backend/app/services/document_type_runtime_resolver.py`
- `backend/app/services/document_reference_sync.py`

2. Temporary compatibility (time-bounded):
- `backend/app/services/workforce_eligibility_resolver.py`
- `backend/app/services/hr_expected_documents_resolver.py`
- `backend/app/services/hr_documents_queue.py`
- `backend/app/services/hr_verification_plan.py`
- `backend/app/services/hr_review_document_resolution.py`
- `backend/app/services/status_transitions.py`
- `backend/app/services/handoff_snapshot.py`

3. Tests:
- `backend/tests/**`

## 3. Temporary Compatibility Paths

Defined in:
- `scripts/architecture/reference_facade_allowlist.txt`
- `docs/specs/gates/ref3_1_facade_boundary_scan_report_2026-05-27.md`

Rule:
1. no new compatibility paths without owner + removal milestone;
2. no scope expansion of existing compatibility paths without architectural review.

## 4. Explicit Violations (baseline snapshot)

Source of truth:
- `scripts/architecture/reference_facade_boundary_baseline.txt`

Interpretation:
1. entries in baseline are existing debt accepted for controlled migration;
2. any new entry is an architectural violation and must fail CI.

## 5. Removal Owners and Target Milestones

1. platform-reference
- owns: resolver internals + fallback strategy
- milestone: legacy fallback reduction in REF-5+

2. platform-runtime
- owns: `workforce_eligibility_resolver.py` facade cutover
- milestone: first post-REF-4 consumer wave

3. hr-runtime
- owns: HR direct resolver/table consumers
- milestone: phased cutover after eligibility resolver migration

## 6. Forbidden Future Patterns

1. new direct calls to `DocumentApplicabilityResolver` outside allowlist;
2. new direct calls to `DocumentTypeRuntimeResolver` outside allowlist;
3. new direct `Ref*` model/table reads for module decisioning outside allowlist;
4. new local `doc_type`-driven applicability/metadata decision logic;
5. new module-local rule engines duplicating reference/applicability logic.

## 7. Hard Enforcement

1. Guard scan rule:
- `scripts/architecture/check_reference_facade_boundary.py`

2. CI check:
- `backend-ci` workflow runs guard scan.

3. Architectural violation marker:
- `docs/specs/gates/ref3_1_arch_violation_marker.md`
- generated on new violations.

4. Mandatory review trigger:
- guard scan exits non-zero with `ARCH_REVIEW_REQUIRED` on new violations.

## 8. PASS / STOP

PASS if:
1. no new violations vs baseline;
2. allowlist remains explicit and owner-bound;
3. compatibility scope does not expand without gate review.

STOP if:
1. any new violation appears;
2. new direct access added without allowlist update + approval;
3. compatibility path added without owner/milestone.
