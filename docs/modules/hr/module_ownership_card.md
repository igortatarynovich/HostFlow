# HR Module Ownership Card

Status: baseline-established  
Date: 2026-05-29

## Module

Name: `HR`  
Owner: `HR`

## Module-Owned Capabilities

1. HR verification process orchestration;
2. HR review decisions and review case progression;
3. HR checklist/policy execution in HR runtime context;
4. HR acceptance/rejection/return-to-recruitment operational decisions;
5. HR verification UX/task context and verification queue behavior.

## Explicit Non-Ownership Boundaries

Not owned by HR:
1. recruitment stages/funnel ownership (Recruitment owns pre-HR pipeline);
2. document taxonomy/canonical document language (Platform Reference + Document Hub own this);
3. canonical country/citizenship/legal-status catalogs (Platform Reference owns this);
4. workforce eligibility semantics and operational profile semantics (Workforce owns this);
5. document files/storage metadata lifecycle semantics (Documents/Document Hub own this).

## Hand-off Position In Flow

Data/decision flow position:
1. `Recruitment -> HR -> Workforce`;
2. HR is receiving module after recruitment and before workforce operational ownership.

## Current Boundary State

1. HR slice status: `PASS_WITH_BASELINE_NOTE` (REF-4 Phase 2);
2. HR reference reads are routed through `ReferenceServiceFacade` in remediated scope;
3. HR document access in remediated consumer paths is routed through `document_hub_delivery_contract`.
