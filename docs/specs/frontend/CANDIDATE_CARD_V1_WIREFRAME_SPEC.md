# CANDIDATE_CARD_V1_WIREFRAME_SPEC

Status: Deferred  
Layer: Structure (between Contract and Implementation)  
Scope: Candidate Card V1 adaptation (on hold)

## Decision Update (2026-05-29)

Candidate Card has been reclassified as:

- `Current Production Benchmark`
- `Approved Operational Baseline`

Current decision:

- Preserve current production card.
- Defer V1 adaptation until proven business need appears.

This wireframe spec is retained as a reference artifact and must not trigger implementation by itself.

Pilot status:

- `Candidate Card V1` is a pilot implementation of:
  - `ENTITY_LAYOUT_V1`
  - `OPERATIONAL_WORKSPACE_MODEL`

## Purpose

Define structural wireframe for Candidate Card V1.

This artifact is:

- not Figma,
- not visual design,
- not implementation plan.

It is a structural screen schema aligned with:

- `HOSTFLOW_UX_NORTH_STAR.md`
- `ENTITY_LAYOUT_V1_DRAFT.md`
- `ENTITY_LAYOUT_V1_IMPLEMENTATION_SCOPE.md`

This artifact is not a recruitment-only card redesign.
It is a pilot validation of HostFlow’s future UI platform model.

## Structural Wireframe (Desktop)

```text
┌──────────────────────────────────────────────────────────────────┐
│ HEADER: Candidate Name | Primary Status | Owner | Quick Actions │
├──────────────────────────────────────────────────────────────────┤
│ ABOVE-THE-FOLD DECISION SURFACE                                 │
│ [Health] [Next Action] [Blockers] [Critical Counters]           │
├──────────────────────────────────────────────────────────────────┤
│ WORKFLOW ZONE                                                    │
│ Current Stage | Workflow Timeline | SLA Warnings                │
├──────────────────────────────────────────────────────────────────┤
│ INFORMATION ZONE                                                 │
│ Core Entity Data                                                 │
├──────────────────────────────────────────────────────────────────┤
│ RELATED OBJECTS ZONE                                             │
│ Vacancy | Company | Documents | Manager | Linked Records        │
├──────────────────────────────────────────────────────────────────┤
│ ACTIVITY ZONE                                                    │
│ Timeline | Notes | Audit Events                                 │
└──────────────────────────────────────────────────────────────────┘
```

## Zone Placement Contract

1. Header
- fixed top identity/action zone.

2. Above-the-Fold Decision Surface
- mandatory immediate visibility for:
  - health,
  - next action,
  - blockers,
  - critical counters.

3. Workflow Zone
- directly below decision surface.
- must expose current stage and progression path.

4. Information Zone
- main data body.

5. Related Objects Zone
- stable, explicit linked-context zone.

6. Activity Zone
- persistent activity context (not modal-only visibility).

## Above-The-Fold Mandatory Content

Operator must see without scroll/tab/modal:

1. Context
- who/what object is,
- status,
- owner.

2. Health
- critical issues present/absent.

3. Action
- explicit next required action.

4. Counters
- missing docs,
- open tasks,
- overdue items.

## Structural Rules

1. Workflow-first ordering is mandatory.
2. P0/P1 signals must appear before dense informational sections.
3. Details must not displace decision surface above the fold.
4. Duplicate/conflicting signal blocks are forbidden.
5. Modal-only critical information is forbidden.

## Validation Checklist (Structure Approval Gate)

- Header contract present.
- Above-the-fold decision surface present.
- Workflow zone present and placed before deep data sections.
- Critical counters visible without navigation.
- Related objects explicitly grouped.
- Activity not hidden behind modal-only access.

## Next Step

After structural approval of this artifact and approval gate pass:

- pass `CANDIDATE_CARD_V1_APPROVAL_GATE.md` with final result `Approved`,
- produce `CANDIDATE_CARD_V1_IMPLEMENTATION_BACKLOG.md`

## Pilot Success Criteria (Product-Level)

Pilot is successful only if, for core operator flow, user does not need to:

- open additional tabs to find required next step,
- search where blocker reason is located,
- search where critical problem signals are located,
- leave primary card context to understand immediate operational decision.

If any of the above is required in primary flow, pilot is not passed.
