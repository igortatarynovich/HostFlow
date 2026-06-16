# REF-3.1 Facade Boundary Hardening Plan

Status: in progress  
Depends on: REF-3 skeleton PASS  
Purpose: enforce `ReferenceServiceFacade` as mandatory boundary (not optional helper).

## 1. Goal

Prevent contract drift and direct-reference access proliferation by introducing explicit enforcement rules and audit visibility.

## 2. Scope

In scope:
1. define forbidden access patterns;
2. define allowlist exceptions;
3. build consumer registry for reference/applicability paths;
4. define scan rules and reporting format;
5. define PASS/STOP criteria for boundary compliance.

Out of scope:
1. new runtime features;
2. new consumers;
3. catalog expansion (REF-4);
4. UI changes.

## 3. Forbidden Access Patterns

Forbidden in module/runtime paths (outside allowlist):
1. direct calls to `DocumentApplicabilityResolver` from module consumers;
2. direct calls to `DocumentTypeRuntimeResolver` from module consumers;
3. direct reads of reference tables/models for business decisioning;
4. local legacy `doc_type` mapping for applicability/metadata decisions;
5. module-local rule engines duplicating reference/applicability logic.

## 4. Allowlist Exceptions

Allowed temporary zones:
1. facade internals and resolver implementations;
2. sync/backfill/migration services;
3. explicit fallback compatibility adapters;
4. tests validating compatibility behavior.

Each allowlist entry must include:
1. owner;
2. removal milestone;
3. justification.

## 5. Consumer Registry

Registry must list:
1. current consumer path;
2. current source (`facade` vs `direct resolver` vs `table/model`);
3. risk level;
4. migration priority.

## 6. Scan Rules

Primary scans:
1. `DocumentApplicabilityResolver` direct usage;
2. `DocumentTypeRuntimeResolver` direct usage;
3. reference-model/table reads (`Ref*`, `TenantDocumentPackEnablement`, etc.);
4. legacy mapping/fallback markers (`legacy`, `fallback`, `doc_type` decision logic).

Scan output classification:
1. allowed infra;
2. temporary compatibility;
3. must-cutover consumers;
4. violations.

## 7. PASS / STOP Criteria

REF-3.1 PASS if all true:
1. plan + scan report published;
2. allowlist with owners/milestones exists;
3. must-cutover consumer shortlist exists;
4. no unresolved violations in newly touched paths.

STOP if any true:
1. new direct resolver/table usage introduced outside allowlist;
2. unknown consumer paths without classification;
3. compatibility exceptions without owner/milestone.

## 8. Deliverables

1. `ref3_1_facade_boundary_hardening_plan.md` (this file);
2. `ref3_1_facade_boundary_scan_report_YYYY-MM-DD.md`;
3. next-consumer recommendation for cutover (after classification).
