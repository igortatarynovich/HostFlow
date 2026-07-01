# Documents Module Ownership Card

Status: baseline-established  
Date: 2026-05-29

## Module

Name: `Documents`  
Owner: `Documents + Platform (boundary)`

## Business Capabilities

1. document lifecycle for candidate/employee records;
2. checklist/status/progress aggregation for document readiness;
3. upload/order/verification support flows;
4. module-owned applicability behavior execution (runtime decisions remain in module).

## Source-of-Truth Zones

Owned by Documents module:
1. document runtime states and workflows;
2. document checklist runtime projections;
3. module-owned applicability policy behavior (`backend/app/services/document_applicability_policy.py`).

Consumed from Platform Core (not owned by module):
1. canonical document/country/citizenship language;
2. shared normalization contracts;
3. reference snapshots and cross-module boundaries.

## Forbidden Zones

1. no module-owned business rule promotion to system/reference without two-module rule or mandatory cross-module contract;
2. no direct read of platform reference internals from consumer paths;
3. no direct cross-module imports from neighbor module internals (except approved temporary exceptions in registry);
4. no local reference dictionary source-of-truth creation.

## Current Boundary State

1. canonical document type codes consumed via `document_hub_delivery_contract.py`;
2. applicability logic isolated as `MODULE_OWNED_POLICY_ISOLATED` in module policy file;
3. Documents slice status: `PASS_WITH_BASELINE_NOTE` (REF-4 Phase 2).
