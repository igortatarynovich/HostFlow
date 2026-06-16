# Recruitment Module Dependency Audit

Status: baseline-established  
Date: 2026-05-29

## Audit Scope

1. direct cross-module imports;
2. direct reference internals bypass;
3. delivery contract bypass;
4. legacy wrappers used as boundaries;
5. unresolved exceptions relevant to recruitment paths.

## Verified Boundary Outcomes (REF-4)

1. `backend/app/api/v1/candidates/router.py`:
   - direct documents-module import removed;
   - now uses `document_hub_delivery_contract`.
2. `backend/app/api/v1/candidates/service.py`:
   - direct `workforce_eligibility_resolver` consumer dependency removed;
   - now uses `workforce_eligibility_delivery_contract`.

## Current Findings

Must-fix (current):
1. none in recruitment slice gate scope.

Baseline notes:
1. historical/legacy recruitment helper normalizers remain domain-owned behavior and are not classified as platform-boundary violations in this module baseline;
2. recruitment gate retains known test baseline unrelated to boundary-remediation diffs.

## Temporary Exceptions Linkage

Relevant registry alignment:
1. `EXC-006` (Handoff Snapshot, milestone `REF-4.2`) — recruitment+document hub boundary temporary exception (outside direct recruitment router/service blocker scope, but impacts recruitment-adjacent flows);
2. `EXC-008` (Candidate Work Panel, milestone `REF-4.2`) — recruitment+document hub wrapper dependency temporary exception.

## Guard Scan Commands

```bash
cd /opt/HostFlow && rg -n \
  "from backend.app.modules.documents|workforce_eligibility_resolver|document_hub_delivery_contract|workforce_eligibility_delivery_contract|from backend.app.reference|reference_foundation" \
  backend/app/api/v1/candidates/*.py backend/app/services/recruitment_*.py backend/app/services/lead_*.py
```

```bash
cd /opt/HostFlow && rg -n "EXC-006|EXC-008" docs/specs/gates/system_direct_access_exceptions_registry.md
```
