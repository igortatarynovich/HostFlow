# HR Module Dependency Audit

Status: baseline-established  
Date: 2026-05-29

## Audit Scope

1. direct reference internals bypass;
2. cross-module internal imports;
3. contract bypass risks between HR and Recruitment/Documents/Workforce;
4. temporary exception alignment.

## Verified Boundary Outcomes

1. HR reference reads in audited slice use `ReferenceServiceFacade` in remediated paths;
2. HR document consumer access in remediated paths uses `document_hub_delivery_contract`;
3. no must-fix direct reference-layer bypass in HR slice gate (`PASS_WITH_BASELINE_NOTE`).

## Current Findings

Must-fix (current):
1. none in HR slice gate scope.

Allowed baseline notes:
1. constants import usage (`hr_task_types`) classified as allowed baseline utility in HR gate report;
2. one pre-existing HR baseline failing test remains outside boundary-remediation scope.

## Cross-Module Boundary Expectations

1. Recruitment boundary: HR consumes handoff context/contracts, does not own recruitment funnel/stages;
2. Documents boundary: HR consumes document data via delivery contract, does not own document taxonomy/files semantics;
3. Workforce boundary: HR can consume eligibility contract outputs but does not own workforce eligibility semantics;
4. Platform boundary: canonical language must come from facade contracts only.

## Guard Scan Commands

```bash
cd /opt/HostFlow && rg -n \
  "reference_foundation|from backend.app.reference|from backend.app.modules.documents|document_hub_delivery_contract|ReferenceServiceFacade|workforce_eligibility_resolver|workforce_eligibility_delivery_contract" \
  backend/app/services/hr_*.py backend/app/services/workforce_hr_*.py
```

```bash
cd /opt/HostFlow && rg -n "EXC-005|EXC-006|EXC-008|EXC-010" docs/specs/gates/system_direct_access_exceptions_registry.md
```
