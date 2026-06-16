# REF-4 Blocker Remediation Plan

Status: draft-for-execution  
Date: 2026-05-28  
Scope: only REF-4 entry blockers from direct-access scan

Related:
- `docs/specs/gates/system_direct_access_exceptions_registry.md`
- `docs/specs/gates/ref4_preimplementation_direct_access_scan_report.md`
- `docs/specs/gates/system_layers_information_flow_audit.md`

## 1. Scope Lock

In scope (only):
1. `EXC-003`
2. `EXC-004`
3. `EXC-007`
4. `EXC-009`

Out of scope:
1. temporary allowed exceptions (`EXC-005/006/008/010`);
2. REF-4 catalog expansion;
3. parallel cleanup/refactor beyond minimal replacement;
4. runtime module redesign.

Baseline note (fixed before EXC-003 continuation):
- `hr_operational_risk.py` contains pre-existing non-EXC-003 changes in current branch state: `recommended_action`, `by_severity`, `SEVERITY_RANK` and related logic. These are treated as pre-existing branch changes and are out of scope for EXC-003 remediation.

## 2. Blocker Plans

### EXC-003

#### Source file
- Consumer file: `backend/app/services/hr_operational_risk.py`
- Violating access: `from backend.app.constants.reference_foundation import validate_reference_code`
- Target facade: `backend/app/services/reference_service_facade.py` (facade decision/profile codes projection)

#### Minimal replacement strategy
- Было: direct import `validate_reference_code(...)` from internal reference foundation.
- Станет: facade-backed code normalization (via `ReferenceServiceFacade` contract helper/provider), no direct `reference_foundation` import in consumer.

#### Blast radius
- Level: `LOW`
- Что затрагивает: только consumer (`hr_operational_risk.py`) + import wiring.

#### Required tests
1. import boundary test: fails if `hr_operational_risk.py` imports `reference_foundation`.
2. regression test: risk rows keep same `severity`/`recommended_action` values for existing fixtures.
3. facade compatibility test: returned codes are valid within facade contract domain.

#### PASS condition
- `EXC-003`: `PASS WITH BASELINE NOTE` — direct import removed from runtime consumer; facade-only path for code normalization; pre-existing branch baseline changes remain out of scope.

---

### EXC-004

#### Source file
- Consumer file: `backend/app/services/workforce_eligibility_resolver.py`
- Violating access: `from backend.app.constants.reference_foundation import validate_reference_code`
- Target facade: `backend/app/services/reference_service_facade.py`

#### Minimal replacement strategy
- Было: direct reference validator calls for severity/domain/action/impact mapping.
- Станет: mappings resolved through facade contract/provider (facade-only normalization), no `reference_foundation` import in resolver.

#### Blast radius
- Level: `MEDIUM`
- Что затрагивает: consumer + shared resolver mapping helper used in eligibility responses.

#### Required tests
1. import boundary test: resolver cannot import `reference_foundation`.
2. regression test: allowed_operations/blocking_reasons unchanged for baseline scenarios.
3. facade compatibility test: normalized fields (`severity`, `domain`, `resolution_action`, `impact`) conform to facade taxonomy.

#### PASS condition
- `EXC-004`: resolver uses facade-only normalization path; direct import removed.

---

### EXC-007

#### Source file
- Consumer file: `backend/app/services/hr_documents_queue.py`
- Violating access: `from backend.app.modules.documents.crud import list_candidate_documents`
- Target facade: Document Hub delivery contract (service/facade read API for candidate docs)

#### Minimal replacement strategy
- Было: cross-domain direct call to `modules.documents.crud`.
- Станет: document read through canonical delivery contract (Document Hub service/facade client), no direct import from `modules.documents.*` in HR queue.

#### Blast radius
- Level: `MEDIUM`
- Что затрагивает: HR queue consumer + document read adapter contract.

#### Required tests
1. import boundary test: `hr_documents_queue.py` has no `modules.documents.crud` import.
2. regression test: missing/expiring queue output parity for same fixture tenant.
3. facade compatibility test: adapter response shape matches queue expectations (doc type/status/expiry fields).

#### PASS condition
- `EXC-007`: `PASS WITH BASELINE NOTE` when consumer-side cross-domain direct import is removed and contract path is used, while pre-existing unrelated branch changes in `hr_documents_queue.py` remain explicitly out of scope.

---

### EXC-009

#### Source file
- Consumer file: `backend/app/services/candidate_telegram_notifications.py`
- Violating access: imports from `backend.app.modules.documents.*` (`ensure_ruleset_seed`, `list_candidate_documents`, `compute_owner_summary`)
- Target facade: Document Hub delivery contract for ruleset/checklist/owner-summary read operations

#### Minimal replacement strategy
- Было: cross-domain direct imports of document internals.
- Станет: telegram notification flow reads required doc/checklist data via canonical facade/service contract; no direct `modules.documents.*` imports.

#### Blast radius
- Level: `MEDIUM`
- Что затрагивает: notification consumer + document-summary adapter calls.

#### Required tests
1. import boundary test: no `modules.documents.*` imports in `candidate_telegram_notifications.py`.
2. regression test: outgoing telegram status/doc messages unchanged for baseline cases.
3. facade compatibility test: checklist/summary payload from contract contains required fields used by notifier.

#### PASS condition
- `EXC-009`: no direct cross-domain imports; notification path uses contract-only document data access.

## 3. Implementation Order (blockers only)

1. `EXC-003`
2. `EXC-004`
3. `EXC-007`
4. `EXC-009`

Rule: do minimal delta per blocker; no unrelated code movement.

## 4. Gate Transition After Remediation

Only after all 4 blockers pass:

1. rerun guard-scan;
2. update `system_direct_access_exceptions_registry.md`;
3. update `ref4_preimplementation_direct_access_scan_report.md`;
4. move decision from `STOP` to `PASS_WITH_ENFORCEMENT`;
5. then open REF-4 implementation gate.
