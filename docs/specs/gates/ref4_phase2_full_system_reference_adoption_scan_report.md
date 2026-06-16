# REF-4 Phase 2 Full-System Reference Adoption Scan Report

Status: `PASS_WITH_BASELINE_NOTE`  
Date: 2026-05-29  
Scope: full-system reference adoption verification after Phase 2 slice rollout

Related:
- `docs/specs/gates/ref4_phase2_hr_slice_scan_report.md`
- `docs/specs/gates/ref4_phase2_recruitment_slice_scan_report.md`
- `docs/specs/gates/ref4_phase2_workforce_slice_scan_report.md`
- `docs/specs/gates/ref4_phase2_documents_slice_scan_report.md`
- `docs/specs/gates/ref4_phase2_integrations_slice_scan_report.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`
- `docs/specs/gates/ref4_enforcement_baseline_snapshot.md`

## 1. Scan Scope

Checked across `backend/app`:
1. local dictionaries and raw reference lists;
2. direct reference internals usage;
3. direct cross-module imports;
4. legacy wrappers used as runtime boundaries;
5. duplicate normalizers for reference-like fields;
6. raw country/citizenship/document handling;
7. bypass of `ReferenceServiceFacade`;
8. bypass of delivery contracts;
9. unresolved temporary exceptions: `EXC-005`, `EXC-006`, `EXC-008`, `EXC-010`.

## 2. Scan Commands

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|operational_risk_reference|workforce_operational_taxonomy|from backend\\.app\\.reference|from backend\\.app\\.constants\\.reference_foundation|from backend\\.app\\.constants\\.operational_risk_reference|from backend\\.app\\.constants\\.workforce_operational_taxonomy|from backend\\.app\\.modules\\.[a-z_]+\\.(crud|router|service)|legacy|wrapper|normalize_.*country|normalize_.*citizenship|\\.upper\\(\\).*citizenship|country_by_dial|ReferenceServiceFacade|delivery_contract|document_hub_delivery_contract|workforce_eligibility_delivery_contract" \
  backend/app docs/specs/gates --glob '!**/__pycache__/**'
```

```bash
cd /opt/HostFlow && rg -n "EXC-005|EXC-006|EXC-008|EXC-010" \
  docs/specs/gates/system_direct_access_exceptions_registry.md \
  docs/specs/gates/ref4_enforcement_baseline_snapshot.md \
  docs/specs/gates/ref4_phase2_*
```

## 3. Findings Summary

Resolved in Phase 2 rollout:
1. all five slices are `PASS_WITH_BASELINE_NOTE`;
2. integrations now use delivery-contract adapters for document hub entrypoints;
3. inbound country/citizenship normalization is consolidated through integration-level normalization helper backed by `ReferenceServiceFacade`;
4. blocker-class direct imports from `backend.app.modules.documents.*` are remediated in slice-scoped entrypoints that were gated in Phase 2.

Remaining hits are approved baseline / temporary exceptions:
1. `EXC-005`: `backend/app/services/documents.py` still reads `citizenship_rules.json` (known temporary, milestone `REF-4.1`);
2. `EXC-006`: `backend/app/services/handoff_snapshot.py` direct documents CRUD read (known temporary, milestone `REF-4.2`);
3. `EXC-008`: `backend/app/services/candidate_work_panel.py` router-helper dependency (known temporary, milestone `REF-4.2`);
4. `EXC-010`: `backend/app/services/document_type_runtime_resolver.py` direct reference-table queries (known temporary, milestone `REF-5`).

No new unknown `CRITICAL/HIGH` direct-access pattern outside registered exceptions was identified by this full-system scan.

## 4. Reference Adoption Check Against Requested Controls

1. local dictionaries: no new untracked blocker-level local reference dictionaries identified;
2. direct reference internals: controlled via existing facade path and known temporary exceptions only;
3. direct cross-module imports: remaining cases align with registered temporary exceptions;
4. legacy wrappers: remaining wrapper usage is tracked (`EXC-008`);
5. duplicate normalizers: integrations blocker closed; consolidated to integration inbound normalizer path;
6. raw country/citizenship/document handling: blocker-level intake/leads/telegram raw handling remediated; residual known behavior in `EXC-005` remains temporary;
7. facade bypass: no new untracked bypass found in remediated slices;
8. delivery-contract bypass: no new untracked bypass found in remediated slices.

## 5. Gate Decision

Decision: `PASS_WITH_BASELINE_NOTE`

Reason:
1. all Phase 2 slices reached `PASS_WITH_BASELINE_NOTE`;
2. full-system scan shows only approved baseline temporary exceptions (`EXC-005/006/008/010`);
3. no new unknown blocker-class direct-access pattern was introduced.

## 6. Baseline Notes

1. temporary exceptions remain open by design and must be remediated by their milestones:
   - `EXC-005` -> `REF-4.1`
   - `EXC-006` -> `REF-4.2`
   - `EXC-008` -> `REF-4.2`
   - `EXC-010` -> `REF-5`
2. this report does not supersede individual slice reports; it confirms aggregate adoption state.
