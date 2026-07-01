# Recruitment Module Ownership Card

Status: baseline-established  
Date: 2026-05-29

## Module

Name: `Recruitment`  
Owner: `Recruitment`

## Module-Owned Capabilities

1. lead intake processing;
2. candidate sourcing and intake routing;
3. recruitment stages and stage transitions (within recruitment scope);
4. recruiter assignment policies/workflows;
5. recruitment communication workflow;
6. recruitment conversion logic (lead -> candidate/recruitment application orchestration within module boundary).

## Not Owned By Recruitment (Platform/Other Domains)

1. document taxonomy/catalog semantics;
2. country/citizenship canonical catalogs;
3. legal status canonical catalogs;
4. workforce eligibility rule engine semantics;
5. HR verification policy semantics.

## Boundary Rules

1. recruitment consumes shared language via platform contracts only;
2. recruitment does not own platform reference semantics;
3. no direct imports from neighbor-module internals without approved exception.

## Current Boundary State

1. recruitment slice status: `PASS_WITH_BASELINE_NOTE` (REF-4 Phase 2);
2. documents access in candidate router remediated to delivery contract;
3. workforce eligibility dependency in candidate service remediated to delivery contract.
