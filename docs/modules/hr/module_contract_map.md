# HR Module Contract Map

Status: baseline-established  
Date: 2026-05-29

## Inbound Contracts (used by HR)

From Recruitment:
1. recruitment handoff payload/state contracts (candidate/review context handoff inputs);
2. recruitment-to-HR transition events/status context.

From Platform:
1. `ReferenceServiceFacade` for canonical language and applicability/runtime reference reads;
2. platform reference snapshots and normalization helpers (facade boundary only).

From Documents boundary:
1. `document_hub_delivery_contract.py` for document list/read/summary adapter calls.

From Workforce boundary (where needed):
1. `workforce_eligibility_delivery_contract.py` for eligibility decision contract calls (not direct resolver ownership by HR).

## Outbound Contracts (provided by HR)

To Workforce:
1. HR review outcome/verification context contracts used for downstream workforce state transitions.

To Recruitment:
1. return-to-recruitment decision/status outputs when HR rejects/returns cases.

To Platform/Audit:
1. HR decision and queue events through established event/audit contracts.

## Stability Notes

Stable:
1. HR reference interactions through `ReferenceServiceFacade`;
2. HR document interactions through delivery-contract adapter path.

Baseline notes:
1. HR slice has one known baseline failing test in phase-2 gate docs (non-boundary behavior stream).
