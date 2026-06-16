# ENTITY_LAYOUT_V1_IMPLEMENTATION_SCOPE

Status: Draft Scope  
Layer: Canonical-to-Implementation Bridge (Scope only, not backlog)  
Source: `ENTITY_LAYOUT_V1_CONTRACT_VALIDATION.md` (`detail_candidate_card` = Major Gaps)

North star reference:

- `HOSTFLOW_UX_NORTH_STAR.md`

## 1. Architectural Decision

Direct migration of other entity cards to current `detail_candidate_card` is forbidden.

Allowed migration path:

`detail_candidate_card`

-> `ENTITY_LAYOUT_V1 Adaptation`

-> `ENTITY_LAYOUT_V1 (contract-compliant)`

-> `Migration of other entity cards`

Rationale:

- Candidate card is best current screen, but not contract-compliant.
- Direct replication would propagate current limitations system-wide.

## 2. Scope Intent

This document defines **what must change** for contract compliance.

This document does not define:

- implementation tasks,
- engineering estimates,
- sprint assignments.

## 3. Scope Priorities

## P0 — Canonical Blocking Gaps

Must be resolved before `ENTITY_LAYOUT_V1` lock.

1. Workflow Zone Canonicalization
- Establish a single explicit workflow surface with:
  - next action,
  - current stage,
  - blockers,
  - SLA warning.

2. Health Summary Canonicalization
- Add explicit health summary visible above the fold.
- Must include critical issues and blocker presence state.

3. Critical Counters Above The Fold
- Add canonical critical counters strip (minimum):
  - missing documents,
  - open tasks,
  - overdue items.

4. Signal Priority Enforcement
- Enforce P0/P1 prominence and suppress P2/P3 competition in primary view.

5. Workflow-First Pass Condition
- Operator must answer within <=3 seconds:
  1. what is happening,
  2. whether critical problem exists,
  3. what to do next.

## P1 — High-Impact Improvements

Substantially improves operator performance after P0.

1. Summary Zone Consolidation
- Merge distributed status/risk/next-action cues into one coherent summary contract.

2. Related Objects Normalization
- Consolidate linked entity context in stable canonical location and hierarchy.

3. Activity Surface Improvement
- Add persistent compact activity context (not only modal access).

## P2 — Quality/Polish Improvements

Post-canonical refinements.

1. Visual consistency tuning across card zones.
2. Information density optimization for high-frequency operations.
3. Navigation friction reduction (micro-interaction and scan-path tuning).

## 4. Acceptance KPI (Operational)

`ENTITY_LAYOUT_V1` acceptance is operational, not decorative.

Mandatory KPI:

- In <=3 seconds, operator identifies:
  1. current object state,
  2. critical problem presence,
  3. next required action.

Gate rule:

- If KPI fails, card is not canonical-compliant.
- This KPI is the runtime gate implementation of `HOSTFLOW_UX_NORTH_STAR.md`.

## 5. Exit Criteria for Scope Completion

Scope is considered complete when:

1. All P0 gaps are explicitly mapped to contract clauses.
2. P1/P2 boundaries are agreed and do not leak into P0.
3. Acceptance KPI is approved as canonical gate.
4. Structural wireframe is approved (`CANDIDATE_CARD_V1_WIREFRAME_SPEC.md`).
5. Scope is approved before any implementation backlog decomposition.
