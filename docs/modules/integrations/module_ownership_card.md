# Integrations Module Ownership Card

Status: baseline-established  
Date: 2026-05-29

## Module

Name: `Integrations`  
Owner: `Integrations`

## Module-Owned Capabilities

1. inbound adapters;
2. outbound adapters;
3. external payload mapping;
4. transport protocol handling;
5. webhook ingestion;
6. external API orchestration.

## Explicit Non-Ownership Boundaries

Integrations does not own:
1. countries canonical catalogs;
2. citizenships canonical catalogs;
3. document taxonomy semantics;
4. legal status canonical catalogs;
5. workforce eligibility semantics;
6. recruitment stage semantics;
7. HR review policy semantics.

## Critical Invariant

1. `Integrations translates external languages into the HostFlow canonical language.`
2. `Integrations does not define the HostFlow canonical language.`

## Current Boundary State

1. Integrations slice status: `PASS_WITH_BASELINE_NOTE` (REF-4 Phase 2);
2. documents direct module imports remediated to `document_hub_delivery_contract`;
3. inbound citizenship/country handling remediated via `integration_inbound_normalization.py` + `ReferenceServiceFacade`;
4. duplicate normalization surfaces remediated in intake/leads/telegram paths.
