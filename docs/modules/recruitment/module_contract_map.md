# Recruitment Module Contract Map

Status: baseline-established  
Date: 2026-05-29

## Inbound Contracts (used by Recruitment)

1. `ReferenceServiceFacade` for canonical/reference reads where required by recruitment contexts;
2. `document_hub_delivery_contract.py` for cross-domain document reads/summaries;
3. `workforce_eligibility_delivery_contract.py` for eligibility decision contract calls;
4. integration canonical inbound normalization contract (`integration_inbound_normalization.py`) for external payload normalization before recruitment runtime consumption.

## Outbound Contracts (provided by Recruitment)

1. recruitment API/service DTOs for candidate/lead/recruitment workflows;
2. recruitment lifecycle/status contracts consumed by downstream modules;
3. recruitment audit/event payload contracts.

## Stability

Stable:
1. `backend/app/api/v1/candidates/router.py` -> `document_hub_delivery_contract.list_candidate_documents_via_contract`;
2. `backend/app/api/v1/candidates/service.py` -> `workforce_eligibility_delivery_contract`.

Baseline notes:
1. recruitment slice has known non-boundary baseline test failures (`4 failed`) tracked in phase-2 gate docs;
2. baseline failures are not contract-boundary regressions for this module baseline.

## Versioning / Change Control

1. contract shape changes require recruitment dependency-audit + boundary-tests update;
2. breaking changes require gate evidence and explicit baseline/exception decision.
