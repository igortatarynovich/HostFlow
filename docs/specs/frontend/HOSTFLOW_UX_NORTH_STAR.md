# HOSTFLOW_UX_NORTH_STAR

Status: Active guiding principle  
Scope: all operational entities and modules in HostFlow

## North Star Statement

Operator opens any working entity and in <=3 seconds understands:

1. What is happening.
2. Whether there is a critical problem.
3. What to do next.

This is a product-level success criterion, not a single-screen KPI.

## UX Mission

HostFlow must reduce time-to-correct operational decision.

## Product Framing

HostFlow UI is not only a classic CRM data interface.
It is a Decision Support System UI.

Traditional CRM focus:

- data,
- forms,
- records,
- tables.

HostFlow focus:

- decisions,
- actions,
- exceptions,
- blockers.

## Applicability

This north star applies to:

- Candidate
- Employee
- Vacancy
- Company
- Fleet entities
- Compliance entities
- Documents entities
- future operational modules

## Derived Rules

## Rule 1: Workflow Beats Data

When there is a conflict between:

- showing additional data,
- showing next required action,

next required action wins.

## Rule 2: Signals Beat Navigation

If operator must:

- open a tab,
- expand a section,
- open a modal,

to see a P0/P1 problem, interface is defective.

Critical signals must be visible immediately.

## Rule 3: Summary Beats Details

Card must answer first:

- state,
- risks,
- actions.

Only after that: detailed data.

## Rule 4: Decision Surfaces First

Before designing tables, tabs, or sections, define first:

- what decisions operator makes,
- what signals are required for those decisions,
- what actions must be immediately available.

Only then define screen structure.

## Design-System Implication

Operational decision speed is the primary UX quality axis.

Therefore:

- visual consistency is necessary but secondary,
- operational clarity and action guidance are canonical gates.

Operational target shift:

- from \"What do we know?\"
- to \"What should we do next?\"

## Current Baseline Decision (2026-05-29)

Candidate Card decision:

- Status: `Current Production Benchmark`
- Status: `Approved Operational Baseline`
- Decision: `Preserve`
- `Candidate Card V1 Adaptation`: `Deferred`
- Reason: `No proven business need`

Implication:

- Candidate Card remains baseline for comparison and audit,
- component canon (`TABLE_V1`, `ENTITY_LAYOUT_V1`, `FILTER_BAR_V1`, etc.) is validated primarily through other cards with proven gaps,
- Candidate Card redesign is reopened only with validated production pain or measurable business upside.
