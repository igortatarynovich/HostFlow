# Module Independence Program

Status: next-architecture-stage  
Date: 2026-05-29

Related:
- `docs/specs/gates/ref4_phase2_final_closeout.md`
- `docs/specs/gates/platform_ownership_map.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Goal

Prove each business module can evolve independently without:
1. breaking Platform Core boundaries;
2. coupling to neighbor module internals;
3. reintroducing direct-access anti-patterns.

## 2. Program Scope

Current modules:
1. Recruitment
2. HR
3. Documents
4. Workforce

Planned modules:
1. Billing
2. Fleet

## 3. Mandatory Artifacts Per Module

For each module, create and maintain:
1. `module_ownership_card.md` — module boundary, owner, source-of-truth zones, forbidden zones.
2. `module_contract_map.md` — inbound/outbound contracts (facade/API/event/DTO).
3. `module_dependency_audit.md` — actual code dependencies and allowed/forbidden access paths.
4. `module_test_boundary.md` — mandatory boundary tests and contract-compatibility checks.

## 4. Required Content Rules

`module_ownership_card.md` must include:
1. module name;
2. owner;
3. business capabilities;
4. source-of-truth areas;
5. explicitly out-of-scope responsibilities.

`module_contract_map.md` must include:
1. inbound contracts (from Platform / other modules);
2. outbound contracts (to Platform / other modules);
3. contract versioning policy;
4. stability level (`stable` / `experimental`).

`module_dependency_audit.md` must include:
1. direct imports inventory;
2. cross-module calls inventory;
3. exception mapping to registry IDs (if any);
4. remediation milestones for violations.

`module_test_boundary.md` must include:
1. import-boundary tests;
2. contract compatibility tests;
3. guard-scan commands;
4. PASS/STOP test criteria.

## 5. Enforcement Model

Hard rules:
1. no direct imports of other module internals;
2. no bypass of platform/reference/delivery contracts;
3. no local duplication of platform semantics without approved exception;
4. every exception must be registered with owner + milestone.

## 6. PASS/STOP Criteria

Module-level `PASS`:
1. all four artifacts exist and are current;
2. dependency audit contains no unknown blocker;
3. boundary tests are green (or baseline-noted);
4. unresolved exceptions are only approved temporary entries.

Module-level `STOP`:
1. missing artifact(s);
2. unknown direct-access path;
3. contract bypass without exception;
4. failing boundary tests without baseline decision.

## 7. Program Exit Criteria

Program `PASS` when:
1. all current modules (Recruitment/HR/Documents/Workforce) are `PASS_WITH_BASELINE_NOTE` or `PASS`;
2. baseline template pack is prepared for future modules (Billing/Fleet);
3. no new untracked cross-module dependency appears across two consecutive full scans.
