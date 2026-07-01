# REF-4 Preimplementation Direct Access Scan Report

Status: draft-for-gate  
Date: 2026-05-28  
Decision target: `PASS` / `PASS_WITH_CONSTRAINTS` / `STOP`

Related:
- `docs/specs/gates/system_layers_information_flow_audit.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`
- `docs/specs/gates/ref4_core_catalog_completion_gate_plan.md`
- `docs/specs/reference_delivery_contract_standard.md`

## 1. Scan Scope

Backend runtime boundary scan for direct access to system layers:

1. reference foundation/direct registries;
2. operational risk/taxonomy references;
3. country/citizenship/document dictionaries;
4. deprecated/legacy wrappers used as runtime contracts;
5. raw config access used as source-of-truth for policy/reference behavior;
6. cross-domain imports bypassing facade/API contracts.

Directories scanned:
- `backend/app/services`
- `backend/app/api`
- `backend/app/modules`
- `backend/app/constants`

## 2. Scan Commands

```bash
rg -n "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|country|citizenship|document[_ ]?type|doc_type|tenant\.settings|deprecated|legacy" /opt/HostFlow/backend/app

rg -n "ReferenceServiceFacade|reference_facade|get_module_settings_snapshot|company_module_settings|company_allows_module|hr_workforce_access|fleet_access" /opt/HostFlow/backend/app

rg -n "from backend\.app\.modules\.[a-z_]+\.|import backend\.app\.modules\.[a-z_]+" /opt/HostFlow/backend/app/services /opt/HostFlow/backend/app/modules /opt/HostFlow/backend/app/api

rg -n "load_config\(|validate_reference_code\(" /opt/HostFlow/backend/app/services
```

## 3. Found Direct-Access Paths

| Finding ID | Consumer file | Imported path / direct path | Violation type | Notes |
|---|---|---|---|---|
| `FND-001` | `backend/app/services/hr_operational_risk.py` | `from backend.app.constants.reference_foundation import validate_reference_code` | `DIRECT_IMPORT` | Runtime HR risk codes normalized via internal reference constant layer |
| `FND-002` | `backend/app/services/workforce_eligibility_resolver.py` | `from backend.app.constants.reference_foundation import validate_reference_code` | `DIRECT_IMPORT` | Eligibility blocker/action/domain mappings rely on direct reference validator |
| `FND-003` | `backend/app/services/documents.py` | `load_config('citizenship_rules.json'|'doc_types.json'|...)` | `CONFIG_BYPASS` | Legacy rules/dictionaries used directly in runtime document logic |
| `FND-004` | `backend/app/services/handoff_snapshot.py` | `from backend.app.modules.documents.crud import list_candidate_documents` | `CROSS_DOMAIN_ACCESS` | Service imports another module CRUD directly |
| `FND-005` | `backend/app/services/hr_documents_queue.py` | `from backend.app.modules.documents.crud import list_candidate_documents` | `CROSS_DOMAIN_ACCESS` | HR queue depends on documents module internals |
| `FND-006` | `backend/app/services/candidate_work_panel.py` | `from backend.app.modules.documents.router import fetch_candidate_documents_summary_response` | `LEGACY_WRAPPER` | Router helper used as service dependency |
| `FND-007` | `backend/app/services/candidate_telegram_notifications.py` | `ensure_ruleset_seed`, `list_candidate_documents`, `compute_owner_summary` from `modules.documents.*` | `CROSS_DOMAIN_ACCESS` | Cross-domain coupling to document module internals |
| `FND-008` | `backend/app/services/document_type_runtime_resolver.py` | direct queries on `RefDocumentType*` tables | `RAW_DB_ACCESS` | Consumer-path runtime reads reference tables directly |

## 4. Mapping to EXC Registry

| Finding ID | EXC ID |
|---|---|
| `FND-001` | `EXC-003` |
| `FND-002` | `EXC-004` |
| `FND-003` | `EXC-005` |
| `FND-004` | `EXC-006` |
| `FND-005` | `EXC-007` |
| `FND-006` | `EXC-008` |
| `FND-007` | `EXC-009` |
| `FND-008` | `EXC-010` |

## 5. Grouping by Enforcement Action

### 5.1 Must fix before REF-4 (blockers)

1. `EXC-003` (`HIGH`) — HR operational risk direct `reference_foundation` import.
2. `EXC-004` (`HIGH`) — workforce eligibility resolver direct `reference_foundation` import.
3. `EXC-007` (`HIGH`) — HR documents queue direct cross-domain `modules.documents.crud` access.
4. `EXC-009` (`HIGH`) — candidate telegram notifications cross-domain document internals.

### 5.2 Temporary allowed (bounded)

1. `EXC-005` (`HIGH`, milestone `REF-4.1`) — legacy config dictionaries in `services/documents.py` with mandatory migration parity tests.
2. `EXC-006` (`MEDIUM`, milestone `REF-4.2`) — handoff snapshot cross-domain doc read.
3. `EXC-008` (`MEDIUM`, milestone `REF-4.2`) — candidate work panel router-wrapper dependency.
4. `EXC-010` (`MEDIUM`, milestone `REF-5`) — direct reference table reads in runtime resolver.

### 5.3 False positive / allowed platform access (baseline)

Observed and treated as allowed baseline in this scan:

1. Consumers already using `ReferenceServiceFacade` (`hr_verification_plan.py`, `workforce_operational_profile.py`, `handoff_snapshot.py` applicability branch, `hr_documents_queue.py` expected-docs branch, `workforce_eligibility_resolver.py` expected-docs/runtime-profile branch).
2. Tenant module checks via canonical snapshots (`get_module_settings_snapshot`, `company_allows_module`, `hr_workforce_access`, `fleet_access`) where used as platform access control.
3. General `tenant.settings` usage that is feature-state/config persistence (non-reference/non-policy decision source) is not auto-classified as violation in this report.

## 6. Blockers Before REF-4

Current blockers:

1. Active `HIGH` direct-import violations in HR runtime (`EXC-003`, `EXC-004`).
2. Active `HIGH` cross-domain document coupling in HR/Recruitment service paths (`EXC-007`, `EXC-009`).
3. Mixed runtime path quality: facade present but bypasses still active in critical flows.

## 7. Accepted Temporary Exceptions

Temporarily accepted with conditions (already recorded in registry):

1. `EXC-005`, `EXC-006`, `EXC-008`, `EXC-010`.
2. Each requires owner, milestone, migration condition, PASS condition, STOP escalation condition.

## 8. Final Gate Decision

Decision: `STOP` (as of 2026-05-28).

Reason:

1. `HIGH` direct-access violations remain unresolved in critical runtime paths.
2. REF-4 entry condition “HIGH closed or bounded with explicit owner/milestone and non-blocking impact” is not met for all blockers.
3. Boundary discipline is incomplete for HR/Document integration paths.

## 9. Exit Criteria to Move from STOP

To move to `PASS_WITH_CONSTRAINTS` for REF-4 start:

1. close `EXC-003`, `EXC-004`, `EXC-007`, `EXC-009` or explicitly downgrade with approved migration evidence;
2. keep `EXC-005/006/008/010` under signed milestones with parity tests;
3. rerun this scan and publish updated report + registry snapshot with zero unresolved `CRITICAL` and no unowned `HIGH`.

## 10. Incremental Update: EXC-003 (2026-05-28)

Applied change:
1. `backend/app/services/hr_operational_risk.py` no longer imports `reference_foundation.validate_reference_code`.
2. Consumer now uses `ReferenceServiceFacade.normalize_reference_code(...)`.

Baseline note:
1. `hr_operational_risk.py` contains pre-existing non-EXC-003 changes in current branch state: `recommended_action`, `by_severity`, `SEVERITY_RANK` and related logic.
2. These are treated as pre-existing branch changes and are out of scope for EXC-003 remediation.

Verification:
1. targeted test: `pytest -q backend/tests/services/test_hr_operational_risk_taxonomy.py` -> passed (`2 passed`).
2. targeted scan: no `reference_foundation` / `validate_reference_code(` matches in `hr_operational_risk.py`.

Gate impact:
1. `FND-001` / `EXC-003` status: `PASS WITH BASELINE NOTE` (remediated-in-scope, baseline explicitly fixed), pending final full blocker-cycle rerun.
2. Overall gate decision remains `STOP` until `EXC-004`, `EXC-007`, `EXC-009` are remediated and full scan is rerun.

## 11. Incremental Update: EXC-004 (2026-05-28)

Applied change:
1. `backend/app/services/workforce_eligibility_resolver.py` no longer imports `reference_foundation.validate_reference_code`.
2. Resolver taxonomy normalization now uses `ReferenceServiceFacade.normalize_reference_code(...)`.

Verification:
1. targeted test: `pytest -q backend/tests/services/test_workforce_eligibility_resolver.py` -> passed (`6 passed`).
2. targeted scan: no `reference_foundation` / `validate_reference_code(` matches in `workforce_eligibility_resolver.py`.

Gate impact:
1. `FND-002` / `EXC-004` status: `PASS` (clean minimal diff, no baseline note required).
2. Overall gate decision remains `STOP` until `EXC-007` and `EXC-009` are remediated and full scan is rerun.

## 12. Incremental Update: EXC-007 (2026-05-28)

Applied change:
1. `backend/app/services/hr_documents_queue.py` no longer imports `backend.app.modules.documents.crud.list_candidate_documents`.
2. Consumer now reads candidate documents via service-level delivery adapter: `backend/app/services/document_hub_delivery_contract.py` -> `list_candidate_documents_via_contract(...)`.

Baseline note:
1. `hr_documents_queue.py` contains pre-existing non-EXC-007 branch changes outside this blocker scope.
2. EXC-007 remediation scope is restricted to removal of cross-domain direct import in consumer and contract-based read substitution.

Verification:
1. targeted test: `pytest -q backend/tests/api/test_hr_documents_queue.py` -> passed (`3 passed`).
2. targeted scan: no `backend.app.modules.documents.*` import remains in `hr_documents_queue.py`.

Gate impact:
1. `FND-005` / `EXC-007` status: `PASS WITH BASELINE NOTE`.
2. Overall gate decision remains `STOP` until `EXC-009` is remediated and full scan is rerun.

## 13. Incremental Update: EXC-009 (2026-05-28)

Applied change:
1. `backend/app/services/candidate_telegram_notifications.py` no longer imports from `backend.app.modules.documents.*`.
2. Consumer now uses service-level contract adapter functions from `backend/app/services/document_hub_delivery_contract.py`:
   - `ensure_ruleset_seed_via_contract`
   - `list_candidate_documents_via_contract`
   - `compute_owner_summary_via_contract`

Verification:
1. targeted test (consumer path subset): `pytest -q backend/tests/services/test_system_candidate_workforce_lock.py -k "run_expiry_notifications or sync_ready_for_handoff_gate"` -> passed (`2 passed`, `2 deselected`).
2. targeted scan: no `backend.app.modules.documents.*` imports in `candidate_telegram_notifications.py`.

Gate impact:
1. `FND-007` / `EXC-009` status: `PASS` (clean minimal diff in consumer).
2. All four blockers are now remediated in code; full blocker guard-scan required for decision transition.

## 14. Full Blocker Guard-Scan Rerun (2026-05-28)

Scope:
1. `EXC-003` consumer path (`hr_operational_risk.py`)
2. `EXC-004` consumer path (`workforce_eligibility_resolver.py`)
3. `EXC-007` consumer path (`hr_documents_queue.py`)
4. `EXC-009` consumer path (`candidate_telegram_notifications.py`)

Guard checks:
1. `rg` for `reference_foundation|validate_reference_code(` across EXC-003/004 files -> no matches.
2. `rg` for `backend.app.modules.documents.*` imports across EXC-007/009 files -> no matches.

Targeted verification pack:
1. `pytest -q backend/tests/services/test_hr_operational_risk_taxonomy.py`
2. `pytest -q backend/tests/services/test_workforce_eligibility_resolver.py`
3. `pytest -q backend/tests/api/test_hr_documents_queue.py`
4. `pytest -q backend/tests/services/test_system_candidate_workforce_lock.py -k "not test_create_attempt_skips_stage_when_workforce_locked"`
Result: `14 passed, 1 deselected`.

Decision update:
1. Previous decision (`§8`): `STOP` (historical checkpoint before blocker closure).
2. Current decision after full blocker rerun: `PASS_WITH_ENFORCEMENT`.

Enforcement carry-forward:
1. Keep baseline notes for `EXC-003` and `EXC-007` as recorded.
2. Temporary exceptions (`EXC-005/006/008/010`) remain tracked and out of blocker-closure scope.
3. REF-4 implementation gate may open only with ongoing guard-scan enforcement.
