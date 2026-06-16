# Integrations Module Contract Map

Status: baseline-established  
Date: 2026-05-29

## Inbound Contracts (used by Integrations)

From Platform:
1. `ReferenceServiceFacade` for canonical normalization context;
2. `integration_inbound_normalization.py` for country/citizenship canonicalization boundary.

From Documents boundary:
1. `document_hub_delivery_contract.py` for document reads/summary/checklist boundary in integration entrypoints.

From module APIs:
1. typed DTO/API contracts for ingestion targets (Recruitment/HR/Workforce/Documents) after canonicalization.

## Outbound Contracts (provided by Integrations)

1. normalized inbound payload contracts to runtime modules;
2. webhook/API transport contracts to external systems;
3. integration event/audit outputs.

## Stability Notes

Stable:
1. inbound canonical normalization path via integration normalizer;
2. document hub access via delivery contract adapters.

Baseline note:
1. full integrations target pack follow-up remains documented baseline note in phase-2 gate.

## Invariant Link

1. integrations translates external language -> canonical language;
2. canonical language definition remains in Platform Core, not Integrations.
