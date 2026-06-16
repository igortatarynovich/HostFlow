# REF-2 Gate Record — 2026-05-27

Decision scope: Reference Delivery Contract readiness audit before REF-3 facade implementation.
Owner: Platform Architecture
Outcome: `PASS_WITH_CONSTRAINTS` (implementation of REF-3 allowed, new runtime/consumer layers blocked)

## 1. Audit Summary

REF-2 baseline contract is documented and accepted:
- `docs/specs/reference_delivery_contract_standard.md`
- `docs/specs/architecture_gate_checklist_standard.md`

Current codebase still contains legacy + mixed consumption patterns. Therefore:
1. REF-3 (facade implementation) can start now.
2. New runtime contracts/engines/consumers beyond existing scope are blocked until REF-3/REF-4/REF-5.

## 2. Foundation Gate

1. Canonical source-of-truth exists partially: `PASS`.
- Evidence: `backend/app/services/document_type_runtime_resolver.py`
- Evidence: `backend/app/services/document_applicability_resolver.py`

2. Reference layer complete for full platform use: `NO`.
- Countries/citizenship/document-field delivery is not yet fully facade-governed.

3. Versioning strategy defined: `PASS` (contract-level).
- Evidence: `docs/specs/reference_delivery_contract_standard.md`

4. Ownership defined: `PASS_WITH_GAP`.
- Target ownership is defined, but module-level legacy paths still exist.

5. Migration path defined: `PASS_WITH_GAP`.
- Legacy fallback/backfill defined; removal milestones not consistently attached in code-level records.

6. Compatibility strategy defined: `PASS`.
- Legacy fallback explicitly present in runtime resolvers.

Foundation Gate result: `PASS_WITH_CONSTRAINTS`.

## 3. Contract Gate

1. Contract frozen: `PASS` (REF-2 baseline).
2. DTO/response model stable for current phase: `PASS`.
3. Facade exists as single read path: `NO`.
4. Direct table access forbidden in consumers: `NO` (not yet enforceable in code).
5. Override policy defined: `PASS` (spec-level).

Contract Gate result: `STOP` for any new consumer/runtime layer; `GO` only for REF-3 implementation.

## 4. Consumer Gate

### 4.1 Existing implicit contract consumers (already coupled)

1. HR review approval gate reads eligibility decision:
- `backend/app/services/workforce_hr_review.py`

2. Recruitment handoff gate reads eligibility decision:
- `backend/app/api/v1/candidates/service.py`

3. Action policy reads eligibility decision:
- `backend/app/services/workforce_action_policy.py`

4. Operational profile projects legacy summary from decision:
- `backend/app/services/workforce_operational_profile.py`

### 4.2 Assumption leakage / compatibility hotspots

1. Widespread legacy `doc_type` presence in services/tests/seeds/scanner paths.
2. Legacy bridging in HR review verification plan paths.
3. Backfill/fallback logic distributed across sync/resolvers.

Consumer Gate result: `PASS_WITH_CONSTRAINTS` (no new consumers until facade boundary enforced).

## 5. Rewrite Risk Gate

Risk: `MEDIUM-HIGH` if contract drift continues before facade.

Impacted layers if foundation changes now:
1. Recruitment handoff readiness.
2. HR approval/readiness profile.
3. Document applicability + type runtime resolution.
4. Tests around operational profile/gates.

Rollback cost: `HIGH` once more modules consume current implicit shapes.

Rewrite Risk Gate result: `PASS_WITH_CONSTRAINTS`.

## 6. Delivery Gate

1. Tests present for current M5/M4.5 runtime: `PASS`.
2. Migration strategy for canonical sync/fallback exists: `PASS`.
3. Observability present in type runtime fallback: `PASS`.
4. Deprecation/removal plan for compatibility paths: `PARTIAL`.
5. Removal owner for each compatibility path: `PARTIAL`.

Delivery Gate result: `PASS_WITH_CONSTRAINTS`.

## 7. STOP Conditions Evaluation

Triggered STOP conditions:
1. Missing facade as mandatory boundary for cross-module reference consumption.
2. Direct-table/legacy access patterns still possible.
3. Consumer logic still contains compatibility branches that can drift without centralized enforcement.

Therefore:
- `STOP` for new runtime layer expansion, new consumer onboarding, new source-of-truth changes.
- `ALLOW` only work that closes REF-3/REF-4/REF-5.

## 8. Binding Constraints (effective immediately)

1. No new runtime contracts outside reference facade track.
2. No new consumers of reference/applicability data without REF-3 facade API.
3. No new module-local rule engines.
4. Any compatibility addition must include owner + removal milestone.

## 9. Approved Next Work (only)

1. REF-3: implement `ReferenceServiceFacade` as single read boundary.
2. Add conformance tests for `ReferenceContext` and `ReferenceResponse`.
3. Add static scan guard for forbidden patterns:
- module-local blocker generation;
- direct reference table reads in module runtime flows;
- new `doc_type`-driven decision logic outside resolver/fallback/sync.
4. REF-4 catalog completion behind facade.
5. REF-5 module cutover (Recruitment/HR facade-only).

## 10. Re-open Criteria for Advanced Runtime Work

Advanced runtime work (M5+ as source of truth) is unblocked only after:
1. REF-3 gate = `PASS`.
2. REF-4 gate = `PASS`.
3. REF-5 gate = `PASS`.
4. STOP conditions are no longer triggered.
