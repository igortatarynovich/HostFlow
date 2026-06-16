# Workforce Module Contract Map

Status: baseline-established  
Date: 2026-05-29

## Inbound Contracts (used by Workforce)

From Platform:
1. `ReferenceServiceFacade` for canonical language, applicability reads, and runtime reference profiles;
2. reference snapshots (workforce/transport, legal/document, field schema) via facade contracts.

From HR:
1. HR verification/review outcome context contracts;
2. verified-information context used as precondition for operational eligibility decisions.

From Documents boundary:
1. `document_hub_delivery_contract.py` for document reads/summaries in workforce consumer paths.

From Workforce boundary layer:
1. `workforce_eligibility_delivery_contract.py` as service-level contract for eligibility decision access.

## Outbound Contracts (provided by Workforce)

1. workforce operational profile/status DTOs;
2. assignment readiness/eligibility outcomes for downstream consumers;
3. workforce lifecycle/operational context outputs.

## Stability Notes

Stable:
1. documents cross-domain access via `document_hub_delivery_contract`;
2. eligibility access via `workforce_eligibility_delivery_contract` in remediated consumers.

Baseline note:
1. workforce slice retained one known baseline failing test in phase-2 gate docs; boundary status remains PASS_WITH_BASELINE_NOTE.

## Invariant Link

1. verified-state ownership remains in HR;
2. operational-eligibility ownership remains in Workforce.
