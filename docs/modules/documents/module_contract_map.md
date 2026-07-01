# Documents Module Contract Map

Status: baseline-established  
Date: 2026-05-29

## Inbound Contracts

From Platform:
1. `ReferenceServiceFacade` (canonical normalization and reference reads);
2. platform reference catalogs/snapshots via facade contracts;
3. integration inbound canonical payload contract (for upstream normalized inputs).

From peer module boundaries (approved contract-only):
1. `document_hub_delivery_contract.py` (read/seed/summary/checklist adapter boundary);
2. `workforce_eligibility_delivery_contract.py` (where workforce eligibility is required by consumers, not direct resolver import).

## Outbound Contracts

1. Document Hub delivery adapters (`document_hub_delivery_contract.py`) for safe cross-module document access;
2. module API contracts in documents endpoints (`candidate_documents` / document APIs);
3. owner-summary/checklist DTO projections for consumers.

## Stability Levels

Stable:
1. canonical document code exposure via delivery contract;
2. list/read summary contract calls used by HR/Recruitment/Workforce/Integrations.

Baseline/temporary:
1. `EXC-006` (`handoff_snapshot` direct CRUD import), milestone `REF-4.2`;
2. `EXC-008` (`candidate_work_panel` router-wrapper dependency), milestone `REF-4.2`;
3. `EXC-010` (`document_type_runtime_resolver` direct DB reads), milestone `REF-5`.

## Versioning Notes

1. contract compatibility follows facade/delivery backward-safe evolution;
2. any breaking change requires gate update + dependency audit update + boundary tests update.
