# Workforce Module Ownership Card

Status: baseline-established  
Date: 2026-05-29

## Module

Name: `Workforce`  
Owner: `Workforce`

## Module-Owned Capabilities

1. workforce profile ownership;
2. workforce status ownership;
3. operational readiness decisions;
4. assignment readiness decisions;
5. employment lifecycle state ownership;
6. workforce eligibility execution.

## Explicit Non-Ownership Boundaries

Workforce does not own:
1. HR review/verification decisions;
2. document taxonomy/canonical document language;
3. recruitment stages/funnel ownership;
4. citizenship canonical catalogs;
5. legal status canonical catalogs;
6. document file storage/metadata ownership semantics.

## Critical Boundary Invariant

1. `HR decides whether information is verified.`
2. `Workforce decides whether a verified person is operationally eligible.`

This invariant is mandatory and must not be collapsed in runtime flows.

## Current Boundary State

1. Workforce slice status: `PASS_WITH_BASELINE_NOTE` (REF-4 Phase 2);
2. workforce consumer paths switched from direct documents CRUD imports to delivery contracts;
3. workforce consumer paths switched from direct eligibility-resolver dependency to workforce eligibility delivery contract.
