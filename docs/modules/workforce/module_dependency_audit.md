# Workforce Module Dependency Audit

Status: baseline-established  
Date: 2026-05-29

## Audit Scope

1. direct cross-module imports (especially documents/recruitment/hr internals);
2. direct reference internals bypass;
3. eligibility-resolver bypass from workforce consumers;
4. delivery-contract adoption in workforce consumer paths.

## Verified Boundary Outcomes (REF-4)

Closed blocker-1:
1. workforce consumer paths removed direct `modules.documents.crud` usage;
2. switched to `document_hub_delivery_contract.list_candidate_documents_via_contract(...)`.

Closed blocker-2:
1. workforce consumer paths removed direct `workforce_eligibility_resolver` consumer dependency;
2. switched to `workforce_eligibility_delivery_contract` entrypoints.

## Current Findings

Must-fix (current):
1. none in workforce slice gate scope.

Allowed baseline notes:
1. known baseline test note remains as recorded in phase-2 workforce gate/report;
2. legacy naming/comment artifacts are non-blocking where explicitly baseline-classified.

## Guard Scan Commands

```bash
cd /opt/HostFlow && rg -n \
  "from backend.app.modules.documents|documents_crud|workforce_eligibility_resolver|workforce_eligibility_delivery_contract|document_hub_delivery_contract|from backend.app.reference|reference_foundation" \
  backend/app/services/workforce_*.py backend/app/services/workforce_hr_*.py backend/app/services/hr_*.py
```

```bash
cd /opt/HostFlow && rg -n "EXC-004|EXC-007|EXC-010" docs/specs/gates/system_direct_access_exceptions_registry.md
```
