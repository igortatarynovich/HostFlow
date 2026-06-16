# Documents Module Dependency Audit

Status: baseline-established  
Date: 2026-05-29

## Audit Scope

1. direct reference internals usage;
2. direct cross-module imports;
3. legacy wrappers as module boundaries;
4. duplicate normalization surfaces;
5. temporary exceptions alignment with registry.

## Current Findings

Closed in REF-4 Phase 2:
1. direct `doc_types.json` local dictionary path removed from runtime consumer path;
2. raw citizenship/work_country assumptions normalized through canonical contract usage;
3. hardcoded applicability logic isolated as module-owned policy;
4. integrations paths moved from direct `backend.app.modules.documents.*` imports to `document_hub_delivery_contract.py`.

Open approved temporary exceptions:
1. `EXC-005` (`CONFIG_BYPASS`, `HIGH`, milestone `REF-4.1`) — legacy rules config in `backend/app/services/documents.py`;
2. `EXC-006` (`CROSS_DOMAIN_ACCESS`, `MEDIUM`, milestone `REF-4.2`) — `backend/app/services/handoff_snapshot.py` direct documents CRUD import;
3. `EXC-008` (`LEGACY_WRAPPER`, `MEDIUM`, milestone `REF-4.2`) — `backend/app/services/candidate_work_panel.py` router helper dependency;
4. `EXC-010` (`RAW_DB_ACCESS`, `MEDIUM`, milestone `REF-5`) — `backend/app/services/document_type_runtime_resolver.py` direct ref-table queries.

## Allowed Access Pattern

1. cross-module document access only through delivery contracts;
2. reference language access through `ReferenceServiceFacade`;
3. module-owned behavior remains in module policy/runtime layer.

## Guard Scan Commands

```bash
cd /opt/HostFlow && rg -n \
  "from backend.app.modules.documents|reference_foundation|from backend.app.reference|load_config\\(\\\"doc_types.json\\\"\\)|citizenship|work_country|legacy|wrapper|document_hub_delivery_contract|ReferenceServiceFacade" \
  backend/app/services backend/app/api/v1 backend/app/api/public
```

```bash
cd /opt/HostFlow && rg -n "EXC-005|EXC-006|EXC-008|EXC-010" \
  docs/specs/gates/system_direct_access_exceptions_registry.md
```
