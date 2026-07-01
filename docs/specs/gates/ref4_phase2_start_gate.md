# REF-4 Phase 2 Start Gate

Status: start-gate (pre-implementation)  
Date: 2026-05-28  
Dependency: `REF4_PHASE1_PLATFORM_REFERENCE_BASELINE_PASS`

Related:
- `docs/specs/gates/ref4_phase1_final_closeout.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`
- `docs/specs/gates/ref4_preimplementation_direct_access_scan_report.md`

## 1. Phase 2 Objective

Enable controlled runtime adoption of the established platform reference layer from Phase 1 without breaking platform boundaries.

## 2. Allowed Scope

1. consumer rollout planning per module (`HR`, `Recruitment`, `Workforce`, `Documents`, `Integrations`);
2. facade adoption sequencing and dependency map;
3. compatibility strategy for existing runtime paths;
4. migration rollout strategy for consumers (no direct reference access);
5. enforcement expansion for rollout checkpoints.

## 3. Blocked Scope

1. direct access reintroduction to internal reference registries/tables/config;
2. bypassing facade contracts in runtime modules;
3. untracked temporary exceptions without owner + milestone;
4. UI-driven architectural shortcuts;
5. mixed rollout without module-level gate evidence.

## 4. Required Entry Checks

1. Phase 1 closeout decision recorded (`PASS`);
2. blocker registry baseline remains valid;
3. guard scan baseline remains green;
4. rollout work starts with module-by-module gate plan, not broad refactor.

## 5. PASS / STOP Criteria

PASS to Phase 2 execution requires:
1. explicit rollout plan with per-module ownership and milestones;
2. enforcement checks mapped to each rollout slice;
3. no unresolved critical boundary regressions.

STOP if any:
1. runtime modules attempt direct reference/config/policy access;
2. facade delivery contracts are bypassed in rollout diffs;
3. exception registry is not updated for temporary deviations.
