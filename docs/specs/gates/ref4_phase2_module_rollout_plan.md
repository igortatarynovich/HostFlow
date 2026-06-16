# REF-4 Phase 2 Module Rollout Plan

Status: draft-for-execution  
Date: 2026-05-28  
Gate dependency: `docs/specs/gates/ref4_phase2_start_gate.md`

## 1. Rollout Order

1. `HR`
2. `Recruitment`
3. `Workforce`
4. `Documents`
5. `Integrations`

Hard sequence rule:
1. next module starts only after previous module reaches `PASS` checkpoint.

## 2. Rollout Slices

### Slice-1: HR

Owner: `HR + Platform`  
Target milestone: `REF-4.P2.1`

Scope:
1. replace remaining reference reads with facade contract usage only;
2. align HR reference lookups with Phase 1 snapshots and resolvers;
3. keep runtime decisions unchanged unless explicitly routed through existing policy layers.

Enforcement checks:
1. no direct reference imports/tables/raw config access;
2. no cross-domain shortcut imports;
3. module guard tests green.

PASS criteria:
1. HR reads reference data only via facade contracts;
2. no new exception entries of `CRITICAL/HIGH` without removal milestone;
3. targeted tests + guard scan green.

STOP criteria:
1. direct import bypass appears;
2. runtime behavior rewrite mixed into rollout diff.

### Slice-2: Recruitment

Owner: `Recruitment + Platform`  
Target milestone: `REF-4.P2.2`

Scope:
1. migrate recruitment reference reads to facade contracts;
2. normalize intake/reference code handling through canonical facade path;
3. preserve workflow behavior (no rollout-coupled feature changes).

Enforcement checks:
1. no raw dictionary/seed/config usage in recruitment runtime;
2. no direct reference DB reads;
3. guard tests + contract tests green.

PASS criteria:
1. recruitment uses facade-only delivery path;
2. no unresolved boundary regressions;
3. module tests + scan checks green.

STOP criteria:
1. new direct-access exception without owner/milestone;
2. workflow behavior changes bundled with reference migration.

### Slice-3: Workforce

Owner: `Workforce + Platform`  
Target milestone: `REF-4.P2.3`

Scope:
1. adopt workforce/transport catalogs through facade snapshots/resolvers;
2. align field schema consumption with reference registry contracts;
3. keep eligibility/decision logic out of reference-layer rollout scope.

Enforcement checks:
1. no direct access to reference internals;
2. no hidden runtime scoring/decision coupling in reference diffs;
3. guard tests green.

PASS criteria:
1. workforce reference access is facade-only;
2. no cross-domain coupling regressions;
3. tests/scans green.

STOP criteria:
1. runtime decision logic introduced under reference migration;
2. reference contract bypass detected.

### Slice-4: Documents

Owner: `Documents + Platform`  
Target milestone: `REF-4.P2.4`

Scope:
1. align document metadata/reference lookups to phase-1 legal/document catalogs;
2. route rule-pack metadata consumption through foundation contracts only;
3. keep document automation behavior out of this slice.

Enforcement checks:
1. no runtime rule execution coupling through reference layer;
2. no direct legacy wrapper/table access;
3. guard tests + compatibility checks green.

PASS criteria:
1. documents module consumes reference via facade contracts;
2. no execution-engine behavior introduced;
3. targeted tests/scans green.

STOP criteria:
1. required-document decisions added through reference-layer changes;
2. legacy direct-access path reintroduced.

### Slice-5: Integrations

Owner: `Integrations + Platform`  
Target milestone: `REF-4.P2.5`

Scope:
1. migrate integration normalization to canonical reference resolvers;
2. enforce payload->canonical mapping via facade contracts;
3. keep connector behavior unchanged unless contract compatibility requires adaptation.

Enforcement checks:
1. no direct registry/config access in integrations runtime;
2. no ad-hoc mapping bypass of canonical contracts;
3. guard tests + integration contract tests green.

PASS criteria:
1. integrations consume canonical references through approved contracts;
2. no unknown direct access patterns remain;
3. tests/scans green.

STOP criteria:
1. ad-hoc mapping bypass appears;
2. rollout introduces untracked temporary exceptions.

## 3. Global Enforcement Rules

1. update `system_direct_access_exceptions_registry.md` for each accepted temporary exception;
2. every temporary exception must include owner + removal milestone + PASS condition;
3. rerun targeted guard scan after each module slice;
4. run full guard scan before Phase 2 closeout decision.

## 4. Phase 2 Exit Criteria

1. all module slices reached `PASS`;
2. no unresolved `CRITICAL` exceptions;
3. all `HIGH` exceptions either closed or time-boxed with owner/milestone;
4. full scan confirms no unknown direct access paths.

## 5. Phase 2 Closeout Invariant (mandatory)

This invariant must be copied verbatim into `ref4_phase2_final_closeout.md` before final decision:

1. no module-owned business rule may be promoted to `system/reference` layer unless it is reused by at least two independent modules or required as a cross-module contract;
2. system/reference keeps shared language and delivery contracts only;
3. module layer keeps workflow and business decision logic.
